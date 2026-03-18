#!/bin/bash
# Start Radon services (FastAPI backend + Next.js frontend)

set -e

# Check for .env files
if [ ! -f .env ]; then
  echo "ERROR: .env file not found. Run:"
  echo "  cp .env.example .env"
  echo "  Then edit it with your Alpaca API keys."
  exit 1
fi

if [ ! -f web/.env ]; then
  echo "ERROR: web/.env file not found. Run:"
  echo "  cp web/.env.example web/.env"
  echo "  Then edit it with your Anthropic API key."
  exit 1
fi

echo "Starting Radon services..."
echo ""

# Start FastAPI in background
echo "[1/2] Starting FastAPI on :8321..."
cd scripts
python -m uvicorn api.server:app --host 0.0.0.0 --port 8321 --reload &
FASTAPI_PID=$!
cd ..

# Wait for FastAPI to be ready
sleep 2

# Start Next.js
echo "[2/2] Starting Next.js on :3000..."
cd web
npx next dev --hostname 0.0.0.0 &
NEXT_PID=$!
cd ..

echo ""
echo "============================================"
echo "  Radon Terminal is running"
echo "============================================"
echo "  UI:  http://localhost:3000"
echo "  API: http://localhost:8321"
echo ""
echo "  Test endpoints:"
echo "    curl http://localhost:8321/health"
echo "    curl http://localhost:8321/ticker/AAPL"
echo "    curl http://localhost:8321/flow/NVDA"
echo "    curl http://localhost:8321/broker/status"
echo ""
echo "  Press Ctrl+C to stop all services"
echo "============================================"

# Trap Ctrl+C to kill both processes
trap "echo 'Stopping...'; kill $FASTAPI_PID $NEXT_PID 2>/dev/null; exit" INT TERM

# Wait for either process to exit
wait
