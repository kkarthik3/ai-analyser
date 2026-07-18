"""
Trade signals model.

Records every trade opportunity identified by the Buy Engine,
including direction, confidence, reasoning, and market snapshot.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base


class TradeSignal(Base):
    __tablename__ = "trade_signals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    symbol: Mapped[str] = mapped_column(String(100), nullable=False)
    underlying: Mapped[str] = mapped_column(String(50), nullable=False)
    direction: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # BUY_CE, BUY_PE, NO_TRADE
    status: Mapped[str] = mapped_column(
        String(20), default="ACTIVE"
    )  # ACTIVE, EXECUTED, EXPIRED, CANCELLED
    entry_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    target_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    stop_loss: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bull_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bear_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    risk_reward: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    reasoning: Mapped[dict] = mapped_column(JSONB, default=dict)
    factors: Mapped[dict] = mapped_column(JSONB, default=dict)
    market_snapshot: Mapped[dict] = mapped_column(JSONB, default=dict)
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return (
            f"<TradeSignal(symbol='{self.symbol}', "
            f"direction='{self.direction}', "
            f"confidence={self.confidence})>"
        )
