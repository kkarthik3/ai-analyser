"""
Central data manager — orchestrates data flow from FYERS to storage.

Coordinates:
  1. WebSocket stream → parse → buffer → batch write to TimescaleDB
  2. REST poller → option chain → compute Greeks → batch write
  3. Real-time cache update to Redis
  4. Fan-out to downstream consumers (analytics, WebSocket broadcast)
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from app.config import get_settings
from app.services.cache.market_cache import MarketCache
from app.services.fyers.auth import FyersAuthService
from app.services.fyers.client import FyersClient
from app.services.fyers.symbols import (
    get_underlying_name,
    select_websocket_symbols,
)
from app.services.fyers.websocket import FyersWebSocketManager
from app.services.ingestion.option_chain_fetcher import OptionChainFetcher
from app.services.ingestion.snapshot_writer import SnapshotWriter

logger = logging.getLogger(__name__)
settings = get_settings()


class DataManager:
    """Central coordinator for all market data ingestion.

    Lifecycle:
      1. start() → authenticate → fetch initial quotes → connect WebSocket
      2. run() → consume messages → buffer → batch write → update cache
      3. stop() → disconnect WebSocket → flush buffers
    """

    def __init__(
        self,
        auth_service: FyersAuthService,
        fyers_client: FyersClient,
        ws_manager: FyersWebSocketManager,
        snapshot_writer: SnapshotWriter,
        option_chain_fetcher: OptionChainFetcher,
        market_cache: MarketCache,
    ) -> None:
        self._auth = auth_service
        self._client = fyers_client
        self._ws = ws_manager
        self._writer = snapshot_writer
        self._chain_fetcher = option_chain_fetcher
        self._cache = market_cache

        self._is_running = False
        self._spot_prices: dict[str, float] = {}
        self._subscribers: list[Callable[[dict[str, Any]], Any]] = []

        # Statistics
        self._stats = {
            "ticks_processed": 0,
            "chains_fetched": 0,
            "errors": 0,
            "started_at": None,
        }

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def stats(self) -> dict:
        return {
            **self._stats,
            "ws": self._ws.stats,
            "writer": self._writer.stats,
        }

    def subscribe(self, callback: Callable[[dict[str, Any]], Any]) -> None:
        """Register a callback that receives every processed tick.

        Used by the WebSocket broadcast to push data to the frontend.
        """
        self._subscribers.append(callback)

    async def start(self) -> None:
        """Initialize and start the data pipeline."""
        logger.info("Starting Data Manager...")
        self._stats["started_at"] = datetime.now(timezone.utc).isoformat()

        # Load tokens
        await self._auth.load_tokens()

        if not self._auth.is_authenticated:
            logger.warning(
                "FYERS not authenticated. Data pipeline paused. "
                "Complete auth flow via /api/v1/auth/login"
            )
            return

        # Fetch initial spot prices for all watchlist symbols
        await self._fetch_initial_prices()

        # Start background tasks
        self._is_running = True
        asyncio.create_task(self._tick_consumer_loop())
        asyncio.create_task(self._option_chain_poll_loop())
        asyncio.create_task(self._writer.flush_loop())

        # Connect WebSocket
        symbols = select_websocket_symbols(
            underlyings=settings.all_watchlist_symbols,
            spot_prices=self._spot_prices,
            max_symbols=200,
            strikes_per_side=settings.option_chain_strike_count,
        )
        asyncio.create_task(self._ws.connect(symbols))

        logger.info(f"Data Manager started. Tracking {len(self._spot_prices)} underlyings.")

    async def stop(self) -> None:
        """Gracefully stop the data pipeline."""
        logger.info("Stopping Data Manager...")
        self._is_running = False
        await self._ws.disconnect()
        await self._writer.flush()
        logger.info("Data Manager stopped.")

    async def _fetch_initial_prices(self) -> None:
        """Fetch current prices for all watchlist symbols via REST."""
        try:
            symbols = settings.all_watchlist_symbols
            # FYERS quotes supports max 50 symbols per request
            for i in range(0, len(symbols), 50):
                batch = symbols[i : i + 50]
                response = await self._client.get_quotes(batch)

                if response.get("s") == "ok" and "d" in response:
                    for quote in response["d"]:
                        symbol = quote.get("n", quote.get("symbol", ""))
                        ltp = quote.get("v", {}).get("lp")
                        if symbol and ltp:
                            self._spot_prices[symbol] = ltp
                            underlying = get_underlying_name(symbol)
                            self._spot_prices[underlying] = ltp

            logger.info(
                f"Fetched initial prices for {len(self._spot_prices)} symbols"
            )
        except Exception as e:
            logger.error(f"Failed to fetch initial prices: {e}")
            self._stats["errors"] += 1

    async def _tick_consumer_loop(self) -> None:
        """Main loop: consume WebSocket messages and process them."""
        logger.info("Tick consumer loop started")

        while self._is_running:
            try:
                message = await self._ws.get_message(timeout=0.5)
                if message is None:
                    continue

                # Handle batch messages
                if "batch" in message:
                    for item in message["batch"]:
                        if item:
                            await self._process_tick(item)
                else:
                    await self._process_tick(message)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Tick consumer error: {e}")
                self._stats["errors"] += 1
                await asyncio.sleep(0.1)

    async def _process_tick(self, tick: dict[str, Any]) -> None:
        """Process a single parsed tick message."""
        symbol = tick.get("symbol", "")
        if not symbol:
            return

        self._stats["ticks_processed"] += 1

        # Update spot price cache
        ltp = tick.get("ltp")
        if ltp:
            self._spot_prices[symbol] = ltp
            underlying = get_underlying_name(symbol)
            self._spot_prices[underlying] = ltp

        # Update Redis cache
        await self._cache.update_tick(symbol, tick)

        # Buffer for batch DB write
        now = datetime.now(timezone.utc)
        tick_record = {
            "time": now,
            "instrument_id": 1,  # Resolved during write
            "symbol": symbol,
            "ltp": tick.get("ltp"),
            "open": tick.get("open"),
            "high": tick.get("high"),
            "low": tick.get("low"),
            "close": tick.get("close"),
            "bid": tick.get("bid"),
            "ask": tick.get("ask"),
            "bid_qty": tick.get("bid_qty"),
            "ask_qty": tick.get("ask_qty"),
            "volume": tick.get("volume"),
            "oi": tick.get("oi", 0),
            "change_oi": 0,  # Computed from delta with previous
            "prev_close": tick.get("prev_close"),
            "change_pct": tick.get("change_pct"),
        }
        self._writer.buffer_tick(tick_record)

        # Fan out to subscribers (WebSocket broadcast, etc.)
        for subscriber in self._subscribers:
            try:
                if asyncio.iscoroutinefunction(subscriber):
                    await subscriber(tick)
                else:
                    subscriber(tick)
            except Exception as e:
                logger.error(f"Subscriber error: {e}")

    async def _option_chain_poll_loop(self) -> None:
        """Periodically fetch option chain via REST and compute Greeks."""
        logger.info(
            f"Option chain poller started "
            f"(interval: {settings.option_chain_poll_interval_s}s)"
        )

        while self._is_running:
            try:
                for symbol in settings.watchlist_indices_list:
                    await self._chain_fetcher.fetch_and_process(
                        symbol, self._spot_prices.get(symbol)
                    )
                    self._stats["chains_fetched"] += 1

                await asyncio.sleep(settings.option_chain_poll_interval_s)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Option chain poll error: {e}")
                self._stats["errors"] += 1
                await asyncio.sleep(5)
