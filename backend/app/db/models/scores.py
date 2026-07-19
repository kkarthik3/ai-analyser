"""
Scoring snapshots hypertable model.

Stores multi-dimensional score breakdowns: Bull/Bear/Confidence plus
all component scores (trend, momentum, OI, Greeks, volatility, etc.).

Primary key is (time, symbol) — time alone is NOT unique since scores are
computed independently for each symbol at the same timestamp.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, PrimaryKeyConstraint, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base


class ScoringSnapshot(Base):
    __tablename__ = "scoring_snapshots"
    __table_args__ = (
        PrimaryKeyConstraint("time", "symbol", name="pk_scoring_snapshots"),
    )

    time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    symbol: Mapped[str] = mapped_column(String(100), nullable=False)
    bull_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bear_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    trend_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    momentum_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    oi_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    greeks_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    volatility_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    structure_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    liquidity_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    risk_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    institutional_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    dealer_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    regime: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    recommendation: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)

    def __repr__(self) -> str:
        return (
            f"<ScoringSnapshot(symbol='{self.symbol}', "
            f"bull={self.bull_score}, bear={self.bear_score}, "
            f"confidence={self.confidence})>"
        )
