FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    PYTHONPATH=/app

WORKDIR /app

# System deps: tesseract for OCR fallback in parser
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential g++ libffi-dev libssl-dev curl tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY Rag-eco-hackathon/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# spaCy model
RUN python -m spacy download en_core_web_sm

# App source
COPY Rag-eco-hackathon/src /app/src
COPY Rag-eco-hackathon/domains /app/domains
COPY Rag-eco-hackathon/docker-entrypoint.sh /app/docker-entrypoint.sh
# config.py is part of src/

RUN chmod +x /app/docker-entrypoint.sh

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -fsS http://localhost:${PORT:-8000}/health || exit 1

EXPOSE 8000
ENTRYPOINT ["/app/docker-entrypoint.sh"]
