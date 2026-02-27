# Deployment Guide

## VoxSentinel (TranscriptGuard) Deployment

### Prerequisites

- Docker >= 24.0
- Docker Compose >= 2.20
- NVIDIA GPU drivers (optional, for local ASR/diarization)
- Kubernetes >= 1.28 (for Helm deployment)

### Local Development

```bash
# Clone and configure
cp .env.example .env
# Edit .env with your API keys and settings

# Build and start all services
make build
make run

# Verify all services are healthy
curl http://localhost:8000/health
```

### Docker Compose (Production)

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Kubernetes (Helm)

```bash
helm install voxsentinel helm/transcriptguard/ -f helm/transcriptguard/values.prod.yaml
```

### Environment Variables

See `.env.example` for all configurable environment variables.

### Database Migrations

```bash
make migrate
make seed  # Optional: seed with sample data
```

### Monitoring

- API health: `GET /health`
- Prometheus metrics: `GET /metrics`
- Dashboard: `http://localhost:8501`
