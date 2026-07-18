"""
Post-trade Analyzer.

Analyzes completed trade records to extract features and factors contributing
to trade success or failure.
"""

from __future__ import annotations

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class TradeAnalyzer:
    """Analyzes historical journal entries to output performance insights."""

    def __init__(self) -> None:
        pass

    def analyze_trade_outcome(self, trade: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze trade performance and assign attributes explaining why the trade
        worked or failed.
        """
        pnl = trade.get("pnl", 0.0)
        direction = trade.get("direction", "")
        reason = trade.get("exit_reason", "")
        scores = trade.get("scores_at_entry", {})

        is_win = pnl > 0
        success_factors = []
        failure_factors = []

        # Analyze technical alignment
        bull_score = scores.get("bull_score", 50)
        bear_score = scores.get("bear_score", 50)

        if is_win:
            if direction == "BUY_CE" and bull_score > 70:
                success_factors.append("Strong bullish score alignment at entry.")
            elif direction == "BUY_PE" and bear_score > 70:
                success_factors.append("Strong bearish score alignment at entry.")
        else:
            if direction == "BUY_CE" and bull_score < 60:
                failure_factors.append("Weak bullish entry score validation.")
            elif direction == "BUY_PE" and bear_score < 60:
                failure_factors.append("Weak bearish entry score validation.")

            if "Stop loss" in reason:
                failure_factors.append("Position stopped out due to adverse price action.")

        return {
            "is_win": is_win,
            "success_factors": success_factors,
            "failure_factors": failure_factors,
            "suggestions": (
                ["Maintain current entry triggers."]
                if is_win
                else ["Tighten entry filters.", "Verify volume confirmation."]
            )
        }
