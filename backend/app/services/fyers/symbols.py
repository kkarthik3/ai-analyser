"""
FYERS symbol resolution and option chain symbol builder.

Handles:
  - Building option contract symbol names from underlying + strike + expiry
  - Smart strike selection (ATM ± N strikes within WebSocket limits)
  - Dynamic re-centering when spot price moves
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any, Optional

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# NSE option symbol format: NSE:NIFTY{YY}{MMM}{STRIKE}{CE/PE}
# Example: NSE:NIFTY24JUL24500CE

MONTH_MAP = {
    1: "JAN", 2: "FEB", 3: "MAR", 4: "APR", 5: "MAY", 6: "JUN",
    7: "JUL", 8: "AUG", 9: "SEP", 10: "OCT", 11: "NOV", 12: "DEC",
}

# Strike price step sizes for different underlyings
STRIKE_STEPS = {
    "NIFTY": 50,
    "NIFTY50": 50,
    "BANKNIFTY": 100,
    "NIFTYBANK": 100,
    "FINNIFTY": 50,
    "SENSEX": 100,
    "RELIANCE": 20,
    "TCS": 50,
    "HDFCBANK": 20,
    "INFY": 20,
    "ICICIBANK": 10,
}

# FYERS uses different names in option symbols vs index symbols.
# e.g. the index trades as "NSE:NIFTY50-INDEX" but options use "NIFTY" prefix.
OPTION_SYMBOL_PREFIX = {
    "NIFTY50": "NIFTY",
    "NIFTYBANK": "BANKNIFTY",
}


def get_option_prefix(underlying: str) -> str:
    """Return the FYERS option symbol prefix for an underlying.

    'NIFTY50'   → 'NIFTY'
    'NIFTYBANK' → 'BANKNIFTY'
    'FINNIFTY'  → 'FINNIFTY'
    'SENSEX'    → 'SENSEX'
    """
    return OPTION_SYMBOL_PREFIX.get(underlying, underlying)


def get_underlying_name(fyers_symbol: str) -> str:
    """Extract underlying name from FYERS symbol.

    'NSE:NIFTY50-INDEX' → 'NIFTY50'
    'NSE:NIFTYBANK-INDEX' → 'NIFTYBANK'
    'NSE:RELIANCE-EQ' → 'RELIANCE'
    """
    name = fyers_symbol.split(":")[-1]
    name = name.replace("-INDEX", "").replace("-EQ", "")
    return name


def get_strike_step(underlying: str) -> int:
    """Get the strike price step size for an underlying."""
    clean = underlying.replace("NSE:", "").replace("-INDEX", "").replace("-EQ", "")
    return STRIKE_STEPS.get(clean, 50)


def round_to_strike(price: float, step: int) -> float:
    """Round a price to the nearest strike price."""
    return round(price / step) * step


def get_nearest_expiry(
    underlying: str,
    reference_date: Optional[date] = None,
) -> date:
    """Calculate the nearest expiry date (Thursday for NSE).

    NSE weekly expiries:
      - NIFTY: Thursday
      - BANKNIFTY: Wednesday
      - FINNIFTY: Tuesday
      - SENSEX: Friday

    For simplicity, we default to Thursday and adjust if needed.
    """
    ref = reference_date or date.today()
    clean = get_underlying_name(underlying) if ":" in underlying else underlying

    # Expiry day of week (0=Monday, 6=Sunday)
    expiry_day = {
        "NIFTY": 3,      # Thursday
        "NIFTY50": 3,
        "BANKNIFTY": 2,   # Wednesday
        "NIFTYBANK": 2,
        "FINNIFTY": 1,    # Tuesday
        "SENSEX": 4,      # Friday
    }.get(clean, 3)

    # Find next expiry day
    days_ahead = expiry_day - ref.weekday()
    if days_ahead < 0:
        days_ahead += 7
    if days_ahead == 0:
        # If today is expiry, check if market is still open (before 3:30 PM)
        now = datetime.now()
        if now.hour >= 15 and now.minute >= 30:
            days_ahead = 7

    return ref + timedelta(days=days_ahead)


# SENSEX options trade on BSE, all others on NSE
_EXCHANGE_MAP: dict[str, str] = {
    "SENSEX": "BSE",
}


def build_option_symbols(
    underlying: str,
    spot_price: float,
    expiry: date,
    strike_count: int = 20,
    exchange: str = "NSE",
) -> dict[str, list[str]]:
    """Build option contract symbol names for an underlying.

    Returns a dict with 'calls', 'puts', and 'all' keys.

    Args:
        underlying: Clean underlying name (e.g., "NIFTY50", "NIFTYBANK")
        spot_price: Current spot price
        expiry: Expiry date
        strike_count: Number of strikes above and below ATM
        exchange: Exchange prefix override (auto-detected when not provided)
    """
    # Normalise to the prefix FYERS uses in option symbols
    # e.g. "NIFTY50" → "NIFTY", "NIFTYBANK" → "BANKNIFTY"
    option_prefix = get_option_prefix(underlying)

    # Auto-detect correct exchange for the underlying
    resolved_exchange = _EXCHANGE_MAP.get(option_prefix, exchange)

    step = get_strike_step(underlying)
    atm = round_to_strike(spot_price, step)

    # Generate strike range: ATM ± strike_count
    strikes = [atm + (i * step) for i in range(-strike_count, strike_count + 1)]

    # Format expiry: YY + MMM (e.g., "26JUL")
    yy = str(expiry.year)[-2:]
    mmm = MONTH_MAP[expiry.month]

    calls = []
    puts = []

    for strike in strikes:
        strike_str = str(int(strike))
        ce_symbol = f"{resolved_exchange}:{option_prefix}{yy}{mmm}{strike_str}CE"
        pe_symbol = f"{resolved_exchange}:{option_prefix}{yy}{mmm}{strike_str}PE"
        calls.append(ce_symbol)
        puts.append(pe_symbol)

    return {
        "calls": calls,
        "puts": puts,
        "all": calls + puts,
        "strikes": strikes,
        "atm": atm,
        "expiry": expiry.isoformat(),
        "option_prefix": option_prefix,
        "exchange": resolved_exchange,
    }


def select_websocket_symbols(
    underlyings: list[str],
    spot_prices: dict[str, float],
    max_symbols: int = 200,
    strikes_per_side: int = 10,
) -> list[str]:
    """Select symbols for WebSocket subscription within the symbol limit.

    Prioritizes ATM ± strikes_per_side for each underlying, plus
    the underlying index/equity symbols themselves.

    Args:
        underlyings: List of underlying symbols
        spot_prices: Current spot prices keyed by underlying
        max_symbols: Maximum WebSocket subscription limit
        strikes_per_side: Strikes above and below ATM per underlying
    """
    all_symbols = list(underlyings)  # Start with the underlyings themselves

    for underlying in underlyings:
        clean_name = get_underlying_name(underlying)
        spot = spot_prices.get(underlying) or spot_prices.get(clean_name)

        if not spot:
            logger.warning(f"No spot price for {underlying}, skipping option symbols")
            continue

        expiry = get_nearest_expiry(underlying)
        chain = build_option_symbols(
            clean_name,
            spot,
            expiry,
            strike_count=strikes_per_side,
        )
        all_symbols.extend(chain["all"])

        if len(all_symbols) >= max_symbols:
            logger.warning(
                f"Symbol limit ({max_symbols}) reached, truncating. "
                f"Total requested: {len(all_symbols)}"
            )
            return all_symbols[:max_symbols]

    logger.info(f"Selected {len(all_symbols)} symbols for WebSocket subscription")
    return all_symbols


def parse_option_symbol(symbol: str) -> Optional[dict[str, Any]]:
    """Parse a FYERS option symbol into its components.

    'NSE:NIFTY24JUL24500CE' → {
        'exchange': 'NSE',
        'underlying': 'NIFTY',
        'expiry_str': '24JUL',
        'strike': 24500.0,
        'option_type': 'CE'
    }
    """
    try:
        exchange, name = symbol.split(":")
        option_type = name[-2:]  # CE or PE

        if option_type not in ("CE", "PE"):
            return None

        # Find where the numeric strike begins
        name_without_type = name[:-2]
        strike_start = -1
        for i, char in enumerate(name_without_type):
            if char.isdigit() and i > 3:
                # Check if this is the strike (not part of expiry year)
                remaining = name_without_type[i:]
                if len(remaining) >= 3 and remaining.replace(".", "").isdigit():
                    strike_start = i
                    break

        if strike_start == -1:
            return None

        underlying_and_expiry = name_without_type[:strike_start]
        strike = float(name_without_type[strike_start:])

        # Split underlying and expiry (e.g., "NIFTY24JUL" → "NIFTY", "24JUL")
        # Find where the year digits start
        for i in range(len(underlying_and_expiry) - 1, -1, -1):
            if underlying_and_expiry[i].isalpha():
                expiry_str = underlying_and_expiry[i-1:] if i > 0 else ""
                underlying = underlying_and_expiry[:i-1] if i > 1 else underlying_and_expiry
                break
        else:
            return None

        return {
            "exchange": exchange,
            "underlying": underlying,
            "expiry_str": expiry_str,
            "strike": strike,
            "option_type": option_type,
            "full_symbol": symbol,
        }
    except Exception:
        return None
