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
│  /docs (Swagger UI)               │  Live transcript, alerts             │
│  /api/v1/* endpoints               │  File analyze, YouTube live, settings│
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

| Software | Version | Notes |
|----------|---------|-------|
| **Python** | 3.11+ | [python.org](https://www.python.org/downloads/) |
| **Node.js** | 20+ | [nodejs.org](https://nodejs.org/) |
| **PostgreSQL** | 17+ | Running as a service or manually; create a database `voxsentinel` |
| **Redis** | 5.0+ | [tporadowski Windows build](https://github.com/tporadowski/redis/releases) — extract to `redis5/` |
| **Elasticsearch** | 9.x | [elastic.co](https://www.elastic.co/downloads/elasticsearch) — extract to `elasticsearch/` |
| **FFmpeg** | 7+ | `winget install ffmpeg` (needed for video uploads) |
| **Deepgram API key** | — | [console.deepgram.com](https://console.deepgram.com) — free tier works |

### 1. Clone & set up Python venv

```powershell
git clone <repo-url>
cd VoxSentinel
python -m venv .venv
.venv\Scripts\activate

# Install packages (editable mode)
pip install -e packages/tg-common
pip install -e services/api
```

### 2. Start infrastructure (3 terminals)

```powershell
# Terminal 1 — Elasticsearch
cd elasticsearch
bin\elasticsearch.bat
# Wait until you see "started" in the output

# Terminal 2 — Redis
cd redis5
redis-server.exe

# Terminal 3 — PostgreSQL (skip if already running as a Windows service)
pg_ctl start -D "C:\Program Files\PostgreSQL\18\data"
```

### 3. Create database & tables

```powershell
# Make sure PostgreSQL is running, then:
psql -U postgres -c "CREATE DATABASE voxsentinel;"
psql -U postgres -c "CREATE USER voxsentinel WITH PASSWORD 'changeme';"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE voxsentinel TO voxsentinel;"

# Create tables
.venv\Scripts\activate
python scripts/create_tables.py
```

### 4. Seed keyword rules (important for alert detection)

```powershell
python scripts/seed_legislation_rules.py
```

### 5. Start the API gateway

```powershell
# Set environment variables and start (one command)
set TG_API_KEY=<your-api-key>
set TG_DEEPGRAM_API_KEY=<your-deepgram-key>
.venv\Scripts\uvicorn.exe api.main:app --host 0.0.0.0 --port 8010 --app-dir services\api\src
```

The API key (`TG_API_KEY`) is used for authenticating dashboard requests.
The Deepgram key (`TG_DEEPGRAM_API_KEY`) is used for speech-to-text transcription.

### 6. Start the dashboard (separate terminal)

```powershell
cd services\dashboard
npm install
npm run dev
```

### 7. Verify everything works

| Check | URL | Expected |
|-------|-----|----------|
| API Health | http://localhost:8010/health | `{"status":"healthy","services":{...}}` |
| API Docs | http://localhost:8010/docs | Swagger UI |
| Dashboard | http://localhost:5173 | VoxSentinel UI |
| Elasticsearch | http://localhost:9200 | Cluster info JSON |

### 8. YouTube Live Transcription (cookies setup)

YouTube requires browser cookies to extract HLS stream URLs. VoxSentinel looks
for cookie files in this priority order:
1. `TG_COOKIES_FILE` environment variable (absolute path)
2. `cookies/vidcookie.txt` — YouTube-only cookies (**recommended**)
3. `cookies/cookies.txt` — general browser cookie export
4. `cookies.txt` in the VoxSentinel root (legacy location)

To export YouTube cookies:
1. Install the **"Get cookies.txt LOCALLY"** extension in your browser
2. Visit youtube.com while logged in and export cookies
3. Save the file as `cookies/vidcookie.txt` inside the VoxSentinel directory

> **Status (tested 2026-03-03):** Full pipeline verified — `resolve` returns
> `is_live: true` with HLS URL, `live-transcribe` starts the background task,
> FFmpeg captures audio chunks, Deepgram transcribes in real time.

### 9. Try it out

1. Open **http://localhost:5173** in your browser
2. Go to the **File Analyze** tab
3. Upload an audio/video file (.mp3, .m4a, .mp4, .wav, etc.)
4. Watch the progress bar — results appear when processing completes
5. Check the **Alerts** tab for keyword match alerts
6. Paste a YouTube URL to analyze a video from the web
7. For YouTube **live** streams, the system auto-detects liveness and starts real-time transcription

---

## Deployment (Cloudflare Tunnel + Vercel)

For public access without port forwarding:

### Backend — Cloudflare Tunnel (free)

```powershell
# Download cloudflared: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/
cloudflared tunnel --url http://localhost:8010
# Copy the generated public URL (e.g., https://xxxx.trycloudflare.com)
```

### Frontend — Vercel

1. Push your repo to GitHub
2. Import in [vercel.com](https://vercel.com) → set **Root Directory** to `services/dashboard`
3. Add environment variable: `VITE_API_BASE_URL` = your Cloudflare tunnel URL + `/api/v1`
4. Deploy

---

## Key Features

- **Live Stream Monitoring** — Connect RTSP cameras, HLS/DASH streams, or microphone input
- **YouTube Live Transcription** — Paste a YouTube live URL, auto-detect if stream is live, capture audio via HLS + FFmpeg, transcribe in real time via Deepgram
- **File Analyze** — Upload audio files for batch transcription via Deepgram pre-recorded API
- **Keyword Detection** — Exact match (Aho-Corasick), fuzzy match (RapidFuzz), regex patterns
- **Legislative Tracking** — Pre-configured rule sets for monitoring government audio streams for bills, votes, committees, enactment language
- **Speaker Diarization** — Identify and track speakers via pyannote.audio
- **Sentiment Analysis** — DistilBERT-based sentiment scoring per segment
- **PII Redaction** — Microsoft Presidio + spaCy for automatic PII removal
- **Multi-Channel Alerts** — WebSocket, Slack, webhooks (dispatched automatically on keyword match)
- **Full-Text Search** — *Removed in v1.1 — Elasticsearch indexing available via API for future use*
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