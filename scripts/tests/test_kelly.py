"""Tests for Kelly Criterion position sizing."""

import numpy as np
import pytest

# Add parent directory to path for imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from kelly import kelly_size, kelly_size_batch, MAX_POSITION_PCT


class TestKellySize:
    """Tests for scalar Kelly sizing."""

    def test_positive_edge(self):
        """Trade with positive edge returns non-zero position."""
        result = kelly_size(
            win_prob=0.6, win_amount=200, loss_amount=100, bankroll=100_000
        )
        assert result["edge"] is True
        assert result["position_size"] > 0
        assert result["kelly_pct"] > 0

    def test_no_edge(self):
        """Trade with no edge returns zero."""
        result = kelly_size(
            win_prob=0.3, win_amount=100, loss_amount=200, bankroll=100_000
        )
        assert result["edge"] is False
        assert result["position_size"] == 0

    def test_cap_enforced(self):
        """Position never exceeds 2.5% of bankroll."""
        result = kelly_size(
            win_prob=0.9, win_amount=1000, loss_amount=100, bankroll=100_000
        )
        max_allowed = 100_000 * MAX_POSITION_PCT
        assert result["position_size"] <= max_allowed

    def test_invalid_probability(self):
        """Zero or negative probability returns zero."""
        result = kelly_size(
            win_prob=0, win_amount=200, loss_amount=100, bankroll=100_000
        )
        assert result["position_size"] == 0

    def test_quarter_kelly_default(self):
        """Default fraction is quarter-Kelly."""
        result = kelly_size(
            win_prob=0.6, win_amount=200, loss_amount=100, bankroll=100_000
        )
        assert result["fraction_used"] == 0.25


class TestKellySizeBatch:
    """Tests for vectorized batch Kelly sizing."""

    def test_batch_matches_scalar(self):
        """Batch results should match individual scalar results."""
        probs = np.array([0.6, 0.7])
        wins = np.array([200.0, 300.0])
        losses = np.array([100.0, 100.0])
        bankroll = 100_000.0

        batch_results = kelly_size_batch(probs, wins, losses, bankroll)

        for i in range(len(probs)):
            scalar = kelly_size(probs[i], wins[i], losses[i], bankroll)
            assert abs(batch_results[i] - scalar["position_size"]) < 0.01

    def test_batch_cap(self):
        """All batch positions respect the cap."""
        probs = np.array([0.9, 0.95])
        wins = np.array([1000.0, 2000.0])
        losses = np.array([100.0, 50.0])
        bankroll = 100_000.0

        batch_results = kelly_size_batch(probs, wins, losses, bankroll)
        max_allowed = bankroll * MAX_POSITION_PCT

        for size in batch_results:
            assert size <= max_allowed + 0.01
