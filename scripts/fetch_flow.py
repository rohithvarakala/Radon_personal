"""Options flow and institutional signal retrieval.

Uses Yahoo Finance for options chain data, put/call ratios, IV,
short interest, and institutional holders as proxies for flow signals.
"""

import sys
import json
from clients.yahoo_client import YahooClient


def fetch_options_flow(ticker: str) -> dict:
    """Fetch options flow data using Yahoo Finance.

    Includes put/call ratio, IV data, and options chain summary.
    """
    client = YahooClient()
    result = {"ticker": ticker, "source": "yahoo_finance"}

    try:
        result["put_call_ratio"] = client.get_put_call_ratio(ticker)
    except Exception as e:
        result["put_call_ratio_error"] = str(e)

    try:
        result["iv_data"] = client.get_iv_data(ticker)
    except Exception as e:
        result["iv_error"] = str(e)

    try:
        chain = client.get_option_chain(ticker)
        result["nearest_expiry"] = chain.get("expiry")
        result["num_expirations"] = len(chain.get("expirations", []))
        result["num_calls"] = len(chain.get("calls", []))
        result["num_puts"] = len(chain.get("puts", []))
    except Exception as e:
        result["chain_error"] = str(e)

    return result


def fetch_institutional_signals(ticker: str) -> dict:
    """Fetch institutional signal proxies.

    Uses short interest and institutional holders as dark pool proxies.
    """
    client = YahooClient()
    result = {"ticker": ticker, "source": "yahoo_finance"}

    try:
        result["short_interest"] = client.get_short_interest(ticker)
    except Exception as e:
        result["short_interest_error"] = str(e)

    try:
        holders = client.get_institutional_holders(ticker)
        result["institutional_holders"] = holders[:10]  # Top 10
        result["num_institutional_holders"] = len(holders)
    except Exception as e:
        result["holders_error"] = str(e)

    return result


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: python fetch_flow.py TICKER"}))
        sys.exit(1)

    ticker = sys.argv[1].upper()
    options = fetch_options_flow(ticker)
    institutional = fetch_institutional_signals(ticker)

    result = {
        "ticker": ticker,
        "options_flow": options,
        "institutional_signals": institutional,
    }
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
