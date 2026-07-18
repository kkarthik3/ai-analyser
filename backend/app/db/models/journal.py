"""
Trade journal model.

Automatically records every trade with complete entry/exit snapshots,
Greeks, scores, P&L, exit reason, and post-trade AI analysis.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base


class TradeJournalEntry(Base):
    __tablename__ = "trade_journal"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    signal_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    symbol: Mapped[str] = mapped_column(String(100), nullable=False)
    direction: Mapped[str] = mapped_column(String(20), nullable=False)
    entry_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    exit_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    entry_price: Mapped[float] = mapped_column(Float, nullable=False)
    exit_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    pnl: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pnl_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    exit_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    entry_snapshot: Mapped[dict] = mapped_column(JSONB, default=dict)
    exit_snapshot: Mapped[dict] = mapped_column(JSONB, default=dict)
    greeks_at_entry: Mapped[dict] = mapped_column(JSONB, default=dict)
    greeks_at_exit: Mapped[dict] = mapped_column(JSONB, default=dict)
    scores_at_entry: Mapped[dict] = mapped_column(JSONB, default=dict)
    lessons: Mapped[dict] = mapped_column(JSONB, default=dict)
    ai_analysis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return (
            f"<TradeJournalEntry(symbol='{self.symbol}', "
            f"pnl={self.pnl}, reason='{self.exit_reason}')>"
        )
