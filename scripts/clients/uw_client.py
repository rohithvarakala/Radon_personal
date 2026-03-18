"""Unusual Whales API client.

Provides access to dark pool flow, options flow, analyst data, and more.
Base URL: https://api.unusualwhales.com
Auth: Authorization: Bearer $UW_TOKEN
"""

import os
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", "web", ".env"))

BASE_URL = "https://api.unusualwhales.com"


class UWRateLimitError(Exception):
    """Raised when Unusual Whales rate limit is hit."""


class UWClient:
    """Client for Unusual Whales API."""

    def __init__(self, token: str | None = None):
        self.token = token or os.getenv("UW_TOKEN", "")
        if not self.token:
            raise ValueError("UW_TOKEN not set. Add it to web/.env or pass directly.")
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
        })

    def _get(self, endpoint: str, params: dict | None = None) -> Any:
        """Make GET request to UW API."""
        url = f"{BASE_URL}{endpoint}"
        resp = self.session.get(url, params=params, timeout=30)
        if resp.status_code == 429:
            raise UWRateLimitError(f"Rate limited on {endpoint}")
        resp.raise_for_status()
        return resp.json()

    # --- Dark Pool ---

    def get_darkpool_flow(self, ticker: str) -> dict:
        """Get dark pool flow data for a ticker."""
        return self._get(f"/api/darkpool/{ticker}")

    # --- Options Flow ---

    def get_flow_alerts(self, **params) -> dict:
        """Get options flow alerts (sweeps, blocks, unusual activity)."""
        return self._get("/api/option-trades/flow-alerts", params=params)

    # --- Stock Info ---

    def get_stock_info(self, ticker: str) -> dict:
        """Get stock information for ticker validation."""
        return self._get(f"/api/stock/{ticker}/info")

    def get_option_contracts(self, ticker: str) -> dict:
        """Get options chain for a ticker."""
        return self._get(f"/api/stock/{ticker}/option-contracts")

    def get_greek_exposure(self, ticker: str) -> dict:
        """Get GEX (Gamma Exposure) data."""
        return self._get(f"/api/stock/{ticker}/greek-exposure")

    # --- Analyst Data ---

    def get_analyst_ratings(self, **params) -> dict:
        """Get analyst ratings from screener."""
        return self._get("/api/screener/analysts", params=params)

    # --- Seasonality ---

    def get_seasonality(self, ticker: str) -> dict:
        """Get monthly seasonality data."""
        return self._get(f"/api/seasonality/{ticker}/monthly")

    # --- Short Interest ---

    def get_short_interest(self, ticker: str) -> dict:
        """Get short interest and float data."""
        return self._get(f"/api/shorts/{ticker}/interest-float/v2")
