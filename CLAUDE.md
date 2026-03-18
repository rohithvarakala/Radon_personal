# Radon Agent Rules

## Core Operational Gates (Mandatory, Sequential)

Every trade must pass three sequential gates. Any gate fails → stop immediately.

**Gate 1 (Convexity):** Potential gain ≥ 2× potential loss; defined-risk structures only (long options, verticals, calendars).

**Gate 2 (Edge):** Specific, data-backed signal that hasn't moved price yet — dark pool accumulation, LEAP IV divergence, cross-asset vol dislocation, or credit-vol regime shifts.

**Gate 3 (Risk Management):** Fractional Kelly sizing with hard 2.5% bankroll cap per position. No pyramiding into weak signals.

## Data Source Priority

1. **Interactive Brokers** — real-time quotes, options chains, portfolio state
2. **Unusual Whales** — dark pool flow, sweeps, options flow, analyst data
3. **Exa** — company and market research
4. **Cboe** — COR1M index feeds (official fallback)
5. **Yahoo Finance** — last-resort fallback

## Credentials Architecture (Two .env Files — Never Commit)

| File | Loaded by | Contains |
|------|-----------|----------|
| `.env` (root) | Python via `python-dotenv` | `MENTHORQ_USER`, `MENTHORQ_PASS` |
| `web/.env` | Next.js built-in | `ANTHROPIC_API_KEY`, `UW_TOKEN`, `EXA_API_KEY` |

## Market Hours Rule

Market open: 9:30–16:00 ET, Mon–Fri. Check `TZ=America/New_York date +"%A %H:%M"`.

- **Market OPEN:** Fetch fresh data. Cache TTL: flow 5 min, ratings 15 min.
- **Market CLOSED:** Use latest available; flag staleness.

## Development Practices

- **TDD:** Failing test first, implementation second, refactor third. Target ≥95% coverage.
- **Atomic writes:** All portfolio/data writes use temp file + `os.replace()` + SHA-256 checksum.
- **Ticker key:** Always `"ticker"` in JSON data files, `"symbol"` only for IB contract objects.

## 7-Milestone Evaluation Workflow

```
1.  Validate Ticker
1B. Seasonality (context only)
1C. Analyst Ratings (context only)
1D. News & Catalysts (context only)
2.  Dark Pool Flow
3.  Options Flow
3B. OI Changes (REQUIRED)
4.  Edge Decision (PASS/FAIL — fail = stop)
5.  Structure (convex, R:R > 2:1)
6.  Kelly Sizing (2.5% cap)
7.  Log (trade_log.json)
```

## Signal Interpretation

- **Put/Call Ratio:** >2.0 BEARISH | 1.2–2.0 LEAN_BEARISH | 0.8–1.2 NEUTRAL | 0.5–0.8 LEAN_BULLISH | <0.5 BULLISH
- **Flow Side:** Ask-side = buying pressure | Bid-side = selling pressure
- **Analyst Buy %:** ≥70% BULLISH | 50–69% LEAN_BULLISH | 30–49% LEAN_BEARISH | <30% BEARISH
- **Discovery Score (0–100):** 60–100 Strong | 40–59 Monitor | 20–39 Weak | <20 No signal

## Three-Service Dev Stack

```bash
npm run dev  # starts all three:
```

| Service | Port | Role |
|---------|------|------|
| Next.js | 3000 | Web UI |
| IB WS relay | 8765 | Real-time price streaming |
| FastAPI | 8321 | Python script execution |

## IB Client ID Allocation

| Range | Zone | Usage |
|-------|------|-------|
| 0–9 | Pool | FastAPI IBPool (sync=0, orders=1, data=2) |
| 10–19 | Relay | WS relay |
| 20–49 | Subprocess | Scripts use `client_id="auto"` |
| 50–69 | Scanners | CRI/VCG rotating pools |
| 70–89 | Daemons | Fill monitor=70, exit service=71 |
| 90–99 | CLI | Standalone scripts |

## Commands

| Command | Action |
|---------|--------|
| `scan` | Watchlist dark pool flow scan |
| `discover` | Market-wide options flow |
| `evaluate [TICKER]` | Full 7-milestone evaluation |
| `portfolio` | Positions, exposure, capacity |
| `sync` | Pull live portfolio from IB |
| `blotter` | Today's fills + P&L |
| `leap-scan [TICKERS]` | LEAP IV mispricing |
| `garch-convergence [TICKERS]` | Cross-asset GARCH vol divergence |
| `vcg-scan` | Volatility-credit gap divergence |
| `cri-scan` | Crash Risk Index |
