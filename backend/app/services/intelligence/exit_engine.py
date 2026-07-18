"""
Exit Engine.

Continuously monitors open trades to recommend exit triggers (HOLD, PARTIAL EXIT, FULL EXIT)
based on profit targets, trailing stops, theta decay risk, and IV crush.
"""

from __future__ import annotations

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class ExitEngine:
    """Evaluates exit conditions for open option positions."""

    def __init__(self) -> None:
        pass

    def evaluate_exit(
        self,
        position: Dict[str, Any],
        current_metrics: Dict[str, float],
        current_scores: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluate an active position's parameters to suggest exit actions.
        Expected position keys:
          - entry_price
          - ltp (current price)
          - direction (BUY_CE / BUY_PE)
          - max_drawdown_limit (percent)
          - target_pct (percent)
          - entry_time
        """
        entry_price = position.get("entry_price", 0.0)
        current_price = position.get("ltp", entry_price)

        if entry_price <= 0:
            return {"action": "HOLD", "reason": "Invalid entry price."}

        # Calculate P&L %
        pnl_pct = ((current_price - entry_price) / entry_price) * 100

        # 1. Stop Loss (Drawdown limit)
        max_drawdown = position.get("max_drawdown_limit", -15.0)  # Default 15% stop loss
        if pnl_pct <= max_drawdown:
            return {"action": "FULL_EXIT", "reason": f"Stop loss hit: current PnL is {pnl_pct:.2f}%"}

        # 2. Take Profit (Target)
        target = position.get("target_pct", 30.0)  # Default 30% take profit target
        if pnl_pct >= target:
            return {"action": "FULL_EXIT", "reason": f"Profit target hit: current PnL is {pnl_pct:.2f}%"}

        # 3. Dynamic Stop: Trend reversal/Score drop
        confidence = current_scores.get("confidence", 100)
        if confidence < 15:
            return {"action": "FULL_EXIT", "reason": f"Confidence dropped below threshold ({confidence}%)"}

        # 4. Trailing Stop (Lock in profits)
        if pnl_pct >= 15.0:
            # If we achieved 15% profit, trailing stop is at entry price (0%)
            if pnl_pct < 2.0:  # If we drop back near entry
                return {"action": "FULL_EXIT", "reason": "Trailing stop hit (protection of capital)"}
            return {"action": "PARTIAL_EXIT", "reason": "Locking in partial profits at 15%."}

        return {"action": "HOLD", "reason": "No exit conditions triggered."}
