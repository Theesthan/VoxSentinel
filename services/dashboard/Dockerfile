FROM python:3.12-slim AS builder
WORKDIR /app
COPY packages/tg-common /app/packages/tg-common
COPY services/dashboard /app/services/dashboard
RUN pip install --no-cache-dir /app/packages/tg-common /app/services/dashboard

FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY services/dashboard/src /app/src
EXPOSE 8501
CMD ["streamlit", "run", "src/dashboard/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
