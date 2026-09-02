#!/bin/bash

# ── Synapse startup script ─────────────────────────────────────────────────
# Ports: Backend=8000, Frontend=3000 (matches Dockerfile and README)
set -e

BACKEND_PORT=${BACKEND_PORT:-8000}
FRONTEND_PORT=${FRONTEND_PORT:-3000}

# Resolve uvicorn: prefer .venv, fall back to PATH
if [ -x ".venv/bin/uvicorn" ]; then
  UVICORN=".venv/bin/uvicorn"
elif command -v uvicorn &>/dev/null; then
  UVICORN="uvicorn"
else
  echo "ERROR: uvicorn not found. Install dependencies first: pip install -r requirements.txt"
  exit 1
fi

# Kill any existing servers on the target ports
echo "Cleaning up existing servers..."
pkill -f "uvicorn src.main:app" 2>/dev/null || true
pkill -f "next dev" 2>/dev/null || true
sleep 1

echo "Starting FastAPI Backend on port ${BACKEND_PORT}..."
nohup ${UVICORN} src.main:app --host 0.0.0.0 --port ${BACKEND_PORT} > backend.log 2>&1 &
echo "FastAPI backend started in background (logs: backend.log)."

echo "Starting Next.js Frontend on port ${FRONTEND_PORT}..."
npm --prefix web install
nohup env NEXT_PUBLIC_API_URL="http://localhost:${BACKEND_PORT}" npm --prefix web run dev -- -p ${FRONTEND_PORT} > frontend.log 2>&1 &
echo "Next.js frontend started in background (logs: frontend.log)."

sleep 2
echo "Done! Backend: http://localhost:${BACKEND_PORT}  Frontend: http://localhost:${FRONTEND_PORT}"
