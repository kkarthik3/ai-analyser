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
from app.dependencies import get_cache_instance, get_fyers_client_instance

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


@router.get("/portfolio/positions")
async def get_positions():
    """Get current positions from FYERS."""
    try:
        client = get_fyers_client_instance()
        res = await client.get_positions()
        return res
    except Exception as e:
        return {"s": "error", "message": str(e)}


@router.get("/portfolio/holdings")
async def get_holdings():
    """Get current holdings from FYERS."""
    try:
        client = get_fyers_client_instance()
        res = await client.get_holdings()
        return res
    except Exception as e:
        return {"s": "error", "message": str(e)}


@router.get("/portfolio/profile")
async def get_profile():
    """Get user profile from FYERS."""
    try:
        client = get_fyers_client_instance()
        res = await client.get_profile()
        return res
    except Exception as e:
        return {"s": "error", "message": str(e)}


@router.get("/portfolio/funds")
async def get_funds():
    """Get account fund details from FYERS."""
    try:
        client = get_fyers_client_instance()
        res = await client.get_funds()
        return res
    except Exception as e:
        return {"s": "error", "message": str(e)}


@router.get("/ai-report/{symbol}")
async def get_ai_report(symbol: str, session: AsyncSession = Depends(get_session)):
    """Get the latest AI report for a symbol from the database."""
    try:
        from app.db.models.ai_reports import AIReport
        from sqlalchemy import select
        
        stmt = (
            select(AIReport)
            .where(AIReport.symbol == symbol)
            .order_by(AIReport.time.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        report = result.scalar_one_or_none()
        
        if report:
            return {
                "symbol": symbol,
                "content": report.content,
                "time": report.time.isoformat(),
                "model": report.model_used,
            }
        return {"symbol": symbol, "content": None, "message": "No AI report generated yet."}
    except Exception as e:
        return {"error": str(e)}


@router.get("/portfolio/journal")
async def get_portfolio_journal(session: AsyncSession = Depends(get_session)):
    """Get historical trade journal entries from database."""
    try:
        from app.db.models.journal import TradeJournalEntry
        from sqlalchemy import select

        stmt = (
            select(TradeJournalEntry)
            .where(TradeJournalEntry.exit_time.isnot(None))
            .order_by(TradeJournalEntry.exit_time.desc())
        )
        result = await session.execute(stmt)
        entries = result.scalars().all()

        return [
            {
                "id": str(e.id),
                "symbol": e.symbol,
                "direction": e.direction,
                "entry_time": e.entry_time.isoformat() if e.entry_time else None,
                "exit_time": e.exit_time.isoformat() if e.exit_time else None,
                "entry_price": e.entry_price,
                "exit_price": e.exit_price,
                "quantity": e.quantity,
                "pnl": e.pnl or 0.0,
                "pnl_pct": e.pnl_pct or 0.0,
                "reason": e.exit_reason or "Unknown",
                "date": e.exit_time.strftime("%Y-%m-%d") if e.exit_time else "",
            }
            for e in entries
        ]
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to fetch portfolio journal: {e}")
        return []


@router.get("/portfolio/analytics")
async def get_portfolio_analytics(session: AsyncSession = Depends(get_session)):
    """Compute and get trade performance analytics dynamically."""
    try:
        from app.db.models.journal import TradeJournalEntry
        from sqlalchemy import select
        import math

        stmt = select(TradeJournalEntry).where(TradeJournalEntry.exit_time.isnot(None))
        result = await session.execute(stmt)
        entries = result.scalars().all()

        trade_count = len(entries)
        if trade_count == 0:
            return {
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "sharpe_ratio": 0.0,
                "sortino_ratio": 0.0,
                "max_drawdown": 0.0,
                "trade_count": 0,
            }

        pnls = [e.pnl or 0.0 for e in entries]
        pnl_pcts = [e.pnl_pct or 0.0 for e in entries]

        # Win Rate
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]
        win_rate = (len(wins) / trade_count) * 100

        # Profit Factor
        total_gains = sum(wins)
        total_losses = abs(sum(losses))
        profit_factor = total_gains / total_losses if total_losses > 0 else (total_gains if total_gains > 0 else 0.0)

        # Helper functions for stats
        def calculate_mean(lst):
            return sum(lst) / len(lst) if lst else 0.0

        def calculate_std(lst, mean):
            if len(lst) <= 1:
                return 0.0
            variance = sum((x - mean) ** 2 for x in lst) / len(lst)
            return math.sqrt(variance)

        # Sharpe / Sortino Ratio calculations
        mean_ret = calculate_mean(pnl_pcts)
        std_ret = calculate_std(pnl_pcts, mean_ret)
        sharpe_ratio = (mean_ret / std_ret) if std_ret > 0 else 0.0

        downside_pcts = [p for p in pnl_pcts if p < 0]
        downside_mean = calculate_mean(downside_pcts)
        downside_std = calculate_std(downside_pcts, downside_mean)
        sortino_ratio = (mean_ret / downside_std) if downside_std > 0 else (sharpe_ratio if downside_mean != 0 else 0.0)

        # Max Drawdown from percentage returns (peak to valley)
        cum_ret = 0.0
        peak = 0.0
        max_drawdown = 0.0
        for p in pnl_pcts:
            cum_ret += p
            if cum_ret > peak:
                peak = cum_ret
            dd = peak - cum_ret
            if dd > max_drawdown:
                max_drawdown = dd

        return {
            "win_rate": round(win_rate, 2),
            "profit_factor": round(profit_factor, 2),
            "sharpe_ratio": round(sharpe_ratio, 2),
            "sortino_ratio": round(sortino_ratio, 2),
            "max_drawdown": round(max_drawdown, 2),
            "trade_count": trade_count,
        }
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to calculate portfolio analytics: {e}")
        return {
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "sharpe_ratio": 0.0,
            "sortino_ratio": 0.0,
            "max_drawdown": 0.0,
            "trade_count": 0,
        }
