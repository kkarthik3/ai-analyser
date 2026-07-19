"""
FYERS OAuth2 authentication service.

Handles the complete auth lifecycle:
  1. Generate authorization URL for user login
  2. Exchange auth code for access token
  3. Refresh expired tokens automatically
  4. Store/load tokens from Redis for persistence across restarts
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Optional

from fyers_apiv3 import fyersModel

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class FyersAuthService:
    """Manages FYERS API authentication and token lifecycle."""

    def __init__(self, redis_client=None) -> None:
        self._redis = redis_client
        self._access_token: Optional[str] = settings.fyers_access_token or None
        self._refresh_token: Optional[str] = settings.fyers_refresh_token or None
        self._token_expiry: Optional[datetime] = None
        self._app_id = settings.fyers_app_id
        self._secret_key = settings.fyers_secret_key
        self._redirect_uri = settings.fyers_redirect_uri

    @property
    def access_token(self) -> Optional[str]:
        """Get the current access token."""
        return self._access_token

    @property
    def is_authenticated(self) -> bool:
        """Check if we have a valid access token."""
        return bool(self._access_token)

    @property
    def formatted_token(self) -> Optional[str]:
        """Get the token formatted for FYERS API (app_id:access_token)."""
        if self._access_token:
            return f"{self._access_token}"
        return None

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

        Args:
            auth_code: The code received from the OAuth2 callback.

        Returns:
            Dict with access_token and refresh_token.
        """
        session = fyersModel.SessionModel(
            client_id=self._app_id,
            secret_key=self._secret_key,
            redirect_uri=self._redirect_uri,
            response_type="code",
            state="aibot_auth",
            grant_type="authorization_code"
        )

        print("auth_code========================================", auth_code)
        session.set_token(auth_code)

        # Run synchronous FYERS SDK call in executor
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, session.generate_token)

        if response.get("s") == "ok" or "access_token" in response:
            self._access_token = response["access_token"]
            self._refresh_token = response.get("refresh_token")
            self._token_expiry = datetime.now() + timedelta(hours=23)

            # Persist tokens to Redis
            await self._save_tokens()

            logger.info("FYERS authentication successful")
            return {
                "status": "authenticated",
                "access_token": self._access_token[:20] + "...",
                "expires_at": self._token_expiry.isoformat() if self._token_expiry else None,
            }
        else:
            logger.error(f"FYERS auth failed: {response}")
            raise ValueError(f"Authentication failed: {response.get('message', 'Unknown error')}")

    async def refresh_access_token(self) -> bool:
        """Refresh the access token using the refresh token.

        Returns:
            True if refresh was successful, False otherwise.
        """
        if not self._refresh_token:
            logger.warning("No refresh token available")
            return False

        try:
            session = fyersModel.SessionModel(
                client_id=self._app_id,
                secret_key=self._secret_key,
                redirect_uri=self._redirect_uri,
                response_type="code",
                state="aibot_auth",
            )

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: session.generate_token_with_refresh_token(
                    {"refresh_token": self._refresh_token}
                ),
            )

            if "access_token" in response:
                self._access_token = response["access_token"]
                self._token_expiry = datetime.now() + timedelta(hours=23)
                await self._save_tokens()
                logger.info("Token refreshed successfully")
                return True

        except Exception as e:
            logger.error(f"Token refresh failed: {e}")

        return False

    async def _save_tokens(self) -> None:
        """Persist tokens to Redis for survival across restarts."""
        if not self._redis:
            return

        token_data = {
            "access_token": self._access_token,
            "refresh_token": self._refresh_token,
            "expiry": self._token_expiry.isoformat() if self._token_expiry else None,
            "updated_at": datetime.now().isoformat(),
        }
        await self._redis.set(
            "fyers:tokens",
            json.dumps(token_data),
            ex=86400 * 15,  # 15-day TTL matching refresh token validity
        )

    async def load_tokens(self) -> bool:
        """Load tokens from Redis on startup.

        Returns:
            True if tokens were loaded successfully.
        """
        if not self._redis:
            return bool(self._access_token)

        data = await self._redis.get("fyers:tokens")
        if data:
            token_data = json.loads(data)
            self._access_token = token_data.get("access_token")
            self._refresh_token = token_data.get("refresh_token")
            if token_data.get("expiry"):
                self._token_expiry = datetime.fromisoformat(token_data["expiry"])
            logger.info("Loaded tokens from Redis")
            return True
        return bool(self._access_token)

    def get_status(self) -> dict:
        """Get current authentication status."""
        return {
            "authenticated": self.is_authenticated,
            "token_preview": (
                self._access_token[:20] + "..." if self._access_token else None
            ),
            "expires_at": self._token_expiry.isoformat() if self._token_expiry else None,
            "has_refresh_token": bool(self._refresh_token),
        }
