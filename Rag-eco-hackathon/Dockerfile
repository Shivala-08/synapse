FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

# Set work directory
WORKDIR /app

# Install system dependencies (tesseract required for the OCR fallback in
# parser.py — without the binary, scanned-PDF pages silently extract as empty)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    g++ \
    libffi-dev \
    libssl-dev \
    curl \
    tesseract-ocr \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install git-lfs so the Docker build can resolve LFS-tracked files
# (chroma_db/, PDFs, PPTX) from the Git repository into real binaries.
RUN curl -sSL https://github.com/git-lfs/git-lfs/releases/download/v3.6.1/git-lfs-linux-amd64-v3.6.1.tar.gz | tar -xz -C /tmp \
    && mv /tmp/git-lfs-3.6.1/git-lfs /usr/local/bin/ \
    && git lfs install --system

# Copy requirements.txt first for layer caching
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Download spaCy model — FAIL THE BUILD if this breaks. A silent skip here
# means entity extraction dies at runtime with zero build-time signal.
RUN python -m spacy download en_core_web_sm

# Copy application files
COPY . /app/

# Pull Git LFS objects so chroma_db/, PDFs, and PPTX are real binaries
# instead of 1KB pointer files. The .git directory from COPY makes this work.
RUN git lfs pull

# Healthcheck: Railway/Render health probes and `docker ps` both use this.
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -fsS http://localhost:${PORT:-8000}/health || exit 1

# Create a seed directory for persistent data volumes.
# The entrypoint copies data_seed/ -> /app/data/ on first boot when the
# persistent volume is empty, so the pre-built ChromaDB index is available
# without rebuilding embeddings from scratch.
RUN mkdir -p /app/data_seed && \
    cp -r /app/data/* /app/data_seed/ || true

# Expose port
EXPOSE 8000

# Entrypoint seeds data (if needed) and starts Uvicorn
ENTRYPOINT ["/app/docker-entrypoint.sh"]
