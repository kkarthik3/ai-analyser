"""
PCR (Put-Call Ratio) calculations.
"""

from __future__ import annotations

import logging
from typing import Any, Sequence

from app.db.models.option_chain import OptionChainSnapshot

logger = logging.getLogger(__name__)


def compute_pcr(chain: Sequence[OptionChainSnapshot]) -> dict[str, float]:
    """
    Compute Put-Call Ratio (PCR) from a sequence of option chain rows.
    Returns both OI-based and Volume-based PCR.
    """
    total_ce_oi = 0
    total_pe_oi = 0
    total_ce_vol = 0
    total_pe_vol = 0

    for option in chain:
        if option.option_type == "CE":
            total_ce_oi += option.oi or 0
            total_ce_vol += option.volume or 0
        elif option.option_type == "PE":
            total_pe_oi += option.oi or 0
            total_pe_vol += option.volume or 0

    pcr_oi = total_pe_oi / total_ce_oi if total_ce_oi > 0 else 0.0
    pcr_volume = total_pe_vol / total_ce_vol if total_ce_vol > 0 else 0.0

    return {
        "pcr_oi": float(round(pcr_oi, 4)),
        "pcr_volume": float(round(pcr_volume, 4)),
        "total_ce_oi": int(total_ce_oi),
        "total_pe_oi": int(total_pe_oi),
        "total_ce_volume": int(total_ce_vol),
        "total_pe_volume": int(total_pe_vol)
    }
