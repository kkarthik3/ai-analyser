"""
Backtest Report Generator.

Compiles backtest runs and trade logs into serialized summary files.
"""

from __future__ import annotations

import logging
from typing import Dict, Any, List

from app.services.backtester.metrics_calculator import calculate_backtest_metrics

logger = logging.getLogger(__name__)


def generate_backtest_report(
    symbol: str,
    trades: List[Dict[str, Any]],
    initial_capital: float = 100000.0
) -> Dict[str, Any]:
    """
    Format a complete backtest execution report.
    """
    metrics = calculate_backtest_metrics(trades, initial_capital)

    return {
        "symbol": symbol,
        "initial_capital": initial_capital,
        "final_capital": initial_capital + metrics["total_pnl"],
        "metrics": metrics,
        "trades": [
            {
                "direction": t["direction"],
                "entry_time": t["entry_time"].isoformat(),
                "exit_time": t["exit_time"].isoformat(),
                "entry_price": float(t["entry_price"]),
                "exit_price": float(t["exit_price"]),
                "qty": int(t["qty"]),
                "pnl": float(t["pnl"]),
                "pnl_pct": float(t["pnl_pct"]),
                "reason": t["reason"]
            }
            for t in trades
        ]
    }
