"""
OI (Open Interest) buildup and momentum analysis.

Categorizes option contracts into:
- Long Build-up (LBU)
- Short Build-up (SBU)
- Long Unwinding (LUW)
- Short Covering (SCV)
Based on changes in Price and Open Interest.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def categorize_buildup(
    price_change: float,
    oi_change: float
) -> str:
    """
    Categorize buildup based on price and OI change.
    """
    if oi_change > 0:
        if price_change > 0:
            return "LONG_BUILDUP"
        elif price_change < 0:
            return "SHORT_BUILDUP"
    elif oi_change < 0:
        if price_change < 0:
            return "LONG_UNWINDING"
        elif price_change > 0:
            return "SHORT_COVERING"

    return "NEUTRAL"


def compute_oi_momentum(
    current_oi: int,
    previous_oi: int,
    time_delta_seconds: float
) -> float:
    """
    Calculate OI Momentum as the rate of change in Open Interest per minute.
    """
    if previous_oi == 0 or time_delta_seconds <= 0:
        return 0.0

    oi_diff = current_oi - previous_oi
    minutes = time_delta_seconds / 60.0
    return float(round(oi_diff / minutes, 2))
