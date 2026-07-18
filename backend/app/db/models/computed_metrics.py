"""
Computed metrics hypertable model.

Stores all calculated metrics: PCR, Max Pain, IV Rank, EMA distances,
technical indicators, OI analytics, etc.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base


class ComputedMetric(Base):
    __tablename__ = "computed_metrics"

    time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True, nullable=False
    )
    symbol: Mapped[str] = mapped_column(String(100), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)

    def __repr__(self) -> str:
        return (
            f"<ComputedMetric(symbol='{self.symbol}', "
            f"metric='{self.metric_name}', value={self.value})>"
        )
