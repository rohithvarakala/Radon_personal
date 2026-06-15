"""LEAP IV Mispricing Scanner — finds underpriced long-dated options.

Strategy:
    LEAPs (Long-Term Equity Anticipation Securities) are options with
    expiration dates 6+ months out. When implied volatility (IV) on a LEAP
    is low relative to the stock's realized (historical) volatility, the
    option is potentially underpriced — you're buying volatility cheap.

How it works:
    1. Fetch 1 year of price history for each ticker.
    2. Compute annualized realized volatility from log returns.
    3. Get the furthest-out option expiration (LEAP territory).
    4. Extract ATM implied volatility from that expiry's chain.
    5. Compare: if realized_vol / implied_vol > 1.2, the LEAP looks cheap.
    6. Score and rank opportunities.

Gate 1 (Convexity): LEAPs are long options — defined risk, unlimited upside.
Gate 2 (Edge): Realized > implied vol is a specific, data-backed signal.

Usage:
    python leap_scanner.py AAPL NVDA TSLA --top 10
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from clients.yahoo_client import YahooClient

# Minimum ratio of realized_vol / implied_vol to flag as underpriced
MIN_VOL_RATIO = 1.2

# Minimum days to expiry for a LEAP
MIN_LEAP_DAYS = 180


def compute_realized_vol(prices: list[dict], window: int | None = None) -> float | None:
    """Compute annualized realized volatility from daily close prices.

    Uses log returns and annualizes by sqrt(252).

    Args:
        prices: List of OHLCV dicts with 'close' key.
        window: If set, use only the last N days. Otherwise use all data.

    Returns:
        Annualized realized volatility as a decimal, or None if insufficient data.
    """
    closes = [p["close"] for p in prices if p.get("close")]
    if window:
        closes = closes[-window:]
    if len(closes) < 20:
        return None

    closes_arr = np.array(closes, dtype=float)
    log_returns = np.diff(np.log(closes_arr))
    return float(np.std(log_returns, ddof=1) * np.sqrt(252))


def get_leap_iv(client: YahooClient, symbol: str) -> dict | None:
    """Get ATM implied volatility for the furthest-out expiration.

    Returns dict with expiry, days_to_expiry, atm_call_iv, atm_put_iv, avg_iv,
    or None if no LEAP expiry is available.
    """
    try:
        expirations = client.get_all_expirations(symbol)
    except Exception:
        return None

    if not expirations:
        return None

    # Find the furthest expiration that qualifies as a LEAP (6+ months out)
    today = datetime.now().date()
    leap_expiry = None
    for exp_str in reversed(expirations):
        try:
            exp_date = datetime.strptime(exp_str, "%Y-%m-%d").date()
            days_out = (exp_date - today).days
            if days_out >= MIN_LEAP_DAYS:
                leap_expiry = exp_str
                break
        except ValueError:
            continue

    if not leap_expiry:
        # Fall back to furthest available if none qualifies as LEAP
        leap_expiry = expirations[-1]

    exp_date = datetime.strptime(leap_expiry, "%Y-%m-%d").date()
    days_to_expiry = (exp_date - today).days

    # Get ATM IV for that expiry
    try:
        chain = client.get_option_chain(symbol, expiry=leap_expiry)
    except Exception:
        return None

    # Get current price
    try:
        info = client.get_stock_info(symbol)
        current_price = info.get("price")
    except Exception:
        current_price = None

    if not current_price:
        return None

    atm_call_iv = None
    atm_put_iv = None

    calls = chain.get("calls", [])
    if calls:
        # Find ATM call (closest strike to current price)
        best = min(calls, key=lambda c: abs(c.get("strike", 0) - current_price))
        atm_call_iv = best.get("impliedVolatility")

    puts = chain.get("puts", [])
    if puts:
        best = min(puts, key=lambda p: abs(p.get("strike", 0) - current_price))
        atm_put_iv = best.get("impliedVolatility")

    ivs = [v for v in [atm_call_iv, atm_put_iv] if v is not None and v > 0]
    avg_iv = sum(ivs) / len(ivs) if ivs else None

    return {
        "expiry": leap_expiry,
        "days_to_expiry": days_to_expiry,
        "atm_call_iv": round(atm_call_iv, 4) if atm_call_iv else None,
        "atm_put_iv": round(atm_put_iv, 4) if atm_put_iv else None,
        "avg_iv": round(avg_iv, 4) if avg_iv else None,
    }


def scan_ticker(client: YahooClient, symbol: str) -> dict:
    """Run LEAP IV mispricing analysis for a single ticker.

    Returns a dict with ticker, realized_vol, implied_vol, vol_ratio,
    score, signal, and supporting details.
    """
    result = {
        "ticker": symbol.upper(),
        "signal": "NO_DATA",
        "score": 0,
    }

    # Step 1: Get 1 year of price history
    try:
        prices = client.get_price_history(symbol, period="1y", interval="1d")
    except Exception as e:
        result["error"] = f"Price history failed: {e}"
        return result

    if not prices or len(prices) < 60:
        result["error"] = "Insufficient price history"
        return result

    # Step 2: Compute realized volatility
    realized_vol = compute_realized_vol(prices)
    if realized_vol is None:
        result["error"] = "Could not compute realized vol"
        return result

    result["realized_vol"] = round(realized_vol, 4)

    # Step 3: Get LEAP IV
    leap_data = get_leap_iv(client, symbol)
    if not leap_data or not leap_data.get("avg_iv"):
        result["error"] = "No LEAP IV data available"
        return result

    implied_vol = leap_data["avg_iv"]
    result["implied_vol"] = implied_vol
    result["leap_expiry"] = leap_data["expiry"]
    result["days_to_expiry"] = leap_data["days_to_expiry"]
    result["atm_call_iv"] = leap_data["atm_call_iv"]
    result["atm_put_iv"] = leap_data["atm_put_iv"]

    # Step 4: Compute vol ratio and score
    if implied_vol > 0:
        vol_ratio = realized_vol / implied_vol
    else:
        vol_ratio = 0

    result["vol_ratio"] = round(vol_ratio, 4)

    # Score: 0-100 based on how much realized exceeds implied
    # ratio 1.0 = 0 score, ratio 2.0 = 100 score, linear between
    raw_score = max(0, min(100, (vol_ratio - 1.0) * 100))
    result["score"] = round(raw_score, 1)

    # Signal classification
    if vol_ratio >= 1.5:
        result["signal"] = "STRONG_BUY"
        result["assessment"] = (
            f"Realized vol ({realized_vol:.1%}) greatly exceeds LEAP IV "
            f"({implied_vol:.1%}). LEAP options appear significantly underpriced."
        )
    elif vol_ratio >= MIN_VOL_RATIO:
        result["signal"] = "BUY"
        result["assessment"] = (
            f"Realized vol ({realized_vol:.1%}) exceeds LEAP IV "
            f"({implied_vol:.1%}) by meaningful margin. LEAP may be underpriced."
        )
    elif vol_ratio >= 1.0:
        result["signal"] = "MONITOR"
        result["assessment"] = (
            f"Realized vol ({realized_vol:.1%}) slightly above LEAP IV "
            f"({implied_vol:.1%}). No strong mispricing yet."
        )
    else:
        result["signal"] = "NO_EDGE"
        result["assessment"] = (
            f"Implied vol ({implied_vol:.1%}) exceeds realized vol "
            f"({realized_vol:.1%}). LEAPs look fairly priced or overpriced."
        )

    # Get current price for context
    try:
        info = client.get_stock_info(symbol)
        result["price"] = info.get("price")
    except Exception:
        pass

    return result


def run_scan(tickers: list[str], top: int = 10) -> list[dict]:
    """Run LEAP mispricing scan across a list of tickers.

    Args:
        tickers: List of ticker symbols.
        top: Number of top results to return.

    Returns:
        List of results sorted by score (descending).
    """
    client = YahooClient()
    results = []

    for ticker in tickers:
        try:
            result = scan_ticker(client, ticker)
            results.append(result)
        except Exception as e:
            results.append({
                "ticker": ticker.upper(),
                "signal": "ERROR",
                "score": 0,
                "error": str(e),
            })

    results.sort(key=lambda r: r.get("score", 0), reverse=True)
    return results[:top]


def main():
    """CLI entry point for LEAP IV mispricing scanner."""
    top = 10
    args = sys.argv[1:]

    # Parse --top flag
    if "--top" in args:
        idx = args.index("--top")
        if idx + 1 < len(args):
            top = int(args[idx + 1])
        args = [a for i, a in enumerate(args) if i != idx and i != idx + 1]

    # Remaining args are tickers
    tickers = [a.upper() for a in args if not a.startswith("--")]

    if not tickers:
        print(json.dumps({"error": "No tickers provided. Usage: python leap_scanner.py AAPL NVDA TSLA --top 10"}))
        sys.exit(1)

    results = run_scan(tickers, top=top)
    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()
