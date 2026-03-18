"""Atomic JSON save/load with SHA-256 checksum.

All portfolio writes use temp file + os.replace() (POSIX atomic) + SHA-256 checksum.
This prevents data corruption from interrupted writes.
"""

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any


def compute_checksum(data: bytes) -> str:
    """Compute SHA-256 checksum of data."""
    return hashlib.sha256(data).hexdigest()


def atomic_save(filepath: str | Path, data: Any, indent: int = 2) -> str:
    """Atomically save JSON data to file.

    Writes to a temp file first, then uses os.replace() for atomic move.
    Returns the SHA-256 checksum of the written data.
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    json_bytes = json.dumps(data, indent=indent, default=str).encode("utf-8")
    checksum = compute_checksum(json_bytes)

    # Write to temp file in same directory (same filesystem for atomic replace)
    fd, tmp_path = tempfile.mkstemp(
        dir=filepath.parent, suffix=".tmp", prefix=filepath.stem
    )
    try:
        os.write(fd, json_bytes)
        os.fsync(fd)
        os.close(fd)
        os.replace(tmp_path, filepath)
    except Exception:
        os.close(fd) if not os.get_inheritable(fd) else None
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise

    return checksum


def atomic_load(filepath: str | Path) -> Any:
    """Load JSON data from file.

    Returns the parsed JSON data.
    Raises FileNotFoundError if file doesn't exist.
    """
    filepath = Path(filepath)
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def safe_load(filepath: str | Path, default: Any = None) -> Any:
    """Load JSON data, returning default if file doesn't exist or is invalid."""
    try:
        return atomic_load(filepath)
    except (FileNotFoundError, json.JSONDecodeError):
        return default
