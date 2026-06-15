# Radon Backend Integration for AlphaHunt

This guide explains how to deploy the Radon FastAPI backend as a standalone service and connect AlphaHunt's frontend to it.

## Architecture

```
AlphaHunt Frontend (Vercel)  -->  Radon FastAPI Backend (Railway/Render)
       |                                    |
   Next.js app                     Python options analysis
   port 3000                       port 8321 (or $PORT)
```

AlphaHunt's frontend calls the Radon API for options flow data, analyst ratings, portfolio state, and Kelly sizing. The backend runs independently and can be deployed to any platform that supports Python.

## Files to Deploy

The Radon backend deployment uses these files from the repository root:

| File/Directory | Purpose |
|----------------|---------|
| `Procfile` | Process definition for Railway/Render |
| `runtime.txt` | Python version pinning (3.11.9) |
| `requirements.txt` | Python dependencies |
| `scripts/` | All backend source code |
| `data/` | Runtime data directory (created automatically) |
| `.env` | Alpaca API credentials (set via platform env vars, never commit) |

## Environment Variables

### Required on the Backend (Railway/Render)

| Variable | Description | Required |
|----------|-------------|----------|
| `PORT` | Port for the web process (set automatically by Railway/Render) | Auto |
| `ALPACA_API_KEY` | Alpaca paper/live API key | For broker features |
| `ALPACA_SECRET_KEY` | Alpaca secret key | For broker features |
| `CORS_ORIGINS` | Comma-separated allowed origins (e.g. `https://alphahunt.vercel.app,https://custom.domain.com`) | Optional |

### Required on the Frontend (AlphaHunt / Vercel)

| Variable | Description | Example |
|----------|-------------|---------|
| `REACT_APP_RADON_API_URL` | Full URL of the deployed Radon backend | `https://radon-api.up.railway.app` |

Set this in AlphaHunt's `.env` or in the Vercel project settings under Environment Variables.

## Deploying the FastAPI Backend

### Option A: Railway (One-Click)

1. Push this repo (or a fork) to GitHub.
2. Go to [railway.app](https://railway.app) and create a new project.
3. Select "Deploy from GitHub repo" and pick the Radon repository.
4. Railway auto-detects the `Procfile` and `runtime.txt`.
5. Add environment variables in the Railway dashboard:
   - `ALPACA_API_KEY`
   - `ALPACA_SECRET_KEY`
   - `CORS_ORIGINS` (set to your AlphaHunt frontend URL)
6. Deploy. Railway assigns a public URL like `https://radon-api.up.railway.app`.

### Option B: Render

1. Push this repo to GitHub.
2. Go to [render.com](https://render.com) and create a new **Web Service**.
3. Connect your GitHub repo.
4. Render detects the `Procfile` automatically. If not, set the start command to:
   ```
   cd scripts && python -m uvicorn api.server:app --host 0.0.0.0 --port $PORT
   ```
5. Set the runtime to Python 3.11.
6. Add environment variables in the Render dashboard.
7. Deploy. Render assigns a URL like `https://radon-api.onrender.com`.

### Option C: Manual / VPS

```bash
# Clone the repo
git clone <repo-url> && cd Radon_personal

# Install dependencies
pip install -r requirements.txt

# Set env vars
export ALPACA_API_KEY="..."
export ALPACA_SECRET_KEY="..."
export CORS_ORIGINS="https://your-alphahunt-url.vercel.app"

# Run
cd scripts && python -m uvicorn api.server:app --host 0.0.0.0 --port 8321
```

## Connecting AlphaHunt to the Deployed Backend

1. Get the deployed backend URL (e.g. `https://radon-api.up.railway.app`).

2. Verify the backend is running:
   ```bash
   curl https://radon-api.up.railway.app/health
   # Expected: {"status":"ok","services":{"yahoo_finance":true,...}}
   ```

3. Set the environment variable in AlphaHunt's deployment:
   ```
   REACT_APP_RADON_API_URL=https://radon-api.up.railway.app
   ```

4. In AlphaHunt frontend code, use this base URL for all API calls:
   ```javascript
   const RADON_API = process.env.REACT_APP_RADON_API_URL || "http://localhost:8321";
   
   // Example: fetch options flow
   const response = await fetch(`${RADON_API}/flow/AAPL`);
   const data = await response.json();
   ```

## Available API Endpoints

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

## CORS Configuration

The backend automatically allows requests from:
- `http://localhost:3000` (local Next.js dev)
- `http://localhost:3001` and `http://localhost:3002` (alternate local ports)
- Any `*.vercel.app` subdomain (regex match)
- Any origins listed in the `CORS_ORIGINS` environment variable (comma-separated)

For production, set `CORS_ORIGINS` to your specific AlphaHunt domain(s) for tighter security:
```
CORS_ORIGINS=https://alphahunt.vercel.app,https://alphahunt.com
```
