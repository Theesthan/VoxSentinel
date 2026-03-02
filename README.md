# VoxSentinel

A low-latency, pluggable platform that ingests live audio/video streams and uploaded audio files, transcribes speech in real time, monitors for configurable keywords/intents/sentiment (including **legislative tracking**), and dispatches multi-channel alerts within 300 ms end-to-end.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          EXTERNAL SOURCES                                │
│  RTSP Cameras │ HLS/DASH │ Audio Files │ Microphone │ WebRTC / SIP      │
└──────────┬──────────────┬───────────────┬───────────────────────────────┘
           │              │               │
     ┌─────┘     ┌───────┘               │
     ▼           ▼                        ▼
┌────────────────────────┐  ┌──────────────────────────────────────────┐
│ STREAMING PIPELINE     │  │ FILE ANALYZE PIPELINE                     │
│                        │  │                                           │
│ Ingestion :8007        │  │ API Gateway: POST /api/v1/file-analyze    │
│ → VAD :8002            │  │ → Deepgram Pre-Recorded REST API          │
│ → ASR :8003            │  │   (nova-2, diarize, utterances)           │
│ → NLP :8004            │  │ → Parse utterances → segments             │
│ → Alerts :8006         │  │ → Return transcript + alerts + summary    │
│ → Storage :8001        │  │                                           │
└────────────┬───────────┘  └──────────────────┬───────────────────────┘
             │                                  │
             ▼                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│               API GATEWAY  :8010  │  DASHBOARD  :5173                    │
│  FastAPI REST + WebSocket          │  React 19 + Vite + Tailwind + shadcn│
│  /docs (Swagger UI)               │  Live transcript, alerts, search     │
│  /api/v1/* endpoints               │  File analyze, settings             │
└─────────────────────────────────────────────────────────────────────────┘
```

### Two Pipeline Modes

1. **Streaming (Live):** Ingestion → VAD → ASR (Deepgram WebSocket) → NLP → Alerts → Storage
2. **File Analyze (Batch):** Upload audio → Deepgram pre-recorded REST API → Parse → Return results

The file analyze pipeline bypasses VAD/ASR/NLP services entirely and calls Deepgram's batch endpoint directly for reliability.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Language** | Python 3.11.9, TypeScript 5 |
| **Frameworks** | FastAPI, React 19, Vite 6 |
| **ASR Engines** | Deepgram Nova-2 (streaming + pre-recorded), Whisper V3 Turbo |
| **NLP** | Aho-Corasick, RapidFuzz, Regex, DistilBERT, Presidio + spaCy |
| **Databases** | PostgreSQL 18, Elasticsearch 9.3.1 |
| **Cache / Queues** | Redis 5.0.14.1, Celery |
| **Observability** | Prometheus metrics, structlog (JSON) |
| **Deployment** | Native local (Windows) or Docker Compose |
| **UI** | Tailwind CSS, shadcn/ui, Framer Motion |
| **Linting / Types** | ruff, mypy (strict) |
| **Testing** | pytest, pytest-asyncio, testcontainers |

---

## Quick Start (Native Local — Windows)

### Prerequisites

- **Python** 3.11+
- **Node.js** 20+
- **PostgreSQL** 17+ (installed or standalone)
- **Redis** 5.0+ ([tporadowski Windows build](https://github.com/tporadowski/redis/releases))
- **Elasticsearch** 9.x (downloaded + extracted)
- A **Deepgram API key** (set `TG_DEEPGRAM_API_KEY` in `.env`)

### 1. Clone & configure

```bash
git clone <repo-url> && cd VoxSentinel
cp .env.example .env
# Edit .env — set TG_DEEPGRAM_API_KEY and database credentials
```

### 2. Start infrastructure

```powershell
# Terminal 1: Elasticsearch
cd elasticsearch && bin\elasticsearch.bat

# Terminal 2: Redis
cd redis5 && redis-server.exe

# Terminal 3: PostgreSQL (if not running as a service)
pg_ctl start -D "C:\Program Files\PostgreSQL\18\data"
```

### 3. Set up Python environment

```powershell
python -m venv .venv
.venv\Scripts\activate

# Install all service packages in editable mode
pip install -e packages/tg-common
pip install -e services/ingestion
pip install -e services/vad
pip install -e services/asr
pip install -e services/nlp
pip install -e services/alerts
pip install -e services/storage
pip install -e services/api

# Create database tables
python scripts/create_tables.py
```

### 4. Start services

```powershell
# Each in its own terminal (activate venv first):
uvicorn api.main:app --host 0.0.0.0 --port 8010
uvicorn storage.main:app --host 0.0.0.0 --port 8001
uvicorn vad.main:app --host 0.0.0.0 --port 8002
uvicorn asr.main:app --host 0.0.0.0 --port 8003
uvicorn nlp.main:app --host 0.0.0.0 --port 8004
uvicorn alerts.main:app --host 0.0.0.0 --port 8006
uvicorn ingestion.main:app --host 0.0.0.0 --port 8007
```

### 5. Start dashboard

```powershell
cd services/dashboard
npm install
npm run dev    # → http://localhost:5173
```

### 6. Seed legislative keyword rules (optional)

```powershell
python scripts/seed_legislation_rules.py
```

### 7. Verify

| Service | URL |
|---------|-----|
| API Gateway health | http://localhost:8010/health |
| Storage health | http://localhost:8001/health |
| VAD health | http://localhost:8002/health |
| ASR health | http://localhost:8003/health |
| NLP health | http://localhost:8004/health |
| Alerts health | http://localhost:8006/health |
| Ingestion health | http://localhost:8007/health |
| Dashboard | http://localhost:5173 |
| API Docs (Swagger) | http://localhost:8010/docs |
| Elasticsearch | http://localhost:9200 |

---

## Quick Start (Docker Compose)

```bash
cp .env.example .env
docker compose up --build
```

Dashboard at `http://localhost:3000`, API docs at `http://localhost:8010/docs`.

---

## Key Features

- **Live Stream Monitoring** — Connect RTSP cameras, HLS/DASH streams, or microphone input
- **File Analyze** — Upload audio files for batch transcription via Deepgram pre-recorded API
- **Keyword Detection** — Exact match (Aho-Corasick), fuzzy match (RapidFuzz), regex patterns
- **Legislative Tracking** — Pre-configured rule sets for monitoring government audio streams for bills, votes, committees, enactment language
- **Speaker Diarization** — Identify and track speakers via pyannote.audio
- **Sentiment Analysis** — DistilBERT-based sentiment scoring per segment
- **PII Redaction** — Microsoft Presidio + spaCy for automatic PII removal
- **Multi-Channel Alerts** — WebSocket, Slack, webhooks, email, SMS
- **Full-Text Search** — Elasticsearch-powered transcript search with highlighting
- **Audit Trail** — SHA-256 hashed transcript segments with Merkle tree verification

## Running Tests

```bash
# Unit tests
python -m pytest services/ packages/ -q

# Integration tests (requires Docker)
python -m pytest tests/integration/ -q
```

## Linting & Type Checking

```bash
python -m ruff check . --fix
python -m mypy services/ packages/ --ignore-missing-imports --explicit-package-bases
```

## Project Structure

```
VoxSentinel/
├── .env.example                # Environment variable template
├── docker-compose.yml          # Docker orchestration
├── pyproject.toml              # Shared ruff, mypy, pytest config
├── scripts/
│   ├── create_tables.py        # DB table creation (bypasses Alembic async issues)
│   ├── seed_db.py              # Sample data seeding
│   └── seed_legislation_rules.py  # Legislative keyword rule sets
├── packages/
│   └── tg-common/              # Shared models, Redis client, DB ORM
├── services/
│   ├── api/                    # REST + WebSocket gateway (:8010)
│   ├── storage/                # PostgreSQL + Elasticsearch persistence (:8001)
│   ├── vad/                    # Voice Activity Detection — Silero (:8002)
│   ├── asr/                    # Speech-to-Text — Deepgram / Whisper (:8003)
│   ├── nlp/                    # Keywords, sentiment, PII redaction (:8004)
│   ├── alerts/                 # Multi-channel alert dispatch (:8006)
│   ├── ingestion/              # Audio ingest — FFmpeg + PyAV (:8007)
│   └── dashboard/              # React 19 SPA (:5173)
├── elasticsearch/              # ES 9.3.1 (local, extracted)
├── redis5/                     # Redis 5.0.14.1 (tporadowski, local)
└── tests/
    └── integration/            # End-to-end pipeline tests
```

## Documentation

- [Agent.md](Agent.md) — Full architecture guide, coding conventions, tech stack
- [PRD.md](PRD.md) — Product requirements, feature specs, data models, API contracts

## License

MIT