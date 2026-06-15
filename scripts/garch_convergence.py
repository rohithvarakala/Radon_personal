"""GARCH-style Vol Convergence Scanner — finds mean-reversion vol opportunities.

Strategy:
    Volatility is mean-reverting. When short-term realized vol diverges
    significantly from long-term realized vol, expect convergence. This
    scanner identifies stocks where:
    - Short-term vol (10d) spikes above long-term vol (60d): vol likely
      to compress — sell premium, use credit spreads.
    - Short-term vol (10d) drops below long-term vol (60d): vol likely
      to expand — buy premium, use debit spreads or straddles.
    Additionally, comparing realized vol to implied vol (from ATM options)
    reveals whether the market has already priced in the vol regime shift.

How it works:
    1. Fetch 6 months of price history for each ticker.
    2. Compute short-term (10d) and long-term (60d) realized volatility.
    3. Calculate vol ratio (short/long) — deviation from 1.0 is the signal.
    4. Get ATM implied vol and compare to realized vol.
    5. Score by total divergence magnitude.

Gate 2 (Edge): Cross-asset vol dislocation and vol regime shifts are
specific, data-backed signals.

Usage:
    python garch_convergence.py AAPL NVDA TSLA
"""

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from clients.yahoo_client import YahooClient

# Lookback windows (trading days)
SHORT_WINDOW = 10
LONG_WINDOW = 60

# Minimum vol ratio divergence to flag
MIN_DIVERGENCE = 0.3  # 30% deviation from 1.0


def compute_realized_vol(closes: list[float], window: int) -> float | None:
    """Compute annualized realized volatility over a window.

    Args:
        closes: List of closing prices.
        window: Number of days to use.

    Returns:
        Annualized realized vol as a decimal, or None if insufficient data.
    """
    if len(closes) < window + 1:
        return None

    subset = closes[-window:]
    arr = np.array(subset, dtype=float)
    log_returns = np.diff(np.log(arr))

    if len(log_returns) < 2:
        return None

    return float(np.std(log_returns, ddof=1) * np.sqrt(252))


def compute_vol_trend(closes: list[float], window: int, n_periods: int = 4) -> str:
    """Determine whether realized vol is trending up, down, or flat.

    Splits the data into n_periods non-overlapping chunks and checks
    whether vol is increasing or decreasing across them.

    Args:
        closes: Full list of closing prices.
        window: Window size for each vol measurement.
        n_periods: Number of non-overlapping periods to compare.

    Returns:
        "RISING", "FALLING", or "FLAT".
    """
    required = window * n_periods + 1
    if len(closes) < required:
        return "UNKNOWN"

    vols = []
    for i in range(n_periods):
        end_idx = len(closes) - i * window
        start_idx = end_idx - window
        if start_idx < 0:
            break
        subset = closes[start_idx:end_idx]
        arr = np.array(subset, dtype=float)
        log_ret = np.diff(np.log(arr))
        if len(log_ret) >= 2:
            vols.append(float(np.std(log_ret, ddof=1) * np.sqrt(252)))

    vols.reverse()  # chronological order

    if len(vols) < 2:
        return "UNKNOWN"

    # Simple trend: compare first half avg to second half avg
    mid = len(vols) // 2
    first_half = np.mean(vols[:mid])
    second_half = np.mean(vols[mid:])

    change = (second_half - first_half) / first_half if first_half > 0 else 0

    if change > 0.15:
        return "RISING"
    elif change < -0.15:
        return "FALLING"
    else:
        return "FLAT"


def scan_ticker(client: YahooClient, symbol: str) -> dict:
    """Run GARCH-style vol convergence analysis for a single ticker.

    Returns a dict with short/long realized vol, implied vol, divergence
    scores, vol trend, and trade suggestions.
    """
    result = {
        "ticker": symbol.upper(),
        "signal": "NO_DATA",
        "score": 0,
    }

    # Step 1: Fetch 6 months of history (need enough for 60d window + trend)
    try:
        prices = client.get_price_history(symbol, period="6mo", interval="1d")
    except Exception as e:
        result["error"] = f"Price history failed: {e}"
        return result

    if not prices or len(prices) < LONG_WINDOW + 10:
        result["error"] = "Insufficient price history"
        return result

    closes = [p["close"] for p in prices if p.get("close")]

    # Step 2: Compute short-term and long-term realized vol
    short_vol = compute_realized_vol(closes, SHORT_WINDOW)
    long_vol = compute_realized_vol(closes, LONG_WINDOW)

    if short_vol is None or long_vol is None:
        result["error"] = "Could not compute realized vol"
        return result

    result["short_vol_10d"] = round(short_vol, 4)
    result["long_vol_60d"] = round(long_vol, 4)

    # Step 3: Vol ratio — deviation from 1.0 is the mean-reversion signal
    if long_vol > 0:
        vol_ratio = short_vol / long_vol
    else:
        vol_ratio = 1.0

    result["vol_ratio_short_long"] = round(vol_ratio, 4)

    # Vol trend
    vol_trend = compute_vol_trend(closes, SHORT_WINDOW)
    result["vol_trend"] = vol_trend

    # Step 4: Get implied vol for comparison
    implied_vol = None
    try:
        iv_data = client.get_iv_data(symbol)
        implied_vol = iv_data.get("avg_atm_iv")
        if implied_vol:
            result["implied_vol_atm"] = implied_vol
    except Exception:
        result["iv_note"] = "Could not fetch implied vol"

    # Realized vs implied divergence
    rv_iv_ratio = None
    if implied_vol and implied_vol > 0 and short_vol:
        rv_iv_ratio = short_vol / implied_vol
        result["rv_iv_ratio"] = round(rv_iv_ratio, 4)

    # Step 5: Score — based on vol ratio divergence + RV/IV divergence
    # Vol ratio divergence from 1.0
    vol_divergence = abs(vol_ratio - 1.0)

    # RV/IV divergence from 1.0
    iv_divergence = abs(rv_iv_ratio - 1.0) if rv_iv_ratio else 0

    # Combined score: 0-100
    # Weight vol ratio divergence 60%, IV divergence 40%
    raw_score = (vol_divergence * 60 + iv_divergence * 40)
    # Cap at 100
    score = min(100, round(raw_score * 100 / 60, 1))  # normalize so ~0.6 div = 100
    result["score"] = score

    # Step 6: Signal classification and trade suggestions
    if vol_ratio > 1.0 + MIN_DIVERGENCE:
        # Short-term vol elevated — expect compression
        result["signal"] = "VOL_COMPRESSION"
        result["assessment"] = (
            f"Short-term vol ({short_vol:.1%}) is {(vol_ratio - 1) * 100:.0f}% above "
            f"long-term vol ({long_vol:.1%}). Expect mean-reversion downward."
        )
        result["trade_ideas"] = [
            "Sell iron condors (neutral, vol compression)",
            "Sell put/call credit spreads",
            "Short straddle/strangle (if comfortable with risk)",
            "Calendar spreads — sell front-month elevated vol",
        ]

        if rv_iv_ratio and rv_iv_ratio > 1.2:
            result["iv_assessment"] = (
                f"IV ({implied_vol:.1%}) hasn't caught up to realized vol "
                f"({short_vol:.1%}). Market may be underpricing current vol."
            )
        elif rv_iv_ratio and rv_iv_ratio < 0.8:
            result["iv_assessment"] = (
                f"IV ({implied_vol:.1%}) already exceeds realized vol "
                f"({short_vol:.1%}). Premium selling may be well-timed."
            )

    elif vol_ratio < 1.0 - MIN_DIVERGENCE:
        # Short-term vol depressed — expect expansion
        result["signal"] = "VOL_EXPANSION"
        result["assessment"] = (
            f"Short-term vol ({short_vol:.1%}) is {(1 - vol_ratio) * 100:.0f}% below "
            f"long-term vol ({long_vol:.1%}). Expect mean-reversion upward."
        )
        result["trade_ideas"] = [
            "Buy straddles/strangles (vol expansion play)",
            "Buy debit spreads (directional with vol tailwind)",
            "Buy calendar spreads — buy back-month cheap vol",
            "Long gamma strategies",
        ]

        if rv_iv_ratio and rv_iv_ratio < 0.8:
            result["iv_assessment"] = (
                f"IV ({implied_vol:.1%}) exceeds depressed realized vol "
                f"({short_vol:.1%}). Options may already price in expansion."
            )
        elif rv_iv_ratio and rv_iv_ratio > 1.2:
            result["iv_assessment"] = (
                f"IV ({implied_vol:.1%}) is low like realized vol "
                f"({short_vol:.1%}). Cheap vol across the board — good entry."
            )

    else:
        result["signal"] = "NEUTRAL"
        result["assessment"] = (
            f"Short-term vol ({short_vol:.1%}) is aligned with "
            f"long-term vol ({long_vol:.1%}). No mean-reversion signal."
        )
        result["trade_ideas"] = ["No strong vol convergence edge"]

    # Add current price for context
    try:
        info = client.get_stock_info(symbol)
        result["price"] = info.get("price")
    except Exception:
        pass

    return result


def run_scan(tickers: list[str]) -> list[dict]:
    """Run GARCH-style vol convergence scan across tickers.

    Args:
        tickers: List of ticker symbols.

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
    return results


def main():
    """CLI entry point for GARCH-style vol convergence scanner."""
    args = sys.argv[1:]

    # Filter out flags (future-proof)
    tickers = [a.upper() for a in args if not a.startswith("--")]

    if not tickers:
        print(json.dumps({
            "error": "No tickers provided. Usage: python garch_convergence.py AAPL NVDA TSLA"
        }))
        sys.exit(1)

    results = run_scan(tickers)
    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()
