"""
Option chain fetcher — periodic REST-based poller.

Fetches the full option chain via FYERS REST API, computes Greeks
locally using Black-Scholes, and stores snapshots to TimescaleDB.
"""

from __future__ import annotations

import asyncio
import logging
import math
from datetime import date, datetime, timezone
from typing import Any, Optional

from scipy.optimize import brentq

from app.config import get_settings
from app.services.fyers.client import FyersClient
from app.services.fyers.symbols import get_nearest_expiry, get_underlying_name
from app.services.ingestion.snapshot_writer import SnapshotWriter

logger = logging.getLogger(__name__)
settings = get_settings()

# Risk-free rate (India 10Y govt bond yield, approximate)
RISK_FREE_RATE = 0.07


def _norm_cdf(x: float) -> float:
    """Standard normal cumulative distribution function."""
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def _norm_pdf(x: float) -> float:
    """Standard normal probability density function."""
    return math.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)


def _bs_price(
    spot: float,
    strike: float,
    time_to_expiry: float,
    rate: float,
    sigma: float,
    option_type: str,
) -> float:
    """Black-Scholes option price.

    Args:
        spot: Underlying price
        strike: Strike price
        time_to_expiry: Time to expiry in years
        rate: Risk-free rate
        sigma: Implied volatility
        option_type: 'CE' or 'PE'
    """
    if time_to_expiry <= 0 or sigma <= 0:
        # At/past expiry — return intrinsic value
        if option_type == "CE":
            return max(spot - strike, 0.0)
        else:
            return max(strike - spot, 0.0)

    d1 = (math.log(spot / strike) + (rate + 0.5 * sigma**2) * time_to_expiry) / (
        sigma * math.sqrt(time_to_expiry)
    )
    d2 = d1 - sigma * math.sqrt(time_to_expiry)

    if option_type == "CE":
        return spot * _norm_cdf(d1) - strike * math.exp(-rate * time_to_expiry) * _norm_cdf(d2)
    else:
        return strike * math.exp(-rate * time_to_expiry) * _norm_cdf(-d2) - spot * _norm_cdf(-d1)


def compute_iv(
    market_price: float,
    spot: float,
    strike: float,
    time_to_expiry: float,
    rate: float,
    option_type: str,
) -> Optional[float]:
    """Compute Implied Volatility using Brent's method.

    Returns None if IV cannot be solved (e.g., deep ITM with no time value).
    """
    if market_price <= 0 or time_to_expiry <= 0:
        return None

    try:
        iv = brentq(
            lambda sigma: _bs_price(spot, strike, time_to_expiry, rate, sigma, option_type)
            - market_price,
            0.01,  # Min IV 1%
            5.0,   # Max IV 500%
            xtol=1e-6,
            maxiter=100,
        )
        return iv
    except (ValueError, RuntimeError):
        return None


def compute_greeks(
    spot: float,
    strike: float,
    time_to_expiry: float,
    rate: float,
    sigma: float,
    option_type: str,
) -> dict[str, Optional[float]]:
    """Compute all option Greeks using Black-Scholes analytical formulas.

    Returns:
        Dict with delta, gamma, theta, vega, rho.
    """
    if time_to_expiry <= 0 or sigma <= 0:
        return {"delta": None, "gamma": None, "theta": None, "vega": None, "rho": None}

    sqrt_t = math.sqrt(time_to_expiry)
    d1 = (math.log(spot / strike) + (rate + 0.5 * sigma**2) * time_to_expiry) / (
        sigma * sqrt_t
    )
    d2 = d1 - sigma * sqrt_t

    # Gamma (same for calls and puts)
    gamma = _norm_pdf(d1) / (spot * sigma * sqrt_t)

    # Vega (same for calls and puts, per 1% move)
    vega = spot * sqrt_t * _norm_pdf(d1) / 100.0

    if option_type == "CE":
        delta = _norm_cdf(d1)
        theta = (
            -spot * _norm_pdf(d1) * sigma / (2 * sqrt_t)
            - rate * strike * math.exp(-rate * time_to_expiry) * _norm_cdf(d2)
        ) / 365.0  # Per day
        rho = strike * time_to_expiry * math.exp(-rate * time_to_expiry) * _norm_cdf(d2) / 100.0
    else:
        delta = _norm_cdf(d1) - 1
        theta = (
            -spot * _norm_pdf(d1) * sigma / (2 * sqrt_t)
            + rate * strike * math.exp(-rate * time_to_expiry) * _norm_cdf(-d2)
        ) / 365.0
        rho = -strike * time_to_expiry * math.exp(-rate * time_to_expiry) * _norm_cdf(-d2) / 100.0

    return {
        "delta": round(delta, 6),
        "gamma": round(gamma, 6),
        "theta": round(theta, 4),
        "vega": round(vega, 4),
        "rho": round(rho, 4),
    }


class OptionChainFetcher:
    """Fetches option chain via REST, computes Greeks, and writes to DB."""

    def __init__(
        self,
        fyers_client: FyersClient,
        snapshot_writer: SnapshotWriter,
    ) -> None:
        self._client = fyers_client
        self._writer = snapshot_writer

    async def fetch_and_process(
        self,
        underlying_symbol: str,
        spot_price: Optional[float] = None,
    ) -> list[dict[str, Any]]:
        """Fetch option chain, compute Greeks, and buffer for storage.

        Args:
            underlying_symbol: FYERS underlying symbol (e.g., 'NSE:NIFTY50-INDEX')
            spot_price: Current spot price (for Greeks computation)

        Returns:
            List of processed option chain records.
        """
        try:
            response = await self._client.get_option_chain(
                symbol=underlying_symbol,
                strike_count=settings.option_chain_strike_count,
            )

            if not response or response.get("s") != "ok":
                logger.warning(f"Option chain fetch failed for {underlying_symbol}: {response}")
                return []

            chain_data = response.get("data", {})
            options_chain = chain_data.get("optionsChain", [])
            expiry_data = chain_data.get("expiryData", [])

            if not options_chain:
                logger.warning(f"Empty option chain for {underlying_symbol}")
                return []

            # Get expiry date from response
            nearest_expiry = self._extract_expiry(expiry_data)
            if not nearest_expiry:
                nearest_expiry = get_nearest_expiry(underlying_symbol)

            # Use spot from response if not provided
            if not spot_price:
                spot_price = chain_data.get("spotPrice") or chain_data.get("ltp")

            if not spot_price:
                logger.warning(f"No spot price for {underlying_symbol}")
                return []

            # Process each strike
            now = datetime.now(timezone.utc)
            time_to_expiry = self._calculate_time_to_expiry(nearest_expiry)
            records = []

            for option in options_chain:
                for opt_type in ["CE", "PE"]:
                    opt_data = option.get(opt_type.lower()) or option.get(opt_type)
                    if not opt_data:
                        continue

                    strike = option.get("strikePrice") or opt_data.get("strikePrice", 0)
                    ltp = opt_data.get("ltp") or opt_data.get("lastPrice", 0)
                    symbol = opt_data.get("symbol", "")

                    # Compute IV
                    iv = compute_iv(
                        market_price=ltp,
                        spot=spot_price,
                        strike=strike,
                        time_to_expiry=time_to_expiry,
                        rate=RISK_FREE_RATE,
                        option_type=opt_type,
                    )

                    # Compute Greeks (using computed IV or fallback)
                    greeks = {"delta": None, "gamma": None, "theta": None, "vega": None, "rho": None}
                    if iv and iv > 0:
                        greeks = compute_greeks(
                            spot=spot_price,
                            strike=strike,
                            time_to_expiry=time_to_expiry,
                            rate=RISK_FREE_RATE,
                            sigma=iv,
                            option_type=opt_type,
                        )

                    # Compute intrinsic and time value
                    if opt_type == "CE":
                        intrinsic = max(spot_price - strike, 0)
                    else:
                        intrinsic = max(strike - spot_price, 0)
                    time_value = max(ltp - intrinsic, 0) if ltp else 0

                    record = {
                        "time": now,
                        "underlying": get_underlying_name(underlying_symbol),
                        "expiry": nearest_expiry,
                        "strike": strike,
                        "option_type": opt_type,
                        "symbol": symbol,
                        "ltp": ltp,
                        "bid": opt_data.get("bidPrice") or opt_data.get("bid", 0),
                        "ask": opt_data.get("askPrice") or opt_data.get("ask", 0),
                        "bid_qty": opt_data.get("bidQty") or opt_data.get("bidQuantity", 0),
                        "ask_qty": opt_data.get("askQty") or opt_data.get("askQuantity", 0),
                        "volume": opt_data.get("volume", 0),
                        "oi": opt_data.get("openInterest") or opt_data.get("oi", 0),
                        "change_oi": opt_data.get("changeinOpenInterest") or opt_data.get("changeInOI", 0),
                        "iv": iv,
                        **greeks,
                        "intrinsic_value": intrinsic,
                        "time_value": time_value,
                        "spot_price": spot_price,
                    }
                    records.append(record)

            # Buffer for batch write
            self._writer.buffer_chain(records)

            logger.debug(
                f"Processed {len(records)} options for {underlying_symbol} "
                f"(spot={spot_price}, expiry={nearest_expiry})"
            )
            return records

        except Exception as e:
            logger.error(f"Option chain processing error for {underlying_symbol}: {e}")
            return []

    def _extract_expiry(self, expiry_data: list) -> Optional[date]:
        """Extract nearest expiry date from FYERS response."""
        if not expiry_data:
            return None
        try:
            # Sort by date and return nearest
            sorted_expiries = sorted(expiry_data, key=lambda x: x.get("date", ""))
            nearest = sorted_expiries[0]
            expiry_ts = nearest.get("date") or nearest.get("expiry")
            if isinstance(expiry_ts, (int, float)):
                return datetime.fromtimestamp(expiry_ts).date()
            elif isinstance(expiry_ts, str):
                return datetime.strptime(expiry_ts, "%Y-%m-%d").date()
        except Exception:
            pass
        return None

    def _calculate_time_to_expiry(self, expiry: date) -> float:
        """Calculate time to expiry in years.

        Accounts for market hours (6.25 hours/day for NSE).
        """
        now = datetime.now()
        expiry_dt = datetime.combine(expiry, datetime.min.time().replace(hour=15, minute=30))
        delta = expiry_dt - now

        if delta.total_seconds() <= 0:
            return 0.0

        # Calendar days to years
        return delta.total_seconds() / (365.25 * 24 * 3600)
