"""
FYERS OAuth2 authentication service.

Handles the complete auth lifecycle:
  1. Generate authorization URL for user login
  2. Exchange auth code for access token
  3. Validate token via a live API call (get_profile)
  4. Store / load tokens from Redis for persistence across restarts
  5. Central invalidation when FYERS rejects a token at runtime
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from fyers_apiv3 import fyersModel

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# FYERS error codes that mean the token is definitively invalid / expired
_AUTH_ERROR_CODES = {-15, -16, -99}


def _mask_token(token: str) -> str:
    """Return a safe preview of a token for logging (never log the full value)."""
    if not token:
        return "<empty>"
    return token[:20] + "..."


class FyersAuthService:
    """Manages FYERS API authentication and token lifecycle.

    Design principles:
    - ``is_authenticated`` reflects *server-confirmed* validity, not just token presence.
    - Artificial expiry timestamps are never invented; FYERS determines validity.
    - ``validate_token()`` must be called explicitly before trusting any stored token.
    - ``mark_token_invalid()`` is the single place to invalidate auth state at runtime.
    """

    def __init__(self, redis_client=None) -> None:
        self._redis = redis_client

        # In-memory token state
        self._access_token: Optional[str] = settings.fyers_access_token or None
        self._token_valid: bool = False          # requires validate_token() to become True
        self._invalidating: bool = False         # prevents concurrent invalidation storms
        self._last_validation_time: Optional[str] = None
        self._last_validation_reason: Optional[str] = None

        # Registered callbacks — called when auth becomes invalid at runtime
        self._on_invalid_callbacks: list[Callable[[], Any]] = []

        # FYERS app credentials
        self._app_id = settings.fyers_app_id
        self._secret_key = settings.fyers_secret_key
        self._redirect_uri = settings.fyers_redirect_uri

    # ------------------------------------------------------------------
    # Public properties
    # ------------------------------------------------------------------

    @property
    def access_token(self) -> Optional[str]:
        """Raw access token string (treat as opaque)."""
        return self._access_token

    @property
    def is_authenticated(self) -> bool:
        """True only when the token has been confirmed valid by FYERS."""
        return self._token_valid and bool(self._access_token)

    @property
    def formatted_token(self) -> Optional[str]:
        """Token in FYERS SDK format: ``<app_id>:<access_token>``."""
        if self._access_token:
            return f"{self._app_id}:{self._access_token}"
        return None

    # ------------------------------------------------------------------
    # Callback registration
    # ------------------------------------------------------------------

    def register_on_invalid(self, callback: Callable[[], Any]) -> None:
        """Register a callback invoked whenever the token becomes invalid.

        Used by DataManager / WebSocket to stop themselves cleanly.
        """
        self._on_invalid_callbacks.append(callback)

    # ------------------------------------------------------------------
    # OAuth flow
    # ------------------------------------------------------------------

    def generate_auth_url(self) -> str:
        """Generate the OAuth2 authorization URL for user login.

        Returns:
            URL that the user should open in a browser to authorize the app.
        """
        session = fyersModel.SessionModel(
            client_id=self._app_id,
            secret_key=self._secret_key,
            redirect_uri=self._redirect_uri,
            response_type="code",
            state="aibot_auth",
        )
        return session.generate_authcode()

    async def exchange_auth_code(self, auth_code: str) -> dict:
        """Exchange the authorization code for an access token.

        This is the **only** place where a brand-new token is created.
        After a successful exchange the token is saved to Redis; the caller
        is responsible for calling ``validate_token()`` next.

        Args:
            auth_code: The code received from the OAuth2 callback.

        Returns:
            Dict with a preview of the new token.

        Raises:
            ValueError: If FYERS rejects the auth code.
        """
        session = fyersModel.SessionModel(
            client_id=self._app_id,
            secret_key=self._secret_key,
            redirect_uri=self._redirect_uri,
            response_type="code",
            state="aibot_auth",
            grant_type="authorization_code",
        )
        session.set_token(auth_code)

        loop = asyncio.get_event_loop()
        response: dict = await loop.run_in_executor(None, session.generate_token)

        if response.get("s") == "ok" or "access_token" in response:
            self._access_token = response["access_token"]
            # Reset validity — caller must call validate_token() to confirm
            self._token_valid = False
            self._last_validation_reason = "Token exchanged — pending validation"

            await self._save_tokens()

            logger.info(
                "Auth code exchanged successfully. Token: %s",
                _mask_token(self._access_token),
            )
            return {
                "status": "token_received",
                "token_preview": _mask_token(self._access_token),
            }
        else:
            logger.error("FYERS auth code exchange failed: %s", response)
            raise ValueError(
                f"Authentication failed: {response.get('message', 'Unknown error')}"
            )

    # ------------------------------------------------------------------
    # Token validation (the critical new method)
    # ------------------------------------------------------------------

    async def validate_token(self) -> bool:
        """Validate the current access token with a live FYERS API call.

        Makes a lightweight ``get_profile`` call.  If FYERS returns ``s == "ok"``
        the token is marked valid.  If FYERS returns an auth error code the token
        is cleared from memory and Redis.

        Returns:
            True if the token is valid and usable, False otherwise.
        """
        if not self._access_token:
            logger.info("No access token present — skipping validation")
            self._token_valid = False
            self._last_validation_reason = "No token present"
            return False

        logger.info("Validating token: %s", _mask_token(self._access_token))

        try:
            # NOTE: FyersModel takes raw access_token + separate client_id.
            # Do NOT pass formatted_token (app_id:token) here — the SDK would
            # double-prefix it and produce an invalid credential.
            fyers = fyersModel.FyersModel(
                token=self._access_token,
                is_async=False,
                client_id=self._app_id,
                log_path="",
            )

            loop = asyncio.get_event_loop()
            response: dict = await loop.run_in_executor(None, fyers.get_profile)
            if response.get("s") == "ok":
                self._token_valid = True
                self._last_validation_time = datetime.now(timezone.utc).isoformat()
                self._last_validation_reason = "Token validated successfully"
                logger.info("Token validation successful")
                return True

            # Check for explicit auth error codes
            code = response.get("code")
            if code in _AUTH_ERROR_CODES:
                reason = f"FYERS rejected token (code {code}): {response.get('message', '')}"
                logger.warning("Token validation failed — %s", reason)
                await self._invalidate_internally(reason)
                return False

            # Any other non-ok response — treat as invalid to be safe
            reason = (
                f"Unexpected validation response (code {code}): "
                f"{response.get('message', response)}"
            )
            logger.warning("Token validation failed — %s", reason)
            await self._invalidate_internally(reason)
            return False

        except Exception as exc:
            reason = f"Validation error: {exc}"
            logger.error("Token validation raised exception — %s", reason)
            await self._invalidate_internally(reason)
            return False

    # ------------------------------------------------------------------
    # Runtime invalidation (called from client / websocket on auth errors)
    # ------------------------------------------------------------------

    async def mark_token_invalid(self, reason: str = "Auth error from FYERS") -> None:
        """Mark the current token as invalid and stop all dependent services.

        Call this from ``FyersClient`` or ``FyersWebSocketManager`` whenever
        FYERS returns error codes ``-15``, ``-16``, or ``-99``.

        Args:
            reason: Human-readable description of why the token was invalidated.
        """
        # Guard: only act on the first call; subsequent concurrent tasks see
        # _token_valid=False and exit immediately, preventing a callback storm.
        if not self._token_valid or self._invalidating:
            return

        self._invalidating = True
        try:
            logger.warning("Marking token invalid: %s", reason)
            await self._invalidate_internally(reason)

            # Notify all registered listeners (DataManager stop, WebSocket stop, etc.)
            for callback in self._on_invalid_callbacks:
                try:
                    result = callback()
                    if asyncio.iscoroutine(result):
                        await result
                except Exception as exc:
                    logger.error("on_invalid callback raised: %s", exc)
        finally:
            self._invalidating = False

    # ------------------------------------------------------------------
    # Redis persistence
    # ------------------------------------------------------------------

    async def _save_tokens(self) -> None:
        """Persist the current access token to Redis."""
        if not self._redis:
            return

        token_data = {
            "access_token": self._access_token,
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }
        await self._redis.set(
            "fyers:tokens",
            json.dumps(token_data),
            ex=86400,  # 24-hour TTL — tokens are valid for one trading day
        )
        logger.info("Token saved to Redis")

    async def _clear_redis_token(self) -> None:
        """Delete the stored token from Redis so it is never reused."""
        if not self._redis:
            return
        try:
            await self._redis.delete("fyers:tokens")
            logger.info("Expired/invalid token removed from Redis")
        except Exception as exc:
            logger.error("Failed to clear Redis token: %s", exc)

    async def load_tokens(self) -> bool:
        """Load token from Redis on startup.

        **Important**: Loading a token does NOT validate it.  Always call
        ``validate_token()`` after this method before starting any pipeline.

        Returns:
            True if a token string was loaded into memory.
        """
        if not self._redis:
            loaded = bool(self._access_token)
            if loaded:
                logger.info(
                    "No Redis — using env token: %s",
                    _mask_token(self._access_token or ""),
                )
            return loaded

        data = await self._redis.get("fyers:tokens")
        if data:
            token_data = json.loads(data)
            self._access_token = token_data.get("access_token")
            # Do NOT set _token_valid here — validation is an explicit step
            self._token_valid = False
            logger.info(
                "Loaded token from Redis (not yet validated): %s",
                _mask_token(self._access_token or ""),
            )
            return bool(self._access_token)

        # Nothing in Redis; check if env provided a token
        if self._access_token:
            logger.info(
                "No Redis token found — using env token: %s",
                _mask_token(self._access_token),
            )
            return True

        logger.info("No token found in Redis or environment — waiting for OAuth login")
        return False

    # ------------------------------------------------------------------
    # Status reporting
    # ------------------------------------------------------------------

    def get_status(self) -> dict:
        """Return a rich authentication status dict for the /status endpoint."""
        return {
            "authenticated": self.is_authenticated,
            "token_present": bool(self._access_token),
            "token_valid": self._token_valid,
            "token_preview": (
                _mask_token(self._access_token) if self._access_token else None
            ),
            "last_validation": self._last_validation_time,
            "reason": self._last_validation_reason,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _invalidate_internally(self, reason: str) -> None:
        """Clear in-memory validity state and remove from Redis."""
        self._token_valid = False
        self._last_validation_time = datetime.now(timezone.utc).isoformat()
        self._last_validation_reason = reason
        # Do NOT clear _access_token so get_status() can still show token_present=True
        await self._clear_redis_token()
