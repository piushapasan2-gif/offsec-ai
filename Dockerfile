# OffSec AI 2025 — Docker image (alternative to native Render Python env)
FROM python:3.11-slim

WORKDIR /app

# System deps for some Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1 PROD=1 STORAGE_BACKEND=supabase

# Render sets $PORT
ENV PORT=10000
EXPOSE 10000

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:${PORT}/health || exit 1

CMD ["sh", "-c", "gunicorn --worker-class gthread -w 1 --threads 8 --bind 0.0.0.0:${PORT} --timeout 120 --log-level info wsgi:app"]
