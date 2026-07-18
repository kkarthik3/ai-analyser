"""
FastAPI application factory.

Creates the main FastAPI app with:
  - CORS middleware
  - Lifespan management (startup/shutdown)
  - API router mounting
  - WebSocket endpoint registration
  - Structured logging
"""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.api.v1.ws import router as ws_router
from app.config import get_settings
from app.dependencies import initialize_services, shutdown_services, start_data_pipeline

settings = get_settings()


def configure_logging() -> None:
    """Configure structured logging with structlog."""
    log_level = getattr(logging, settings.app_log_level.upper(), logging.INFO)

    logging.basicConfig(
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        level=log_level,
        stream=sys.stdout,
    )

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.dev.ConsoleRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager.

    Startup:
      1. Initialize all services (Redis, FYERS, etc.)
      2. Start data pipeline (WebSocket stream, option chain poller)

    Shutdown:
      1. Stop data pipeline
      2. Close connections
    """
    logger = logging.getLogger(__name__)

    # ---- Startup ----
    logger.info("=" * 60)
    logger.info("AI-Bot Options Intelligence Platform starting...")
    logger.info(f"Environment: {settings.app_env}")
    logger.info("=" * 60)

    await initialize_services()
    await start_data_pipeline()

    logger.info("Application ready!")

    yield

    # ---- Shutdown ----
    logger.info("Application shutting down...")
    await shutdown_services()
    logger.info("Goodbye!")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    configure_logging()

    app = FastAPI(
        title="AI-Bot Options Intelligence Platform",
        description=(
            "Production-grade AI-powered platform for Indian options market "
            "analysis, featuring real-time data streaming, 300+ feature engineering, "
            "multi-dimensional scoring, and AI-powered explanations."
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ---- CORS ----
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ---- Routers ----
    app.include_router(api_router)
    app.include_router(ws_router)

    return app


# Application instance
app = create_app()
