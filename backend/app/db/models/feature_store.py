"""
Feature store hypertable model.

Stores the 300+ engineered features computed per symbol per time interval.
Features are stored as a JSONB blob for flexibility during rapid iteration.

Primary key is (time, symbol) — time alone is NOT unique since features are
computed for each symbol independently at the same time.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, PrimaryKeyConstraint, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base


class FeatureStoreEntry(Base):
    __tablename__ = "feature_store"
    __table_args__ = (
        PrimaryKeyConstraint("time", "symbol", name="pk_feature_store"),
    )

    time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    symbol: Mapped[str] = mapped_column(String(100), nullable=False)
    features: Mapped[dict] = mapped_column(JSONB, nullable=False)

    def __repr__(self) -> str:
        n_features = len(self.features) if self.features else 0
        return f"<FeatureStoreEntry(symbol='{self.symbol}', n_features={n_features})>"
