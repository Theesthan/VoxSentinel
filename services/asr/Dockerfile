FROM python:3.12-slim AS builder

ARG TORCH_INDEX=https://download.pytorch.org/whl/cpu

WORKDIR /app
COPY packages/tg-common /app/packages/tg-common
COPY services/asr /app/services/asr
RUN pip install --no-cache-dir \
    --extra-index-url ${TORCH_INDEX} \
    /app/packages/tg-common /app/services/asr

FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY services/asr/src /app/src
EXPOSE 8003
CMD ["python", "-m", "asr.main"]
