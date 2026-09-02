#!/bin/bash
# Stop the Synapse backend and frontend started by ./start.sh

echo "Stopping Synapse servers..."
pkill -f "uvicorn src.main:app" 2>/dev/null && echo "FastAPI backend stopped." || echo "No backend process found."
pkill -f "next dev" 2>/dev/null && echo "Next.js frontend stopped." || echo "No frontend process found."
sleep 1
echo "Done. Ports freed."
