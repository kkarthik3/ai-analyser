"""
Dependency injection module.

Provides singleton instances of core services, initialized at app startup.
FastAPI's Depends() system is used for request-scoped dependencies (sessions),
while service singletons are module-level for long-lived components.

Startup sequence:
  1. initialize_services() — create all service objects, load Redis token
  2. start_data_pipeline() — validate token with FYERS; start DataManager only
     if validation succeeds; otherwise wait for OAuth login
"""

from __future__ import annotations

import logging
from typing import Optional

from app.services.cache.market_cache import MarketCache
from app.services.fyers.auth import FyersAuthService
from app.services.fyers.client import FyersClient
from app.services.fyers.websocket import FyersWebSocketManager
from app.services.ingestion.data_manager import DataManager
from app.services.ingestion.option_chain_fetcher import OptionChainFetcher
from app.services.ingestion.snapshot_writer import SnapshotWriter

logger = logging.getLogger(__name__)

# Singleton service instances (initialized at app startup)
_auth_service: Optional[FyersAuthService] = None
_fyers_client: Optional[FyersClient] = None
_ws_manager: Optional[FyersWebSocketManager] = None
_snapshot_writer: Optional[SnapshotWriter] = None
_chain_fetcher: Optional[OptionChainFetcher] = None
_data_manager: Optional[DataManager] = None
_market_cache: Optional[MarketCache] = None
_metrics_publisher = None
_compute_engine = None


async def _handle_auth_failure(reason: str = "Auth error") -> None:
    """Central handler called AFTER mark_token_invalid() has already fired.

    This function is registered as an ``on_invalid`` callback on the auth service
    and is therefore invoked INSIDE ``mark_token_invalid()``.  Do NOT call
    ``mark_token_invalid()`` here — that would create a recursive loop.

    Responsibilities:
      - Invalidate the cached FyersModel SDK instance in FyersClient
      - Stop the DataManager (REST polling + WebSocket + snapshot writer)
    """
    logger.warning("Authentication failure handler triggered: %s", reason)

    if _fyers_client:
        _fyers_client.invalidate()

    if _data_manager and _data_manager.is_running:
        logger.info("Stopping Data Manager due to auth failure")
        await _data_manager.stop()

    logger.info("System halted — waiting for new OAuth login via /api/v1/auth/login")


async def initialize_services() -> None:
    """Initialize all service singletons. Called at app startup.

    Loads the stored token from Redis but does NOT validate it.
    Validation happens in ``start_data_pipeline()``.
    """
    global _auth_service, _fyers_client, _ws_manager
    global _snapshot_writer, _chain_fetcher, _data_manager, _market_cache
    global _metrics_publisher, _compute_engine

    logger.info("Initializing services...")

    # Redis + Cache
    from app.services.cache.redis_client import get_redis
    redis = await get_redis()
    _market_cache = MarketCache(redis)

    # FYERS Auth — load token from Redis (not yet validated)
    _auth_service = FyersAuthService(redis_client=redis)
    await _auth_service.load_tokens()

    # Register the central auth-failure callback so the auth service
    # can notify everything when mark_token_invalid() is called
    _auth_service.register_on_invalid(_handle_auth_failure)

    # FYERS Client
    _fyers_client = FyersClient(auth_service=_auth_service)

    # WebSocket Manager — wire the auth-error callback
    _ws_manager = FyersWebSocketManager(
        auth_service=_auth_service,
        on_auth_error=_handle_auth_failure,
    )

    # Snapshot Writer
    _snapshot_writer = SnapshotWriter(flush_interval_ms=500, max_buffer_size=5000)

    # Option Chain Fetcher
    _chain_fetcher = OptionChainFetcher(
        fyers_client=_fyers_client,
        snapshot_writer=_snapshot_writer,
    )

    # Data Manager (central coordinator)
    _data_manager = DataManager(
        auth_service=_auth_service,
        fyers_client=_fyers_client,
        ws_manager=_ws_manager,
        snapshot_writer=_snapshot_writer,
        option_chain_fetcher=_chain_fetcher,
        market_cache=_market_cache,
    )

    # Analytics
    from app.services.analytics.metrics_publisher import MetricsPublisher
    from app.services.analytics.compute_engine import ComputeEngine
    _metrics_publisher = MetricsPublisher(market_cache=_market_cache)
    _compute_engine = ComputeEngine(market_cache=_market_cache, publisher=_metrics_publisher)

    logger.info("All services initialized")


async def start_data_pipeline() -> None:
    """Validate the stored token, then start the data pipeline if valid.

    Flow:
        load_tokens()  (done in initialize_services)
            ↓
        validate_token()  ← live FYERS API call
            ├── valid   → start DataManager → connect WebSocket
            └── invalid → clear Redis token → log + wait for login
    """
    if not _auth_service or not _data_manager:
        logger.error("Services not initialized — cannot start pipeline")
        return

    if not _auth_service.access_token:
        logger.info(
            "No access token available. "
            "Waiting for OAuth login via /api/v1/auth/login"
        )
        return

    logger.info("Validating token before starting data pipeline...")
    is_valid = await _auth_service.validate_token()

    if is_valid:
        logger.info("Token validation successful — starting data pipeline")
        await _data_manager.start()
    else:
        logger.warning(
            "Token validation failed — data pipeline NOT started. "
            "Waiting for OAuth login via /api/v1/auth/login"
        )


async def restart_data_pipeline() -> None:
    """Restart the data pipeline after a successful OAuth login.

    Validates the freshly obtained token, then calls DataManager.restart().
    Called by the auth callback endpoint after ``exchange_auth_code()``.
    """
    if not _auth_service or not _data_manager:
        logger.error("Services not initialized — cannot restart pipeline")
        return

    logger.info("Validating new token before restarting data pipeline...")
    is_valid = await _auth_service.validate_token()

    if is_valid:
        logger.info("Authentication completed — restarting data pipeline")
        await _data_manager.restart()
        logger.info("WebSocket reconnected. System operational.")
    else:
        logger.error(
            "New token failed validation — data pipeline NOT started. "
            "Check FYERS credentials and try again."
        )


async def shutdown_services() -> None:
    """Gracefully shut down all services. Called at app shutdown."""
    logger.info("Shutting down services...")

    if _data_manager:
        await _data_manager.stop()

    from app.services.cache.redis_client import close_redis
    await close_redis()

    logger.info("All services shut down")


# ---- Accessor functions for route handlers ----

def get_auth_service_instance() -> FyersAuthService:
    if not _auth_service:
        raise RuntimeError("Auth service not initialized")
    return _auth_service


def get_fyers_client_instance() -> FyersClient:
    if not _fyers_client:
        raise RuntimeError("FYERS client not initialized")
    return _fyers_client


def get_data_manager_instance() -> Optional[DataManager]:
    return _data_manager


def get_cache_instance() -> Optional[MarketCache]:
    return _market_cache


def get_compute_engine_instance():
    if not _compute_engine:
        raise RuntimeError("Compute engine not initialized")
    return _compute_engine


def get_metrics_publisher_instance():
    if not _metrics_publisher:
        raise RuntimeError("Metrics publisher not initialized")
    return _metrics_publisher
