"""Watchlist batch scanner with ThreadPoolExecutor.

Scans options flow, IV, put/call ratios, and institutional signals
for watchlist tickers using Yahoo Finance (free, no API key).
Uses 15 workers by default with per-ticker exception catching.
"""

import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from clients.yahoo_client import YahooClient
from utils.atomic_io import safe_load

DEFAULT_WORKERS = 15
WATCHLIST_PATH = Path(__file__).parent.parent / "data" / "watchlist.json"


def scan_ticker(client: YahooClient, ticker: str) -> dict:
    """Scan a single ticker for options flow and institutional signals."""
    result = {"ticker": ticker, "signals": []}

    try:
        pc = client.get_put_call_ratio(ticker)
        result["put_call_ratio"] = pc
        if pc.get("signal") in ("BULLISH", "LEAN_BULLISH"):
            result["signals"].append(f"P/C ratio {pc['ratio']} → {pc['signal']}")
    except Exception as e:
        result["put_call_error"] = str(e)

    try:
        iv = client.get_iv_data(ticker)
        result["iv_data"] = iv
    except Exception as e:
        result["iv_error"] = str(e)

    try:
        si = client.get_short_interest(ticker)
        result["short_interest"] = si
        spf = si.get("short_percent_of_float")
        if spf and spf > 0.10:
            result["signals"].append(f"High short interest: {spf:.1%}")
    except Exception as e:
        result["short_error"] = str(e)

    try:
        ratings = client.get_analyst_ratings(ticker)
        result["analyst_ratings"] = ratings
    except Exception as e:
        result["ratings_error"] = str(e)

    result["signal_count"] = len(result["signals"])
    return result


def run_scan(
    tickers: list[str] | None = None,
    top: int = 15,
    workers: int = DEFAULT_WORKERS,
) -> list[dict]:
    """Run batch scan across tickers.

    Args:
        tickers: List of tickers. If None, loads from watchlist.json.
        top: Number of top results to return.
        workers: Number of ThreadPoolExecutor workers.

    Returns:
        List of scan results sorted by signal count (descending).
    """
    if tickers is None:
        watchlist = safe_load(WATCHLIST_PATH, [])
        tickers = [
            t.get("ticker") or t.get("symbol")
            for t in watchlist
            if t.get("ticker") or t.get("symbol")
        ]

    if not tickers:
        return []

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
                results.append({"ticker": ticker, "error": str(e), "signal_count": 0})

    # Sort by signal count descending
    results.sort(key=lambda r: r.get("signal_count", 0), reverse=True)
    return results[:top]


def main():
    top = 15
    tickers = None

    if "--top" in sys.argv:
        idx = sys.argv.index("--top")
        if idx + 1 < len(sys.argv):
            top = int(sys.argv[idx + 1])

    # Allow passing tickers as positional args
    positional = [a for a in sys.argv[1:] if not a.startswith("--") and a != str(top)]
    if positional:
        tickers = [t.upper() for t in positional]

    results = run_scan(tickers=tickers, top=top)
    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()
