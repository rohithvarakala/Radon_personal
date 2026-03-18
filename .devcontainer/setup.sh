#!/bin/bash
# Radon Codespaces setup — runs automatically on container creation

set -e

echo "=== Installing Python dependencies ==="
pip install -r requirements.txt

echo "=== Installing Node.js dependencies ==="
cd web && npm install && cd ..

echo "=== Creating data directories ==="
mkdir -p data/seasonality_cache data/menthorq_cache data/price_history_cache/stocks data/price_history_cache/options data/cri_scheduled

echo ""
echo "============================================"
echo "  Radon Terminal — Setup Complete"
echo "============================================"
echo ""
echo "  Next steps:"
echo ""
echo "  1. Create your .env files:"
echo "     cp .env.example .env"
echo "     cp web/.env.example web/.env"
echo "     Then edit them with your API keys."
echo ""
echo "  2. Start the system:"
echo "     bash start.sh"
echo ""
echo "  3. Or start services individually:"
echo "     FastAPI:  cd scripts && python -m uvicorn api.server:app --port 8321 --reload"
echo "     Next.js:  cd web && npm run dev:web"
echo ""
echo "============================================"
