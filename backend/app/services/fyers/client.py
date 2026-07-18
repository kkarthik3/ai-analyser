"""
FYERS REST API client wrapper.

Provides async access to FYERS REST endpoints:
  - Quotes (snapshot of current prices)
  - Market Depth (order book)
  - Historical data (OHLCV candles)
  - Option chain (strikes and their symbols)
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from fyers_apiv3 import fyersModel

from app.config import get_settings
from app.services.fyers.auth import FyersAuthService

logger = logging.getLogger(__name__)
settings = get_settings()


class FyersClient:
    """Async wrapper around the FYERS API v3 REST client."""

    def __init__(self, auth_service: FyersAuthService) -> None:
        self._auth = auth_service
        self._fyers: Optional[fyersModel.FyersModel] = None

    def _ensure_client(self) -> fyersModel.FyersModel:
        """Ensure the FYERS client is initialized with a valid token."""
        token = self._auth.formatted_token
        if not token:
            raise RuntimeError("FYERS not authenticated. Complete auth flow first.")

        # Re-create client if token changed
        if self._fyers is None:
            self._fyers = fyersModel.FyersModel(
                token=token,
                is_async=False,
                client_id=settings.fyers_app_id,
                log_path="",
            )
        return self._fyers

    async def _run_sync(self, func, *args, **kwargs) -> Any:
        """Run a synchronous FYERS SDK call in a thread pool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

    # ---- Quotes ----

    async def get_quotes(self, symbols: list[str]) -> dict[str, Any]:
        """Get current quotes for a list of symbols (max 50 per request).

        Returns:
            Dict with quote data per symbol.
        """
        client = self._ensure_client()
        data = {"symbols": ",".join(symbols)}
        response = await self._run_sync(client.quotes, data=data)
        return response

    # ---- Market Depth ----

    async def get_market_depth(self, symbol: str) -> dict[str, Any]:
        """Get market depth (order book) for a single symbol.

        Includes OHLCV data alongside bid/ask levels.
        """
        client = self._ensure_client()
        data = {"symbol": symbol, "ohlcv_flag": 1}
        response = await self._run_sync(client.depth, data=data)
        return response

    # ---- Historical Data ----

    async def get_history(
        self,
        symbol: str,
        resolution: str = "1",
        date_from: str = "",
        date_to: str = "",
    ) -> dict[str, Any]:
        """Get historical OHLCV candles.

        Args:
            symbol: FYERS symbol (e.g., "NSE:NIFTY50-INDEX")
            resolution: Candle interval ("1", "5", "15", "30", "60", "D")
            date_from: Start date "YYYY-MM-DD"
            date_to: End date "YYYY-MM-DD"
        """
        client = self._ensure_client()
        data = {
            "symbol": symbol,
            "resolution": resolution,
            "date_format": "1",
            "range_from": date_from,
            "range_to": date_to,
            "cont_flag": "1",
        }
        response = await self._run_sync(client.history, data=data)
        return response

    # ---- Option Chain ----

    async def get_option_chain(
        self,
        symbol: str,
        strike_count: int = 20,
        timestamp: str = "",
    ) -> dict[str, Any]:
        """Fetch the option chain for an underlying.

        Returns strike prices and their corresponding option symbols.

        Args:
            symbol: Underlying symbol (e.g., "NSE:NIFTY50-INDEX")
            strike_count: Number of strikes above and below ATM
            timestamp: Specific expiry timestamp (empty = nearest)
        """
        client = self._ensure_client()
        data = {
            "symbol": symbol,
            "strikecount": strike_count,
            "timestamp": timestamp,
        }
        response = await self._run_sync(client.optionchain, data=data)
        return response

    # ---- Profile & Metadata ----

    async def get_profile(self) -> dict[str, Any]:
        """Get user profile to verify authentication."""
        client = self._ensure_client()
        response = await self._run_sync(client.get_profile)
        return response

    async def get_funds(self) -> dict[str, Any]:
        """Get account fund details."""
        client = self._ensure_client()
        response = await self._run_sync(client.funds)
        return response
