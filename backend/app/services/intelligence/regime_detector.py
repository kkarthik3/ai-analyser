"""
Market Regime Detector.

Automatically classifies market conditions into states like Trending, Range, Volatile,
Breakout, Mean Reversion, Low Volatility, and High Volatility based on technical indicators.
"""

from __future__ import annotations

import logging
from typing import Dict

logger = logging.getLogger(__name__)


def classify_market_regime(metrics: Dict[str, float]) -> str:
    """
    Classify the current market regime based on technical indicators.
    Indicators used:
      - ADX (Trend Strength)
      - Bollinger Band Width (Volatility)
      - RSI (Overbought/Oversold/Momentum)
      - EMA Distances (Trend Direction)
      - ATR (Relative Volatility)
    """
    adx = metrics.get("adx", 0.0)
    rsi = metrics.get("rsi_14", 50.0)
    bb_width = metrics.get("bb_width", 0.02)
    atr = metrics.get("atr_14", 0.0)
    ema_20 = metrics.get("ema_20", 0.0)
    ema_200 = metrics.get("ema_200", 0.0)

    # 1. Volatility Regimes
    is_high_vol = bb_width > 0.04
    is_low_vol = bb_width < 0.01

    # 2. Trend Strength
    is_strong_trend = adx >= 25
    is_weak_trend = adx < 15

    # 3. Mean Reversion / Oversold / Overbought
    is_extreme = rsi >= 70 or rsi <= 30

    # Decision Matrix
    if is_strong_trend:
        if is_high_vol:
            return "VOLATILE_TRENDING"
        return "STRONG_TREND"

    if is_low_vol:
        return "LOW_VOLATILITY_RANGE"

    if is_extreme:
        return "MEAN_REVERSION"

    if is_weak_trend:
        return "TIGHT_RANGE"

    # Default to general Range or Volatile
    if is_high_vol:
        return "HIGH_VOLATILITY_RANGE"

    return "NORMAL_RANGE"
