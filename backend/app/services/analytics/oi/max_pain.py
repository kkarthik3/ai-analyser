"""
Max Pain calculation engine.
Calculates the strike price where option buyers experience maximum pain
(i.e., where sellers experience the minimum loss upon expiry).
"""

from __future__ import annotations

import logging
from typing import Sequence

from app.db.models.option_chain import OptionChainSnapshot

logger = logging.getLogger(__name__)


def compute_max_pain(chain: Sequence[OptionChainSnapshot]) -> float:
    """
    Compute the Max Pain strike price.
    Calculates total cash loss for option sellers at each candidate strike.
    """
    if not chain:
        return 0.0

    # Extract unique strikes and sort them
    strikes = sorted(list(set(option.strike for option in chain)))
    if not strikes:
        return 0.0

    min_loss = float("inf")
    max_pain_strike = strikes[0]

    # Calculate loss at each strike
    for candidate_strike in strikes:
        total_loss = 0.0

        for option in chain:
            oi = option.oi or 0
            if oi <= 0:
                continue

            strike = option.strike
            opt_type = option.option_type

            if opt_type == "CE":
                # In-the-money Call option sellers lose money if market expires above strike
                if candidate_strike > strike:
                    total_loss += (candidate_strike - strike) * oi
            elif opt_type == "PE":
                # In-the-money Put option sellers lose money if market expires below strike
                if candidate_strike < strike:
                    total_loss += (strike - candidate_strike) * oi

        if total_loss < min_loss:
            min_loss = total_loss
            max_pain_strike = candidate_strike

    return float(max_pain_strike)
