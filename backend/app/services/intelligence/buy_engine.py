"""
Buy Engine.

Evaluates directional trade setups, requiring multi-factor convergence across Trend,
OI, Greeks, PCR, IV, VWAP, EMA, breakout levels, and volume spikes.
"""

from __future__ import annotations

import logging
from typing import Dict, Any

from app.services.intelligence.trade_filters import is_trade_allowed

logger = logging.getLogger(__name__)


class BuyEngine:
    """Evaluates entry triggers for CE and PE option purchasing."""

    def __init__(self, scoring_results: Dict[str, Any] = None) -> None:
        pass

    def evaluate_opportunity(
        self,
        symbol: str,
        metrics: Dict[str, float],
        scores: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluate entry conditions. Never recommends on one indicator alone.
        Requires Bull/Bear Score >= 70% and additional convergence rules.
        """
        # 1. Apply pre-trade filters
        if not is_trade_allowed(metrics):
            return {
                "symbol": symbol,
                "direction": "NO_TRADE",
                "confidence": 0.0,
                "reasoning": ["Risk/Time filter blocked trade entry."]
            }

        bull_score = scores.get("bull_score", 50)
        bear_score = scores.get("bear_score", 50)
        confidence = scores.get("confidence", 0)

        reasons = []

        # 2. Check Volume Confirmation
        vol_spike = metrics.get("volume_spike_ratio", 1.0)
        if vol_spike > 1.2:
            reasons.append("Volume confirmation: high volume spike detected.")
        else:
            # Drop signal if no volume momentum
            return {
                "symbol": symbol,
                "direction": "NO_TRADE",
                "confidence": 0.0,
                "reasoning": ["No volume confirmation."]
            }

        # 3. Check technical convergence for Bull/Bear
        spot = metrics.get("close", 0.0)
        vwap = metrics.get("vwap", 0.0)

        if bull_score >= 70 and confidence >= 40:
            if spot > vwap:
                reasons.append("Spot price trading above intraday VWAP (Bullish confirmation).")
                return {
                    "symbol": symbol,
                    "direction": "BUY_CE",
                    "confidence": float(confidence),
                    "reasoning": reasons
                }

        if bear_score >= 70 and confidence >= 40:
            if spot < vwap:
                reasons.append("Spot price trading below intraday VWAP (Bearish confirmation).")
                return {
                    "symbol": symbol,
                    "direction": "BUY_PE",
                    "confidence": float(confidence),
                    "reasoning": reasons
                }

        return {
            "symbol": symbol,
            "direction": "NO_TRADE",
            "confidence": 0.0,
            "reasoning": ["No strong convergence of Bull/Bear indicators."]
        }
