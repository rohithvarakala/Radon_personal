"""Interactive Brokers client wrapper around ib_insync.

Provides connection management, quotes, orders, fills, and Flex queries
with resilient reconnection logic.
"""

import logging
import os
import time

from ib_insync import IB, Contract, Stock, Option, Order, LimitOrder, MarketOrder

logger = logging.getLogger(__name__)

# Default ports
GATEWAY_LIVE_PORT = 4001
GATEWAY_PAPER_PORT = 4002
TWS_LIVE_PORT = 7496
TWS_PAPER_PORT = 7497


class IBClient:
    """Wrapper around ib_insync.IB with auto-reconnect."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = GATEWAY_LIVE_PORT,
        client_id: int | str = "auto",
        readonly: bool = False,
    ):
        self.host = host
        self.port = port
        self.readonly = readonly
        self.ib = IB()

        if client_id == "auto":
            self.client_id = self._allocate_client_id()
        else:
            self.client_id = int(client_id)

    def _allocate_client_id(self) -> int:
        """Auto-allocate client ID from the 20-49 subprocess range."""
        import random
        return random.randint(20, 49)

    def connect(self, max_retries: int = 3) -> bool:
        """Connect to IB Gateway/TWS with retry logic."""
        for attempt in range(max_retries):
            try:
                self.ib.connect(
                    self.host,
                    self.port,
                    clientId=self.client_id,
                    readonly=self.readonly,
                    timeout=15,
                )
                logger.info(
                    f"Connected to IB on {self.host}:{self.port} "
                    f"(client_id={self.client_id})"
                )
                return True
            except Exception as e:
                logger.warning(
                    f"IB connection attempt {attempt + 1}/{max_retries} failed: {e}"
                )
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
        return False

    def disconnect(self):
        """Disconnect from IB."""
        if self.ib.isConnected():
            self.ib.disconnect()

    def is_connected(self) -> bool:
        """Check if connected to IB."""
        return self.ib.isConnected()

    # --- Portfolio ---

    def get_positions(self) -> list:
        """Get all current positions."""
        return self.ib.positions()

    def get_portfolio(self) -> list:
        """Get portfolio items with market values."""
        return self.ib.portfolio()

    def get_account_summary(self) -> list:
        """Get account summary values."""
        return self.ib.accountSummary()

    # --- Market Data ---

    def get_quote(self, contract: Contract) -> dict:
        """Get real-time quote for a contract."""
        self.ib.qualifyContracts(contract)
        ticker = self.ib.reqMktData(contract, genericTickList="", snapshot=True)
        self.ib.sleep(2)
        return {
            "bid": ticker.bid,
            "ask": ticker.ask,
            "last": ticker.last,
            "close": ticker.close,
            "volume": ticker.volume,
        }

    def get_option_chain(self, ticker: str) -> list:
        """Get option chain for underlying ticker."""
        stock = Stock(ticker, "SMART", "USD")
        self.ib.qualifyContracts(stock)
        chains = self.ib.reqSecDefOptParams(stock.symbol, "", stock.secType, stock.conId)
        return chains

    # --- Orders ---

    def place_order(self, contract: Contract, order: Order):
        """Place an order."""
        self.ib.qualifyContracts(contract)
        trade = self.ib.placeOrder(contract, order)
        return trade

    def place_limit_order(
        self, contract: Contract, action: str, quantity: int, limit_price: float
    ):
        """Place a limit order."""
        order = LimitOrder(action, quantity, limit_price)
        return self.place_order(contract, order)

    def cancel_order(self, order):
        """Cancel an existing order."""
        return self.ib.cancelOrder(order)

    def get_open_orders(self) -> list:
        """Get all open orders."""
        return self.ib.openOrders()

    # --- Fills ---

    def get_fills(self) -> list:
        """Get today's fills."""
        return self.ib.fills()

    def get_executions(self) -> list:
        """Get today's executions."""
        return self.ib.executions()

    # --- Context Manager ---

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
