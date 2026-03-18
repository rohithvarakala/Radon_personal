"""FastAPI server — main entry point for Radon's Python backend.

Runs on port 8321. Provides endpoints for scanning, evaluation, portfolio,
and IB operations. Eliminates per-request fork overhead (~200-500ms) and
IB reconnection lag (~500ms-2s).
"""

import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.atomic_io import safe_load

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent.parent / "data"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    logger.info("Radon FastAPI server starting on port 8321")
    # TODO: Initialize IB pool, check Gateway health
    yield
    logger.info("Radon FastAPI server shutting down")
    # TODO: Disconnect IB pool


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
    """Health check — returns IB Gateway status, pool states, UW availability."""
    uw_available = bool(os.getenv("UW_TOKEN"))
    return {
        "status": "ok",
        "ib_gateway": {
            "port_listening": False,  # TODO: Check port 4001
        },
        "uw_available": uw_available,
    }


# --- Portfolio ---

@app.get("/portfolio")
async def get_portfolio():
    """Get current portfolio state."""
    portfolio = safe_load(DATA_DIR / "portfolio.json", default={})
    return portfolio


@app.get("/watchlist")
async def get_watchlist():
    """Get watchlist tickers."""
    watchlist = safe_load(DATA_DIR / "watchlist.json", default=[])
    return watchlist


# --- Scanning ---

@app.post("/scan")
async def run_scan(top: int = 15):
    """Run watchlist dark pool flow scan."""
    try:
        from scanner import run_scan as _run_scan
        results = _run_scan(top=top)
        return {"results": results}
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
    """Get dark pool and options flow for a ticker."""
    try:
        from fetch_flow import fetch_darkpool_flow, fetch_options_flow
        darkpool = fetch_darkpool_flow(symbol)
        options = fetch_options_flow(symbol)
        return {"ticker": symbol, "darkpool": darkpool, "options_flow": options}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- IB Operations ---

@app.post("/ib/restart")
async def restart_ib_gateway():
    """Restart IB Gateway via IBC service."""
    # TODO: Implement IB Gateway restart
    return {"status": "not_implemented"}


@app.get("/ib/status")
async def ib_status():
    """Check IB Gateway connection status."""
    # TODO: Check actual IB connection
    return {"connected": False, "port": 4001}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8321)
