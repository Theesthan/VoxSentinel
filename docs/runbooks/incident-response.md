# Incident Response Runbook

## VoxSentinel Incident Response Procedures

### Severity Classification

| Severity | Description | Response Time | Examples |
|----------|-------------|---------------|----------|
| SEV-1 | Complete system outage | < 15 min | All streams down, no transcription |
| SEV-2 | Partial degradation | < 30 min | ASR failover active, high latency |
| SEV-3 | Minor issue | < 2 hours | Single stream failure, dashboard lag |
| SEV-4 | Cosmetic / low impact | Next business day | UI glitch, non-critical log errors |

### Common Incidents

#### 1. ASR Engine Failure

**Symptoms**: Transcription latency spike, failover alerts in logs
**Steps**:
1. Check ASR service logs: `docker compose logs asr --tail=100`
2. Verify engine health: `curl http://localhost:8000/health`
3. If cloud API (Deepgram) is down → system auto-fails to local Whisper
4. If all engines fail → restart ASR service: `docker compose restart asr`
5. Monitor recovery via dashboard

#### 2. Redis Connection Loss

**Symptoms**: No new transcripts appearing, services report unhealthy
**Steps**:
1. Check Redis: `docker compose logs redis --tail=50`
2. Test connectivity: `redis-cli ping`
3. Restart Redis: `docker compose restart redis`
4. Services will auto-reconnect

#### 3. PostgreSQL Disk Full

**Symptoms**: Storage service errors, write failures
**Steps**:
1. Check disk: `docker compose exec postgres df -h`
2. Run emergency cleanup of old data
3. Verify TimescaleDB compression is active
4. Consider increasing volume size

#### 4. Elasticsearch Cluster Red

**Symptoms**: Search API returns errors, no new indexing
**Steps**:
1. Check cluster health: `curl http://localhost:9200/_cluster/health`
2. Check unassigned shards: `curl http://localhost:9200/_cat/shards?v&h=index,shard,prirep,state,unassigned.reason`
3. Resolve based on reason (disk space, node failure, etc.)

### Escalation Path

1. On-call engineer investigates and resolves SEV-3/4
2. Team lead engaged for SEV-2
3. Engineering manager + team for SEV-1
