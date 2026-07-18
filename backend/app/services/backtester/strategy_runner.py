"""
Strategy Runner.

Simulates strategy execution: runs Buy and Exit engines against replayed data feeds,
managing virtual cash, positions, and filled trades.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Dict, Any

from app.services.intelligence.scoring_engine import ScoringEngine
from app.services.intelligence.buy_engine import BuyEngine
from app.services.intelligence.exit_engine import ExitEngine

logger = logging.getLogger(__name__)


class StrategyRunner:
    """Executes virtual trading transactions on historical feeds."""

    def __init__(self, initial_capital: float = 100000.0) -> None:
        self.capital = initial_capital
        self.balance = initial_capital
        self.positions: List[Dict[str, Any]] = []
        self.trade_history: List[Dict[str, Any]] = []

        self.scoring_engine = ScoringEngine()
        self.buy_engine = BuyEngine()
        self.exit_engine = ExitEngine()

    def run_event(self, event: Dict[str, Any], metrics: Dict[str, float]) -> None:
        """
        Process a single feed event (TICK or OPTION_CHAIN).
        """
        event_time = event["time"]
        event_type = event["type"]

        # Update open positions valuation on Tick events
        if event_type == "TICK":
            spot = event["ltp"]
            symbol = event["symbol"]

            # Evaluate exits
            active_positions = []
            for pos in self.positions:
                if pos["symbol"] == symbol:
                    # Update position ltp
                    pos["ltp"] = spot

                    # Calculate scoring for exit check
                    scores = self.scoring_engine.calculate_scores(metrics)

                    exit_check = self.exit_engine.evaluate_exit(pos, metrics, scores)

                    if exit_check["action"] == "FULL_EXIT":
                        # Sell / Close position
                        pnl = (spot - pos["entry_price"]) * pos["qty"]
                        self.balance += spot * pos["qty"]

                        self.trade_history.append({
                            "symbol": symbol,
                            "direction": pos["direction"],
                            "entry_time": pos["entry_time"],
                            "exit_time": event_time,
                            "entry_price": pos["entry_price"],
                            "exit_price": spot,
                            "qty": pos["qty"],
                            "pnl": pnl,
                            "pnl_pct": ((spot - pos["entry_price"]) / pos["entry_price"]) * 100,
                            "reason": exit_check["reason"]
                        })
                        logger.info(f"Closed trade P&L: {pnl:.2f}")
                    else:
                        active_positions.append(pos)
                else:
                    active_positions.append(pos)
            self.positions = active_positions

            # Evaluate entry
            if not self.positions:
                scores = self.scoring_engine.calculate_scores(metrics)
                signal = self.buy_engine.evaluate_opportunity(symbol, metrics, scores)

                if signal["direction"] in ("BUY_CE", "BUY_PE"):
                    # Calculate quantity based on capital allocation
                    # Virtual 1 lot size = 50 qty
                    lot_cost = spot * 50
                    if self.balance >= lot_cost:
                        self.balance -= lot_cost
                        self.positions.append({
                            "symbol": symbol,
                            "direction": signal["direction"],
                            "entry_price": spot,
                            "entry_time": event_time,
                            "qty": 50,
                            "ltp": spot,
                            "max_drawdown_limit": -15.0,
                            "target_pct": 30.0
                        })
                        logger.info(f"Opened position at {spot} ({signal['direction']})")
