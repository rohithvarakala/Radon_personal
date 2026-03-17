# Radon Setup & Implementation Plan

## What is Radon?

Radon is a **Python/Next.js trading system** that detects institutional positioning through dark pool flow, options signals, and cross-asset volatility data, then converts these into structured options trades. It enforces three sequential gates on every trade: **Convexity** (2:1+ R:R), **Edge** (data-backed signal), and **Risk Management** (fractional Kelly sizing, 2.5% max per position).

---

## Phase 1: Repository Foundation

### 1.1 Project Structure Setup
Create the core directory structure mirroring Radon's architecture:

```
Radon_personal/
├── scripts/                # Python scanners, evaluators, broker integrations
│   ├── clients/            # IBClient, UWClient, MenthorQClient adapters
│   ├── api/                # FastAPI server, IB pool, gateway manager
│   ├── utils/              # atomic_io, price_cache, vectorized_greeks
│   └── tests/              # Python test suite (pytest)
├── web/                    # Next.js 16 terminal UI
│   ├── app/                # Next.js app router routes
│   ├── components/         # Terminal UI components
│   └── lib/                # Shared utilities (criStaleness, exposureBreakdown, etc.)
├── data/                   # Runtime artifacts and scan outputs (gitignored)
│   ├── seasonality_cache/
│   ├── menthorq_cache/
│   ├── price_history_cache/
│   └── cri_scheduled/
├── docs/                   # Strategy and implementation documentation
├── brand/                  # Design system, tokens, component kit
├── config/                 # Service configuration (launchd plists etc.)
├── .pi/                    # Command registry and agent skills
├── requirements.txt        # Python dependencies
├── .env.example            # Template for root env vars
├── web/.env.example        # Template for web env vars
├── .gitignore              # Exclude data/, .env files, node_modules, etc.
└── CLAUDE.md               # Agent rules and workflows
```

### 1.2 Git & GitHub Configuration
- Initialize with `.gitignore` (exclude `data/`, `.env`, `node_modules/`, `__pycache__/`, `*.pyc`, `.next/`)
- Add `.env.example` files as credential templates (never commit real keys)
- Set up branch protection on `main`

---

## Phase 2: Dependencies & Environment

### 2.1 Python Dependencies (`requirements.txt`)
```
ib_insync>=0.9.86        # Interactive Brokers API
requests>=2.28.0         # HTTP requests
pandas>=1.5.0            # Data analysis
numpy                    # Vectorized math (Kelly, Greeks)
python-dotenv            # .env file loading
httpx                    # Async HTTP client
playwright               # Browser automation (MenthorQ)
fastapi                  # API server
uvicorn                  # ASGI server for FastAPI
pytest                   # Testing
```

### 2.2 Node.js Dependencies (web/)
- Next.js 16, React, Vitest, Playwright (E2E)
- D3 (regime charts), Satori/next-og (share cards)
- `@fontsource/ibm-plex-mono` (typography)

### 2.3 API Keys & Credentials (Two `.env` files)

**Root `.env`** (loaded by Python scripts via `python-dotenv`):
```
MENTHORQ_USER=your-menthorq-email
MENTHORQ_PASS=your-menthorq-password
```

**`web/.env`** (loaded by Next.js):
```
ANTHROPIC_API_KEY=your-anthropic-key
UW_TOKEN=your-unusual-whales-api-key
EXA_API_KEY=your-exa-key
CEREBRAS_API_KEY=your-cerebras-key  # optional
```

**Optional**: `XAI_API_KEY` for X sentiment scanning.

### 2.4 External Service Accounts Needed
| Service | Purpose | Required? |
|---------|---------|-----------|
| **Interactive Brokers** | Live quotes, order execution, portfolio sync | Yes (core) |
| **Unusual Whales** | Dark pool flow, options flow, analyst data | Yes (primary signal source) |
| **Anthropic (Claude)** | AI chat, vision for seasonality extraction | Yes |
| **Exa** | Company/market research | Recommended |
| **MenthorQ** | CTA positioning data | Optional |
| **xAI** | X/Twitter sentiment | Optional |

---

## Phase 3: Core Python Infrastructure

### 3.1 Client Adapters (`scripts/clients/`)
Build in this order:

1. **`ib_client.py`** — IBClient: connection management, quotes, orders, fills, Flex queries, resilient reconnect
2. **`uw_client.py`** — UWClient: dark pool, flow alerts, options chain, ratings, seasonality (50+ endpoints against `api.unusualwhales.com`)
3. **`menthorq_client.py`** — MenthorQClient: browser automation via Playwright for CTA positioning

### 3.2 Utility Layer (`scripts/utils/`)
1. **`atomic_io.py`** — Atomic JSON save/load with `os.replace()` + SHA-256 checksum
2. **`price_cache.py`** — Per-contract JSON cache with TTL (15 min market hours, 24h after close)
3. **`vectorized_greeks.py`** — NumPy vectorized delta/gamma across portfolio
4. **`incremental_sync.py`** — Diff-based portfolio sync by `(ticker, expiry)` key

### 3.3 Core Scripts
| Priority | Script | Purpose |
|----------|--------|---------|
| 1 | `scripts/fetch_ticker.py` | Ticker validation |
| 2 | `scripts/fetch_flow.py` | Dark pool + options flow retrieval |
| 3 | `scripts/fetch_options.py` | Options chain + institutional flow |
| 4 | `scripts/kelly.py` | Kelly sizing (scalar + NumPy batch) |
| 5 | `scripts/scanner.py` | Watchlist batch scan (ThreadPoolExecutor, 15 workers) |
| 6 | `scripts/discover.py` | Market-wide flow scanner (10 workers) |
| 7 | `scripts/ib_sync.py` | Sync IB portfolio, detect position structures |
| 8 | `scripts/cri_scan.py` | Crash Risk Index computation |
| 9 | `scripts/vcg_scan.py` | Volatility-Credit Gap divergence |
| 10 | `scripts/leap_scanner_uw.py` | LEAP IV mispricing detection |

---

## Phase 4: FastAPI Server (`scripts/api/`)

### 4.1 Server Components
1. **`server.py`** — 19 endpoints, CORS, health check, auto-restart (port 8321)
2. **`ib_pool.py`** — Role-based persistent IB connections (sync=0, orders=11, data=31) with auto-reconnect
3. **`ib_gateway.py`** — Health check, auto-restart IB Gateway on `ECONNREFUSED`
4. **`subprocess.py`** — Async subprocess helper with JSON extraction and timeout

### 4.2 Key Design Patterns
- **Client ID allocation**: Ranges 0-9 (pool), 10-19 (relay), 20-49 (subprocess/auto), 50-69 (scanners), 70-89 (daemons), 90-99 (CLI)
- **Graceful degradation**: FastAPI up + IB down = auto-restart Gateway, retry once, else 503 + cached data
- **Health endpoint**: `GET /health` returns IB Gateway port status, pool states, UW availability

---

## Phase 5: Next.js Terminal UI (`web/`)

### 5.1 Foundation
- Next.js 16 app with app router
- Radon brand system (design tokens, Inter + IBM Plex Mono typography)
- Dark/light theme support via CSS variables

### 5.2 Core Components
| Component | Purpose |
|-----------|---------|
| Portfolio table | Live positions with per-leg P&L, Greeks, trend arrows |
| RegimePanel | RVOL/COR1M regime classification strip (5-up responsive) |
| CriHistoryChart | D3 charts for VIX/VVIX and RVOL/COR1M (20 sessions) |
| Options chain | Sticky header grid with live Greeks |
| Order management | Combo spread workflows, BAG orders |
| AI chat | Command execution interface |
| Share PnL card | 1200x630 PNG via Satori for social sharing |

### 5.3 Real-Time Data
- **WebSocket relay** (`scripts/ib_realtime_server.js`) on port 8765 — batched ticks, 100ms flush
- **`usePrices.ts` state machine** — ref-based state, socket generation guard, diff-based subscription sync, exponential backoff reconnect

---

## Phase 6: Six Trading Strategies

Implement each strategy module with its signal detection, evaluation, and structure design:

| # | Strategy | Key Script | Signal Source |
|---|----------|------------|---------------|
| 1 | Dark Pool Flow | `fetch_flow.py` | Unusual Whales dark pool API |
| 2 | LEAP IV Mispricing | `leap_scanner_uw.py` | UW + Yahoo Finance IV data |
| 3 | GARCH Convergence | `garch_convergence.py` | Cross-asset vol surfaces |
| 4 | Risk Reversal | `risk_reversal.py` | IV skew analysis |
| 5 | VCG (Vol-Credit Gap) | `vcg_scan.py` | VIX/VVIX/HYG divergence |
| 6 | CRI (Crash Risk Index) | `cri_scan.py` | CTA deleveraging + correlation |

Each strategy feeds into the **7-Milestone Evaluation Workflow**:
```
1.  Validate Ticker → 1B. Seasonality → 1C. Analyst Ratings → 1D. News
2.  Dark Pool Flow
3.  Options Flow → 3B. OI Changes
4.  Edge Decision (PASS/FAIL — fail = stop)
5.  Structure Design (convex, R:R > 2:1)
6.  Kelly Sizing (2.5% cap)
7.  Log (trade_log.json)
```

---

## Phase 7: Background Services & Automation

### 7.1 Services to Configure
| Service | Schedule | Purpose |
|---------|----------|---------|
| CRI scan | Every 30 min, 4:05 AM–8 PM ET | Crash risk regime refresh |
| CTA sync | 4:15 PM + 5:00 PM ET daily | MenthorQ CTA cache update |
| Fill monitor | Continuous | Track fills, post-entry workflows |
| Data refresh | Continuous | Portfolio + order data freshness |

### 7.2 GitHub Actions (CI/CD)
Set up workflows for:
- **Python tests**: `pytest scripts/tests/ -v` on push/PR
- **Frontend tests**: `npm test` (Vitest) on push/PR
- **E2E tests**: Playwright browser tests
- **Linting**: Code quality checks

---

## Phase 8: Testing & Quality

### 8.1 Testing Requirements
- **Target**: >=95% test coverage
- **TDD**: Red/green/refactor — failing test first, implementation second
- **Python**: pytest with mocked API calls (no live IB/UW needed for dev)
- **Frontend**: Vitest for unit tests
- **E2E**: Playwright browser tests
- **Financial calculations**: Cross-validated against TypeScript to 10^-12 tolerance

### 8.2 Commands
```bash
python -m pytest scripts/tests/ -v      # Python unit tests
cd web && npm test                       # Vitest frontend tests
cd web && npx playwright test            # E2E browser tests
```

---

## Phase 9: Deployment & Operations

### 9.1 GitHub-Based Setup (No Local Machine Required)
Since you want this on GitHub without local setup:

1. **GitHub Codespaces** or **Gitpod** for cloud development environment
2. **Vercel** for the Next.js terminal UI deployment (use `web/` as root directory)
3. **Railway/Render** for the FastAPI backend (port 8321)
4. **GitHub Secrets** for all API keys (ANTHROPIC_API_KEY, UW_TOKEN, EXA_API_KEY, etc.)
5. **GitHub Actions** for automated scans (CRI, CTA sync on cron schedules)

### 9.2 IB Gateway Considerations
Interactive Brokers requires a persistent connection. Options for cloud:
- **IBeam** — Dockerized IB Gateway (runs in cloud)
- **ib-gateway-docker** — Community Docker image for headless IB Gateway
- Cloud VM (AWS/GCP) running IB Gateway with Tailscale for secure access

### 9.3 Marketing Site
Standalone Next.js site in `site/` directory, deployable to Vercel with `NEXT_PUBLIC_SITE_URL` configured.

---

## Execution Order Summary

| Step | Phase | Key Deliverable | Dependencies |
|------|-------|-----------------|-------------|
| 1 | Phase 1 | Repo structure, .gitignore, CLAUDE.md | None |
| 2 | Phase 2 | requirements.txt, package.json, .env templates | Phase 1 |
| 3 | Phase 3.1-3.2 | Client adapters + utility layer | Phase 2 |
| 4 | Phase 3.3 | Core scanning/evaluation scripts | Phase 3.1-3.2 |
| 5 | Phase 4 | FastAPI server with IB pool | Phase 3 |
| 6 | Phase 5 | Next.js terminal UI | Phase 4 |
| 7 | Phase 6 | All 6 strategy modules | Phase 3-5 |
| 8 | Phase 7 | Background services + GitHub Actions CI | Phase 5-6 |
| 9 | Phase 8 | Full test suite (95%+ coverage) | All phases |
| 10 | Phase 9 | Cloud deployment (Vercel + Railway + IB) | Phase 8 |

---

## Critical Rules to Follow Throughout

1. **Three Gates are non-negotiable** — Convexity, Edge, Risk Management. Any failure = stop.
2. **Data source priority**: IB > Unusual Whales > Exa > Cboe > Yahoo Finance
3. **Never commit `.env` files** — use `.env.example` templates only
4. **Atomic writes** for all portfolio/trade data — temp file + `os.replace()` + SHA-256
5. **Brand compliance** is mandatory for all UI — 4px max border-radius, design tokens only, no raw hex
6. **TDD** — failing test first, then implementation, then refactor
7. **Financial calculation correctness** — follow exact formulas for daily change %, return on risk, leg P&L
8. **Ticker key = `"ticker"`** in JSON data files, `"symbol"` only for IB contract objects
