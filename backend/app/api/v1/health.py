"""
Health check and system status endpoints.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from app.config import get_settings

router = APIRouter()
settings = get_settings()


@router.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "0.1.0",
        "environment": settings.app_env,
    }


@router.get("/status")
async def system_status():
    """Detailed system status including all service states."""
    # Import here to avoid circular imports at module level
    from app.dependencies import get_data_manager_instance

    dm = get_data_manager_instance()

    return {
        "status": "running" if (dm and dm.is_running) else "idle",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": {
            "data_manager": dm.stats if dm else {"status": "not_initialized"},
            "fyers_auth": "configured" if settings.fyers_app_id else "not_configured",
            "groq": "configured" if settings.groq_api_key else "not_configured",
            "redis": "configured",
            "database": "configured",
        },
        "config": {
            "watchlist_indices": settings.watchlist_indices_list,
            "watchlist_stocks": settings.watchlist_stocks_list,
            "option_chain_strikes": settings.option_chain_strike_count,
        },
    }
