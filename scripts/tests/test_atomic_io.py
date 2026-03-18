"""Tests for atomic I/O utilities."""

import json
import tempfile
from pathlib import Path

import pytest

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.atomic_io import atomic_save, atomic_load, safe_load, compute_checksum


class TestAtomicIO:

    def test_save_and_load(self, tmp_path):
        """Data survives a save/load round trip."""
        data = {"ticker": "AAPL", "price": 150.25, "positions": [1, 2, 3]}
        filepath = tmp_path / "test.json"

        checksum = atomic_save(filepath, data)
        loaded = atomic_load(filepath)

        assert loaded == data
        assert len(checksum) == 64  # SHA-256 hex

    def test_checksum_consistency(self):
        """Same data produces same checksum."""
        data = b'{"key": "value"}'
        c1 = compute_checksum(data)
        c2 = compute_checksum(data)
        assert c1 == c2

    def test_safe_load_missing_file(self, tmp_path):
        """safe_load returns default for missing files."""
        result = safe_load(tmp_path / "nonexistent.json", default=[])
        assert result == []

    def test_safe_load_corrupt_json(self, tmp_path):
        """safe_load returns default for corrupt JSON."""
        filepath = tmp_path / "corrupt.json"
        filepath.write_text("not valid json {{{")
        result = safe_load(filepath, default=None)
        assert result is None

    def test_creates_parent_directories(self, tmp_path):
        """atomic_save creates parent dirs if needed."""
        filepath = tmp_path / "deep" / "nested" / "dir" / "data.json"
        atomic_save(filepath, {"test": True})
        loaded = atomic_load(filepath)
        assert loaded == {"test": True}
