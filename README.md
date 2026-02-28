# VoxSentinel

A low-latency, pluggable platform that ingests live audio/video streams, transcribes speech in real time, monitors for configurable keywords/intents/sentiment, and dispatches multi-channel alerts within 300 ms end-to-end.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          EXTERNAL SOURCES                                │
│  RTSP Cameras │ HLS/DASH Streams │ Audio Files │ WebRTC / SIP           │
└──────────┬──────────────┬───────────────┬───────────────────────────────┘
           │              │               │
           ▼              ▼               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    INGESTION SERVICE  :8000                               │
│  FFmpeg + PyAV │ Audio Extraction │ 16 kHz Mono PCM │ Chunk Producer     │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │ Audio Chunks (240–320 ms)
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    VAD SERVICE  :8001                                     │
│  Silero VAD │ Speech / Non-Speech Classification │ Drop Silent Chunks    │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │ Speech Chunks Only
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                ASR ENGINE ABSTRACTION  :8002                              │
│  Deepgram Nova-2 (WebSocket) │ Whisper V3 Turbo (self-hosted)            │
│  → Unified TranscriptToken stream                                        │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │ TranscriptTokens
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│              NLP & KEYWORD ENGINE  :8003                                  │
│  Aho-Corasick + RapidFuzz + Regex │ DistilBERT Sentiment │ PII Redaction │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
┌──────────────────┐ ┌──────────────┐ ┌────────────────────────────────┐
│ DIARIZATION      │ │ ALERTS       │ │ STORAGE SERVICE  :8006         │
│ SERVICE  :8004   │ │ SERVICE :8005│ │ PostgreSQL + TimescaleDB       │
│ pyannote.audio   │ │ WebSocket,   │ │ Elasticsearch (full-text)      │
│ Speaker merge    │ │ Webhook,     │ │ Redis (cache / queues)         │
│                  │ │ Slack, Celery│ │                                │
└──────────────────┘ └──────────────┘ └────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│               API GATEWAY  :8007  │  DASHBOARD  :3000                    │
│  FastAPI REST + WebSocket          │  React 19 + Vite + Tailwind + shadcn│
│  /docs (Swagger UI)               │  Live transcript, alerts, search     │
└─────────────────────────────────────────────────────────────────────────┘
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Language** | Python 3.12, TypeScript 5 |
| **Frameworks** | FastAPI, React 19, Vite |
| **ASR Engines** | Deepgram Nova-2, Whisper V3 Turbo (faster-whisper) |
| **NLP** | Aho-Corasick, RapidFuzz, DistilBERT, Presidio + spaCy |
| **Diarization** | pyannote.audio 3.x |
| **Databases** | PostgreSQL 16 + TimescaleDB, Elasticsearch 8.13 |
| **Cache / Queues** | Redis 7, Celery |
| **Observability** | Prometheus metrics, structlog (JSON) |
| **Containerisation** | Docker Compose (dev + prod profiles) |
| **UI** | Tailwind CSS, shadcn/ui, Framer Motion |
| **Linting / Types** | ruff, mypy (strict) |
| **Testing** | pytest, pytest-asyncio, testcontainers |

## Quick Start

### Prerequisites

- **Docker** ≥ 24 and **Docker Compose** v2
- A Deepgram API key (or use Whisper V3 Turbo for fully self-hosted ASR)

### 1. Clone & configure

```bash
git clone <repo-url> && cd VoxSentinel
cp .env.example .env
# Edit .env — set DEEPGRAM_API_KEY and any other secrets
```

### 2. Start all services

```bash
docker compose up --build        # dev profile (default)
```

For production (with replicas and resource limits):

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build
```

### 3. Verify

| Endpoint | URL |
|----------|-----|
| Ingestion health | http://localhost:8000/health |
| VAD health | http://localhost:8011/health |
| ASR health | http://localhost:8002/health |
| NLP health | http://localhost:8003/health |
| Diarization health | http://localhost:8004/health |
| Alerts health | http://localhost:8005/health |
| Storage health | http://localhost:8006/health |
| API Gateway health | http://localhost:8007/health |
| Dashboard | http://localhost:3000 |
| Kibana | http://localhost:5601 |

Every service also exposes `/metrics` (Prometheus format).

## API Documentation

Interactive Swagger UI is served by the API Gateway at:

```
http://localhost:8007/docs
```

ReDoc alternative: `http://localhost:8007/redoc`

## Running Tests

### Unit tests (no Docker required)

```bash
python -m pytest services/ packages/ -q
```

### Integration tests (requires Docker)

```bash
python -m pytest tests/integration/ -q
```

Integration tests use **testcontainers** to spin up Redis, PostgreSQL, and Elasticsearch automatically.

## Linting & Type Checking

```bash
# Lint (auto-fix)
python -m ruff check . --fix

# Type check (strict, source only — tests excluded)
python -m mypy services/ packages/ --ignore-missing-imports --explicit-package-bases
```

## Project Structure

```
VoxSentinel/
├── docker-compose.yml          # Dev orchestration (13 services)
├── docker-compose.prod.yml     # Production overrides
├── .env.example                # Environment variable template
├── pyproject.toml              # Shared ruff, mypy, pytest config
├── packages/
│   └── tg-common/              # Shared models, Redis client, DB ORM
├── services/
│   ├── ingestion/              # Audio ingest (FFmpeg + PyAV)
│   ├── vad/                    # Voice Activity Detection (Silero)
│   ├── asr/                    # Speech-to-Text (Deepgram / Whisper)
│   ├── nlp/                    # Keywords, sentiment, PII redaction
│   ├── diarization/            # Speaker identification (pyannote)
│   ├── alerts/                 # Multi-channel alert dispatch
│   ├── storage/                # PostgreSQL + Elasticsearch persistence
│   ├── api/                    # REST + WebSocket gateway
│   └── dashboard/              # React 19 SPA
└── tests/
    └── integration/            # End-to-end pipeline tests
```

## License

See [PRD.md](PRD.md) and [Agent.md](Agent.md) for full architecture and product requirements.