"""FastAPI server — main entry point for Radon's Python backend.

Runs on port 8321. Provides endpoints for scanning, evaluation, portfolio,
and broker operations. Uses Yahoo Finance (free) and Alpaca (free paper trading).
"""

import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.atomic_io import safe_load, atomic_save

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent.parent / "data"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    logger.info("Radon FastAPI server starting on port 8321")
    # Ensure data directory exists
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    yield
    logger.info("Radon FastAPI server shutting down")


app = FastAPI(title="Radon API", version="0.1.0", lifespan=lifespan)

# CORS — allow Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Health ---

@app.get("/health")
async def health():
    """Health check — returns service status."""
    alpaca_configured = bool(os.getenv("ALPACA_API_KEY"))
    anthropic_configured = bool(os.getenv("ANTHROPIC_API_KEY"))
    return {
        "status": "ok",
        "services": {
            "yahoo_finance": True,  # Always available (no key needed)
            "alpaca": alpaca_configured,
            "anthropic": anthropic_configured,
        },
    }


# --- Portfolio ---

@app.get("/portfolio")
async def get_portfolio():
    """Get current portfolio state."""
    return safe_load(DATA_DIR / "portfolio.json", default={
        "positions": [],
        "bankroll": 0,
        "note": "Configure Alpaca API keys to sync live portfolio",
    })


@app.get("/watchlist")
async def get_watchlist():
    """Get watchlist tickers."""
    return safe_load(DATA_DIR / "watchlist.json", default=[])


@app.post("/watchlist/{symbol}")
async def add_to_watchlist(symbol: str):
    """Add a ticker to the watchlist."""
    watchlist = safe_load(DATA_DIR / "watchlist.json", default=[])
    symbol = symbol.upper()
    if any(t.get("ticker") == symbol for t in watchlist):
        return {"status": "already_exists", "ticker": symbol}
    watchlist.append({"ticker": symbol})
    atomic_save(DATA_DIR / "watchlist.json", watchlist)
    return {"status": "added", "ticker": symbol}


@app.delete("/watchlist/{symbol}")
async def remove_from_watchlist(symbol: str):
    """Remove a ticker from the watchlist."""
    watchlist = safe_load(DATA_DIR / "watchlist.json", default=[])
    symbol = symbol.upper()
    watchlist = [t for t in watchlist if t.get("ticker") != symbol]
    atomic_save(DATA_DIR / "watchlist.json", watchlist)
    return {"status": "removed", "ticker": symbol}


# --- Scanning ---

@app.post("/scan")
async def run_scan(
    top: int = Query(15, ge=1, le=50),
    tickers: Optional[str] = Query(None, description="Comma-separated tickers"),
):
    """Run batch options flow scan."""
    try:
        from scanner import run_scan as _run_scan
        ticker_list = [t.strip().upper() for t in tickers.split(",")] if tickers else None
        results = _run_scan(tickers=ticker_list, top=top)
        return {"results": results, "count": len(results)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Ticker ---

@app.get("/ticker/{symbol}")
async def get_ticker(symbol: str):
    """Validate and get info for a ticker."""
    try:
        from fetch_ticker import validate_ticker
        result = validate_ticker(symbol)
        if result and result.get("valid"):
            return result
        raise HTTPException(status_code=404, detail=f"Ticker {symbol} not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Flow ---

@app.get("/flow/{symbol}")
async def get_flow(symbol: str):
    """Get options flow and institutional signals for a ticker."""
    try:
        from fetch_flow import fetch_options_flow, fetch_institutional_signals
        options = fetch_options_flow(symbol.upper())
        institutional = fetch_institutional_signals(symbol.upper())
        return {
            "ticker": symbol.upper(),
            "options_flow": options,
            "institutional_signals": institutional,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Options Chain ---

@app.get("/options/{symbol}")
async def get_options_chain(
    symbol: str,
    expiry: Optional[str] = Query(None, description="Expiration date YYYY-MM-DD"),
):
    """Get options chain for a ticker."""
    try:
        from clients.yahoo_client import YahooClient
        client = YahooClient()
        chain = client.get_option_chain(symbol.upper(), expiry=expiry)
        return chain
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Analyst Ratings ---

@app.get("/analyst/{symbol}")
async def get_analyst_ratings(symbol: str):
    """Get analyst ratings and price targets."""
    try:
        from clients.yahoo_client import YahooClient
        client = YahooClient()
        return client.get_analyst_ratings(symbol.upper())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Price History ---

@app.get("/history/{symbol}")
async def get_price_history(
    symbol: str,
    period: str = Query("3mo", description="1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, max"),
    interval: str = Query("1d", description="1m, 5m, 15m, 1h, 1d, 1wk, 1mo"),
):
    """Get historical price data."""
    try:
        from clients.yahoo_client import YahooClient
        client = YahooClient()
        return {
            "ticker": symbol.upper(),
            "period": period,
            "interval": interval,
            "data": client.get_price_history(symbol.upper(), period=period, interval=interval),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Kelly Sizing ---

@app.post("/kelly")
async def calculate_kelly(
    win_prob: float = Query(..., ge=0, le=1),
    win_amount: float = Query(..., gt=0),
    loss_amount: float = Query(..., gt=0),
    bankroll: float = Query(..., gt=0),
):
    """Calculate Kelly-optimal position size."""
    from kelly import kelly_size
    return kelly_size(win_prob, win_amount, loss_amount, bankroll)


# --- Broker (Alpaca) ---

@app.get("/broker/status")
async def broker_status():
    """Check broker (Alpaca) connection status."""
    if not os.getenv("ALPACA_API_KEY"):
        return {
            "connected": False,
            "broker": "alpaca",
            "message": "Set ALPACA_API_KEY and ALPACA_SECRET_KEY in .env",
        }
    try:
        from clients.alpaca_client import AlpacaClient
        client = AlpacaClient()
        account = client.get_account()
        return {
            "connected": True,
            "broker": "alpaca",
            "paper": client.paper,
            "equity": account.get("equity"),
            "buying_power": account.get("buying_power"),
        }
    except Exception as e:
        return {"connected": False, "broker": "alpaca", "error": str(e)}


@app.get("/broker/positions")
async def broker_positions():
    """Get open positions from broker."""
    try:
        from clients.alpaca_client import AlpacaClient
        client = AlpacaClient()
        return {"positions": client.get_positions()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8321)
