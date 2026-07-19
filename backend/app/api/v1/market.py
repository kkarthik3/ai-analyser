"""
Market data API endpoints.

Provides REST access to:
  - Latest ticks for watchlist symbols
  - Current option chain with Greeks
  - Historical OHLCV data
  - Computed metrics and scores
"""

from __future__ import annotations

from datetime import datetime, date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_session
from app.db.repositories.tick_repo import TickRepository
from app.db.repositories.option_chain_repo import OptionChainRepository
from app.dependencies import get_cache_instance

router = APIRouter()


@router.get("/ticks/latest")
async def get_latest_ticks(
    symbols: str = Query(
        default="",
        description="Comma-separated symbols. Empty = all watchlist symbols.",
    ),
):
    """Get the latest tick data for specified or all watchlist symbols."""
    cache = get_cache_instance()
    if not cache:
        return {"error": "Cache not initialized"}

    from app.config import get_settings
    settings = get_settings()

    symbol_list = (
        [s.strip() for s in symbols.split(",") if s.strip()]
        if symbols
        else settings.all_watchlist_symbols
    )

    ticks = await cache.get_all_ticks(symbol_list)
    return {
        "data": {k: v for k, v in ticks.items() if v is not None},
        "count": sum(1 for v in ticks.values() if v),
    }


@router.get("/ticks/{symbol}")
async def get_tick_history(
    symbol: str,
    start: Optional[str] = Query(None, description="Start datetime ISO format"),
    end: Optional[str] = Query(None, description="End datetime ISO format"),
    interval: str = Query("1 minute", description="OHLCV interval"),
    limit: int = Query(500, ge=1, le=10000),
    session: AsyncSession = Depends(get_session),
):
    """Get historical tick/OHLCV data for a symbol."""
    repo = TickRepository(session)

    if start and end:
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)
        ohlcv = await repo.get_ohlcv(symbol, start_dt, end_dt, interval)
        return {"data": ohlcv, "count": len(ohlcv)}
    else:
        # Return latest ticks
        latest = await repo.get_latest_tick(symbol)
        return {
            "data": {
                "symbol": latest.symbol if latest else symbol,
                "ltp": latest.ltp if latest else None,
                "time": latest.time.isoformat() if latest else None,
            }
        }


@router.get("/option-chain/{underlying}")
async def get_option_chain(
    underlying: str,
    expiry: Optional[str] = Query(None, description="Expiry date YYYY-MM-DD"),
    session: AsyncSession = Depends(get_session),
):
    """Get the latest option chain with Greeks for an underlying.

    First tries Redis cache, falls back to database.
    """
    cache = get_cache_instance()

    # Try cache first
    if cache:
        cached = await cache.get_chain(underlying)
        if cached:
            return {
                "source": "cache",
                "underlying": underlying,
                "data": cached,
                "count": len(cached),
            }

    # Fallback to database
    repo = OptionChainRepository(session)
    expiry_date = date.fromisoformat(expiry) if expiry else None
    chain = await repo.get_latest_chain(underlying, expiry_date)

    if chain:
        return {
            "source": "database",
            "underlying": underlying,
            "data": [
                {
                    "strike": s.strike,
                    "option_type": s.option_type,
                    "ltp": s.ltp,
                    "bid": s.bid,
                    "ask": s.ask,
                    "volume": s.volume,
                    "oi": s.oi,
                    "change_oi": s.change_oi,
                    "iv": s.iv,
                    "delta": s.delta,
                    "gamma": s.gamma,
                    "theta": s.theta,
                    "vega": s.vega,
                    "intrinsic_value": s.intrinsic_value,
                    "time_value": s.time_value,
                    "spot_price": s.spot_price,
                    "time": s.time.isoformat(),
                }
                for s in chain
            ],
            "count": len(chain),
        }

    return {
        "source": "none",
        "underlying": underlying,
        "data": [],
        "message": "No data available. Ensure data pipeline is running.",
    }


@router.get("/option-chain/{underlying}/db")
async def get_option_chain_from_db(
    underlying: str,
    expiry: Optional[str] = Query(None, description="Expiry date YYYY-MM-DD"),
    session: AsyncSession = Depends(get_session),
):
    """Get the latest option chain from the database."""
    repo = OptionChainRepository(session)
    expiry_date = date.fromisoformat(expiry) if expiry else None
    chain = await repo.get_latest_chain(underlying, expiry_date)

    return {
        "source": "database",
        "underlying": underlying,
        "data": [
            {
                "strike": s.strike,
                "option_type": s.option_type,
                "ltp": s.ltp,
                "bid": s.bid,
                "ask": s.ask,
                "volume": s.volume,
                "oi": s.oi,
                "change_oi": s.change_oi,
                "iv": s.iv,
                "delta": s.delta,
                "gamma": s.gamma,
                "theta": s.theta,
                "vega": s.vega,
                "intrinsic_value": s.intrinsic_value,
                "time_value": s.time_value,
                "spot_price": s.spot_price,
                "time": s.time.isoformat(),
            }
            for s in chain
        ],
        "count": len(chain),
    }


@router.get("/metrics/{symbol}")
async def get_computed_metrics(symbol: str):
    """Get all cached computed metrics for a symbol."""
    cache = get_cache_instance()
    if not cache:
        return {"error": "Cache not initialized"}

    metrics = await cache.get_metrics(symbol)
    return {
        "symbol": symbol,
        "metrics": metrics or {},
    }


@router.get("/scores/{symbol}")
async def get_scores(symbol: str):
    """Get the latest scoring snapshot for a symbol."""
    cache = get_cache_instance()
    if not cache:
        return {"error": "Cache not initialized"}

    scores = await cache.get_scores(symbol)
    return {
        "symbol": symbol,
        "scores": scores or {},
    }
