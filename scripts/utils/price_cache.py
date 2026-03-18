"""Price history cache with SHA-256 filenames and TTL management.

Per-contract JSON files in data/price_history_cache/{stocks,options}/.
TTL: 15 min during market hours, 24h after close.
"""

import hashlib
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "price_history_cache"
STOCKS_DIR = DATA_DIR / "stocks"
OPTIONS_DIR = DATA_DIR / "options"

# TTL in seconds
MARKET_HOURS_TTL = 15 * 60       # 15 minutes
AFTER_HOURS_TTL = 24 * 60 * 60   # 24 hours
MAX_CACHE_FILES = 500


def _cache_key(identifier: str) -> str:
    """Generate SHA-256 filename for a cache entry."""
    return hashlib.sha256(identifier.encode()).hexdigest() + ".json"


def _is_market_hours() -> bool:
    """Check if current time is within US market hours (9:30-16:00 ET)."""
    try:
        from zoneinfo import ZoneInfo
    except ImportError:
        return True  # Default to shorter TTL if timezone unavailable

    now = datetime.now(ZoneInfo("America/New_York"))
    if now.weekday() >= 5:  # Weekend
        return False
    market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
    return market_open <= now <= market_close


def _get_ttl() -> int:
    """Get appropriate TTL based on market hours."""
    return MARKET_HOURS_TTL if _is_market_hours() else AFTER_HOURS_TTL


def get_cached(identifier: str, asset_type: str = "stocks") -> Any | None:
    """Get cached price data if still valid.

    Args:
        identifier: Ticker symbol or contract identifier.
        asset_type: 'stocks' or 'options'.

    Returns:
        Cached data dict or None if expired/missing.
    """
    cache_dir = STOCKS_DIR if asset_type == "stocks" else OPTIONS_DIR
    cache_file = cache_dir / _cache_key(identifier)

    if not cache_file.exists():
        return None

    mtime = cache_file.stat().st_mtime
    if time.time() - mtime > _get_ttl():
        return None

    try:
        with open(cache_file, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def set_cached(identifier: str, data: Any, asset_type: str = "stocks") -> None:
    """Cache price data.

    Args:
        identifier: Ticker symbol or contract identifier.
        data: Data to cache.
        asset_type: 'stocks' or 'options'.
    """
    cache_dir = STOCKS_DIR if asset_type == "stocks" else OPTIONS_DIR
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / _cache_key(identifier)

    with open(cache_file, "w") as f:
        json.dump(data, f, default=str)


def prune_cache(max_files: int = MAX_CACHE_FILES) -> int:
    """Remove oldest cache files if count exceeds max_files.

    Returns number of files removed.
    """
    removed = 0
    for cache_dir in [STOCKS_DIR, OPTIONS_DIR]:
        if not cache_dir.exists():
            continue
        files = sorted(cache_dir.glob("*.json"), key=lambda f: f.stat().st_mtime)
        while len(files) > max_files:
            files[0].unlink()
            files.pop(0)
            removed += 1
    return removed
