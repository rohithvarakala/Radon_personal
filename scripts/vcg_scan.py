"""Volatility-Credit Gap (VCG) Scanner — detects divergence between vol and credit.

Strategy:
    Volatility (VIX) and credit stress (HYG, high-yield bonds) normally move
    inversely: when fear rises (VIX up), risky bonds sell off (HYG down).
    When they diverge — VIX spikes but HYG stays flat, or HYG drops while
    VIX remains calm — one market is mispricing risk.

How it works:
    1. Fetch 1 month of VIX (^VIX) and HYG price history.
    2. Compute 5-day percentage changes for both.
    3. Calculate the gap: if VIX rises and HYG doesn't fall proportionally
       (or vice versa), there's a divergence.
    4. Assess the regime and suggest trades.

Interpretation:
    - VIX up + HYG flat/up → Credit is complacent. Buy put spreads on HYG
      or short credit via CDS proxies. Credit will catch up to vol.
    - VIX down + HYG flat/down → Vol is complacent. Buy VIX calls or
      volatility-linked instruments. Vol will catch up to credit stress.
    - VIX up + HYG down → Markets aligned. No divergence.
    - VIX down + HYG up → Markets aligned (risk-on). No divergence.

Gate 2 (Edge): Cross-asset vol dislocation is a specific, data-backed signal.

Usage:
    python vcg_scan.py
"""

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from clients.yahoo_client import YahooClient

# Thresholds
DIVERGENCE_THRESHOLD = 3.0  # minimum absolute gap (%) to flag divergence
VIX_TICKER = "^VIX"
HYG_TICKER = "HYG"
LOOKBACK_PERIOD = "1mo"
CHANGE_WINDOW = 5  # 5-day change


def compute_pct_change(prices: list[dict], window: int = 5) -> dict | None:
    """Compute percentage change over the last N trading days.

    Args:
        prices: List of OHLCV dicts with 'close' and 'date' keys.
        window: Number of days for the change calculation.

    Returns:
        Dict with start/end prices, dates, and pct_change, or None if
        insufficient data.
    """
    if not prices or len(prices) < window + 1:
        return None

    recent = prices[-1]
    prior = prices[-(window + 1)]

    end_price = recent["close"]
    start_price = prior["close"]

    if start_price == 0:
        return None

    pct_change = ((end_price - start_price) / start_price) * 100

    return {
        "start_date": prior["date"],
        "end_date": recent["date"],
        "start_price": start_price,
        "end_price": end_price,
        "pct_change": round(pct_change, 3),
    }


def compute_rolling_correlation(
    vix_prices: list[dict],
    hyg_prices: list[dict],
    window: int = 20,
) -> float | None:
    """Compute rolling correlation between VIX and HYG returns.

    Normally negative (fear up = credit down). A positive or near-zero
    correlation confirms divergence.

    Args:
        vix_prices: VIX OHLCV data.
        hyg_prices: HYG OHLCV data.
        window: Rolling window for correlation.

    Returns:
        Pearson correlation of daily returns over the window, or None.
    """
    vix_closes = [p["close"] for p in vix_prices]
    hyg_closes = [p["close"] for p in hyg_prices]

    # Align to minimum length
    min_len = min(len(vix_closes), len(hyg_closes))
    if min_len < window + 1:
        return None

    vix_closes = vix_closes[-min_len:]
    hyg_closes = hyg_closes[-min_len:]

    vix_returns = np.diff(np.log(np.array(vix_closes, dtype=float)))
    hyg_returns = np.diff(np.log(np.array(hyg_closes, dtype=float)))

    # Use last `window` returns
    vix_ret = vix_returns[-window:]
    hyg_ret = hyg_returns[-window:]

    if len(vix_ret) < window or len(hyg_ret) < window:
        return None

    corr_matrix = np.corrcoef(vix_ret, hyg_ret)
    return round(float(corr_matrix[0, 1]), 4)


def assess_regime(
    vix_change: float,
    hyg_change: float,
    gap: float,
    correlation: float | None,
) -> dict:
    """Classify the vol-credit regime and suggest trades.

    Args:
        vix_change: VIX 5-day % change.
        hyg_change: HYG 5-day % change.
        gap: Absolute divergence gap.
        correlation: Rolling VIX/HYG return correlation.

    Returns:
        Dict with regime, assessment, divergence_detected, and trade_ideas.
    """
    divergence_detected = gap >= DIVERGENCE_THRESHOLD

    if vix_change > 1.0 and hyg_change > -0.5:
        # VIX rising, HYG not falling — credit complacent
        regime = "CREDIT_COMPLACENT"
        assessment = (
            f"VIX up {vix_change:+.1f}% but HYG only {hyg_change:+.1f}%. "
            "Credit markets are not pricing in the volatility spike. "
            "Expect HYG to catch down."
        )
        trade_ideas = [
            "Buy HYG put spreads (bearish credit)",
            "Buy JNK puts (junk bond proxy)",
            "Short high-yield via leveraged inverse ETFs",
            "Sell credit call spreads on HYG",
        ]

    elif vix_change < -1.0 and hyg_change < 0.5:
        # VIX falling, HYG not rising — vol complacent
        regime = "VOL_COMPLACENT"
        assessment = (
            f"VIX down {vix_change:+.1f}% but HYG only {hyg_change:+.1f}%. "
            "Volatility has fallen but credit hasn't confirmed risk-on. "
            "Vol may be underpriced."
        )
        trade_ideas = [
            "Buy VIX call spreads (vol catch-up)",
            "Buy UVXY calls (leveraged vol)",
            "Buy SPY put spreads as hedge",
            "Sell put credit spreads on HYG (bullish credit conviction)",
        ]

    elif vix_change > 1.0 and hyg_change < -0.5:
        # Aligned: both pricing in risk
        regime = "ALIGNED_RISK_OFF"
        assessment = (
            f"VIX up {vix_change:+.1f}% and HYG down {hyg_change:+.1f}%. "
            "Both markets pricing in risk. No divergence to exploit."
        )
        trade_ideas = [
            "No VCG edge — markets aligned",
            "Consider tail hedges if move continues",
        ]

    elif vix_change < -1.0 and hyg_change > 0.5:
        # Aligned: both pricing in risk-on
        regime = "ALIGNED_RISK_ON"
        assessment = (
            f"VIX down {vix_change:+.1f}% and HYG up {hyg_change:+.1f}%. "
            "Both markets pricing in calm. No divergence."
        )
        trade_ideas = [
            "No VCG edge — markets aligned",
            "Consider vol as cheap insurance",
        ]

    else:
        # Neither moved enough
        regime = "NEUTRAL"
        assessment = (
            f"VIX {vix_change:+.1f}%, HYG {hyg_change:+.1f}%. "
            "Small moves — no significant divergence."
        )
        trade_ideas = ["No actionable signal"]

    return {
        "regime": regime,
        "divergence_detected": divergence_detected,
        "assessment": assessment,
        "trade_ideas": trade_ideas,
    }


def run_scan() -> dict:
    """Run the Volatility-Credit Gap scan.

    Fetches VIX and HYG data, computes divergence metrics,
    and returns a regime assessment.

    Returns:
        Dict with VIX/HYG data, gap metrics, regime, and trade suggestions.
    """
    client = YahooClient()
    result = {
        "scan": "volatility_credit_gap",
        "vix_ticker": VIX_TICKER,
        "hyg_ticker": HYG_TICKER,
    }

    # Fetch VIX history
    try:
        vix_prices = client.get_price_history(VIX_TICKER, period=LOOKBACK_PERIOD, interval="1d")
    except Exception as e:
        result["error"] = f"Failed to fetch VIX data: {e}"
        return result

    if not vix_prices or len(vix_prices) < CHANGE_WINDOW + 1:
        result["error"] = "Insufficient VIX price data"
        return result

    # Fetch HYG history
    try:
        hyg_prices = client.get_price_history(HYG_TICKER, period=LOOKBACK_PERIOD, interval="1d")
    except Exception as e:
        result["error"] = f"Failed to fetch HYG data: {e}"
        return result

    if not hyg_prices or len(hyg_prices) < CHANGE_WINDOW + 1:
        result["error"] = "Insufficient HYG price data"
        return result

    # Compute 5-day changes
    vix_change_data = compute_pct_change(vix_prices, window=CHANGE_WINDOW)
    hyg_change_data = compute_pct_change(hyg_prices, window=CHANGE_WINDOW)

    if not vix_change_data or not hyg_change_data:
        result["error"] = "Could not compute price changes"
        return result

    vix_change = vix_change_data["pct_change"]
    hyg_change = hyg_change_data["pct_change"]

    # The gap: if VIX up and HYG not down, they should offset
    # VIX up = positive, HYG down = negative. If both positive or both
    # near zero, there's a gap.
    gap = abs(vix_change + hyg_change)

    # Rolling correlation
    correlation = compute_rolling_correlation(vix_prices, hyg_prices)

    # Current levels
    result["vix_current"] = vix_prices[-1]["close"]
    result["hyg_current"] = hyg_prices[-1]["close"]
    result["vix_5d_change_pct"] = vix_change
    result["hyg_5d_change_pct"] = hyg_change
    result["divergence_gap"] = round(gap, 3)
    result["rolling_correlation_20d"] = correlation

    result["vix_detail"] = {
        "start_date": vix_change_data["start_date"],
        "end_date": vix_change_data["end_date"],
        "start": vix_change_data["start_price"],
        "end": vix_change_data["end_price"],
    }
    result["hyg_detail"] = {
        "start_date": hyg_change_data["start_date"],
        "end_date": hyg_change_data["end_date"],
        "start": hyg_change_data["start_price"],
        "end": hyg_change_data["end_price"],
    }

    # Regime assessment
    regime = assess_regime(vix_change, hyg_change, gap, correlation)
    result.update(regime)

    return result


def main():
    """CLI entry point for VCG scanner."""
    result = run_scan()
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
