"""
Market tick data repository.

Optimized for high-throughput writes (buffered batch inserts)
and time-range queries against the TimescaleDB hypertable.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional, Sequence

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.market_ticks import MarketTick
from app.db.repositories.base import BaseRepository


class TickRepository(BaseRepository[MarketTick]):
    """Repository for market tick data with batch-optimized writes."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, MarketTick)

    async def insert_tick_batch(self, ticks: list[dict[str, Any]]) -> None:
        """Insert a batch of tick records using high-performance bulk insert.

        This bypasses ORM overhead for maximum write throughput.
        Each dict should match MarketTick column names.
        """
        await self.bulk_insert_mappings(ticks)

    async def get_latest_tick(self, symbol: str) -> Optional[MarketTick]:
        """Get the most recent tick for a symbol."""
        stmt = (
            select(MarketTick)
            .where(MarketTick.symbol == symbol)
            .order_by(MarketTick.time.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_ticks_in_range(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        limit: int = 10000,
    ) -> Sequence[MarketTick]:
        """Get ticks for a symbol within a time range."""
        stmt = (
            select(MarketTick)
            .where(
                MarketTick.symbol == symbol,
                MarketTick.time >= start,
                MarketTick.time <= end,
            )
            .order_by(MarketTick.time.asc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_ohlcv(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        interval: str = "1 minute",
    ) -> list[dict[str, Any]]:
        """Get OHLCV data using TimescaleDB time_bucket.

        Falls back to raw SQL for TimescaleDB-specific functions.
        """
        query = text("""
            SELECT
                time_bucket(:interval, time) AS bucket,
                symbol,
                FIRST(ltp, time) AS open,
                MAX(ltp) AS high,
                MIN(ltp) AS low,
                LAST(ltp, time) AS close,
                SUM(volume) AS volume,
                LAST(oi, time) AS oi
            FROM market_ticks
            WHERE symbol = :symbol
              AND time >= :start
              AND time <= :end
            GROUP BY bucket, symbol
            ORDER BY bucket ASC
        """)
        result = await self._session.execute(
            query,
            {"symbol": symbol, "start": start, "end": end, "interval": interval},
        )
        rows = result.fetchall()
        return [
            {
                "time": row.bucket,
                "symbol": row.symbol,
                "open": row.open,
                "high": row.high,
                "low": row.low,
                "close": row.close,
                "volume": row.volume,
                "oi": row.oi,
            }
            for row in rows
        ]
