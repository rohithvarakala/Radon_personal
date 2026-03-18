"""Kelly Criterion position sizing — scalar and vectorized (NumPy).

Fractional Kelly sizing with hard 2.5% bankroll cap per position.
"""

import numpy as np

MAX_POSITION_PCT = 0.025  # 2.5% hard cap
KELLY_FRACTION = 0.25     # Quarter-Kelly for safety


def kelly_size(
    win_prob: float,
    win_amount: float,
    loss_amount: float,
    bankroll: float,
    fraction: float = KELLY_FRACTION,
    max_pct: float = MAX_POSITION_PCT,
) -> dict:
    """Calculate Kelly-optimal position size for a single trade.

    Args:
        win_prob: Probability of winning (0-1).
        win_amount: Expected gain if trade wins (positive).
        loss_amount: Expected loss if trade loses (positive).
        bankroll: Total available capital.
        fraction: Kelly fraction (default 0.25 = quarter-Kelly).
        max_pct: Maximum position as fraction of bankroll.

    Returns:
        Dict with kelly_pct, position_size, capped status.
    """
    if win_prob <= 0 or win_prob >= 1:
        return {"kelly_pct": 0, "position_size": 0, "capped": False, "edge": False}
    if win_amount <= 0 or loss_amount <= 0:
        return {"kelly_pct": 0, "position_size": 0, "capped": False, "edge": False}

    # Kelly formula: f* = (p * b - q) / b
    # where b = win/loss ratio, p = win prob, q = 1 - p
    b = win_amount / loss_amount
    p = win_prob
    q = 1 - p

    full_kelly = (p * b - q) / b

    if full_kelly <= 0:
        return {"kelly_pct": 0, "position_size": 0, "capped": False, "edge": False}

    fractional_kelly = full_kelly * fraction
    capped = fractional_kelly > max_pct
    final_pct = min(fractional_kelly, max_pct)
    position_size = round(bankroll * final_pct, 2)

    return {
        "kelly_pct": round(final_pct * 100, 4),
        "full_kelly_pct": round(full_kelly * 100, 4),
        "fractional_kelly_pct": round(fractional_kelly * 100, 4),
        "position_size": position_size,
        "capped": capped,
        "edge": True,
        "fraction_used": fraction,
    }


def kelly_size_batch(
    win_probs: np.ndarray,
    win_amounts: np.ndarray,
    loss_amounts: np.ndarray,
    bankroll: float,
    fraction: float = KELLY_FRACTION,
    max_pct: float = MAX_POSITION_PCT,
) -> np.ndarray:
    """Vectorized Kelly sizing for N candidates.

    Args:
        win_probs: Array of win probabilities.
        win_amounts: Array of expected gains.
        loss_amounts: Array of expected losses.
        bankroll: Total available capital.
        fraction: Kelly fraction.
        max_pct: Maximum position as fraction of bankroll.

    Returns:
        Array of position sizes in dollars.
    """
    b = win_amounts / loss_amounts
    q = 1 - win_probs
    full_kelly = (win_probs * b - q) / b
    full_kelly = np.maximum(full_kelly, 0)
    fractional = full_kelly * fraction
    capped = np.minimum(fractional, max_pct)
    return np.round(bankroll * capped, 2)
