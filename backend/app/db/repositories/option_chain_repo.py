"""
Option chain data repository.

Optimized for batch inserts of full chain snapshots and
time-range queries for chain replay/backtesting.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.option_chain import OptionChainSnapshot
from app.db.repositories.base import BaseRepository


class OptionChainRepository(BaseRepository[OptionChainSnapshot]):
    """Repository for option chain snapshot data."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, OptionChainSnapshot)

    async def insert_chain_batch(self, snapshots: list[dict[str, Any]]) -> None:
        """Insert a full option chain snapshot as a batch."""
        await self.bulk_insert_mappings(snapshots)

    async def get_latest_chain(
        self,
        underlying: str,
        expiry: Optional[date] = None,
    ) -> Sequence[OptionChainSnapshot]:
        """Get the most recent complete option chain for an underlying.

        Fetches the latest timestamp and returns all strikes at that time.
        """
        # First, find the latest timestamp
        latest_time_stmt = (
            select(OptionChainSnapshot.time)
            .where(OptionChainSnapshot.underlying == underlying)
        )
        if expiry:
            latest_time_stmt = latest_time_stmt.where(
                OptionChainSnapshot.expiry == expiry
            )
        latest_time_stmt = latest_time_stmt.order_by(
            OptionChainSnapshot.time.desc()
        ).limit(1)

        result = await self._session.execute(latest_time_stmt)
        latest_time = result.scalar_one_or_none()

        if not latest_time:
            return []

        # Then fetch all strikes at that time
        stmt = (
            select(OptionChainSnapshot)
            .where(
                OptionChainSnapshot.underlying == underlying,
                OptionChainSnapshot.time == latest_time,
            )
        )
        if expiry:
            stmt = stmt.where(OptionChainSnapshot.expiry == expiry)
        stmt = stmt.order_by(OptionChainSnapshot.strike.asc())

        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_chain_at_time(
        self,
        underlying: str,
        at_time: datetime,
        expiry: Optional[date] = None,
    ) -> Sequence[OptionChainSnapshot]:
        """Get the option chain closest to a specific time (for replay)."""
        stmt = (
            select(OptionChainSnapshot)
            .where(
                OptionChainSnapshot.underlying == underlying,
                OptionChainSnapshot.time <= at_time,
            )
        )
        if expiry:
            stmt = stmt.where(OptionChainSnapshot.expiry == expiry)

        # Get the max time <= at_time
        time_stmt = (
            select(OptionChainSnapshot.time)
            .where(
                OptionChainSnapshot.underlying == underlying,
                OptionChainSnapshot.time <= at_time,
            )
            .order_by(OptionChainSnapshot.time.desc())
            .limit(1)
        )
        result = await self._session.execute(time_stmt)
        closest_time = result.scalar_one_or_none()

        if not closest_time:
            return []

        stmt = (
            select(OptionChainSnapshot)
            .where(
                OptionChainSnapshot.underlying == underlying,
                OptionChainSnapshot.time == closest_time,
            )
            .order_by(OptionChainSnapshot.strike.asc())
        )
        if expiry:
            stmt = stmt.where(OptionChainSnapshot.expiry == expiry)

        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_oi_history(
        self,
        underlying: str,
        strike: float,
        option_type: str,
        start: datetime,
        end: datetime,
    ) -> Sequence[OptionChainSnapshot]:
        """Get OI history for a specific strike over a time range."""
        stmt = (
            select(OptionChainSnapshot)
            .where(
                OptionChainSnapshot.underlying == underlying,
                OptionChainSnapshot.strike == strike,
                OptionChainSnapshot.option_type == option_type,
                OptionChainSnapshot.time >= start,
                OptionChainSnapshot.time <= end,
            )
            .order_by(OptionChainSnapshot.time.asc())
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()
