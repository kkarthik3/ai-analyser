"""
Central data manager — orchestrates data flow from FYERS to storage.

Coordinates:
  1. WebSocket stream → parse → buffer → batch write to TimescaleDB
  2. REST poller → option chain → compute Greeks → batch write
  3. Real-time cache update to Redis
  4. Fan-out to downstream consumers (analytics, WebSocket broadcast)

Auth contract:
  - ``start()`` requires the auth service to already be validated.
    It does NOT call ``load_tokens()`` or ``validate_token()`` itself —
    that is the responsibility of the startup orchestrator (``dependencies.py``).
  - If the auth service invalidates the token at runtime (via callbacks),
    ``stop()`` will be called externally by the invalidation handler.
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
      1. ``start()`` — verify auth → fetch initial quotes → connect WebSocket
      2. ``run()`` — consume messages → buffer → batch write → update cache
      3. ``stop()`` — disconnect WebSocket → flush buffers → cancel tasks
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

        # Background task references for clean cancellation
        self._tasks: list[asyncio.Task] = []

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
        """Initialize and start the data pipeline.

        Requires ``auth_service.is_authenticated`` to be ``True`` before calling.
        Callers should validate the token via ``auth_service.validate_token()`` first.
        """
        if not self._auth.is_authenticated:
            logger.warning(
                "FYERS not authenticated. Data pipeline paused. "
                "Complete auth flow via /api/v1/auth/login"
            )
            return

        logger.info("Starting Data Manager...")
        self._stats["started_at"] = datetime.now(timezone.utc).isoformat()

        # Fetch initial spot prices for all watchlist symbols
        await self._fetch_initial_prices()

        # Mark as running before creating tasks
        self._is_running = True

        # Start background tasks and retain references for clean cancellation
        self._tasks = [
            asyncio.create_task(self._tick_consumer_loop(), name="tick_consumer"),
            asyncio.create_task(self._option_chain_poll_loop(), name="option_chain_poll"),
            asyncio.create_task(self._writer.flush_loop(), name="snapshot_flush"),
        ]

        # Connect WebSocket as a separate task
        symbols = select_websocket_symbols(
            underlyings=settings.all_watchlist_symbols,
            spot_prices=self._spot_prices,
            max_symbols=200,
            strikes_per_side=settings.option_chain_strike_count,
        )
        self._tasks.append(
            asyncio.create_task(self._ws.connect(symbols), name="ws_connect")
        )

        logger.info(
            "Data Manager started. Tracking %d underlyings.", len(self._spot_prices)
        )

    async def stop(self) -> None:
        """Gracefully stop the data pipeline."""
        logger.info("Stopping Data Manager...")
        self._is_running = False

        # Cancel all background tasks
        for task in self._tasks:
            if not task.done():
                task.cancel()

        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

        self._tasks.clear()

        await self._ws.disconnect()
        await self._writer.flush()
        logger.info("Data Manager stopped.")

    async def restart(self) -> None:
        """Stop (if running) then start the pipeline.

        Convenience helper used by the auth callback after a successful login.
        """
        if self._is_running:
            await self.stop()
        await self.start()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _fetch_initial_prices(self) -> None:
        """Fetch current prices for all watchlist symbols via REST."""
        try:
            symbols = settings.all_watchlist_symbols
            for i in range(0, len(symbols), 50):
                batch = symbols[i : i + 50]
                response = await self._client.get_quotes(batch)

                if response.get("s") == "ok" and "d" in response:
                    for quote in response["d"]:
                        symbol = quote.get("n", quote.get("symbol", ""))
                        v = quote.get("v", {})
                        ltp = v.get("lp")
                        if symbol and ltp:
                            self._spot_prices[symbol] = ltp
                            underlying = get_underlying_name(symbol)
                            self._spot_prices[underlying] = ltp
                            
                            # Cache the initial quotes in Redis
                            tick_data = {
                                "symbol": symbol,
                                "ltp": ltp,
                                "open": v.get("open_price"),
                                "high": v.get("high_price"),
                                "low": v.get("low_price"),
                                "close": v.get("prev_close_price") or ltp,
                                "volume": v.get("volume"),
                                "bid": v.get("bid"),
                                "ask": v.get("ask"),
                                "bid_qty": v.get("bidQuantity"),
                                "ask_qty": v.get("askQuantity"),
                                "oi": v.get("oi", 0),
                                "prev_close": v.get("prev_close_price") or ltp,
                                "timestamp": v.get("tt"),
                                "change_pct": v.get("ch"),
                                "received_at": datetime.now().isoformat(),
                            }
                            await self._cache.update_tick(symbol, tick_data)

            logger.info(
                "Fetched initial prices for %d symbols", len(self._spot_prices)
            )
        except Exception as exc:
            logger.error("Failed to fetch initial prices: %s", exc)
            self._stats["errors"] += 1

    async def _tick_consumer_loop(self) -> None:
        """Main loop: consume WebSocket messages and process them."""
        logger.info("Tick consumer loop started")

        while self._is_running:
            try:
                message = await self._ws.get_message(timeout=0.5)
                if message is None:
                    continue

                if "batch" in message:
                    for item in message["batch"]:
                        if item:
                            await self._process_tick(item)
                else:
                    await self._process_tick(message)

            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Tick consumer error: %s", exc)
                self._stats["errors"] += 1
                await asyncio.sleep(0.1)

    async def _process_tick(self, tick: dict[str, Any]) -> None:
        """Process a single parsed tick message."""
        symbol = tick.get("symbol", "")
        if not symbol:
            return

        self._stats["ticks_processed"] += 1

        ltp = tick.get("ltp")
        if ltp:
            self._spot_prices[symbol] = ltp
            underlying = get_underlying_name(symbol)
            self._spot_prices[underlying] = ltp

        await self._cache.update_tick(symbol, tick)

        now = datetime.now(timezone.utc)
        tick_record = {
            "time": now,
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
            "change_oi": 0,
            "prev_close": tick.get("prev_close"),
            "change_pct": tick.get("change_pct"),
        }
        self._writer.buffer_tick(tick_record)

        for subscriber in self._subscribers:
            try:
                if asyncio.iscoroutinefunction(subscriber):
                    await subscriber(tick)
                else:
                    subscriber(tick)
            except Exception as exc:
                logger.error("Subscriber error: %s", exc)

    async def _option_chain_poll_loop(self) -> None:
        """Periodically fetch option chain via REST and compute Greeks."""
        logger.info(
            "Option chain poller started (interval: %ds)",
            settings.option_chain_poll_interval_s,
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
            except Exception as exc:
                logger.error("Option chain poll error: %s", exc)
                self._stats["errors"] += 1
                await asyncio.sleep(5)
