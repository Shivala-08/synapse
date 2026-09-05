#!/bin/bash

# ── Synapse startup script ─────────────────────────────────────────────────
# Ports: Backend=8000, Frontend=3000 (matches Dockerfile and README).
# If a target port is already held by another process (e.g. a local service
# on 8000), the script falls back to 8010/3010 automatically and prints the
# URLs actually in use. Override explicitly with BACKEND_PORT/FRONTEND_PORT.
set -e

BACKEND_PORT=${BACKEND_PORT:-8000}
FRONTEND_PORT=${FRONTEND_PORT:-3000}

# Resolve python: prefer .venv, fall back to PATH
if [ -x ".venv/bin/python" ]; then
  PYTHON=".venv/bin/python"
elif command -v python3 &>/dev/null; then
  PYTHON="python3"
else
  echo "ERROR: python not found. Install dependencies first: pip install -r requirements.txt"
  exit 1
fi

# Returns 0 when something already answers HTTP on the port (i.e. it's busy).
port_in_use() {
  curl -s -o /dev/null --max-time 2 "http://localhost:$1" 2>/dev/null
}

# Kill stale servers from a previous run of this script.
echo "Cleaning up existing servers..."
pkill -f "uvicorn src.main:app" 2>/dev/null || true
pkill -f "next dev" 2>/dev/null || true
sleep 1

# Detect occupied ports AFTER cleanup so stale copies of our own servers
# don't trigger a pointless fallback.
if port_in_use "$BACKEND_PORT"; then
  echo "NOTE: port ${BACKEND_PORT} is already in use by another process."
  BACKEND_PORT="${BACKEND_PORT_ALT:-8010}"
  echo "      Backend will run on ${BACKEND_PORT} instead."
fi
if port_in_use "$FRONTEND_PORT"; then
  echo "NOTE: port ${FRONTEND_PORT} is already in use by another process."
  FRONTEND_PORT="${FRONTEND_PORT_ALT:-3010}"
  echo "      Frontend will run on ${FRONTEND_PORT} instead."
fi

echo "Starting FastAPI Backend on port ${BACKEND_PORT}..."
nohup ${PYTHON} -m uvicorn src.main:app --host 0.0.0.0 --port ${BACKEND_PORT} > backend.log 2>&1 &
echo "FastAPI backend started in background (logs: backend.log)."

echo "Starting Next.js Frontend on port ${FRONTEND_PORT}..."
npm --prefix web install
nohup env NEXT_PUBLIC_API_URL="http://localhost:${BACKEND_PORT}" npm --prefix web run dev -- -p ${FRONTEND_PORT} > frontend.log 2>&1 &
echo "Next.js frontend started in background (logs: frontend.log)."

# Wait for the backend to finish pre-warming before declaring success.
echo -n "Waiting for backend health... "
backend_ok=0
for i in $(seq 1 45); do
  if curl -sf "http://localhost:${BACKEND_PORT}/health" >/dev/null 2>&1; then
    echo "OK"
    backend_ok=1
    break
  fi
  sleep 1
done
if [ "$backend_ok" -eq 0 ]; then
  echo "TIMEOUT — backend did not become healthy. Last lines of backend.log:"
  echo "──────────────────────────────────────────────────"
  tail -15 backend.log
  echo "──────────────────────────────────────────────────"
fi

# First Next.js compile can take a while; give it a bounded window.
echo -n "Waiting for frontend... "
frontend_ok=0
for i in $(seq 1 60); do
  if curl -s -o /dev/null --max-time 2 "http://localhost:${FRONTEND_PORT}/" 2>/dev/null; then
    echo "OK"
    frontend_ok=1
    break
  fi
  sleep 1
done
if [ "$frontend_ok" -eq 0 ]; then
  echo "TIMEOUT — frontend did not respond. Last lines of frontend.log:"
  echo "──────────────────────────────────────────────────"
  tail -15 frontend.log
  echo "──────────────────────────────────────────────────"
fi

echo ""
echo "Done! Backend: http://localhost:${BACKEND_PORT}  Frontend: http://localhost:${FRONTEND_PORT}"
echo "API docs:      http://localhost:${BACKEND_PORT}/docs"