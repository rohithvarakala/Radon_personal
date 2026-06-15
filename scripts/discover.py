"""Market-wide candidate discovery scanner.

Scans a broad list of popular/liquid tickers to find ones with
interesting options signals. Uses ThreadPoolExecutor (10 workers).
Each ticker is scored 0-100 based on signal strength and sorted
by discovery_score descending.
"""

import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from clients.yahoo_client import YahooClient

DEFAULT_WORKERS = 10
DEFAULT_TOP = 20

# Broad, liquid universe — large-cap + popular mid-cap + meme/vol names
SCAN_UNIVERSE = [
    # Mega-cap tech
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA",
    # Semiconductors
    "AMD", "INTC", "AVGO", "MU", "QCOM", "MRVL", "ARM",
    # Software / cloud
    "CRM", "ORCL", "ADBE", "NOW", "SNOW", "PLTR", "NET",
    # Financials
    "JPM", "BAC", "GS", "MS", "WFC", "C", "SCHW",
    # Healthcare / biotech
    "JNJ", "UNH", "PFE", "ABBV", "MRK", "LLY", "MRNA",
    # Energy
    "XOM", "CVX", "COP", "SLB", "OXY",
    # Consumer
    "DIS", "NFLX", "SBUX", "NKE", "MCD", "WMT", "COST", "TGT",
    # Industrials / defense
    "BA", "CAT", "LMT", "RTX", "GE", "HON",
    # EV / clean energy
    "RIVN", "LCID", "ENPH", "FSLR",
    # Crypto-adjacent
    "COIN", "MARA", "RIOT",
    # High-vol / meme
    "GME", "AMC", "SOFI", "HOOD",
    # ETFs with options volume
    "SPY", "QQQ", "IWM", "XLF", "XLE", "GLD", "TLT", "HYG",
]


# ---------------------------------------------------------------------------
# Signal interpretation
# ---------------------------------------------------------------------------

def _classify_put_call(ratio: float | None) -> str:
    if ratio is None:
        return "NO_DATA"
    if ratio > 2.0:
        return "BEARISH"
    if ratio > 1.2:
        return "LEAN_BEARISH"
    if ratio > 0.8:
        return "NEUTRAL"
    if ratio > 0.5:
        return "LEAN_BULLISH"
    return "BULLISH"


def _classify_discovery_score(score: float) -> str:
    if score >= 60:
        return "STRONG"
    if score >= 40:
        return "MONITOR"
    if score >= 20:
        return "WEAK"
    return "NO_SIGNAL"


# ---------------------------------------------------------------------------
# Per-ticker scan
# ---------------------------------------------------------------------------

def scan_ticker(client: YahooClient, ticker: str) -> dict:
    """Scan a single ticker and compute a discovery score (0-100)."""
    result = {
        "ticker": ticker,
        "discovery_score": 0,
        "signals": [],
    }
    score = 0

    # --- Put/Call ratio (up to 30 points) ---
    try:
        pc = client.get_put_call_ratio(ticker)
        result["put_call_ratio"] = pc.get("ratio")
        signal = pc.get("signal", "NO_DATA")
        result["pc_signal"] = signal
        if signal in ("BULLISH", "BEARISH"):
            score += 30
            result["signals"].append(f"P/C {pc['ratio']} -> {signal}")
        elif signal in ("LEAN_BULLISH", "LEAN_BEARISH"):
            score += 20
            result["signals"].append(f"P/C {pc['ratio']} -> {signal}")
        elif signal == "NEUTRAL":
            score += 5
    except Exception as e:
        result["put_call_error"] = str(e)

    # --- IV (up to 25 points for elevated IV) ---
    try:
        iv = client.get_iv_data(ticker)
        avg_iv = iv.get("avg_atm_iv")
        result["avg_iv"] = avg_iv
        if avg_iv is not None:
            if avg_iv > 0.60:
                score += 25
                result["signals"].append(f"High IV: {avg_iv:.1%}")
            elif avg_iv > 0.40:
                score += 15
                result["signals"].append(f"Elevated IV: {avg_iv:.1%}")
            elif avg_iv > 0.25:
                score += 5
    except Exception as e:
        result["iv_error"] = str(e)

    # --- Short interest (up to 25 points) ---
    try:
        si = client.get_short_interest(ticker)
        spf = si.get("short_percent_of_float")
        result["short_pct_float"] = spf
        if spf is not None:
            if spf > 0.20:
                score += 25
                result["signals"].append(f"Very high SI: {spf:.1%}")
            elif spf > 0.10:
                score += 15
                result["signals"].append(f"High SI: {spf:.1%}")
            elif spf > 0.05:
                score += 5
    except Exception as e:
        result["short_error"] = str(e)

    # --- Analyst divergence (up to 20 points) ---
    try:
        ratings = client.get_analyst_ratings(ticker)
        rec_key = ratings.get("recommendation_key", "")
        target_mean = ratings.get("target_mean_price")
        result["recommendation_key"] = rec_key

        # Check for price target divergence from current price
        iv_data_price = result.get("avg_iv")  # already fetched
        stock_info = client.get_stock_info(ticker)
        current_price = stock_info.get("price")
        if target_mean and current_price and current_price > 0:
            upside = (target_mean - current_price) / current_price
            result["target_upside"] = round(upside, 4)
            if abs(upside) > 0.30:
                score += 20
                direction = "upside" if upside > 0 else "downside"
                result["signals"].append(
                    f"Analyst target {direction}: {upside:+.1%}"
                )
            elif abs(upside) > 0.15:
                score += 10
    except Exception as e:
        result["analyst_error"] = str(e)

    score = min(score, 100)
    result["discovery_score"] = score
    result["tier"] = _classify_discovery_score(score)
    result["signal_count"] = len(result["signals"])

    return result


# ---------------------------------------------------------------------------
# Discovery scan
# ---------------------------------------------------------------------------

def discover(
    tickers: list[str] | None = None,
    top: int = DEFAULT_TOP,
    workers: int = DEFAULT_WORKERS,
) -> list[dict]:
    """Run market-wide discovery scan.

    Args:
        tickers: Optional override list. If None, uses SCAN_UNIVERSE.
        top: Number of top results to return.
        workers: Number of ThreadPoolExecutor workers.

    Returns:
        List of scan results sorted by discovery_score descending.
    """
    if tickers is None:
        tickers = SCAN_UNIVERSE

    client = YahooClient()
    results = []

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(scan_ticker, client, t): t for t in tickers
        }
        for future in as_completed(futures):
            ticker = futures[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                results.append({
                    "ticker": ticker,
                    "discovery_score": 0,
                    "tier": "NO_SIGNAL",
                    "error": str(e),
                    "signal_count": 0,
                    "signals": [],
                })

    results.sort(key=lambda r: r.get("discovery_score", 0), reverse=True)
    return results[:top]


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Radon market-wide candidate discovery scanner"
    )
    parser.add_argument("--top", type=int, default=DEFAULT_TOP,
                        help=f"Number of top results (default: {DEFAULT_TOP})")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS,
                        help=f"Thread pool workers (default: {DEFAULT_WORKERS})")
    parser.add_argument("tickers", nargs="*",
                        help="Optional: specific tickers to scan")
    args = parser.parse_args()

    tickers = [t.upper() for t in args.tickers] if args.tickers else None
    results = discover(tickers=tickers, top=args.top, workers=args.workers)
    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()
