"""
Scoring weights configuration profiles.
"""

from __future__ import annotations

# Weights for each score component (must sum to 1.0)
DEFAULT_WEIGHTS = {
    "trend": 0.15,
    "momentum": 0.15,
    "oi": 0.15,
    "greeks": 0.10,
    "volatility": 0.10,
    "structure": 0.10,
    "liquidity": 0.05,
    "risk": 0.05,
    "institutional": 0.08,
    "dealer": 0.07
}

AGGRESSIVE_WEIGHTS = {
    "trend": 0.10,
    "momentum": 0.25,
    "oi": 0.20,
    "greeks": 0.10,
    "volatility": 0.10,
    "structure": 0.10,
    "liquidity": 0.05,
    "risk": 0.02,
    "institutional": 0.05,
    "dealer": 0.03
}

CONSERVATIVE_WEIGHTS = {
    "trend": 0.20,
    "momentum": 0.10,
    "oi": 0.10,
    "greeks": 0.10,
    "volatility": 0.10,
    "structure": 0.15,
    "liquidity": 0.05,
    "risk": 0.10,
    "institutional": 0.05,
    "dealer": 0.05
}
