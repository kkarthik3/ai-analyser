"""
FYERS authentication endpoints.

Provides the OAuth2 flow:
  1. GET /auth/login → returns the auth URL for the user to open
  2. GET /auth/callback → handles the redirect with auth code
  3. POST /auth/token → manually set a token
  4. GET /auth/status → check current auth state
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.dependencies import get_auth_service_instance

router = APIRouter()


class TokenInput(BaseModel):
    access_token: str
    refresh_token: str = ""


@router.get("/login")
async def get_login_url():
    """Generate the FYERS OAuth2 authorization URL.

    Open the returned URL in a browser to authorize the app.
    """
    auth = get_auth_service_instance()
    url = auth.generate_auth_url()
    return {"auth_url": url, "instructions": "Open this URL in your browser to authorize."}


@router.get("/callback")
async def auth_callback(
    auth_code: str = Query(..., alias="auth_code"),
    state: str = Query(default=""),
    s: str = Query(default="ok"),
):
    """Handle the OAuth2 callback from FYERS.

    FYERS redirects here with an auth_code parameter after user authorization.
    """
    auth = get_auth_service_instance()

    try:
        result = await auth.exchange_auth_code(auth_code)
        return {
            "status": "authenticated",
            "message": "Authentication successful! Data pipeline will start.",
            **result,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/token")
async def set_token(token_input: TokenInput):
    """Manually set the access token (for pre-authenticated sessions)."""
    auth = get_auth_service_instance()
    auth._access_token = token_input.access_token
    if token_input.refresh_token:
        auth._refresh_token = token_input.refresh_token
    await auth._save_tokens()

    return {
        "status": "token_set",
        "message": "Token has been set successfully.",
    }


@router.get("/status")
async def auth_status():
    """Check current authentication status."""
    auth = get_auth_service_instance()
    return auth.get_status()


@router.post("/refresh")
async def refresh_token():
    """Manually trigger token refresh."""
    auth = get_auth_service_instance()
    success = await auth.refresh_access_token()

    if success:
        return {"status": "refreshed", "message": "Token refreshed successfully."}
    else:
        raise HTTPException(
            status_code=400,
            detail="Token refresh failed. Re-authenticate via /auth/login.",
        )
