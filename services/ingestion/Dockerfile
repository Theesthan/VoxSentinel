FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY packages/tg-common /app/packages/tg-common
COPY services/ingestion /app/services/ingestion

RUN pip install --no-cache-dir /app/packages/tg-common /app/services/ingestion

FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg curl && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY services/ingestion/src /app/src

EXPOSE 8001
CMD ["python", "-m", "ingestion.main"]
