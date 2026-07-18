"""
AI Report Generator.

Coordinates the prompt construction, LLM inference via Groq,
and database persistence of AI explanations.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, Any

from app.db.engine import get_async_session
from app.db.models.ai_reports import AIReport
from app.services.ai.groq_client import GroqClient
from app.services.ai.prompt_builder import build_analysis_prompt

logger = logging.getLogger(__name__)


class AIReportGenerator:
    """Generates structured market analysis reports using LLMs."""

    def __init__(self, groq_client: GroqClient) -> None:
        self._groq = groq_client

    async def generate_and_save_report(
        self,
        symbol: str,
        metrics: Dict[str, float],
        scores: Dict[str, Any],
        report_type: str = "MARKET_ANALYSIS"
    ) -> str:
        """
        Generate market report, save it to database, and return the content.
        """
        try:
            # 1. Build Prompt
            messages = build_analysis_prompt(symbol, metrics, scores)

            # 2. Call Groq Client
            resp = await self._groq.generate_completion(messages, temperature=0.15)
            content = resp["content"]

            # 3. Save to database
            async with get_async_session() as session:
                report = AIReport(
                    symbol=symbol,
                    report_type=report_type,
                    content=content,
                    metrics_referenced=metrics,
                    scores_snapshot=scores,
                    model_used=resp["model"],
                    prompt_tokens=resp["prompt_tokens"],
                    completion_tokens=resp["completion_tokens"]
                )
                session.add(report)

            logger.info(f"Saved AI report for {symbol} to database.")
            return content

        except Exception as e:
            logger.error(f"Failed to generate and save AI report for {symbol}: {e}")
            return "AI report generation failed."
