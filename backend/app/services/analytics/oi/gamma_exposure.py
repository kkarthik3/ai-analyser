"""
Gamma Exposure (GEX) and Delta Exposure (DEX) calculations.

Estimates institutional dealer positioning and market support/resistance
levels from options open interest and Greeks.
"""

from __future__ import annotations

import logging
from typing import Sequence

from app.db.models.option_chain import OptionChainSnapshot

logger = logging.getLogger(__name__)


def compute_gamma_exposure(
    chain: Sequence[OptionChainSnapshot],
    spot_price: float,
    lot_size: int = 1
) -> dict[str, float]:
    """
    Compute total dealer Gamma Exposure (GEX) and Delta Exposure (DEX).
    Estimated assuming dealers are short CE and short PE (net option sellers).

    Formulas:
    Call GEX = Option Gamma * Open Interest * Spot * Lot Size
    Put GEX = Option Gamma * Open Interest * Spot * Lot Size * -1 (negative gamma)
    Net Dealer Gamma = Call GEX + Put GEX

    Call DEX = Option Delta * Open Interest * Spot * Lot Size
    Put DEX = Option Delta * Open Interest * Spot * Lot Size (Option Delta for PE is negative)
    Net Dealer Delta = Call DEX + Put DEX
    """
    if not chain or spot_price <= 0:
        return {"net_gex": 0.0, "net_dex": 0.0, "call_gex": 0.0, "put_gex": 0.0}

    total_call_gex = 0.0
    total_put_gex = 0.0
    total_call_dex = 0.0
    total_put_dex = 0.0

    for option in chain:
        oi = option.oi or 0
        gamma = option.gamma or 0.0
        delta = option.delta or 0.0

        if oi <= 0 or gamma <= 0:
            continue

        # Scale GEX and DEX for typical index/equity volume
        # GEX typically represents the dollar value of shares the dealers must trade per 1% move.
        # Dollar Gamma = 0.01 * Spot * Spot * Gamma * OI * Lot Size
        # Standard GEX = Gamma * OI * Lot Size * Spot
        exposure_factor = oi * lot_size * spot_price

        if option.option_type == "CE":
            # Dealer short Call -> positive gamma
            gex = gamma * exposure_factor
            dex = delta * exposure_factor
            total_call_gex += gex
            total_call_dex += dex
        elif option.option_type == "PE":
            # Dealer short Put -> negative gamma
            gex = -1 * gamma * exposure_factor
            dex = delta * exposure_factor  # Note: delta is already negative for Puts
            total_put_gex += gex
            total_put_dex += dex

    net_gex = total_call_gex + total_put_gex
    net_dex = total_call_dex + total_put_dex

    return {
        "net_gex": float(round(net_gex, 2)),
        "net_dex": float(round(net_dex, 2)),
        "call_gex": float(round(total_call_gex, 2)),
        "put_gex": float(round(total_put_gex, 2)),
        "call_dex": float(round(total_call_dex, 2)),
        "put_dex": float(round(total_put_dex, 2))
    }
