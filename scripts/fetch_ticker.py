"""Ticker validation — verifies a ticker exists and fetches basic info.

Data source priority: IB → Unusual Whales → Yahoo Finance (fallback).
"""

import sys
import json
from clients.uw_client import UWClient


def validate_ticker(ticker: str) -> dict | None:
    """Validate a ticker symbol and return basic info.

    Returns dict with ticker info or None if invalid.
    """
    ticker = ticker.upper().strip()
    if not ticker or not ticker.isalpha():
        return None

    try:
        client = UWClient()
        info = client.get_stock_info(ticker)
        return {
            "ticker": ticker,
            "valid": True,
            "data": info,
        }
    except Exception as e:
        return {
            "ticker": ticker,
            "valid": False,
            "error": str(e),
        }


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: python fetch_ticker.py TICKER"}))
        sys.exit(1)

    ticker = sys.argv[1]
    result = validate_ticker(ticker)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
