"""
Strike analysis: Support, resistance, and liquidity zones from options data.
"""

from __future__ import annotations

import logging
from typing import Sequence

from app.db.models.option_chain import OptionChainSnapshot

logger = logging.getLogger(__name__)


def analyze_strikes(chain: Sequence[OptionChainSnapshot]) -> dict[str, any]:
    """
    Analyze option chain to identify support, resistance, strike concentration,
    and liquidity zones.
    """
    if not chain:
        return {
            "support_oi": None,
            "resistance_oi": None,
            "support_vol": None,
            "resistance_vol": None,
            "liquidity_zones": []
        }

    # Separate CE and PE
    ce_options = [o for o in chain if o.option_type == "CE"]
    pe_options = [o for o in chain if o.option_type == "PE"]

    # Key Support (Max Put OI Strike)
    support_oi = None
    if pe_options:
        max_pe_oi = max(pe_options, key=lambda o: o.oi or 0)
        support_oi = float(max_pe_oi.strike) if max_pe_oi.oi and max_pe_oi.oi > 0 else None

    # Key Resistance (Max Call OI Strike)
    resistance_oi = None
    if ce_options:
        max_ce_oi = max(ce_options, key=lambda o: o.oi or 0)
        resistance_oi = float(max_ce_oi.strike) if max_ce_oi.oi and max_ce_oi.oi > 0 else None

    # Volume-based levels
    support_vol = None
    if pe_options:
        max_pe_vol = max(pe_options, key=lambda o: o.volume or 0)
        support_vol = float(max_pe_vol.strike) if max_pe_vol.volume and max_pe_vol.volume > 0 else None

    resistance_vol = None
    if ce_options:
        max_ce_vol = max(ce_options, key=lambda o: o.volume or 0)
        resistance_vol = float(max_ce_vol.strike) if max_ce_vol.volume and max_ce_vol.volume > 0 else None

    # Identify Liquidity Zones (Strikes with both high volume and tight spreads)
    liquidity_zones = []
    sorted_options = sorted(chain, key=lambda o: (o.volume or 0), reverse=True)

    # Take top 5 high volume strikes with spreads
    for opt in sorted_options[:5]:
        spread = (opt.ask - opt.bid) if (opt.ask and opt.bid) else 0.0
        liquidity_zones.append({
            "strike": float(opt.strike),
            "option_type": opt.option_type,
            "volume": int(opt.volume or 0),
            "oi": int(opt.oi or 0),
            "spread": float(round(spread, 2))
        })

    return {
        "support_oi": support_oi,
        "resistance_oi": resistance_oi,
        "support_vol": support_vol,
        "resistance_vol": resistance_vol,
        "liquidity_zones": liquidity_zones
    }
