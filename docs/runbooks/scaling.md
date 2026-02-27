# Scaling Runbook

## VoxSentinel Horizontal & Vertical Scaling

### When to Scale

| Metric | Threshold | Action |
|--------|-----------|--------|
| Ingestion queue depth | > 1000 messages | Scale ingestion replicas |
| ASR p95 latency | > 2 seconds | Scale ASR replicas or add GPU |
| NLP processing backlog | > 500 messages | Scale NLP replicas |
| API response time | > 500ms p95 | Scale API replicas |
| Dashboard WebSocket connections | > 100 per pod | Scale dashboard replicas |

### Scaling Services

#### Docker Compose

```bash
docker compose up -d --scale ingestion=3 --scale asr=2 --scale nlp=2
```

#### Kubernetes

```bash
kubectl scale deployment voxsentinel-asr --replicas=3
# or update values.prod.yaml and:
helm upgrade voxsentinel helm/transcriptguard/ -f helm/transcriptguard/values.prod.yaml
```

### GPU Scaling for ASR / Diarization

- Each ASR pod with local Whisper requires 1 NVIDIA GPU (8GB+ VRAM)
- Diarization pods with pyannote require 1 GPU (4GB+ VRAM)
- Use `nvidia-smi` to monitor GPU utilization

### Redis Scaling

- For > 50 concurrent streams, consider Redis Cluster or Redis Sentinel
- Monitor memory usage: `redis-cli info memory`

### PostgreSQL Scaling

- Enable read replicas for search-heavy workloads
- TimescaleDB hypertable compression for data > 30 days old

### Elasticsearch Scaling

- Add data nodes for index performance
- Set ILM policies for index lifecycle management
