"""
Dependency injection module.

Provides singleton instances of core services, initialized at app startup.
FastAPI's Depends() system is used for request-scoped dependencies (sessions),
while service singletons are module-level for long-lived components.
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
_metrics_publisher: Optional[MetricsPublisher] = None
_compute_engine: Optional[ComputeEngine] = None


async def initialize_services() -> None:
    """Initialize all service singletons. Called at app startup."""
    global _auth_service, _fyers_client, _ws_manager
    global _snapshot_writer, _chain_fetcher, _data_manager, _market_cache
    global _metrics_publisher, _compute_engine

    logger.info("Initializing services...")

    # Redis + Cache
    from app.services.cache.redis_client import get_redis
    redis = await get_redis()
    _market_cache = MarketCache(redis)

    # FYERS Auth
    _auth_service = FyersAuthService(redis_client=redis)

    # FYERS Client
    _fyers_client = FyersClient(auth_service=_auth_service)

    # WebSocket Manager
    _ws_manager = FyersWebSocketManager(auth_service=_auth_service)

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

    # Publisher & Compute Engine
    from app.services.analytics.metrics_publisher import MetricsPublisher
    from app.services.analytics.compute_engine import ComputeEngine
    _metrics_publisher = MetricsPublisher(market_cache=_market_cache)
    _compute_engine = ComputeEngine(market_cache=_market_cache, publisher=_metrics_publisher)

    logger.info("All services initialized")


async def start_data_pipeline() -> None:
    """Start the data ingestion pipeline. Called after services are initialized."""
    if _data_manager:
        await _data_manager.start()


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


def get_compute_engine_instance() -> ComputeEngine:
    if not _compute_engine:
        raise RuntimeError("Compute engine not initialized")
    return _compute_engine


def get_metrics_publisher_instance() -> MetricsPublisher:
    if not _metrics_publisher:
        raise RuntimeError("Metrics publisher not initialized")
    return _metrics_publisher
