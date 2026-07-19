"""
Core Analytics Compute Engine.

Orchestrates technical analysis, option chain analytics, Greeks aggregation,
and the feature store pipeline for all tracked instruments.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List

import pandas as pd

from app.db.engine import get_async_session
from app.db.repositories.tick_repo import TickRepository
from app.db.repositories.option_chain_repo import OptionChainRepository
from app.services.cache.market_cache import MarketCache
from app.services.analytics.metrics_publisher import MetricsPublisher

# Technical Indicators
from app.services.analytics.technical.indicators import (
    compute_ema, compute_rsi, compute_atr, compute_adx, compute_macd,
    compute_bollinger_bands, compute_supertrend
)
from app.services.analytics.technical.vwap import compute_vwap
from app.services.analytics.technical.pivot_points import compute_daily_levels
from app.services.analytics.technical.market_structure import (
    detect_swings, detect_fvg, detect_bos_choch, detect_order_blocks, detect_liquidity_sweeps
)

# Option Analytics
from app.services.analytics.oi.pcr import compute_pcr
from app.services.analytics.oi.max_pain import compute_max_pain
from app.services.analytics.oi.gamma_exposure import compute_gamma_exposure
from app.services.analytics.oi.strike_analysis import analyze_strikes

# Feature store
from app.services.analytics.features.feature_pipeline import generate_feature_matrix
from app.services.intelligence.scoring_engine import ScoringEngine

logger = logging.getLogger(__name__)


class ComputeEngine:
    """Coordinates the execution of all analytical models and pipelines."""

    def __init__(
        self,
        market_cache: MarketCache,
        publisher: MetricsPublisher
    ) -> None:
        self._cache = market_cache
        self._publisher = publisher

    async def run_calculation_cycle(self, symbol: str) -> None:
        """
        Execute a full calculation cycle for a given underlying symbol.
        1. Fetch historical price data.
        2. Calculate technical indicators.
        3. Detect market structure.
        4. Load and process option chain.
        5. Generate features and publish.
        """
        logger.info(f"Starting compute cycle for {symbol}")

        try:
            # 1. Load history (last 500 minutes)
            now = datetime.now(timezone.utc)
            start = now - timedelta(days=2)  # Go back 2 days for continuous intraday context

            async with get_async_session() as session:
                tick_repo = TickRepository(session)
                chain_repo = OptionChainRepository(session)

                ticks = await tick_repo.get_ticks_in_range(symbol, start, now, limit=1000)
                chain = await chain_repo.get_latest_chain(symbol)

            if not ticks:
                logger.warning(f"No price tick history found for {symbol}, skipping calculation.")
                return

            # Construct DataFrame
            df = pd.DataFrame([
                {
                    "time": t.time,
                    "open": t.open or t.ltp,
                    "high": t.high or t.ltp,
                    "low": t.low or t.ltp,
                    "close": t.ltp,
                    "volume": t.volume or 0,
                    "oi": t.oi or 0
                }
                for t in ticks
            ])
            df.set_index("time", inplace=True)
            df.sort_index(inplace=True)

            if len(df) < 20:
                logger.warning(f"Insufficient candles ({len(df)}) for {symbol}")
                return

            # 2. Compute Technical Indicators
            close = df["close"]
            metrics = {
                "ema_9": float(compute_ema(close, 9).iloc[-1]),
                "ema_20": float(compute_ema(close, 20).iloc[-1]),
                "ema_50": float(compute_ema(close, 50).iloc[-1]),
                "ema_200": float(compute_ema(close, 200).iloc[-1]),
                "rsi_14": float(compute_rsi(close, 14).iloc[-1]),
                "atr_14": float(compute_atr(df, 14).iloc[-1]),
                "vwap": float(compute_vwap(df).iloc[-1]),
            }

            # ADX
            adx_df = compute_adx(df, 14)
            metrics["adx"] = float(adx_df["adx"].iloc[-1])
            metrics["plus_di"] = float(adx_df["plus_di"].iloc[-1])
            metrics["minus_di"] = float(adx_df["minus_di"].iloc[-1])

            # Bollinger
            bb_df = compute_bollinger_bands(close, 20, 2.0)
            metrics["bb_upper"] = float(bb_df["upper"].iloc[-1])
            metrics["bb_lower"] = float(bb_df["lower"].iloc[-1])

            # Supertrend
            st_df = compute_supertrend(df, 10, 3.0)
            metrics["supertrend"] = float(st_df["supertrend"].iloc[-1])
            metrics["supertrend_dir"] = float(st_df["direction"].iloc[-1])

            # 3. Market Structure detection
            swings = detect_swings(df, 5)
            fvgs = detect_fvg(df)
            bos_events = detect_bos_choch(df, swings)

            metrics["fvg_count"] = float(len(fvgs))
            metrics["bos_count"] = float(len(bos_events))

            # 4. Option Chain calculations
            spot_price = float(close.iloc[-1])
            if chain:
                # PCR
                pcr_data = compute_pcr(chain)
                metrics.update({
                    "pcr_oi": pcr_data["pcr_oi"],
                    "pcr_volume": pcr_data["pcr_volume"],
                })

                # Max Pain
                metrics["max_pain"] = compute_max_pain(chain)

                # GEX/DEX
                gex_data = compute_gamma_exposure(chain, spot_price, lot_size=50)
                metrics.update({
                    "net_gex": gex_data["net_gex"],
                    "net_dex": gex_data["net_dex"],
                })

                # Support/Resistance from OI
                oi_levels = analyze_strikes(chain)
                metrics.update({
                    "support_oi": oi_levels["support_oi"] or 0.0,
                    "resistance_oi": oi_levels["resistance_oi"] or 0.0,
                })

                # Cache chain matrix for frontend
                await self._cache.update_chain(
                    symbol,
                    [
                        {
                            "strike": s.strike,
                            "option_type": s.option_type,
                            "ltp": s.ltp,
                            "volume": s.volume,
                            "oi": s.oi,
                            "iv": s.iv,
                            "delta": s.delta,
                            "gamma": s.gamma,
                            "theta": s.theta,
                            "vega": s.vega,
                        }
                        for s in chain
                    ]
                )

            # 5. Generate 300+ Features Matrix
            pcr_history = pd.Series([metrics.get("pcr_oi", 0.5)] * len(df), index=df.index)
            gex_history = pd.Series([metrics.get("net_gex", 0.0)] * len(df), index=df.index)
            dex_history = pd.Series([metrics.get("net_dex", 0.0)] * len(df), index=df.index)

            feature_matrix = generate_feature_matrix(
                price_df=df,
                pcr_history=pcr_history,
                iv_history=None,
                gex_history=gex_history,
                dex_history=dex_history
            )

            # Extract latest feature row
            latest_features = feature_matrix.iloc[-1].to_dict()

            # 6. Compute Scores & Regimes
            scoring_engine = ScoringEngine()
            scores = scoring_engine.calculate_scores(metrics)
            await self._publisher.publish_scores(symbol, scores)

            # 7. Publish outputs
            await self._publisher.publish_metrics(symbol, metrics)
            await self._publisher.publish_features(symbol, latest_features)

            logger.info(f"Calculation cycle completed successfully for {symbol}")

        except Exception as e:
            logger.exception(f"Error in compute cycle for {symbol}: {e}")
