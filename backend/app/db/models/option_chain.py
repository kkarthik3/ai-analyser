"""
Option chain snapshots hypertable model.

Stores complete option chain data including locally-computed Greeks and IV.
Each row = one strike at one point in time.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import BigInteger, Date, DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base


class OptionChainSnapshot(Base):
    __tablename__ = "option_chain_snapshots"

    time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True, nullable=False
    )
    underlying: Mapped[str] = mapped_column(String(50), nullable=False)
    expiry: Mapped[date] = mapped_column(Date, nullable=False)
    strike: Mapped[float] = mapped_column(Float, nullable=False)
    option_type: Mapped[str] = mapped_column(String(2), nullable=False)  # CE or PE
    symbol: Mapped[str] = mapped_column(String(100), nullable=False)
    ltp: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bid: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ask: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bid_qty: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    ask_qty: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    volume: Mapped[int] = mapped_column(BigInteger, default=0)
    oi: Mapped[int] = mapped_column(BigInteger, default=0)
    change_oi: Mapped[float] = mapped_column(Float, default=0.0)
    iv: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    delta: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gamma: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    theta: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    vega: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rho: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    intrinsic_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    time_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    spot_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<OptionChainSnapshot("
            f"underlying='{self.underlying}', "
            f"strike={self.strike}, "
            f"type='{self.option_type}', "
            f"ltp={self.ltp}"
            f")>"
        )
