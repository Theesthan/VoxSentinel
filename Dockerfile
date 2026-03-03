# ── VoxSentinel API — Railway Dockerfile ──────────────────────────────────────
# Builds only the FastAPI backend (services/api + packages/tg-common).
# The React dashboard is deployed as a separate Railway service.

FROM python:3.11-slim

# System deps: FFmpeg (video audio extraction + YouTube HLS), git (for pip editable)
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg git && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Copy local packages (order matters for layer caching) ─────────────────────
COPY packages/ packages/
COPY services/api/ services/api/
COPY scripts/ scripts/
COPY create_tables.py .
COPY pyproject.toml .
# YouTube cookies (vidcookie.txt from throwaway account — private repo only)
COPY cookies/ cookies/

# ── Install Python packages ────────────────────────────────────────────────────
# 1. tg-common (local dep required by the API service)
# 2. the API service itself (pulls in fastapi, uvicorn, redis, sqlalchemy, etc.)
# 3. extras needed at runtime that are commented out in root pyproject.toml
RUN pip install --no-cache-dir -e packages/tg-common && \
    pip install --no-cache-dir -e services/api && \
    pip install --no-cache-dir \
        python-dotenv \
        "deepgram-sdk>=3.0" \
        pyahocorasick \
        rapidfuzz && \
    pip install --no-cache-dir --upgrade yt-dlp

# ── Port ──────────────────────────────────────────────────────────────────────
# Railway injects $PORT at runtime; we default to 8010 for local docker runs.
EXPOSE 8010

# ── Start ─────────────────────────────────────────────────────────────────────
# 1. Run DB migrations (create_tables.py is idempotent — safe to run every boot)
# 2. Start the FastAPI gateway
CMD ["sh", "-c", "python create_tables.py; exec uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8010} --app-dir services/api/src"]
