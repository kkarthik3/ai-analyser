"""
Backtest Replay Engine.

Queries historical TimescaleDB data (ticks, option chains, Greeks, OI)
and replays them chronologically to simulate market feeds.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Generator, Tuple, List, Dict, Any

from sqlalchemy import select

from app.db.engine import get_async_session
from app.db.repositories.tick_repo import TickRepository
from app.db.repositories.option_chain_repo import OptionChainRepository
from app.db.models.market_ticks import MarketTick
from app.db.models.option_chain import OptionChainSnapshot

logger = logging.getLogger(__name__)


class ReplayEngine:
    """Streams historical database records sequentially for strategy simulation."""

    def __init__(self) -> None:
        pass

    async def get_historical_stream(
        self,
        symbol: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict[str, Any]]:
        """
        Fetch and sort ticks and option chains to construct a chronological market feed.
        """
        async with get_async_session() as session:
            tick_repo = TickRepository(session)
            chain_repo = OptionChainRepository(session)

            logger.info(f"ReplayEngine loading data for {symbol} from {start_time} to {end_time}")

            # Fetch ticks
            ticks = await tick_repo.get_ticks_in_range(symbol, start_time, end_time, limit=5000)

            # Fetch option chain snapshots
            stmt = (
                select(OptionChainSnapshot)
                .where(
                    OptionChainSnapshot.underlying == symbol,
                    OptionChainSnapshot.time >= start_time,
                    OptionChainSnapshot.time <= end_time
                )
                .order_by(OptionChainSnapshot.time.asc())
            )
            chains = await chain_repo.execute_query(stmt)

        # Merge ticks and chains into a single timeline list
        timeline = []

        for tick in ticks:
            timeline.append({
                "time": tick.time,
                "type": "TICK",
                "symbol": tick.symbol,
                "ltp": tick.ltp,
                "volume": tick.volume,
                "oi": tick.oi
            })

        # Group option snapshots by timestamp
        chain_by_time = {}
        for c in chains:
            t = c.time
            if t not in chain_by_time:
                chain_by_time[t] = []
            chain_by_time[t].append(c)

        for t, snaps in chain_by_time.items():
            timeline.append({
                "time": t,
                "type": "OPTION_CHAIN",
                "snapshots": snaps
            })

        # Sort timeline chronologically
        timeline.sort(key=lambda x: x["time"])
        logger.info(f"Timeline loaded with {len(timeline)} events.")
        return timeline
