# Backup & Restore Runbook

## VoxSentinel Data Backup and Recovery

### What to Back Up

| Component | Data | Frequency | Retention |
|-----------|------|-----------|-----------|
| PostgreSQL | Transcripts, alerts, rules, audit logs | Daily + WAL continuous | 90 days |
| Elasticsearch | Search indexes | Daily snapshot | 30 days |
| Redis | Ephemeral (no backup needed) | — | — |
| Configuration | `.env`, Helm values, rules | On change | Indefinite |

### PostgreSQL Backup

#### Automated Daily Backup

```bash
# Full logical backup
docker compose exec postgres pg_dump -U tguser transcriptguard | gzip > backup_$(date +%Y%m%d).sql.gz

# With TimescaleDB
docker compose exec postgres pg_dump -U tguser -Fc transcriptguard > backup_$(date +%Y%m%d).dump
```

#### Continuous WAL Archiving

Configure `archive_command` in PostgreSQL for point-in-time recovery (PITR).

### PostgreSQL Restore

```bash
# From logical backup
gunzip -c backup_20260101.sql.gz | docker compose exec -T postgres psql -U tguser transcriptguard

# From custom format
docker compose exec -T postgres pg_restore -U tguser -d transcriptguard < backup_20260101.dump
```

### Elasticsearch Backup

#### Create Snapshot Repository

```bash
curl -X PUT "localhost:9200/_snapshot/backups" -H 'Content-Type: application/json' -d '{
  "type": "fs",
  "settings": { "location": "/usr/share/elasticsearch/backups" }
}'
```

#### Take Snapshot

```bash
curl -X PUT "localhost:9200/_snapshot/backups/snapshot_$(date +%Y%m%d)"
```

#### Restore from Snapshot

```bash
curl -X POST "localhost:9200/_snapshot/backups/snapshot_20260101/_restore"
```

### Disaster Recovery

1. Deploy fresh infrastructure (Docker Compose or Kubernetes)
2. Restore PostgreSQL from latest backup
3. Restore Elasticsearch from latest snapshot
4. Restart all services: `make run`
5. Verify data integrity: `curl http://localhost:8000/api/v1/audit/verify`
6. Re-seed keyword rules if needed: `make seed`
