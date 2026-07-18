"""
AI reports model.

Stores all Groq-generated AI explanations and analysis reports,
along with the actual metrics that were referenced in the prompt.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base


class AIReport(Base):
    __tablename__ = "ai_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    symbol: Mapped[str] = mapped_column(String(100), nullable=False)
    report_type: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # MARKET_ANALYSIS, TRADE_EXPLANATION, EXIT_ANALYSIS, LEARNING
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metrics_referenced: Mapped[dict] = mapped_column(JSONB, default=dict)
    scores_snapshot: Mapped[dict] = mapped_column(JSONB, default=dict)
    model_used: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    prompt_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<AIReport(symbol='{self.symbol}', "
            f"type='{self.report_type}')>"
        )
