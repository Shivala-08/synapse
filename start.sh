#!/bin/bash

# Kill any existing servers on ports 8081 and 3001
echo "Cleaning up existing servers..."
pkill -f "uvicorn src.main:app"
pkill -f "next dev"
sleep 1

echo "Starting FastAPI Backend on port 8081..."
nohup .venv/bin/uvicorn src.main:app --host 0.0.0.0 --port 8081 > backend.log 2>&1 &
echo "FastAPI backend started in background (logs: backend.log)."

echo "Starting Next.js Frontend on port 3001..."
# Run npm install to ensure all dependencies are resolved
npm --prefix web install
nohup env NEXT_PUBLIC_API_URL="http://localhost:8081" npm --prefix web run dev -- -p 3001 > frontend.log 2>&1 &
echo "Next.js frontend started in background (logs: frontend.log)."

sleep 2
echo "Done! Check server statuses using 'lsof -i :8081' and 'lsof -i :3001'."
