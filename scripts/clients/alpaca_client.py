"""Alpaca Markets client — free alternative to Interactive Brokers.

Provides paper and live trading, real-time quotes, portfolio management.
Free tier includes unlimited paper trading — no minimum deposit.

Sign up: https://alpaca.markets
Docs: https://docs.alpaca.markets
"""

import os
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

PAPER_BASE_URL = "https://paper-api.alpaca.markets"
LIVE_BASE_URL = "https://api.alpaca.markets"
DATA_BASE_URL = "https://data.alpaca.markets"


class AlpacaClient:
    """Client for Alpaca Markets API (paper + live trading)."""

    def __init__(
        self,
        api_key: str | None = None,
        secret_key: str | None = None,
        paper: bool = True,
    ):
        self.api_key = api_key or os.getenv("ALPACA_API_KEY", "")
        self.secret_key = secret_key or os.getenv("ALPACA_SECRET_KEY", "")
        self.paper = paper
        self.base_url = PAPER_BASE_URL if paper else LIVE_BASE_URL

        if not self.api_key or not self.secret_key:
            raise ValueError(
                "Alpaca API keys not set. Add ALPACA_API_KEY and "
                "ALPACA_SECRET_KEY to .env or pass directly."
            )

        self.session = requests.Session()
        self.session.headers.update({
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.secret_key,
            "Accept": "application/json",
        })

        self.data_session = requests.Session()
        self.data_session.headers.update({
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.secret_key,
            "Accept": "application/json",
        })

    def _trading_get(self, endpoint: str, params: dict | None = None) -> Any:
        """Make GET request to Trading API."""
        url = f"{self.base_url}{endpoint}"
        resp = self.session.get(url, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def _trading_post(self, endpoint: str, data: dict | None = None) -> Any:
        """Make POST request to Trading API."""
        url = f"{self.base_url}{endpoint}"
        resp = self.session.post(url, json=data, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def _trading_delete(self, endpoint: str) -> Any:
        """Make DELETE request to Trading API."""
        url = f"{self.base_url}{endpoint}"
        resp = self.session.delete(url, timeout=30)
        resp.raise_for_status()
        if resp.content:
            return resp.json()
        return {"status": "ok"}

    def _data_get(self, endpoint: str, params: dict | None = None) -> Any:
        """Make GET request to Market Data API."""
        url = f"{DATA_BASE_URL}{endpoint}"
        resp = self.data_session.get(url, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    # --- Account ---

    def get_account(self) -> dict:
        """Get account information (buying power, equity, etc.)."""
        return self._trading_get("/v2/account")

    def get_buying_power(self) -> float:
        """Get available buying power."""
        account = self.get_account()
        return float(account.get("buying_power", 0))

    def get_portfolio_value(self) -> float:
        """Get total portfolio value."""
        account = self.get_account()
        return float(account.get("portfolio_value", 0))

    # --- Positions ---

    def get_positions(self) -> list[dict]:
        """Get all open positions."""
        return self._trading_get("/v2/positions")

    def get_position(self, symbol: str) -> dict:
        """Get position for a specific symbol."""
        return self._trading_get(f"/v2/positions/{symbol}")

    def close_position(self, symbol: str) -> dict:
        """Close a position (market order)."""
        return self._trading_delete(f"/v2/positions/{symbol}")

    def close_all_positions(self) -> list:
        """Close all open positions."""
        return self._trading_delete("/v2/positions")

    # --- Orders ---

    def place_order(
        self,
        symbol: str,
        qty: int,
        side: str,
        order_type: str = "market",
        time_in_force: str = "day",
        limit_price: float | None = None,
        stop_price: float | None = None,
    ) -> dict:
        """Place an order.

        Args:
            symbol: Ticker symbol.
            qty: Number of shares.
            side: 'buy' or 'sell'.
            order_type: 'market', 'limit', 'stop', 'stop_limit'.
            time_in_force: 'day', 'gtc', 'opg', 'cls', 'ioc', 'fok'.
            limit_price: Required for limit/stop_limit orders.
            stop_price: Required for stop/stop_limit orders.
        """
        order = {
            "symbol": symbol.upper(),
            "qty": str(qty),
            "side": side,
            "type": order_type,
            "time_in_force": time_in_force,
        }
        if limit_price is not None:
            order["limit_price"] = str(limit_price)
        if stop_price is not None:
            order["stop_price"] = str(stop_price)

        return self._trading_post("/v2/orders", data=order)

    def get_orders(self, status: str = "open") -> list[dict]:
        """Get orders by status ('open', 'closed', 'all')."""
        return self._trading_get("/v2/orders", params={"status": status})

    def cancel_order(self, order_id: str) -> dict:
        """Cancel a specific order."""
        return self._trading_delete(f"/v2/orders/{order_id}")

    def cancel_all_orders(self) -> list:
        """Cancel all open orders."""
        return self._trading_delete("/v2/orders")

    # --- Market Data ---

    def get_quote(self, symbol: str) -> dict:
        """Get latest quote for a symbol."""
        data = self._data_get(f"/v2/stocks/{symbol}/quotes/latest")
        return data.get("quote", data)

    def get_bars(
        self,
        symbol: str,
        timeframe: str = "1Day",
        limit: int = 100,
    ) -> list[dict]:
        """Get historical bars/candles.

        Args:
            symbol: Ticker symbol.
            timeframe: '1Min', '5Min', '15Min', '1Hour', '1Day'.
            limit: Max number of bars.
        """
        data = self._data_get(
            f"/v2/stocks/{symbol}/bars",
            params={"timeframe": timeframe, "limit": limit},
        )
        return data.get("bars", [])

    def get_snapshot(self, symbol: str) -> dict:
        """Get market snapshot (latest trade, quote, bar)."""
        return self._data_get(f"/v2/stocks/{symbol}/snapshot")

    # --- Watchlist ---

    def get_watchlists(self) -> list[dict]:
        """Get all watchlists."""
        return self._trading_get("/v2/watchlists")

    def create_watchlist(self, name: str, symbols: list[str]) -> dict:
        """Create a new watchlist."""
        return self._trading_post(
            "/v2/watchlists",
            data={"name": name, "symbols": symbols},
        )

    # --- Context Manager ---

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()
        self.data_session.close()
