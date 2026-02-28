# VoxSentinel — Live Demo Guide

## Prerequisites

| Requirement | Notes |
|---|---|
| Docker Desktop | Running with ≥ 8 GB RAM allocated |
| `.env` file | All keys filled (see below) |
| Ports free | 3000, 5436, 5601, 6382, 8000–8007, 8011, 9200 |

### Required `.env` keys

```
TG_API_KEY=<your-random-secret>
TG_DEEPGRAM_API_KEY=<deepgram.com signup → free key>
TG_HF_TOKEN=<huggingface.co → Settings → Access Tokens>
TG_SLACK_WEBHOOK_URL=<Slack incoming webhook URL>
TG_SLACK_BOT_TOKEN=<Slack bot token, xoxb-...>
```

> **Diarization note:** You must visit <https://huggingface.co/pyannote/speaker-diarization-3.1>
> and click **"Agree and access repository"** while logged in with the same HF account.
> Without this, diarization runs in **degraded mode** (everything else works fine).

---

## Step 1 — Start All Containers

```bash
cd VoxSentinel
docker compose up --build -d
```

Wait ~60 seconds for all 14 containers to become healthy:

```bash
docker compose ps
```

All containers should show `Up ... (healthy)`. If any show `unhealthy`, check logs:

```bash
docker logs <container-name> --tail 30
```

---

## Step 2 — Verify Health

```bash
curl http://localhost:8000/health
```

**Expected output:**
```json
{"status": "healthy", "services": {"database": "healthy", "redis": "healthy", "elasticsearch": "healthy"}}
```

If any service shows `unhealthy`, check the corresponding container logs.

---

## Step 3 — Initialize Database (First Run Only)

If this is a fresh start, run the DB init script to create tables and seed keyword rules:

```bash
docker exec voxsentinel-api-1 python -c "
import asyncio, sys, os
sys.path.insert(0, '/app/src')
os.environ.setdefault('TG_DB_URI', os.environ.get('DATABASE_URL', ''))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from tg_common.db.orm_models import Base, KeywordRuleORM
import uuid
from datetime import datetime, timezone

db_url = os.environ.get('TG_DB_URI', os.environ.get('DATABASE_URL', '')).replace('+asyncpg', '')
engine = create_engine(db_url)
Base.metadata.create_all(engine)

seeds = [
    ('gun', 'exact', 'critical', 'security'),
    ('fire', 'exact', 'critical', 'security'),
    ('help', 'exact', 'high', 'security'),
    ('weapon', 'fuzzy', 'critical', 'security'),
    ('threat', 'fuzzy', 'high', 'security'),
    ('complaint', 'exact', 'medium', 'compliance'),
    ('refund', 'exact', 'low', 'compliance'),
]

with Session(engine) as s:
    existing = s.query(KeywordRuleORM).count()
    if existing == 0:
        for kw, mt, sev, cat in seeds:
            s.add(KeywordRuleORM(
                rule_id=uuid.uuid4(), rule_set_name='default', keyword=kw,
                match_type=mt, fuzzy_threshold=0.8, severity=sev, category=cat,
            ))
        s.commit()
        print(f'Seeded {len(seeds)} keyword rules')
    else:
        print(f'DB already has {existing} rules, skipping seed')
"
```

---

## Step 4 — Open the UI

| URL | What |
|---|---|
| <http://localhost:3000> | Dashboard (landing + operational UI) |
| <http://localhost:8000/docs> | Swagger API docs (interactive) |
| <http://localhost:5601> | Kibana (Elasticsearch UI) |

---

## Step 5 — Demo the API (All Endpoints)

Set the API key as a variable for convenience:

```bash
# PowerShell
$H = @{ "Authorization" = "Bearer <YOUR_TG_API_KEY>" }

# Bash / curl
AUTH="Authorization: Bearer <YOUR_TG_API_KEY>"
```

### 5.1 — List Keyword Rules (Pre-seeded)

```bash
curl -H "$AUTH" http://localhost:8000/api/v1/rules
```

Shows 7 pre-seeded rules: gun, fire, help, weapon, threat, complaint, refund.

### 5.2 — Create a New Rule

```bash
curl -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"rule_set_name": "security_v2", "keyword": "bomb", "match_type": "exact", "severity": "critical", "category": "security"}' \
  http://localhost:8000/api/v1/rules
```

Returns `201` with `rule_id` and `created_at`. Changes hot-reload to NLP within 5 seconds.

### 5.3 — Update a Rule

```bash
curl -X PATCH -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"severity": "high", "match_type": "fuzzy", "fuzzy_threshold": 0.75}' \
  http://localhost:8000/api/v1/rules/<rule_id>
```

### 5.4 — Delete a Rule

```bash
curl -X DELETE -H "$AUTH" http://localhost:8000/api/v1/rules/<rule_id>
```

Returns `204 No Content`.

### 5.5 — Create a Stream

```bash
curl -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d '{
    "name": "Lobby Camera 1",
    "source_type": "rtsp",
    "source_url": "rtsp://192.168.1.100:554/stream1",
    "asr_backend": "deepgram_nova2",
    "vad_threshold": 0.5,
    "chunk_size_ms": 280
  }' \
  http://localhost:8000/api/v1/streams
```

Returns `201` with `stream_id`, `session_id`, and `status: "active"`.

### 5.6 — List Streams

```bash
curl -H "$AUTH" http://localhost:8000/api/v1/streams
```

### 5.7 — Get Stream Details

```bash
curl -H "$AUTH" http://localhost:8000/api/v1/streams/<stream_id>
```

### 5.8 — Pause / Resume a Stream

```bash
curl -X POST -H "$AUTH" http://localhost:8000/api/v1/streams/<stream_id>/pause
curl -X POST -H "$AUTH" http://localhost:8000/api/v1/streams/<stream_id>/resume
```

### 5.9 — Update Stream Config

```bash
curl -X PATCH -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"name": "Lobby Camera 1 - Updated", "vad_threshold": 0.6}' \
  http://localhost:8000/api/v1/streams/<stream_id>
```

### 5.10 — Delete a Stream

```bash
curl -X DELETE -H "$AUTH" http://localhost:8000/api/v1/streams/<stream_id>
```

### 5.11 — Create an Alert Channel (Slack)

```bash
curl -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d '{
    "channel_type": "slack",
    "config": {"webhook_url": "https://hooks.slack.com/services/T.../B.../xxx"},
    "min_severity": "high",
    "alert_types": ["keyword", "compliance"],
    "enabled": true
  }' \
  http://localhost:8000/api/v1/alert-channels
```

### 5.12 — List Alert Channels

```bash
curl -H "$AUTH" http://localhost:8000/api/v1/alert-channels
```

### 5.13 — Update / Delete Alert Channel

```bash
curl -X PATCH -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"min_severity": "critical"}' \
  http://localhost:8000/api/v1/alert-channels/<channel_id>

curl -X DELETE -H "$AUTH" http://localhost:8000/api/v1/alert-channels/<channel_id>
```

### 5.14 — List Alerts

```bash
curl -H "$AUTH" http://localhost:8000/api/v1/alerts
curl -H "$AUTH" "http://localhost:8000/api/v1/alerts?severity=critical&limit=10"
```

Returns alerts (empty if no audio has been processed yet).

### 5.15 — Get Transcript for a Session

```bash
curl -H "$AUTH" http://localhost:8000/api/v1/sessions/<session_id>/transcript
```

### 5.16 — Search Transcripts

```bash
curl -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"query": "suspicious activity", "search_type": "fuzzy", "limit": 20}' \
  http://localhost:8000/api/v1/search
```

Returns empty results unless transcripts have been indexed to Elasticsearch.

### 5.17 — Verify Audit Trail

```bash
curl -H "$AUTH" http://localhost:8000/api/v1/audit/verify/<segment_id>
```

Returns Merkle proof and verification status for a transcript segment.

### 5.18 — WebSocket Live Transcript (via wscat or browser)

```bash
# Install wscat: npm i -g wscat
wscat -c ws://localhost:8000/ws/streams/<stream_id>/transcript
wscat -c ws://localhost:8000/ws/alerts
```

---

## Step 6 — Dashboard Walkthrough

1. Open <http://localhost:3000>
2. **Landing page** — see the animated preloader, hero section, pipeline diagram, feature grid
3. Navigate to `/dashboard` — see operational UI with:
   - Active streams list with status indicators
   - Alert panel (real-time via WebSocket)
   - Transcript viewer with keyword highlights
   - Search tab for historical queries

The dashboard proxies all `/api/*` and `/ws/*` requests through nginx to the API gateway.

---

## Step 7 — Microservice Health Checks

Every service exposes its own `/health` endpoint:

```bash
curl http://localhost:8000/health     # API Gateway
curl http://localhost:8011/health     # Ingestion
curl http://localhost:8002/health     # VAD
curl http://localhost:8003/health     # ASR
curl http://localhost:8004/health     # NLP
curl http://localhost:8005/health     # Diarization
curl http://localhost:8006/health     # Alerts
curl http://localhost:8007/health     # Storage
```

---

## Step 8 — Prometheus Metrics

```bash
curl http://localhost:8000/metrics
```

Shows counters and histograms: `api_requests_total`, `api_request_duration_seconds`, etc.

---

## Architecture Summary (14 Containers)

| Container | Port | Purpose |
|---|---|---|
| `api` | 8000 | FastAPI REST + WebSocket gateway |
| `ingestion` | 8011 | RTSP/HLS audio ingestion |
| `vad` | 8002 | Voice Activity Detection (Silero) |
| `asr` | 8003 | ASR engine (Deepgram / Whisper) |
| `nlp` | 8004 | Keywords, sentiment, PII |
| `diarization` | 8005 | Speaker diarization (pyannote) |
| `alerts` | 8006 | Alert dispatch (WS/Webhook/Slack) |
| `storage` | 8007 | DB + ES write service |
| `celery-worker` | — | Background tasks + retries |
| `dashboard` | 3000 | React SPA + nginx reverse proxy |
| `postgres` | 5436 | PostgreSQL + TimescaleDB |
| `redis` | 6382 | Pub/sub + cache + Celery broker |
| `elasticsearch` | 9200 | Full-text transcript search |
| `kibana` | 5601 | ES visualization UI |

---

## Known Limitations (V1 Demo)

| Item | Details |
|---|---|
| **No live audio source** | Without a real RTSP/HLS feed, the pipeline doesn't produce transcripts. All transcript/alert/search queries return empty. The API CRUD is fully functional. |
| **Diarization degraded** | If the HF gated model license hasn't been accepted, diarization runs in degraded mode. This doesn't affect other services. |
| **Search empty** | No transcripts = no Elasticsearch data. Search will return `[]` but with 200 status. |
| **Dashboard data** | Dashboard shows empty stream/alert lists until real audio flows through the pipeline. |

---

## Stopping Everything

```bash
docker compose down        # Stop and remove containers
docker compose down -v     # Also remove volumes (DB data, ES data)
```
