FROM python:3.12-slim AS builder
WORKDIR /app
COPY packages/tg-common /app/packages/tg-common
COPY services/storage /app/services/storage
RUN pip install --no-cache-dir /app/packages/tg-common /app/services/storage

FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY services/storage/src /app/src
EXPOSE 8007
CMD ["python", "-m", "storage.main"]
