"""
Trade Journal Service.

Automatically logs trade executions (entry/exit snapshots, Greeks, scores)
into the database for historical auditing and learning.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from app.db.engine import get_async_session
from app.db.models.journal import TradeJournalEntry

logger = logging.getLogger(__name__)


class JournalService:
    """Handles insertions and updates to the trade journal database table."""

    def __init__(self) -> None:
        pass

    async def log_trade_entry(
        self,
        symbol: str,
        direction: str,
        price: float,
        qty: int,
        scores_at_entry: Dict[str, Any],
        greeks_at_entry: Dict[str, Any] = None,
        signal_id: Optional[uuid.UUID] = None
    ) -> uuid.UUID:
        """
        Record a new trade entry in the journal.
        """
        now = datetime.now(timezone.utc)
        record_id = uuid.uuid4()

        try:
            async with get_async_session() as session:
                entry = TradeJournalEntry(
                    id=record_id,
                    signal_id=signal_id,
                    symbol=symbol,
                    direction=direction,
                    entry_time=now,
                    entry_price=price,
                    quantity=qty,
                    scores_at_entry=scores_at_entry,
                    greeks_at_entry=greeks_at_entry or {},
                    entry_snapshot={}
                )
                session.add(entry)
            logger.info(f"Logged trade entry in journal: {record_id}")
            return record_id
        except Exception as e:
            logger.error(f"Failed to log trade entry: {e}")
            raise

    async def log_trade_exit(
        self,
        record_id: uuid.UUID,
        price: float,
        exit_reason: str,
        greeks_at_exit: Dict[str, Any] = None,
        lessons: Dict[str, Any] = None
    ) -> None:
        """
        Record the exit details of an existing journaled trade.
        """
        now = datetime.now(timezone.utc)

        try:
            async with get_async_session() as session:
                from sqlalchemy import select
                stmt = select(TradeJournalEntry).where(TradeJournalEntry.id == record_id)
                res = await session.execute(stmt)
                entry = res.scalar_one_or_none()

                if not entry:
                    logger.error(f"Journal trade record not found for exit update: {record_id}")
                    return

                entry.exit_time = now
                entry.exit_price = price
                entry.exit_reason = exit_reason
                entry.greeks_at_exit = greeks_at_exit or {}
                entry.lessons = lessons or {}

                # Calculate P&L
                pnl = (price - entry.entry_price) * entry.quantity
                pnl_pct = ((price - entry.entry_price) / entry.entry_price) * 100

                entry.pnl = pnl
                entry.pnl_pct = pnl_pct

            logger.info(f"Logged trade exit in journal: {record_id}. P&L: {pnl:.2f}")
        except Exception as e:
            logger.error(f"Failed to log trade exit for {record_id}: {e}")
            raise
