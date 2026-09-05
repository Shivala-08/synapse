#!/bin/bash
set -e
export PYTHONPATH=/app:${PYTHONPATH:-}

echo "Starting Synapse FastAPI backend on port ${PORT:-8000}..."
exec uvicorn src.main:app --host 0.0.0.0 --port "${PORT:-8000}"
