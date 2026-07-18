"""
Instruments reference table.

Stores metadata for all tracked instruments: indices, equities, and option contracts.
This is a standard PostgreSQL table (not a hypertable).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Float, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base


class Instrument(Base):
    __tablename__ = "instruments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    exchange: Mapped[str] = mapped_column(String(10), nullable=False, default="NSE")
    instrument_type: Mapped[str] = mapped_column(
        String(10), nullable=False, default="INDEX"
    )  # INDEX, EQ, CE, PE, FUT
    name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    lot_size: Mapped[int] = mapped_column(Integer, default=1)
    tick_size: Mapped[float] = mapped_column(Float, default=0.05)
    expiry: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    strike: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    underlying: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<Instrument(symbol='{self.symbol}', type='{self.instrument_type}')>"
