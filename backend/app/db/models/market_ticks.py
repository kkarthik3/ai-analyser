"""
Market ticks hypertable model.

Stores every price tick from FYERS WebSocket stream.
Mapped to TimescaleDB hypertable with 1-day chunk intervals.

Primary key is (time, symbol) — time alone is NOT unique since multiple
symbols produce ticks at the same millisecond timestamp.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Integer, PrimaryKeyConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base


class MarketTick(Base):
    __tablename__ = "market_ticks"
    __table_args__ = (
        PrimaryKeyConstraint("time", "symbol", name="pk_market_ticks"),
    )

    time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    instrument_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("instruments.id"), nullable=False
    )
    symbol: Mapped[str] = mapped_column(String(100), nullable=False)
    ltp: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    open: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    high: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    low: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    close: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bid: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ask: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bid_qty: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    ask_qty: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    volume: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    oi: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    change_oi: Mapped[float] = mapped_column(Float, default=0.0, server_default="0")
    prev_close: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    change_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    def __repr__(self) -> str:
        return f"<MarketTick(symbol='{self.symbol}', ltp={self.ltp}, time={self.time})>"
