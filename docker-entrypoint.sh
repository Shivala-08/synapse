#!/bin/bash
set -e

# If /app/data is mounted and empty (e.g. on Railway/Render persistent volumes),
# copy seed files to it.
if [ ! -f /app/data/knowledge_graph.json ]; then
  echo "Data volume is empty or uninitialized. Initializing with seed data..."
  mkdir -p /app/data
  cp -r /app/data_seed/* /app/data/
fi

# If chroma_db is empty or doesn't exist, build it
if [ ! -d /app/data/chroma_db ] || [ -z "$(ls -A /app/data/chroma_db 2>/dev/null)" ]; then
  echo "ChromaDB vector store is empty. Building index (this may take a few minutes)..."
  python -m src.pipeline.ingest
fi

echo "Starting Synapse FastAPI backend on port ${PORT:-8000}..."
exec uvicorn src.main:app --host 0.0.0.0 --port "${PORT:-8000}"
