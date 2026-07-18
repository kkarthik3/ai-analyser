"""
Scoring Engine.

Calculates individual component scores (trend, momentum, open interest, etc.)
and consolidates them into overall Bull, Bear, and Confidence ratings.
"""

from __future__ import annotations

import logging
from typing import Dict, Any

from app.services.intelligence.score_weights import DEFAULT_WEIGHTS
from app.services.intelligence.regime_detector import classify_market_regime

logger = logging.getLogger(__name__)


class ScoringEngine:
    """Calculates weighted directional probability scores for market assets."""

    def __init__(self, weights: Dict[str, float] = None) -> None:
        self.weights = weights or DEFAULT_WEIGHTS

    def calculate_scores(self, metrics: Dict[str, float]) -> Dict[str, Any]:
        """
        Evaluate all technical, structural, and options indicators to output
        bull/bear scores and overall confidence.
        """
        # 1. Trend Score (-100 to +100)
        # Spot relative to EMAs
        spot = metrics.get("close", metrics.get("ema_9", 0.0)) # Fallback to EMA
        ema_20 = metrics.get("ema_20", spot)
        ema_200 = metrics.get("ema_200", spot)
        trend_score = 0.0
        if spot > ema_20:
            trend_score += 50
        else:
            trend_score -= 50
        if spot > ema_200:
            trend_score += 50
        else:
            trend_score -= 50

        # 2. Momentum Score (-100 to +100)
        rsi = metrics.get("rsi_14", 50)
        momentum_score = (rsi - 50) * 2  # Normalize to -100 to +100

        # 3. Open Interest (OI) Score (-100 to +100)
        pcr = metrics.get("pcr_oi", 1.0)
        oi_score = (pcr - 1.0) * 100
        oi_score = max(-100.0, min(100.0, oi_score))

        # 4. Greeks / Volatility Score (-100 to +100)
        net_gex = metrics.get("net_gex", 0.0)
        greeks_score = 100.0 if net_gex > 0 else -100.0

        # 5. Volatility Score (-100 to +100)
        vol_score = 0.0  # Volatility neutrality

        # 6. Market Structure Score (-100 to +100)
        structure_score = 0.0
        st_dir = metrics.get("supertrend_dir", 1.0)
        structure_score += st_dir * 100

        # Component collection (each normalized between -100 and +100)
        components = {
            "trend": trend_score,
            "momentum": momentum_score,
            "oi": oi_score,
            "greeks": greeks_score,
            "volatility": vol_score,
            "structure": structure_score,
            "liquidity": 0.0,
            "risk": 0.0,
            "institutional": 0.0,
            "dealer": greeks_score * 0.5
        }

        # Weighted calculation
        net_weighted = 0.0
        for comp_name, weight in self.weights.items():
            net_weighted += components.get(comp_name, 0.0) * weight

        # Overall scores
        # Net weighted is between -100 and +100.
        # Shift to Bull and Bear percentage estimates
        bull_pct = int(max(0.0, min(100.0, 50.0 + (net_weighted / 2.0))))
        bear_pct = 100 - bull_pct

        # Confidence corresponds to how far the score diverges from the 50% neutral level
        confidence_pct = int(abs(bull_pct - 50) * 2)

        regime = classify_market_regime(metrics)

        # Recommendation logic
        recommendation = "NO_TRADE"
        if bull_pct >= 65 and confidence_pct >= 30:
            recommendation = "BUY_CE"
        elif bear_pct >= 65 and confidence_pct >= 30:
            recommendation = "BUY_PE"

        return {
            "bull_score": bull_pct,
            "bear_score": bear_pct,
            "confidence": confidence_pct,
            "regime": regime,
            "recommendation": recommendation,
            "components": components
        }
