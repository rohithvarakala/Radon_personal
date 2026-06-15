"""7-milestone trade evaluation workflow — the core of Radon.

Runs a sequential evaluation pipeline for a given ticker:
1.  Validate Ticker
1B. Analyst Ratings (context)
1C. News context (noted, no API)
2.  Options Flow (put/call ratio, IV)
3.  Institutional Signals (short interest, holders)
3B. OI Changes (open interest from options chain)
4.  Edge Decision (PASS/FAIL — aggregate signals)
5.  Structure Design (convex structure if edge passes)
6.  Kelly Sizing (2.5% cap)
7.  Log result to trade_log.json (atomic)

Stops immediately if Gate 4 (Edge) fails.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from clients.yahoo_client import YahooClient
from kelly import kelly_size
from utils.atomic_io import atomic_save, safe_load

TRADE_LOG_PATH = Path(__file__).parent.parent / "data" / "trade_log.json"


# ---------------------------------------------------------------------------
# Signal interpretation helpers
# ---------------------------------------------------------------------------

def classify_put_call(ratio: float | None) -> str:
    """Put/Call ratio signal classification."""
    if ratio is None:
        return "NO_DATA"
    if ratio > 2.0:
        return "BEARISH"
    if ratio > 1.2:
        return "LEAN_BEARISH"
    if ratio > 0.8:
        return "NEUTRAL"
    if ratio > 0.5:
        return "LEAN_BULLISH"
    return "BULLISH"


def classify_analyst_buy_pct(buy_pct: float | None) -> str:
    """Analyst buy-percentage signal classification."""
    if buy_pct is None:
        return "NO_DATA"
    if buy_pct >= 70:
        return "BULLISH"
    if buy_pct >= 50:
        return "LEAN_BULLISH"
    if buy_pct >= 30:
        return "LEAN_BEARISH"
    return "BEARISH"


def classify_discovery_score(score: float) -> str:
    """Discovery score tier."""
    if score >= 60:
        return "STRONG"
    if score >= 40:
        return "MONITOR"
    if score >= 20:
        return "WEAK"
    return "NO_SIGNAL"


# ---------------------------------------------------------------------------
# Signal direction helper
# ---------------------------------------------------------------------------

_BULLISH_SIGNALS = {"BULLISH", "LEAN_BULLISH"}
_BEARISH_SIGNALS = {"BEARISH", "LEAN_BEARISH"}


def _signal_direction(signals: list[str]) -> str:
    """Determine dominant direction from a list of signal labels."""
    bull = sum(1 for s in signals if s in _BULLISH_SIGNALS)
    bear = sum(1 for s in signals if s in _BEARISH_SIGNALS)
    if bull > bear:
        return "BULLISH"
    if bear > bull:
        return "BEARISH"
    return "NEUTRAL"


# ---------------------------------------------------------------------------
# Milestone functions
# ---------------------------------------------------------------------------

def milestone_1_validate(client: YahooClient, ticker: str) -> dict:
    """Milestone 1: Validate ticker via Yahoo Finance."""
    try:
        valid = client.validate_ticker(ticker)
        if not valid:
            return {"milestone": "1_validate", "status": "FAIL",
                    "reason": f"Ticker {ticker} not found or has no price data"}
        info = client.get_stock_info(ticker)
        return {"milestone": "1_validate", "status": "PASS",
                "data": info, "reason": f"{info.get('name', ticker)} validated"}
    except Exception as e:
        return {"milestone": "1_validate", "status": "FAIL",
                "reason": f"Validation error: {e}"}


def milestone_1b_analyst(client: YahooClient, ticker: str) -> dict:
    """Milestone 1B: Analyst ratings (context only, never fails the pipeline)."""
    try:
        ratings = client.get_analyst_ratings(ticker)

        # Calculate buy percentage from recommendations
        buy_pct = None
        recs = ratings.get("recommendations", [])
        if recs:
            buy_keywords = {"buy", "strongBuy", "strong_buy", "outperform", "overweight"}
            total = len(recs)
            buys = sum(1 for r in recs
                       if str(r.get("To Grade", r.get("toGrade", ""))).lower()
                       in buy_keywords)
            buy_pct = round(buys / total * 100, 1) if total > 0 else None

        signal = classify_analyst_buy_pct(buy_pct)
        return {
            "milestone": "1B_analyst",
            "status": "PASS",
            "data": {
                "target_mean": ratings.get("target_mean_price"),
                "target_high": ratings.get("target_high_price"),
                "target_low": ratings.get("target_low_price"),
                "recommendation_key": ratings.get("recommendation_key"),
                "num_analysts": ratings.get("number_of_analyst_opinions"),
                "buy_pct": buy_pct,
                "signal": signal,
            },
            "reason": f"Analyst signal: {signal} (buy%={buy_pct})",
        }
    except Exception as e:
        return {"milestone": "1B_analyst", "status": "PASS",
                "data": {}, "reason": f"Analyst data unavailable: {e}"}


def milestone_1c_news(ticker: str) -> dict:
    """Milestone 1C: News context placeholder (no API needed)."""
    return {
        "milestone": "1C_news",
        "status": "PASS",
        "data": {"note": "News context requires manual review or future API integration"},
        "reason": "News noted — no automated source configured",
    }


def milestone_2_options_flow(client: YahooClient, ticker: str) -> dict:
    """Milestone 2: Options flow — put/call ratio, IV data."""
    data = {}

    # Put/Call ratio
    try:
        pc = client.get_put_call_ratio(ticker)
        data["put_call_ratio"] = pc
    except Exception as e:
        data["put_call_error"] = str(e)

    # IV data
    try:
        iv = client.get_iv_data(ticker)
        data["iv_data"] = iv
    except Exception as e:
        data["iv_error"] = str(e)

    pc_signal = data.get("put_call_ratio", {}).get("signal", "NO_DATA")
    ratio_val = data.get("put_call_ratio", {}).get("ratio")
    return {
        "milestone": "2_options_flow",
        "status": "PASS",
        "data": data,
        "reason": f"P/C ratio={ratio_val} signal={pc_signal}",
    }


def milestone_3_institutional(client: YahooClient, ticker: str) -> dict:
    """Milestone 3: Institutional signals — short interest, holders."""
    data = {}

    try:
        si = client.get_short_interest(ticker)
        data["short_interest"] = si
    except Exception as e:
        data["short_interest_error"] = str(e)

    try:
        holders = client.get_institutional_holders(ticker)
        data["institutional_holders"] = holders[:10]
        data["num_institutional_holders"] = len(holders)
    except Exception as e:
        data["holders_error"] = str(e)

    spf = data.get("short_interest", {}).get("short_percent_of_float")
    short_note = f"Short % of float: {spf:.1%}" if spf else "Short data unavailable"
    return {
        "milestone": "3_institutional",
        "status": "PASS",
        "data": data,
        "reason": short_note,
    }


def milestone_3b_oi_changes(client: YahooClient, ticker: str) -> dict:
    """Milestone 3B: Open interest changes from options chain (REQUIRED)."""
    try:
        chain = client.get_option_chain(ticker)
        calls = chain.get("calls", [])
        puts = chain.get("puts", [])

        total_call_oi = sum(c.get("openInterest", 0) or 0 for c in calls)
        total_put_oi = sum(p.get("openInterest", 0) or 0 for p in puts)
        total_oi = total_call_oi + total_put_oi

        # Find max OI strikes
        max_call_oi_strike = None
        max_put_oi_strike = None
        if calls:
            max_call = max(calls, key=lambda c: c.get("openInterest", 0) or 0)
            max_call_oi_strike = {
                "strike": max_call.get("strike"),
                "oi": max_call.get("openInterest", 0),
            }
        if puts:
            max_put = max(puts, key=lambda p: p.get("openInterest", 0) or 0)
            max_put_oi_strike = {
                "strike": max_put.get("strike"),
                "oi": max_put.get("openInterest", 0),
            }

        oi_ratio = round(total_put_oi / total_call_oi, 3) if total_call_oi > 0 else None

        return {
            "milestone": "3B_oi_changes",
            "status": "PASS",
            "data": {
                "expiry": chain.get("expiry"),
                "total_call_oi": total_call_oi,
                "total_put_oi": total_put_oi,
                "total_oi": total_oi,
                "oi_put_call_ratio": oi_ratio,
                "max_call_oi_strike": max_call_oi_strike,
                "max_put_oi_strike": max_put_oi_strike,
            },
            "reason": f"Total OI={total_oi}, OI P/C ratio={oi_ratio}",
        }
    except Exception as e:
        return {"milestone": "3B_oi_changes", "status": "PASS",
                "data": {}, "reason": f"OI data error: {e}"}


def milestone_4_edge_decision(milestones: dict) -> dict:
    """Milestone 4: Edge Decision — aggregate signals into PASS/FAIL.

    Collects directional signals from prior milestones and computes a
    discovery score (0-100). Score >= 40 passes.
    """
    signals = []
    score = 0

    # --- Put/Call ratio signal (up to 30 points) ---
    pc_data = milestones.get("2_options_flow", {}).get("data", {})
    pc_signal = pc_data.get("put_call_ratio", {}).get("signal", "NO_DATA")
    if pc_signal != "NO_DATA":
        signals.append(pc_signal)
        if pc_signal in ("BULLISH", "BEARISH"):
            score += 30
        elif pc_signal in ("LEAN_BULLISH", "LEAN_BEARISH"):
            score += 20
        # NEUTRAL gets 5 points — the market is pricing something
        else:
            score += 5

    # --- IV data (up to 15 points for elevated IV) ---
    iv_data = pc_data.get("iv_data", {})
    avg_iv = iv_data.get("avg_atm_iv")
    if avg_iv is not None:
        if avg_iv > 0.60:
            score += 15
        elif avg_iv > 0.40:
            score += 10
        elif avg_iv > 0.25:
            score += 5

    # --- Analyst signal (up to 15 points) ---
    analyst_data = milestones.get("1B_analyst", {}).get("data", {})
    analyst_signal = analyst_data.get("signal", "NO_DATA")
    if analyst_signal != "NO_DATA":
        signals.append(analyst_signal)
        if analyst_signal in ("BULLISH", "BEARISH"):
            score += 15
        elif analyst_signal in ("LEAN_BULLISH", "LEAN_BEARISH"):
            score += 10

    # --- Short interest (up to 20 points for high SI) ---
    inst_data = milestones.get("3_institutional", {}).get("data", {})
    spf = inst_data.get("short_interest", {}).get("short_percent_of_float")
    if spf is not None:
        if spf > 0.20:
            score += 20
            signals.append("BEARISH")  # Very high SI is contrarian-bullish or bearish
        elif spf > 0.10:
            score += 15
            signals.append("LEAN_BEARISH")
        elif spf > 0.05:
            score += 5

    # --- OI concentration (up to 20 points) ---
    oi_data = milestones.get("3B_oi_changes", {}).get("data", {})
    oi_ratio = oi_data.get("oi_put_call_ratio")
    if oi_ratio is not None:
        oi_signal = classify_put_call(oi_ratio)
        if oi_signal != "NO_DATA":
            signals.append(oi_signal)
            if oi_signal in ("BULLISH", "BEARISH"):
                score += 20
            elif oi_signal in ("LEAN_BULLISH", "LEAN_BEARISH"):
                score += 10
            else:
                score += 5

    score = min(score, 100)
    tier = classify_discovery_score(score)
    direction = _signal_direction(signals)
    passed = score >= 40

    return {
        "milestone": "4_edge_decision",
        "status": "PASS" if passed else "FAIL",
        "data": {
            "discovery_score": score,
            "tier": tier,
            "direction": direction,
            "signals": signals,
        },
        "reason": (f"Score={score} ({tier}), direction={direction}"
                   + ("" if passed else " — below threshold, stopping")),
    }


def milestone_5_structure(milestones: dict, stock_info: dict) -> dict:
    """Milestone 5: Suggest a convex structure based on signal direction.

    All structures must satisfy Gate 1: potential gain >= 2x potential loss,
    using defined-risk positions only.
    """
    edge = milestones.get("4_edge_decision", {}).get("data", {})
    direction = edge.get("direction", "NEUTRAL")
    score = edge.get("discovery_score", 0)

    price = stock_info.get("price") or stock_info.get("previous_close") or 0
    iv_data = milestones.get("2_options_flow", {}).get("data", {}).get("iv_data", {})
    avg_iv = iv_data.get("avg_atm_iv")

    structures = []

    if direction == "BULLISH":
        structures.append({
            "type": "long_call",
            "description": "Buy OTM call 30-60 DTE",
            "rationale": "Defined risk, unlimited upside, R:R > 2:1",
            "strike_hint": f"~{round(price * 1.05, 2)} (5% OTM)" if price else None,
        })
        if avg_iv and avg_iv > 0.40:
            structures.append({
                "type": "bull_call_spread",
                "description": "Buy ATM call, sell OTM call 30-60 DTE",
                "rationale": "Reduced cost in high-IV environment, capped risk",
                "strike_hint": (f"Buy ~{round(price, 2)}, "
                                f"Sell ~{round(price * 1.10, 2)}") if price else None,
            })
    elif direction == "BEARISH":
        structures.append({
            "type": "long_put",
            "description": "Buy OTM put 30-60 DTE",
            "rationale": "Defined risk, large downside capture, R:R > 2:1",
            "strike_hint": f"~{round(price * 0.95, 2)} (5% OTM)" if price else None,
        })
        if avg_iv and avg_iv > 0.40:
            structures.append({
                "type": "bear_put_spread",
                "description": "Buy ATM put, sell OTM put 30-60 DTE",
                "rationale": "Reduced cost in high-IV environment, capped risk",
                "strike_hint": (f"Buy ~{round(price, 2)}, "
                                f"Sell ~{round(price * 0.90, 2)}") if price else None,
            })
    else:
        # Neutral / mixed — calendar spread for vol expansion
        structures.append({
            "type": "long_straddle",
            "description": "Buy ATM call + ATM put 30-60 DTE",
            "rationale": "Profits from large move in either direction",
            "strike_hint": f"ATM ~{round(price, 2)}" if price else None,
        })

    recommended = structures[0] if structures else None

    return {
        "milestone": "5_structure",
        "status": "PASS",
        "data": {
            "direction": direction,
            "recommended_structure": recommended,
            "alternatives": structures[1:] if len(structures) > 1 else [],
            "current_price": price,
            "avg_iv": avg_iv,
        },
        "reason": f"Recommended: {recommended['type'] if recommended else 'none'} "
                  f"for {direction} bias",
    }


def milestone_6_kelly(direction: str, avg_iv: float | None,
                       score: int, bankroll: float) -> dict:
    """Milestone 6: Kelly Criterion position sizing with 2.5% cap.

    Estimates win probability from discovery score and derives
    approximate win/loss amounts from structure.
    """
    # Map score to estimated win probability (conservative)
    if score >= 80:
        win_prob = 0.55
    elif score >= 60:
        win_prob = 0.50
    elif score >= 40:
        win_prob = 0.45
    else:
        win_prob = 0.35

    # Convex structure: typical R:R is 2:1 to 3:1
    # Use 2.5:1 as default (gain 2.5x premium, lose 1x premium)
    win_amount = 2.5
    loss_amount = 1.0

    sizing = kelly_size(
        win_prob=win_prob,
        win_amount=win_amount,
        loss_amount=loss_amount,
        bankroll=bankroll,
    )

    return {
        "milestone": "6_kelly_sizing",
        "status": "PASS" if sizing.get("edge") else "FAIL",
        "data": {
            "win_prob_est": win_prob,
            "win_loss_ratio": f"{win_amount}:{loss_amount}",
            **sizing,
        },
        "reason": (f"Position size=${sizing['position_size']:,.2f} "
                   f"({sizing['kelly_pct']:.2f}% of bankroll)"
                   if sizing.get("edge")
                   else "No Kelly edge — position size is $0"),
    }


def milestone_7_log(ticker: str, report: dict) -> dict:
    """Milestone 7: Log evaluation result to trade_log.json (atomic write)."""
    try:
        log = safe_load(TRADE_LOG_PATH, [])
        if not isinstance(log, list):
            log = []

        entry = {
            "ticker": ticker,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "edge_status": report.get("edge_status", "UNKNOWN"),
            "discovery_score": report.get("discovery_score"),
            "direction": report.get("direction"),
            "recommended_structure": report.get("recommended_structure"),
            "position_size": report.get("position_size"),
            "bankroll": report.get("bankroll"),
        }
        log.append(entry)

        checksum = atomic_save(TRADE_LOG_PATH, log)
        return {
            "milestone": "7_log",
            "status": "PASS",
            "data": {"log_path": str(TRADE_LOG_PATH), "checksum": checksum,
                     "entries": len(log)},
            "reason": f"Logged to {TRADE_LOG_PATH} ({len(log)} entries)",
        }
    except Exception as e:
        return {"milestone": "7_log", "status": "FAIL",
                "data": {}, "reason": f"Logging error: {e}"}


# ---------------------------------------------------------------------------
# Main evaluate function
# ---------------------------------------------------------------------------

def evaluate(ticker: str, bankroll: float = 100_000) -> dict:
    """Run the full 7-milestone evaluation for a ticker.

    Args:
        ticker: Stock ticker symbol.
        bankroll: Total available capital for Kelly sizing.

    Returns:
        Full evaluation report dict.
    """
    ticker = ticker.upper()
    client = YahooClient()
    milestones = {}
    report = {
        "ticker": ticker,
        "bankroll": bankroll,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # --- Milestone 1: Validate Ticker ---
    m1 = milestone_1_validate(client, ticker)
    milestones["1_validate"] = m1
    if m1["status"] == "FAIL":
        report["milestones"] = milestones
        report["edge_status"] = "FAIL"
        report["reason"] = m1["reason"]
        return report

    stock_info = m1.get("data", {})

    # --- Milestone 1B: Analyst Ratings (context) ---
    m1b = milestone_1b_analyst(client, ticker)
    milestones["1B_analyst"] = m1b

    # --- Milestone 1C: News context ---
    m1c = milestone_1c_news(ticker)
    milestones["1C_news"] = m1c

    # --- Milestone 2: Options Flow ---
    m2 = milestone_2_options_flow(client, ticker)
    milestones["2_options_flow"] = m2

    # --- Milestone 3: Institutional Signals ---
    m3 = milestone_3_institutional(client, ticker)
    milestones["3_institutional"] = m3

    # --- Milestone 3B: OI Changes (REQUIRED) ---
    m3b = milestone_3b_oi_changes(client, ticker)
    milestones["3B_oi_changes"] = m3b

    # --- Milestone 4: Edge Decision (GATE — stops if FAIL) ---
    m4 = milestone_4_edge_decision(milestones)
    milestones["4_edge_decision"] = m4

    edge_data = m4.get("data", {})
    report["discovery_score"] = edge_data.get("discovery_score")
    report["direction"] = edge_data.get("direction")

    if m4["status"] == "FAIL":
        report["milestones"] = milestones
        report["edge_status"] = "FAIL"
        report["reason"] = m4["reason"]
        # Log even failed evaluations
        milestone_7_log(ticker, report)
        return report

    report["edge_status"] = "PASS"

    # --- Milestone 5: Structure Design ---
    m5 = milestone_5_structure(milestones, stock_info)
    milestones["5_structure"] = m5
    report["recommended_structure"] = (
        m5.get("data", {}).get("recommended_structure", {}).get("type")
    )

    # --- Milestone 6: Kelly Sizing ---
    m6 = milestone_6_kelly(
        direction=edge_data.get("direction", "NEUTRAL"),
        avg_iv=milestones.get("2_options_flow", {}).get("data", {})
                .get("iv_data", {}).get("avg_atm_iv"),
        score=edge_data.get("discovery_score", 0),
        bankroll=bankroll,
    )
    milestones["6_kelly_sizing"] = m6
    report["position_size"] = m6.get("data", {}).get("position_size", 0)

    # --- Milestone 7: Log ---
    m7 = milestone_7_log(ticker, report)
    milestones["7_log"] = m7

    report["milestones"] = milestones
    return report


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Radon 7-milestone trade evaluation workflow"
    )
    parser.add_argument("ticker", help="Stock ticker symbol (e.g. AAPL)")
    parser.add_argument("--bankroll", type=float, default=100_000,
                        help="Total bankroll for Kelly sizing (default: 100000)")
    args = parser.parse_args()

    result = evaluate(args.ticker, args.bankroll)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
