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
    && rm -rf /var/lib/apt/lists/*

# Copy requirements.txt
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Download spaCy model — FAIL THE BUILD if this breaks. A silent skip here
# means entity extraction dies at runtime with zero build-time signal.
RUN python -m spacy download en_core_web_sm


# Copy application files
COPY . /app/

# Healthcheck: Render/FaaS orchestrators and `docker ps` both use this.
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -fsS http://localhost:${PORT:-8000}/health || exit 1

# Create a seed directory for persistent data volumes
RUN mkdir -p /app/data_seed && \
    cp -r /app/data/* /app/data_seed/ || true

# Copy and configure entrypoint script
COPY docker-entrypoint.sh /app/
RUN chmod +x /app/docker-entrypoint.sh

# Expose port
EXPOSE 8000

# Entrypoint runs volume initialization and starts Uvicorn
ENTRYPOINT ["/app/docker-entrypoint.sh"]
