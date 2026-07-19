"""
FYERS REST API client wrapper.

Provides async access to FYERS REST endpoints:
  - Quotes (snapshot of current prices)
  - Market Depth (order book)
  - Historical data (OHLCV candles)
  - Option chain (strikes and their symbols)
  - Profile / Funds (used for token validation)

Token management:
  - The underlying FyersModel SDK is recreated whenever the formatted token changes.
  - Any response containing FYERS auth error codes (-15, -16, -99) triggers central
    invalidation via ``auth.mark_token_invalid()``.
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

# FYERS error codes that mean the access token has been rejected
_AUTH_ERROR_CODES = {-15, -16, -99}


class FyersClient:
    """Async wrapper around the FYERS API v3 REST client.

    Recreates the underlying SDK instance whenever the access token changes so
    that a freshly-obtained token is always picked up without a restart.
    """

    def __init__(self, auth_service: FyersAuthService) -> None:
        self._auth = auth_service
        self._fyers: Optional[fyersModel.FyersModel] = None
        self._current_token: Optional[str] = None  # raw access_token the SDK currently holds

    # ------------------------------------------------------------------
    # SDK instance management
    # ------------------------------------------------------------------

    def _ensure_client(self) -> fyersModel.FyersModel:
        """Return a FyersModel instance backed by the current access token.

        Recreates the SDK if the access token has changed since the last call.

        Token format note:
            ``FyersModel`` takes the raw ``access_token`` together with a separate
            ``client_id`` parameter.  Do NOT pass ``formatted_token`` (``app_id:token``)
            here — the SDK would double-prefix it and produce an invalid credential.
            The ``formatted_token`` format is only used by ``FyersDataSocket`` (WebSocket).

        Raises:
            RuntimeError: If there is no valid token.
        """
        raw_token = self._auth.access_token
        if not raw_token:
            raise RuntimeError(
                "FYERS not authenticated. Complete the OAuth flow via /api/v1/auth/login."
            )

        if raw_token != self._current_token:
            logger.info("Token changed — recreating FyersModel SDK instance")
            self._fyers = fyersModel.FyersModel(
                token=raw_token,
                is_async=False,
                client_id=settings.fyers_app_id,
                log_path="",
            )
            self._current_token = raw_token

        return self._fyers  # type: ignore[return-value]

    def invalidate(self) -> None:
        """Discard the cached SDK instance.

        Called after ``auth.mark_token_invalid()`` so the next request is forced
        to re-evaluate the token before touching FYERS.
        """
        self._fyers = None
        self._current_token = None
        logger.info("FyersClient SDK instance invalidated")

    # ------------------------------------------------------------------
    # Internal async runner with auth-error detection
    # ------------------------------------------------------------------

    async def _run_sync(self, func, *args, **kwargs) -> Any:
        """Run a synchronous FYERS SDK call in a thread pool.

        After the call completes, checks the response for auth error codes and
        triggers central invalidation if found.
        """
        loop = asyncio.get_event_loop()
        response: Any = await loop.run_in_executor(
            None, lambda: func(*args, **kwargs)
        )

        # Auth-error detection — only applicable when the response is a dict
        if isinstance(response, dict):
            code = response.get("code")
            if code in _AUTH_ERROR_CODES:
                reason = (
                    f"FYERS returned auth error (code {code}): "
                    f"{response.get('message', '')}"
                )
                logger.warning("Auth error detected in REST response — %s", reason)
                # Fire-and-forget; the coroutine will propagate to callbacks
                asyncio.create_task(self._auth.mark_token_invalid(reason))

        return response

    # ------------------------------------------------------------------
    # Quotes
    # ------------------------------------------------------------------

    async def get_quotes(self, symbols: list[str]) -> dict[str, Any]:
        """Get current quotes for a list of symbols (max 50 per request).

        Returns:
            Dict with quote data per symbol.
        """
        client = self._ensure_client()
        data = {"symbols": ",".join(symbols)}
        return await self._run_sync(client.quotes, data=data)

    # ------------------------------------------------------------------
    # Market Depth
    # ------------------------------------------------------------------

    async def get_market_depth(self, symbol: str) -> dict[str, Any]:
        """Get market depth (order book) for a single symbol.

        Includes OHLCV data alongside bid/ask levels.
        """
        client = self._ensure_client()
        data = {"symbol": symbol, "ohlcv_flag": 1}
        return await self._run_sync(client.depth, data=data)

    # ------------------------------------------------------------------
    # Historical Data
    # ------------------------------------------------------------------

    async def get_history(
        self,
        symbol: str,
        resolution: str = "1",
        date_from: str = "",
        date_to: str = "",
    ) -> dict[str, Any]:
        """Get historical OHLCV candles.

        Args:
            symbol: FYERS symbol (e.g., ``"NSE:NIFTY50-INDEX"``)
            resolution: Candle interval (``"1"``, ``"5"``, ``"15"``, ``"30"``, ``"60"``, ``"D"``)
            date_from: Start date ``"YYYY-MM-DD"``
            date_to: End date ``"YYYY-MM-DD"``
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
        return await self._run_sync(client.history, data=data)

    # ------------------------------------------------------------------
    # Option Chain
    # ------------------------------------------------------------------

    async def get_option_chain(
        self,
        symbol: str,
        strike_count: int = 20,
        timestamp: str = "",
    ) -> dict[str, Any]:
        """Fetch the option chain for an underlying.

        Returns strike prices and their corresponding option symbols.

        Args:
            symbol: Underlying symbol (e.g., ``"NSE:NIFTY50-INDEX"``)
            strike_count: Number of strikes above and below ATM
            timestamp: Specific expiry timestamp (empty = nearest)
        """
        client = self._ensure_client()
        data = {
            "symbol": symbol,
            "strikecount": strike_count,
            "timestamp": timestamp,
        }
        return await self._run_sync(client.optionchain, data=data)

    # ------------------------------------------------------------------
    # Profile & Metadata
    # ------------------------------------------------------------------

    async def get_profile(self) -> dict[str, Any]:
        """Get user profile (also used for token validation)."""
        client = self._ensure_client()
        return await self._run_sync(client.get_profile)

    async def get_funds(self) -> dict[str, Any]:
        """Get account fund details."""
        client = self._ensure_client()
        return await self._run_sync(client.funds)

    async def get_positions(self) -> dict[str, Any]:
        """Get current open/closed positions for the day."""
        client = self._ensure_client()
        return await self._run_sync(client.positions)

    async def get_holdings(self) -> dict[str, Any]:
        """Get long-term holdings."""
        client = self._ensure_client()
        return await self._run_sync(client.holdings)
