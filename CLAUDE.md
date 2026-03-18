# Radon Agent Rules

## Core Operational Gates (Mandatory, Sequential)

Every trade must pass three sequential gates. Any gate fails → stop immediately.

**Gate 1 (Convexity):** Potential gain ≥ 2× potential loss; defined-risk structures only (long options, verticals, calendars).

**Gate 2 (Edge):** Specific, data-backed signal that hasn't moved price yet — IV divergence, cross-asset vol dislocation, unusual options activity, or credit-vol regime shifts.

**Gate 3 (Risk Management):** Fractional Kelly sizing with hard 2.5% bankroll cap per position. No pyramiding into weak signals.

## Data Source Priority

1. **Yahoo Finance** — options chains, IV data, analyst ratings, price history (free, no API key)
2. **Alpaca** — paper/live trading, real-time quotes, portfolio state (free paper trading)
3. **Anthropic Claude** — AI analysis, vision extraction, chat interface
4. **Exa** — company and market research (optional)

## Credentials Architecture (Two .env Files — Never Commit)

| File | Loaded by | Contains |
|------|-----------|----------|
| `.env` (root) | Python via `python-dotenv` | `ALPACA_API_KEY`, `ALPACA_SECRET_KEY` |
| `web/.env` | Next.js built-in | `ANTHROPIC_API_KEY`, `EXA_API_KEY` |

## Market Hours Rule

Market open: 9:30–16:00 ET, Mon–Fri. Check `TZ=America/New_York date +"%A %H:%M"`.

- **Market OPEN:** Fetch fresh data. Cache TTL: flow 5 min, ratings 15 min.
- **Market CLOSED:** Use latest available; flag staleness.

## Development Practices

- **TDD:** Failing test first, implementation second, refactor third. Target ≥95% coverage.
- **Atomic writes:** All portfolio/data writes use temp file + `os.replace()` + SHA-256 checksum.
- **Ticker key:** Always `"ticker"` in JSON data files, `"symbol"` only for broker contract objects.

## 7-Milestone Evaluation Workflow

```
1.  Validate Ticker
1B. Seasonality (context only)
1C. Analyst Ratings (context only)
1D. News & Catalysts (context only)
2.  Options Flow (put/call ratio, IV, unusual activity)
3.  Institutional Signals (short interest, institutional holders)
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

## Two-Service Dev Stack

```bash
npm run dev  # starts both:
```

| Service | Port | Role |
|---------|------|------|
| Next.js | 3000 | Web UI |
| FastAPI | 8321 | Python script execution + broker API |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Service status check |
| GET | `/portfolio` | Current portfolio state |
| GET | `/watchlist` | Watchlist tickers |
| POST | `/watchlist/{symbol}` | Add ticker to watchlist |
| DELETE | `/watchlist/{symbol}` | Remove from watchlist |
| POST | `/scan` | Batch options flow scan |
| GET | `/ticker/{symbol}` | Validate ticker + info |
| GET | `/flow/{symbol}` | Options flow + institutional signals |
| GET | `/options/{symbol}` | Options chain |
| GET | `/analyst/{symbol}` | Analyst ratings + targets |
| GET | `/history/{symbol}` | Price history |
| POST | `/kelly` | Kelly position sizing |
| GET | `/broker/status` | Alpaca connection status |
| GET | `/broker/positions` | Open broker positions |

## Commands

| Command | Action |
|---------|--------|
| `scan` | Watchlist options flow scan |
| `discover` | Market-wide options flow |
| `evaluate [TICKER]` | Full 7-milestone evaluation |
| `portfolio` | Positions, exposure, capacity |
| `sync` | Pull live portfolio from Alpaca |
| `leap-scan [TICKERS]` | LEAP IV mispricing |
| `garch-convergence [TICKERS]` | Cross-asset GARCH vol divergence |
| `vcg-scan` | Volatility-credit gap divergence |
| `cri-scan` | Crash Risk Index |
