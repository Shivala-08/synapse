#!/bin/bash
set -e

# Ensure Python can find the src package
export PYTHONPATH=/app:${PYTHONPATH:-}

# Sync seed data if ChromaDB is not present in the target data directory
if [ ! -f /app/data/chroma_db/chroma.sqlite3 ]; then
  echo "ChromaDB SQLite index not found in /app/data. Seeding from pre-built database..."
  mkdir -p /app/data
  cp -r /app/data_seed/* /app/data/ || true
fi

# Double check if chroma_db is still empty (in case seeding was skipped or failed)
if [ ! -d /app/data/chroma_db ] || [ -z "$(ls -A /app/data/chroma_db 2>/dev/null)" ]; then
  echo "ChromaDB vector store is empty. Building index (this may take a few minutes)..."
  python -m src.pipeline.ingest
fi

echo "Starting Synapse FastAPI backend on port ${PORT:-8000}..."
exec uvicorn src.main:app --host 0.0.0.0 --port "${PORT:-8000}"
