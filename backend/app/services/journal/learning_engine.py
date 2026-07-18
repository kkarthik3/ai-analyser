"""
Scoring Learning Engine.

Dynamically adjusts scoring engine component weights based on the outcomes (win/loss)
of historical journaled trades.
"""

from __future__ import annotations

import logging
from typing import Dict

from app.services.intelligence.score_weights import DEFAULT_WEIGHTS

logger = logging.getLogger(__name__)

LEARNING_RATE = 0.02


class LearningEngine:
    """Updates model weights based on historical trade outcomes to optimize scoring."""

    def __init__(self, initial_weights: Dict[str, float] = None) -> None:
        self.weights = initial_weights or DEFAULT_WEIGHTS.copy()

    def update_weights_from_trade(
        self,
        trade_pnl: float,
        entry_scores: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Adjust weights based on trade outcome.
        If trade won: reinforce components that matched the direction.
        If trade lost: penalize components that gave false validation.
        """
        is_win = trade_pnl > 0
        direction = 1 if is_win else -1

        # We inspect entry scores (components dictionary)
        components = entry_scores.get("components", {})

        adjusted_weights = self.weights.copy()
        total = 0.0

        for comp, val in components.items():
            if comp not in adjusted_weights:
                continue

            # If component matched direction of P&L
            # (e.g. positive value for win, or negative value for loss)
            weight_shift = LEARNING_RATE * (val / 100.0) * direction
            adjusted_weights[comp] = max(0.01, adjusted_weights[comp] + weight_shift)

        # Re-normalize to sum to 1.0
        sum_weights = sum(adjusted_weights.values())
        if sum_weights > 0:
            for k in adjusted_weights:
                adjusted_weights[k] = float(round(adjusted_weights[k] / sum_weights, 3))

        self.weights = adjusted_weights
        logger.info(f"Dynamically adjusted scoring weights: {self.weights}")
        return self.weights
