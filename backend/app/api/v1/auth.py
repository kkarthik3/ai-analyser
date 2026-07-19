"""
FYERS authentication endpoints.

OAuth2 flow:
  1. GET  /auth/login    → returns the FYERS authorization URL for the user to open
  2. GET  /auth/callback → handles the redirect with auth code, validates, restarts pipeline
  3. POST /auth/token    → manually set a pre-obtained access token
  4. GET  /auth/status   → returns full authentication status (validity, not just presence)
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from app.dependencies import (
    get_auth_service_instance,
    restart_data_pipeline,
)
from app.config import get_settings

router = APIRouter()
settings = get_settings()


class TokenInput(BaseModel):
    access_token: str


@router.get("/login")
async def get_login_url():
    """Generate the FYERS OAuth2 authorization URL.

    Open the returned URL in a browser to authorize the app.
    """
    auth = get_auth_service_instance()
    url = auth.generate_auth_url()
    return {
        "auth_url": url,
        "instructions": "Open this URL in your browser to authorize.",
    }


@router.get("/callback")
async def auth_callback(
    auth_code: str = Query(..., alias="auth_code"),
    state: str = Query(default=""),
    s: str = Query(default="ok"),
):
    """Handle the OAuth2 callback from FYERS.

    FYERS redirects here with an ``auth_code`` parameter after user authorization.

    Flow:
      1. Exchange the auth code for a fresh access token
      2. Validate the token with a live FYERS API call
      3. Restart the data pipeline (WebSocket + polling) if valid
      4. Redirect the user back to the frontend dashboard
    """
    auth = get_auth_service_instance()

    try:
        await auth.exchange_auth_code(auth_code)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # Validate and restart the pipeline — errors are logged but do not 500 the redirect
    await restart_data_pipeline()

    return RedirectResponse(url=settings.frontend_url)


@router.post("/token")
async def set_token(token_input: TokenInput):
    """Manually set the access token (for pre-authenticated sessions).

    After setting, the token is validated with FYERS before the pipeline is started.
    """
    auth = get_auth_service_instance()

    # Directly inject the token and persist it
    auth._access_token = token_input.access_token
    auth._token_valid = False  # Require re-validation
    await auth._save_tokens()

    # Validate + restart pipeline
    await restart_data_pipeline()

    status = auth.get_status()
    return {
        "status": "token_set",
        "authenticated": status["authenticated"],
        "token_valid": status["token_valid"],
        "reason": status["reason"],
    }


@router.get("/status")
async def auth_status():
    """Return the current authentication status.

    Reports actual server-confirmed validity, not merely token presence.

    Response fields:
      - ``authenticated``:    True only if the token has been validated by FYERS
      - ``token_present``:    True if a token string exists in memory
      - ``token_valid``:      True if the last validation call succeeded
      - ``token_preview``:    First 20 characters of the token (masked)
      - ``last_validation``:  ISO timestamp of the last validation attempt
      - ``reason``:           Human-readable description of the current auth state
    """
    auth = get_auth_service_instance()
    return auth.get_status()


@router.post("/refresh")
async def refresh_token():
    """Token refresh is no longer supported.

    FYERS discontinued refresh tokens effective April 1 2026.
    Daily manual login via ``/auth/login`` is required.
    """
    raise HTTPException(
        status_code=410,
        detail=(
            "FYERS refresh tokens have been discontinued (effective April 1, 2026). "
            "Daily manual login via /api/v1/auth/login is required."
        ),
    )
