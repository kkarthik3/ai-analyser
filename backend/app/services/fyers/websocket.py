"""
FYERS WebSocket manager for real-time market data streaming.

Handles:
  - WebSocket connection lifecycle (connect, reconnect, heartbeat)
  - Symbol subscription management
  - Message routing to registered callbacks
  - Error handling and auto-reconnection
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Callable, Optional

from app.config import get_settings
from app.services.fyers.auth import FyersAuthService

logger = logging.getLogger(__name__)
settings = get_settings()


class FyersWebSocketManager:
    """Manages the FYERS Data WebSocket for real-time streaming.

    Since the FYERS SDK's WebSocket is synchronous, we run it in a
    background thread and bridge messages to asyncio via a queue.
    """

    def __init__(self, auth_service: FyersAuthService) -> None:
        self._auth = auth_service
        self._ws = None
        self._subscribed_symbols: list[str] = []
        self._callbacks: list[Callable[[dict[str, Any]], None]] = []
        self._message_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=10000)
        self._is_connected: bool = False
        self._is_running: bool = False
        self._reconnect_attempts: int = 0
        self._max_reconnect_attempts: int = 10
        self._stats = {
            "messages_received": 0,
            "last_message_time": None,
            "connect_time": None,
            "reconnect_count": 0,
        }

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    @property
    def stats(self) -> dict:
        return {**self._stats, "is_connected": self._is_connected}

    def register_callback(self, callback: Callable[[dict[str, Any]], None]) -> None:
        """Register a callback to receive parsed WebSocket messages."""
        self._callbacks.append(callback)

    async def connect(self, symbols: list[str], data_type: str = "symbolUpdate") -> None:
        """Connect to FYERS WebSocket and subscribe to symbols.

        Args:
            symbols: List of FYERS symbols to subscribe to.
            data_type: "symbolUpdate" (full) or "lite" (LTP only).
        """
        token = self._auth.formatted_token
        if not token:
            raise RuntimeError("Cannot connect WebSocket: not authenticated")

        self._subscribed_symbols = symbols
        self._is_running = True

        logger.info(
            f"Starting WebSocket connection for {len(symbols)} symbols "
            f"(mode: {data_type})"
        )

        # Run the synchronous FYERS WebSocket in a background thread
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self._start_websocket,
            token,
            symbols,
            data_type,
        )

    def _start_websocket(
        self, token: str, symbols: list[str], data_type: str
    ) -> None:
        """Start the FYERS WebSocket (runs in thread pool)."""
        try:
            from fyers_apiv3.FyersWebsocket import data_ws

            self._ws = data_ws.FyersDataSocket(
                access_token=token,
                log_path="",
                litemode=(data_type == "lite"),
                write_to_file=False,
                reconnect=True,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
                on_open=lambda: self._on_open(symbols, data_type),
            )
            self._ws.connect()

        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            self._is_connected = False

    def _on_open(self, symbols: list[str], data_type: str) -> None:
        """Called when WebSocket connection is established."""
        self._is_connected = True
        self._reconnect_attempts = 0
        self._stats["connect_time"] = datetime.now().isoformat()
        logger.info(f"WebSocket connected, subscribing to {len(symbols)} symbols")

        if self._ws:
            self._ws.subscribe(symbols=symbols, data_type=data_type)

    def _on_message(self, message: Any) -> None:
        """Called on each WebSocket message (runs in WebSocket thread)."""
        self._stats["messages_received"] += 1
        self._stats["last_message_time"] = datetime.now().isoformat()

        # Parse the message
        parsed = self._parse_message(message)
        if parsed:
            # Put into async queue for processing
            try:
                self._message_queue.put_nowait(parsed)
            except asyncio.QueueFull:
                # Drop oldest message if queue is full (backpressure)
                try:
                    self._message_queue.get_nowait()
                    self._message_queue.put_nowait(parsed)
                except asyncio.QueueEmpty:
                    pass

            # Fire callbacks
            for callback in self._callbacks:
                try:
                    callback(parsed)
                except Exception as e:
                    logger.error(f"Callback error: {e}")

    def _on_error(self, error: Any) -> None:
        """Called on WebSocket error."""
        logger.error(f"WebSocket error: {error}")

    def _on_close(self) -> None:
        """Called when WebSocket closes."""
        self._is_connected = False
        self._stats["reconnect_count"] += 1
        logger.warning("WebSocket connection closed")

    def _parse_message(self, raw_message: Any) -> Optional[dict[str, Any]]:
        """Parse a raw FYERS WebSocket message into a standardized dict.

        FYERS symbolUpdate format includes:
          - symbol, ltp, open_price, high_price, low_price, close_price,
          - vol_traded_today, last_traded_time, bid_price, ask_price,
          - bid_qty, ask_qty, oi, prev_close_price, tot_sell_qty, tot_buy_qty
        """
        if isinstance(raw_message, dict):
            return {
                "symbol": raw_message.get("symbol", ""),
                "ltp": raw_message.get("ltp"),
                "open": raw_message.get("open_price"),
                "high": raw_message.get("high_price"),
                "low": raw_message.get("low_price"),
                "close": raw_message.get("close_price") or raw_message.get("prev_close_price"),
                "volume": raw_message.get("vol_traded_today"),
                "bid": raw_message.get("bid_price"),
                "ask": raw_message.get("ask_price"),
                "bid_qty": raw_message.get("bid_qty"),
                "ask_qty": raw_message.get("ask_qty"),
                "oi": raw_message.get("oi", 0),
                "prev_close": raw_message.get("prev_close_price"),
                "timestamp": raw_message.get("last_traded_time"),
                "change_pct": raw_message.get("ch"),
                "received_at": datetime.now().isoformat(),
            }
        elif isinstance(raw_message, list):
            # Batch message — parse each item
            return {
                "batch": [self._parse_message(item) for item in raw_message if item]
            }
        return None

    async def get_message(self, timeout: float = 1.0) -> Optional[dict[str, Any]]:
        """Get the next message from the async queue.

        Used by the DataManager to consume messages asynchronously.
        """
        try:
            return await asyncio.wait_for(
                self._message_queue.get(), timeout=timeout
            )
        except asyncio.TimeoutError:
            return None

    async def update_subscription(self, symbols: list[str]) -> None:
        """Update the subscribed symbols (e.g., when ATM changes)."""
        if self._ws and self._is_connected:
            # Unsubscribe old symbols that aren't in the new list
            old_only = set(self._subscribed_symbols) - set(symbols)
            new_only = set(symbols) - set(self._subscribed_symbols)

            if old_only:
                self._ws.unsubscribe(symbols=list(old_only))
            if new_only:
                self._ws.subscribe(symbols=list(new_only), data_type="symbolUpdate")

            self._subscribed_symbols = symbols
            logger.info(
                f"Updated subscription: -{len(old_only)} +{len(new_only)} symbols"
            )

    async def disconnect(self) -> None:
        """Gracefully disconnect the WebSocket."""
        self._is_running = False
        if self._ws:
            try:
                self._ws.close_connection()
            except Exception as e:
                logger.error(f"Error closing WebSocket: {e}")
        self._is_connected = False
        logger.info("WebSocket disconnected")
