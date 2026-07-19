"""
ML predictions hypertable model.

Stores predictions from all ML models with probability estimates
for various gain thresholds and time horizons.

Primary key is (time, symbol, model_name) — time alone is NOT unique since
multiple models and symbols generate predictions at the same timestamp.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, Integer, PrimaryKeyConstraint, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base


class MLPrediction(Base):
    __tablename__ = "ml_predictions"
    __table_args__ = (
        PrimaryKeyConstraint("time", "symbol", "model_name", name="pk_ml_predictions"),
    )

    time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    symbol: Mapped[str] = mapped_column(String(100), nullable=False)
    model_name: Mapped[str] = mapped_column(String(50), nullable=False)
    model_version: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    prob_gain_10pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    prob_gain_20pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    prob_gain_30pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    horizon_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    feature_importance: Mapped[dict] = mapped_column(JSONB, default=dict)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)

    def __repr__(self) -> str:
        return (
            f"<MLPrediction(symbol='{self.symbol}', "
            f"model='{self.model_name}', "
            f"p10={self.prob_gain_10pct})>"
        )
