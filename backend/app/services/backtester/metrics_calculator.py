"""
Backtest Metrics Calculator.

Computes trade statistics: Win Rate, Profit Factor, Sharpe Ratio,
Sortino Ratio, and Max Drawdown.
"""

from __future__ import annotations

import logging
from typing import List, Dict, Any

import numpy as np

logger = logging.getLogger(__name__)


def calculate_backtest_metrics(trades: List[Dict[str, Any]], initial_capital: float = 100000.0) -> Dict[str, Any]:
    """
    Calculate performance metrics from a list of completed trades.
    """
    if not trades:
        return {
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "sharpe_ratio": 0.0,
            "sortino_ratio": 0.0,
            "max_drawdown": 0.0,
            "total_pnl": 0.0,
            "trade_count": 0
        }

    pnls = [t["pnl"] for t in trades]
    pnl_pcts = [t["pnl_pct"] for t in trades]

    total_pnl = sum(pnls)

    # Win Rate
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    win_rate = len(wins) / len(trades) if trades else 0.0

    # Profit Factor
    gross_profits = sum(wins)
    gross_losses = abs(sum(losses))
    profit_factor = gross_profits / gross_losses if gross_losses > 0 else float("inf")

    # Sharpe & Sortino (assuming risk free rate = 0 for trade sequence metrics)
    mean_return = np.mean(pnl_pcts) if pnl_pcts else 0.0
    std_return = np.std(pnl_pcts) if len(pnl_pcts) > 1 else 1.0

    sharpe = (mean_return / std_return) * np.sqrt(252) if std_return > 0 else 0.0

    neg_returns = [r for r in pnl_pcts if r < 0]
    std_neg = np.std(neg_returns) if len(neg_returns) > 1 else 1.0
    sortino = (mean_return / std_neg) * np.sqrt(252) if std_neg > 0 else 0.0

    # Max Drawdown
    equity_curve = initial_capital + np.cumsum(pnls)
    peak = initial_capital
    max_dd = 0.0

    for eq in equity_curve:
        if eq > peak:
            peak = eq
        dd = (peak - eq) / peak * 100
        if dd > max_dd:
            max_dd = dd

    # Average Holding Time
    holding_times = []
    for t in trades:
        duration = t["exit_time"] - t["entry_time"]
        holding_times.append(duration.total_seconds() / 60.0)  # in minutes
    avg_hold_min = np.mean(holding_times) if holding_times else 0.0

    return {
        "win_rate": float(round(win_rate * 100, 2)),
        "profit_factor": float(round(profit_factor, 2)) if profit_factor != float("inf") else 999.0,
        "sharpe_ratio": float(round(sharpe, 2)),
        "sortino_ratio": float(round(sortino, 2)),
        "max_drawdown": float(round(max_dd, 2)),
        "total_pnl": float(round(total_pnl, 2)),
        "trade_count": len(trades),
        "avg_holding_time_minutes": float(round(avg_hold_min, 1))
    }
