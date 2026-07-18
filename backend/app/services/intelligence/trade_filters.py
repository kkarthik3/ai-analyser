"""
Trade filters and risk validation rules.
"""

from __future__ import annotations

import logging
from datetime import datetime, time
from typing import Dict, Any

logger = logging.getLogger(__name__)


def is_trade_allowed(
    metrics: Dict[str, float],
    current_time: datetime = None
) -> bool:
    """
    Validate trade risk rules.
    Disallows trading if:
      - Time is outside 9:15 AM to 3:15 PM IST (market closing zone risk).
      - Absolute IV is extremely high (> 40) or low (< 8).
    """
    now = current_time or datetime.now()

    # Market Time constraints (Indian Standard Time)
    trade_start = time(9, 30)  # Avoid first 15 mins (volatility noise)
    trade_end = time(15, 10)    # Avoid last 20 mins (intraday square-off zone)
    curr_time = now.time()

    if curr_time < trade_start or curr_time > trade_end:
        logger.debug("Trade filtered out: outside allowed time window.")
        return False

    # Volatility bounds
    iv = metrics.get("atm_iv", metrics.get("iv", 15.0))
    if iv > 40.0:
        logger.debug("Trade filtered out: IV too high (extreme risk).")
        return False
    if iv < 8.0:
        logger.debug("Trade filtered out: IV too low (insufficient premium expansion).")
        return False

    return True
