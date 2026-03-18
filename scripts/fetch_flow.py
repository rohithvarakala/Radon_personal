"""Dark pool + options flow retrieval.

Fetches institutional dark pool flow and options flow data for a given ticker.
Primary source: Unusual Whales API.
"""

import sys
import json
from clients.uw_client import UWClient, UWRateLimitError


def fetch_darkpool_flow(ticker: str) -> dict:
    """Fetch dark pool flow data for a ticker."""
    client = UWClient()
    try:
        flow = client.get_darkpool_flow(ticker)
        return {
            "ticker": ticker,
            "type": "darkpool",
            "data": flow,
            "source": "unusual_whales",
        }
    except UWRateLimitError:
        return {"ticker": ticker, "type": "darkpool", "error": "rate_limited"}
    except Exception as e:
        return {"ticker": ticker, "type": "darkpool", "error": str(e)}


def fetch_options_flow(ticker: str | None = None) -> dict:
    """Fetch options flow alerts (sweeps, blocks, unusual activity)."""
    client = UWClient()
    try:
        params = {}
        if ticker:
            params["ticker_symbol"] = ticker
        flow = client.get_flow_alerts(**params)
        return {
            "ticker": ticker,
            "type": "options_flow",
            "data": flow,
            "source": "unusual_whales",
        }
    except UWRateLimitError:
        return {"ticker": ticker, "type": "options_flow", "error": "rate_limited"}
    except Exception as e:
        return {"ticker": ticker, "type": "options_flow", "error": str(e)}


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: python fetch_flow.py TICKER"}))
        sys.exit(1)

    ticker = sys.argv[1].upper()
    darkpool = fetch_darkpool_flow(ticker)
    options = fetch_options_flow(ticker)

    result = {
        "ticker": ticker,
        "darkpool": darkpool,
        "options_flow": options,
    }
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
