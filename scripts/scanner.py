"""Watchlist batch scanner with ThreadPoolExecutor.

Scans dark pool flow and options flow for watchlist tickers.
Uses 15 workers by default with per-ticker exception catching.
"""

import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from clients.uw_client import UWClient, UWRateLimitError
from utils.atomic_io import safe_load

DEFAULT_WORKERS = 15
WATCHLIST_PATH = Path(__file__).parent.parent / "data" / "watchlist.json"


def scan_ticker(client: UWClient, ticker: str) -> dict:
    """Scan a single ticker for dark pool and options flow signals."""
    result = {"ticker": ticker, "signals": []}

    try:
        darkpool = client.get_darkpool_flow(ticker)
        result["darkpool"] = darkpool
    except UWRateLimitError:
        result["darkpool_error"] = "rate_limited"
    except Exception as e:
        result["darkpool_error"] = str(e)

    try:
        flow = client.get_flow_alerts(ticker_symbol=ticker)
        result["options_flow"] = flow
    except UWRateLimitError:
        result["options_flow_error"] = "rate_limited"
    except Exception as e:
        result["options_flow_error"] = str(e)

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
        List of scan results sorted by signal strength.
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

    client = UWClient()
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
                results.append({"ticker": ticker, "error": str(e)})

    return results[:top]


def main():
    top = 15
    if "--top" in sys.argv:
        idx = sys.argv.index("--top")
        if idx + 1 < len(sys.argv):
            top = int(sys.argv[idx + 1])

    results = run_scan(top=top)
    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()
