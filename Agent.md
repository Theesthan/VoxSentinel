# Architecture & Agent Guide (AGENTS.md)
## VoxSentinel — Real-Time Multi-Source Transcription, Analytics & Alerting Platform

**Version:** 1.1
**Date:** 2025-07-03
**For:** AI Coding Agents (Copilot, Cursor, Claude) and Human Developers

---

## 1. Project Architecture Overview

### High-Level Architecture (Textual Diagram)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          EXTERNAL SOURCES                                │
│  RTSP Cameras │ HLS/DASH Streams │ Audio Files │ (V2: WebRTC, SIP,     │
│                                                    Meeting Relays)       │
└──────────┬──────────────┬───────────────┬───────────────────────────────┘
           │              │               │
           ▼              ▼               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    INGESTION SERVICE                                     │
│  FFmpeg + PyAV │ Audio Extraction │ 16kHz Mono PCM │ Chunk Producer     │
│  (NVDEC HW accel when available)                                        │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │ Audio Chunks (240–320ms)
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    VAD SERVICE                                           │
│  Silero VAD │ Speech/Non-Speech Classification │ Drop Silent Chunks     │
│  (V2: Wake-Word Gating via RealtimeSTT/Picovoice)                       │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │ Speech Chunks Only
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                ASR ENGINE ABSTRACTION LAYER                              │
│  ┌──────────────┐  ┌────────────────┐  ┌──────────────────────┐        │
│  │ Deepgram     │  │ Whisper V3     │  │ (V2: Lightning ASR,  │        │
│  │ Nova-2       │  │ Turbo (self-   │  │  AssemblyAI, Parakeet│        │
│  │ (WebSocket)  │  │ hosted, WS)    │  │  TDT, Riva, Canary) │        │
│  └──────┬───────┘  └───────┬────────┘  └──────────┬───────────┘        │
│         └──────────────┬────┘───────────────────────┘                   │
│                        ▼                                                 │
│         Unified TranscriptToken Stream                                   │
│  {text, is_final, start_time, end_time, confidence, language,           │
│   word_timestamps[]}                                                     │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │ TranscriptTokens
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│              NLP & KEYWORD ENGINE SERVICE                                │
│  ┌─────────────────┐  ┌───────────────┐  ┌──────────────────────┐      │
│  │ Keyword Matching │  │ Sentiment/    │  │ PII Redaction        │      │
│  │ • Aho-Corasick  │  │ Intent Engine │  │ • Presidio + spaCy/  │      │
│  │ • RapidFuzz     │  │ • DistilBERT  │  │   GLiNER             │      │
│  │ • Regex         │  │               │  │                      │      │
│  └────────┬────────┘  └───────┬───────┘  └──────────┬───────────┘      │
│           └────────────┬──────┘──────────────────────┘                  │
│                        ▼                                                 │
│         Match Events, Sentiment Events, Redacted Text                   │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
┌──────────────────┐ ┌──────────────┐ ┌──────────���─────────────────────┐
│ DIARIZATION      │ │ ALERT        │ │ STORAGE SERVICE                │
│ SERVICE          │ │ DISPATCH     │ │                                │
│ pyannote.audio   │ │ SERVICE      │ │ • PostgreSQL + TimescaleDB     │
│ 3.x             │ │              │ │   (transcripts, alerts, audit) │
│ Speaker IDs →    │ │ • WebSocket  │ │ • ~~Elasticsearch/OpenSearch~~ │
│ merge with       │ │ • Webhooks   │ │   ~~(full-text search)~~       │
│ transcript       │ │ • Slack      │ │   (deferred to V2)             │
│                  │ │ • Celery +   │ │ • Redis (cache, state, queues) │
│                  │ │   Redis      │ │                                │
└──────────────────┘ └──────────────┘ └────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    OPERATOR DASHBOARD                                    │
│  React 19 + Vite + TypeScript + Tailwind CSS + shadcn/ui + Framer Motion│
│  • Awwwards-tier landing page with scroll-triggered text reveals        │
│  • Live transcript view with keyword highlighting & speaker colors      │
│  • Alert panel with severity indicators & real-time animation           │
│  • Sentiment gauges per stream/speaker                                  │
│  • ~~Historical transcript search~~ (deferred to V2)                    │
│  • Stream management UI with brutalist bento grid layout                │
│  Connected via WebSocket for real-time updates; nginx SPA proxy         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Layer Interactions
1. **Ingestion Service** pulls audio from external sources, normalizes it, and produces chunks.
2. **VAD Service** filters out non-speech chunks to reduce downstream load.
3. **ASR Abstraction Layer** routes speech chunks to the configured backend and emits unified `TranscriptToken` objects.
4. **NLP & Keyword Engine** consumes tokens, runs keyword matching + sentiment/intent + PII redaction in parallel pipelines.
5. **Diarization Service** runs concurrently with NLP, intersecting speaker segments with ASR timestamps.
6. **Alert Dispatch Service** receives match/sentiment/compliance events and routes them to configured channels.
7. **Storage Service** persists redacted transcripts, alerts, audit hashes to PostgreSQL. *(Elasticsearch indexing deferred to V2.)*
8. **Dashboard** connects via WebSocket to receive live tokens and alerts; queries REST API for historical data.

### Data Flow: Audio Capture → Alert Delivery
```
1. RTSP camera sends video+audio stream
2. Ingestion Service connects via FFmpeg, extracts audio, resamples to 16kHz mono
3. Audio split into 280ms chunks, each timestamped
4. VAD Service receives chunk → Silero classifies as speech (0.87 > 0.5 threshold) → passes through
5. ASR Layer receives speech chunk → sends to Deepgram Nova-2 via WebSocket
6. Deepgram returns partial token: {"text": "he has a", "is_final": false}
7. Deepgram returns final token: {"text": "he has a gun near the entrance", "is_final": true, ...}
8. NLP Engine receives final token:
   a. Aho-Corasick matches "gun" (exact, critical severity)
   b. Presidio detects no PII → text stored as-is
   c. DistilBERT classifies sentiment as "negative" (0.89)
9. Diarization assigns speaker: SPEAKER_01
10. Alert Dispatch creates alert event, sends to:
    a. WebSocket → dashboard shows red alert with highlighted "gun"
    b. Slack → #security-alerts channel receives formatted message
11. Storage Service writes TranscriptSegment + Alert to PostgreSQL
12. Audit Service computes SHA-256 hash of segment, stores in segment_hash column

Total elapsed time: ~250ms
```

### File Analyze Pipeline (Batch / Pre-Recorded)

For uploaded audio/video files, VoxSentinel bypasses the streaming pipeline (VAD → ASR WebSocket → NLP)
and instead uses **Deepgram's pre-recorded REST API** (`POST https://api.deepgram.com/v1/listen`):

```
1. User uploads audio/video file via POST /api/v1/file-analyze (multipart form)
   - Video files (.mp4, .mkv, .avi, .mov, .webm, .flv) have audio extracted via FFmpeg
2. API saves file to temp dir, creates Stream (source_type="file") + Session in DB
3. Background task sends raw audio bytes to Deepgram pre-recorded API with:
   - model=nova-2, diarize=true, utterances=true, smart_format=true, punctuate=true
4. Deepgram returns full JSON with utterances (speaker-labeled segments)
5. API parses utterances → FileAnalyzeSegment objects (speaker_id, timestamps, confidence)
6. Keyword rule sets are loaded from DB and matched against each segment
   - Supports exact (Aho-Corasick), fuzzy (RapidFuzz), and regex matching
   - Generates alerts for each match with severity and rule metadata
7. Results persisted:
   - TranscriptSegmentORM rows → PostgreSQL (for transcript retrieval)
   - AlertORM rows → PostgreSQL (for Alerts tab in dashboard)
   - ~~Transcript segments → Elasticsearch "transcripts" index~~ (deferred to V2)
   - In-process job dict (job_id → transcript, alerts, summary) for polling
8. Dashboard polls GET /api/v1/file-analyze/{job_id} until status="completed"
```

#### YouTube Video Analysis

YouTube URLs are also supported via `POST /api/v1/youtube/download-analyze`:
```
1. User submits YouTube URL, API resolves video title via yt-dlp
2. Audio track downloaded as WAV via yt-dlp + FFmpeg
3. Downloaded file enters the same file analyze pipeline (steps 3-8 above)
```

#### YouTube Live Transcription

YouTube **live** streams are supported via `POST /api/v1/youtube/live-transcribe`:
```
1. Frontend calls POST /api/v1/youtube/resolve — detects if stream is live
2. If live, POST /api/v1/youtube/live-transcribe creates stream + background task
3. Background task captures 10s audio chunks via FFmpeg from HLS URL
4. Each chunk sent to Deepgram pre-recorded API for transcription
5. Results published to Redis channel "redacted_tokens:{stream_id}"
6. Dashboard WebSocket receives tokens in real time
```

**Note:** YouTube requires browser cookies in Netscape format for HLS URL
extraction. VoxSentinel looks in this order:
1. `TG_COOKIES_FILE` env var (absolute path)
2. `cookies/vidcookie.txt` — YouTube cookies (export via "Get cookies.txt LOCALLY" browser extension)

Without cookies, liveness detection works via HTTP scraping but live audio capture
will fail (no HLS URL returned by yt-dlp).

**Test result (2026-03-03):** Full pipeline verified with `cookies/vidcookie.txt`:
- `POST /youtube/resolve` returns `is_live: true` with valid HLS manifest URL
- `POST /youtube/live-transcribe` starts background task (`stream_id` returned)
- FFmpeg captures ~320 KB WAV chunks every 10s from the HLS stream
- Transcription task stops cleanly via `POST /youtube/stop-live/{stream_id}`

#### Microphone Live Transcription

The `/ws/mic` WebSocket endpoint connects the browser microphone directly to
Deepgram's streaming API (`wss://api.deepgram.com/v1/listen`). The browser sends
raw PCM audio (16kHz, 16-bit, mono) and receives JSON transcript results back.

#### Search Feature (Removed)

The search tab and Elasticsearch transcript search have been removed from the
dashboard UI. The search router is no longer registered in the API gateway.
Elasticsearch remains available for future indexing use.

### Native Local Development Setup

VoxSentinel runs entirely natively on Windows without Docker:

| Component | Version | Location / Notes |
|-----------|---------|------------------|
| Python | 3.11.9 | venv at `.venv/` |
| PostgreSQL | 18 | `localhost:5432`, user `voxsentinel`, db `voxsentinel` |
| Redis | 5.0.14.1 | tporadowski build at `redis5/`, port 6379 |
| Elasticsearch | 9.3.1 | At `elasticsearch/`, single-node, security off, port 9200 |
| Node.js | 20.x | Dashboard via Vite dev server |
| FFmpeg | 7+ | Required for video file audio extraction and YouTube downloads |
| yt-dlp | latest | In venv, for YouTube audio download |

#### Service Ports (Native)

| Service | Port | Notes |
|---------|------|-------|
| API Gateway | 8010 | Main backend — handles REST, WebSocket, file analyze, YouTube |
| Dashboard | 5173 | Vite dev server, proxies `/api` → `http://localhost:8010` |
| YT Media Worker | 8787 | Standalone yt-dlp/FFmpeg service (runs on separate machine) |
| PostgreSQL | 5432 | Stores streams, sessions, transcripts, alerts, rules, channels |
| Redis | 6379 | Caching and rate limiting |
| Elasticsearch | 9200 | Full-text transcript search index |

#### Environment Variables

| Variable | Purpose |
|----------|---------|
| `TG_API_KEY` | API authentication key (used in `Authorization: Bearer <key>` header) |
| `TG_DEEPGRAM_API_KEY` | Deepgram API key for speech-to-text |
| `TG_DB_URI` | PostgreSQL connection (default: `postgresql+asyncpg://voxsentinel:changeme@localhost:5432/voxsentinel`) |
| `TG_REDIS_URL` | Redis URL (default: `redis://localhost:6379/0`) |
| `TG_ES_URL` | Elasticsearch URL (default: `http://localhost:9200`) |
| `GROQ_API_KEY` | Groq API key for AI-powered keyword suggestions (free at console.groq.com) |
| `YT_WORKER_URL` | YouTube Media Worker base URL for delegating yt-dlp/FFmpeg ops (e.g. `http://home-ip:8787`) |
| `YT_WORKER_SECRET` | Shared secret for authenticating with the YT Media Worker |

#### Deployment

For public access, use **Cloudflare Tunnel** (free) to expose the API gateway, and **Vercel** for the static frontend dashboard.
The dashboard's `VITE_API_BASE_URL` env var points to the tunnel URL.

---

## 2. Directory Structure

```
voxsentinel/
├── README.md                          # Project overview, quick start guide
├── PRD.md                             # Product Requirements Document
├── AGENTS.md                          # This file: architecture & coding guide
├── LICENSE
├── .env.example                       # Template for environment variables
├── .gitignore
├── docker-compose.yml                 # Development environment orchestration
├── docker-compose.prod.yml            # Production-like local environment
├── Makefile                           # Common commands (build, test, lint, run)
│
├── helm/                              # Kubernetes Helm charts
│   └── transcriptguard/
│       ├── Chart.yaml
│       ├── values.yaml
│       ├── values.prod.yaml
│       └── templates/
│           ├── ingestion-deployment.yaml
│           ├── vad-deployment.yaml
│           ├── asr-deployment.yaml
│           ├── nlp-deployment.yaml
│           ├── diarization-deployment.yaml
│           ├── alert-deployment.yaml
│           ├── storage-deployment.yaml
│           ├── api-deployment.yaml
│           ├── dashboard-deployment.yaml
│           └── ...
│
├── proto/                             # Protobuf definitions (if using gRPC internally)
│   └── transcriptguard/
│       ├── common.proto
│       ├── asr.proto
│       └── alerts.proto
│
├── packages/                          # Shared Python packages
│   └── tg-common/                     # Shared models, config, utilities
│       ├── pyproject.toml
│       ├── src/
│       │   └── tg_common/
│       │       ├── __init__.py
│       │       ├── config.py          # Pydantic Settings for env-based config
│       │       ├── models/            # Shared data models (Pydantic)
│       │       │   ├── __init__.py
│       │       │   ├── stream.py
│       │       │   ├── session.py
│       │       │   ├── transcript.py
│       │       │   ├── alert.py
│       │       │   ├── keyword_rule.py
│       │       │   └── audit.py
│       │       ├── db/                # Database connection and ORM models
│       │       │   ├── __init__.py
│       │       │   ├── connection.py
│       │       │   ├── orm_models.py  # SQLAlchemy ORM models
│       │       │   └── migrations/    # Alembic migrations
│       │       │       ├── env.py
│       │       │       ├── alembic.ini
│       │       │       └── versions/
│       │       ├── messaging/         # Redis pub/sub, Celery task definitions
│       │       │   ├── __init__.py
│       │       │   ├── redis_client.py
│       │       │   └── celery_app.py
│       │       ├── logging.py         # Structured logging setup
│       │       ├── metrics.py         # Prometheus metrics helpers
│       │       └── utils.py           # Shared utility functions
│       └── tests/
│           ├── test_config.py
│           ├── test_models.py
│           └── ...
│
├── services/                          # Microservices (one directory per service)
│   │
│   ├── ingestion/                     # Audio ingestion service
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   ├── src/
│   │   │   └── ingestion/
│   │   │       ├── __init__.py
│   │   │       ├── main.py            # Service entry point
│   │   │       ├── stream_manager.py  # Manages RTSP/HLS/file connections
│   │   │       ├── audio_extractor.py # FFmpeg + PyAV audio extraction
│   │   │       ├── chunk_producer.py  # Produces 280ms audio chunks
│   │   │       ├── reconnection.py    # Exponential backoff reconnection
│   │   │       └── health.py          # Health check endpoint
│   │   └── tests/
│   │       ├── test_stream_manager.py
│   │       ├── test_audio_extractor.py
│   │       └── ...
│   │
│   ├── vad/                           # Voice Activity Detection service
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   ├── src/
│   │   │   └── vad/
│   │   │       ├── __init__.py
│   │   │       ├── main.py
│   │   │       ├── silero_vad.py      # Silero VAD wrapper
│   │   │       ├── vad_processor.py   # Chunk classification logic
│   │   │       └── health.py
│   │   └── tests/
│   │       └── ...
│   │
│   ├── asr/                           # ASR Engine Abstraction Layer
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   ├── src/
│   │   │   └── asr/
│   │   │       ├── __init__.py
│   │   │       ├── main.py
│   │   │       ├── engine_base.py     # Abstract ASREngine base class
│   │   │       ├── engine_registry.py # Registry for backend discovery
│   │   │       ├── engines/
│   │   │       │   ├── __init__.py
│   │   │       │   ├── deepgram_nova2.py
│   │   │       │   ├── whisper_v3_turbo.py
│   │   │       │   ├── lightning_asr.py      # V2
│   │   │       │   ├── assemblyai.py         # V2
│   │   │       │   ├── parakeet_tdt.py       # V2
│   │   │       │   ├── canary_qwen.py        # V2
│   │   │       │   └── riva.py               # V2
│   │   │       ├── router.py          # Routes streams to engines
│   │   │       ├── failover.py        # Circuit breaker + failover logic
│   │   │       └── health.py
│   │   └── tests/
│   │       ├── test_engine_base.py
│   │       ├── test_deepgram_nova2.py
│   │       ├── test_whisper_v3_turbo.py
│   │       ├── test_router.py
│   │       ├── test_failover.py
│   │       └── ...
│   │
│   ├── nlp/                           # NLP, Keyword, Sentiment, PII Service
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   ├── src/
│   │   │   └── nlp/
│   │   │       ├── __init__.py
│   │   │       ├── main.py
│   │   │       ├── keyword_engine.py        # Aho-Corasick + RapidFuzz + Regex
│   │   │       ├── aho_corasick_index.py    # Manages Aho-Corasick automaton
│   │   │       ├── fuzzy_matcher.py         # RapidFuzz wrapper
│   │   │       ├── regex_matcher.py         # Compiled regex management
│   │   │       ├── sliding_window.py        # Per-stream rolling text window
│   │   │       ├── sentiment_engine.py      # DistilBERT inference
│   │   │       ├── intent_engine.py         # Intent classification
│   │   │       ├── pii_redactor.py          # Presidio + spaCy/GLiNER
│   │   │       ├─�� deduplication.py         # Alert deduplication logic
│   │   │       ├── rule_loader.py           # Hot-reload keyword rules from DB/API
│   │   │       └── health.py
│   │   └── tests/
│   │       ├── test_keyword_engine.py
│   │       ├── test_aho_corasick_index.py
│   │       ├── test_fuzzy_matcher.py
│   │       ├── test_sentiment_engine.py
│   │       ├── test_pii_redactor.py
│   │       ├── test_deduplication.py
│   │       └── ...
│   │
│   ├── diarization/                   # Speaker Diarization Service
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   ├── src/
│   │   │   └── diarization/
│   │   │       ├── __init__.py
│   │   │       ├── main.py
│   │   │       ├── pyannote_pipeline.py     # pyannote.audio 3.x wrapper
│   │   │       ├── speaker_merger.py        # Merge diarization with ASR timestamps
│   │   │       ├── external_metadata.py     # Merge platform speaker metadata
│   │   │       └── health.py
│   │   └── tests/
│   │       └── ...
│   │
│   ├── alerts/                        # Alert Dispatch Service
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   ├── src/
│   │   │   └── alerts/
│   │   │       ├── __init__.py
│   │   │       ├── main.py
│   │   │       ├── dispatcher.py            # Central alert routing
│   │   │       ├── channels/
│   │   │       │   ├── __init__.py
│   │   │       │   ├── base.py              # Abstract AlertChannel
│   │   │       │   ├── websocket_channel.py
│   │   │       │   ├── webhook_channel.py
│   │   │       │   ├── slack_channel.py
│   │   │       │   ├── teams_channel.py     # V2
│   │   │       │   ├── email_channel.py     # V2
│   │   │       │   ├── sms_channel.py       # V2
│   │   │       │   └── signal_channel.py    # V2
│   │   │       ├── throttle.py              # Rate limiting & dedup
│   │   │       ├── retry.py                 # Celery retry tasks
│   │   │       └── health.py
│   │   └── tests/
│   │       ├── test_dispatcher.py
│   │       ├── test_websocket_channel.py
│   │       ├── test_webhook_channel.py
│   │       ├── test_slack_channel.py
│   │       ├── test_throttle.py
│   │       └── ...
│   │
│   ├── storage/                       # Storage & Indexing Service
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   ├── src/
│   │   │   └── storage/
│   │   │       ├── __init__.py
│   │   │       ├── main.py
│   │   │       ├── transcript_writer.py     # PostgreSQL/TimescaleDB writes
│   │   │       ├── alert_writer.py
│   │   │       ├── es_indexer.py            # Elasticsearch indexing
│   │   │       ├── audit_hasher.py          # SHA-256 hashing + Merkle anchoring
│   │   │       └── health.py
│   │   └── tests/
│   │       └── ...
│   │
│   ├── api/                           # REST API Gateway (FastAPI)
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   ├── src/
│   │   │   └── api/
│   │   │       ├── __init__.py
│   │   │       ├── main.py                  # FastAPI app entry
│   │   │       ├── dependencies.py          # Auth, DB sessions, etc.
│   │   │       ├── routers/
│   │   │       │   ├── __init__.py
│   │   │       │   ├── streams.py
│   │   │       │   ├── rules.py
│   │   │       │   ├── alert_channels.py
│   │   │       │   ├── transcripts.py
│   │   │       │   ├── search.py
│   │   │       │   ├── alerts.py
│   │   │       │   ├── audit.py
│   │   │       │   ├── health.py
│   │   │       │   └── ws.py               # WebSocket endpoints
│   │   │       ├── schemas/                 # Pydantic request/response schemas
│   │   │       │   ├── __init__.py
│   │   │       │   ├── stream_schemas.py
│   │   │       │   ├── rule_schemas.py
│   │   │       │   ├── alert_schemas.py
│   │   │       │   ├── transcript_schemas.py
│   │   │       │   └── search_schemas.py
│   │   │       └── middleware/
│   │   │           ├── auth.py
│   │   │           ├── cors.py
│   │   │           ├── rate_limit.py
│   │   │           └── logging.py
│   │   └── tests/
│   │       ├── test_streams_router.py
│   │       ├── test_rules_router.py
│   │       ├── test_search_router.py
│   │       └── ...
│   │
│   └── dashboard/                     # Operator Dashboard (React SPA)
│       ├── Dockerfile                 # Multi-stage: node build → nginx serve
│       ├── package.json               # React 19, Vite 6, Framer Motion 11
│       ├── tsconfig.json
│       ├── tsconfig.app.json
│       ├── tsconfig.node.json
│       ├── vite.config.ts
│       ├── tailwind.config.ts
│       ├── postcss.config.js
│       ├── components.json            # shadcn/ui configuration
│       ├── nginx.conf                 # SPA routing + API/WS reverse proxy
│       ├── index.html
│       ├── public/
│       │   └── vite.svg
│       └── src/
│           ├── main.tsx               # React entry point
│           ├── App.tsx                # BrowserRouter + Routes
│           ├── index.css              # Tailwind base + dark theme
│           ├── vite-env.d.ts
│           ├── lib/
│           │   └── utils.ts           # cn() utility (clsx + tailwind-merge)
│           ├── hooks/
│           │   └── useScrollReveal.ts  # Scroll-linked animation hooks
│           ├── components/
│           │   ├── ui/                # shadcn/ui primitives (brutalist-themed)
│           │   │   ├── button.tsx
│           │   │   ├── card.tsx
│           │   │   └── badge.tsx
│           │   ├── landing/           # Landing page sections
│           │   │   ├── Preloader.tsx   # "Initializing... Access Granted."
│           │   │   ├── Hero.tsx        # Masked text reveal hero
│           │   │   ├── IntroReveal.tsx # Word-by-word scroll opacity reveal
│           │   │   ├── StatsBanner.tsx # 4 stats with staggered entrance
│           │   │   ├── StickyPipeline.tsx # Sticky left + scrolling right
│           │   │   ├── FeaturesGrid.tsx   # Bento grid feature cards
│           │   │   └── Footer.tsx
│           │   └── dashboard/         # Dashboard operational UI
│           │       ├── DashboardShell.tsx  # Sidebar + main layout
│           │       ├── Sidebar.tsx
│           │       ├── StreamCard.tsx
│           │       ├── AlertPanel.tsx
│           │       └── TranscriptViewer.tsx # Live transcript with highlights
│           └── pages/
│               ├── Landing.tsx        # / route — marketing landing
│               └── Dashboard.tsx      # /dashboard/* — operational UI
│
├── scripts/                           # Utility and deployment scripts
│   ├── seed_db.py                     # Seed database with test data
│   ├── benchmark_asr.py              # ASR latency/WER benchmarking tool
│   ├── load_test.py                   # Multi-stream load testing
│   └── generate_test_audio.py        # Generate test audio with known keywords
│
├── tests/                             # Integration and E2E tests
│   ├── conftest.py                    # Shared fixtures
│   ├── integration/
│   │   ├── test_ingestion_to_asr.py
│   │   ├── test_asr_to_nlp.py
│   │   ├── test_nlp_to_alerts.py
│   │   ├── test_full_pipeline.py
│   │   └── test_storage_search.py
│   └── e2e/
│       ├── test_rtsp_to_dashboard.py
│       ├── test_keyword_alert_slack.py
│       └── test_pii_redaction_audit.py
│
└── docs/                              # Additional documentation
    ├── deployment.md                  # Deployment guide
    ├── api-reference.md              # Detailed API docs
    ├── asr-backend-guide.md          # How to add a new ASR backend
    ├── keyword-rule-guide.md         # Keyword rule configuration guide
    └── runbooks/                     # Operational runbooks
        ├── scaling.md
        ├── incident-response.md
        └── backup-restore.md
```

---

## 3. Tech Stack & Libraries

### Core Language
| Component | Language | Version | Rationale |
|-----------|----------|---------|-----------|
| All backend services | Python | 3.12+ | Primary language for ML/NLP ecosystem; async support via asyncio; team expertise |
| API Gateway | Python (FastAPI) | 3.12+ | Same language as services; FastAPI provides high-performance async HTTP + WebSocket |
| Dashboard | TypeScript (React + Vite) | 19 / 6 | Production SPA; Framer Motion animations; shadcn/ui components; nginx reverse proxy |

### Ingestion & Media

| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| `ffmpeg` (system) | 6.x+ | Audio/video stream handling, transcoding, NVDEC/NVENC | Installed as system dependency in Docker |
| `PyAV` | 12.x+ | Pythonic FFmpeg bindings for audio extraction | Preferred over subprocess calls for reliability |
| `numpy` | 1.26+ | Audio buffer manipulation (PCM arrays) | |

### VAD

| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| `silero-vad` | 5.x+ | Voice activity detection | Via `torch.hub` or pip; runs on CPU or GPU |
| `torch` | 2.3+ | PyTorch runtime for Silero and ML models | CPU build for VAD-only services; GPU build for ASR/NLP |

### ASR Backends

| Library / SDK | Version | Purpose | Notes |
|---------------|---------|---------|-------|
| `deepgram-sdk` | 3.x+ | Deepgram Nova-2 streaming API client | WebSocket-based streaming |
| `faster-whisper` | 1.1+ | Self-hosted Whisper V3 Turbo inference | CTranslate2-based, ~5.4× faster than original |
| `websockets` | 12.x+ | WebSocket communication for ASR streaming | Used by both client and server sides |
| `grpcio` + `grpcio-tools` | 1.60+ | gRPC for NVIDIA Riva and internal communication (V2) | |

### NLP & Keyword Engine

| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| `pyahocorasick` | 2.1+ | Aho-Corasick automaton for exact multi-pattern matching | O(n) scanning regardless of pattern count |
| `rapidfuzz` | 3.8+ | Fuzzy string matching | `token_set_ratio`, `partial_ratio` |
| `transformers` | 4.40+ | Hugging Face Transformers for DistilBERT sentiment/intent | |
| `presidio-analyzer` | 2.2+ | Microsoft Presidio PII detection | |
| `presidio-anonymizer` | 2.2+ | Microsoft Presidio PII anonymization | |
| `spacy` | 3.7+ | NER backbone for Presidio | |
| `gliner` | 0.2+ | Zero-shot NER for custom entity types | Supplements spaCy for domain-specific entities |

### Diarization

| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| `pyannote.audio` | 3.3+ | Speaker diarization pipeline | Requires Hugging Face token for model access |
| `speechbrain` | 1.0+ | Speaker embedding models (used by pyannote) | |

### API & Web Framework

| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| `fastapi` | 0.111+ | REST API and WebSocket server | Async, auto-docs, Pydantic integration |
| `uvicorn` | 0.30+ | ASGI server for FastAPI | Production deployment with multiple workers |
| `pydantic` | 2.7+ | Data validation and serialization | Used everywhere for schemas and config |
| `pydantic-settings` | 2.3+ | Environment-based configuration | Reads from `.env` files and env vars |

### Database & Search

| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| `sqlalchemy` | 2.0+ | ORM and database abstraction | Async support via `asyncpg` |
| `asyncpg` | 0.29+ | Async PostgreSQL driver | |
| `alembic` | 1.13+ | Database migrations | |
| `elasticsearch[async]` | 8.13+ | Elasticsearch client | Async variant for non-blocking indexing |

### Task Queue & Messaging

| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| `celery` | 5.4+ | Distributed task queue for alert retries and background jobs | |
| `redis` | 5.0+ | Redis client for caching, pub/sub, and Celery broker | |

### Alert Integrations

| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| `httpx` | 0.27+ | Async HTTP client for webhooks and API calls | Preferred over `requests` for async |
| `slack-sdk` | 3.30+ | Slack API and webhook integration | |

### Testing

| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| `pytest` | 8.2+ | Test runner | |
| `pytest-asyncio` | 0.23+ | Async test support | |
| `pytest-cov` | 5.0+ | Coverage reporting | |
| `pytest-mock` | 3.14+ | Mocking utilities | |
| `httpx` | 0.27+ | Test client for FastAPI (via `ASGITransport`) | |
| `factory-boy` | 3.3+ | Test data factories | |
| `testcontainers` | 4.4+ | Disposable Docker containers for integration tests | PostgreSQL, Redis, Elasticsearch |

### Code Quality

| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| `ruff` | 0.4+ | Linting and formatting (replaces flake8 + black + isort) | |
| `mypy` | 1.10+ | Static type checking | |
| `pre-commit` | 3.7+ | Git hooks for code quality | |

### Observability

| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| `prometheus-client` | 0.20+ | Prometheus metrics export | |
| `structlog` | 24.2+ | Structured JSON logging | |
| `opentelemetry-api` + `opentelemetry-sdk` | 1.24+ | Distributed tracing (V2) | |

### Dashboard Frontend

| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| `react` | 19.x | UI component framework | |
| `react-dom` | 19.x | DOM rendering | |
| `react-router-dom` | 7.x | Client-side routing (/ landing, /dashboard/* operational UI) | |
| `vite` | 6.x | Build tool and dev server | HMR, proxy to API/WS |
| `typescript` | 5.7+ | Type safety | Strict mode enabled |
| `tailwindcss` | 3.4+ | Utility-first CSS framework | Dark mode (#000), monochrome palette |
| `framer-motion` | 11.x | Animation library | useScroll, useTransform, masked reveals, staggered fade-ins |
| `@radix-ui/react-slot` | 1.x | Composition primitive for shadcn/ui Button | |
| `class-variance-authority` | 0.7+ | Component variant management | Used by shadcn/ui primitives |
| `clsx` + `tailwind-merge` | 2.x / 2.x | Conditional class merging | cn() utility |
| `lucide-react` | 0.468+ | Icon library | Thin-stroke icons matching brutalist aesthetic |

### Explicitly Discouraged / Forbidden Libraries
| Library | Reason |
|---------|--------|
| `requests` (in async code) | Use `httpx` instead; `requests` blocks the event loop |
| `flask` | Use FastAPI for all HTTP/WS services |
| `pymongo` | Not using MongoDB; use PostgreSQL + TimescaleDB |
| `pandas` (in hot path) | Too heavy for real-time processing; use numpy for audio buffers |
| `subprocess` for FFmpeg | Use PyAV bindings instead for reliability and error handling |
| Any ORM other than SQLAlchemy | Standardize on SQLAlchemy 2.0 async |

---

## 4. Coding Style & Conventions

### Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Files/modules | `snake_case.py` | `audio_extractor.py`, `keyword_engine.py` |
| Classes | `PascalCase` | `ASREngine`, `KeywordMatchEvent`, `TranscriptSegment` |
| Functions/methods | `snake_case` | `process_audio_chunk()`, `detect_keywords()` |
| Constants | `UPPER_SNAKE_CASE` | `DEFAULT_VAD_THRESHOLD`, `MAX_CHUNK_SIZE_MS` |
| Private members | `_leading_underscore` | `_build_automaton()`, `self._connection` |
| Environment variables | `UPPER_SNAKE_CASE` with `TG_` prefix | `TG_DEEPGRAM_API_KEY`, `TG_DB_URI` |
| Pydantic models | `PascalCase` with descriptive suffix | `StreamCreateRequest`, `AlertResponse` |
| Test files | `test_<module_name>.py` | `test_keyword_engine.py` |
| Test functions | `test_<behavior_description>` | `test_exact_match_returns_correct_keyword()` |

### Preferred Patterns

1. **Async/await everywhere** in services. All I/O operations (database, HTTP, WebSocket, Redis) must use async variants. Never call synchronous blocking I/O in an async context.

2. **Dependency injection via FastAPI's `Depends()`** for API endpoints. For services, use constructor injection.

3. **Abstract base classes** for pluggable components:
   ```python
   from abc import ABC, abstractmethod

   class ASREngine(ABC):
       @abstractmethod
       async def stream_audio(self, chunk: bytes) -> AsyncIterator[TranscriptToken]:
           ...
   ```

4. **Pydantic models for all data boundaries**: API request/response schemas, inter-service messages, configuration objects. Never pass raw dicts across service boundaries.

5. **Functional composition for data processing pipelines**: prefer small, composable functions over large class hierarchies. Classes are appropriate for stateful components (ASR connections, sliding windows), but pure functions are preferred for transformations.

6. **Context managers** for resource lifecycle:
   ```python
   async with asr_engine.connect(stream_config) as connection:
       async for token in connection.stream_audio(chunk):
           yield token
   ```

7. **Dataclass or Pydantic model over tuple/dict** for all structured data.

### Documentation Standards

1. **Module-level docstring** at the top of every file explaining its purpose:
   ```python
   """
   Keyword detection engine using Aho-Corasick, RapidFuzz, and regex matching.

   This module maintains a per-stream sliding window of transcript text and
   runs all configured matching rules against each window update.
   """
   ```

2. **Google-style docstrings** for all public functions and classes:
   ```python
   async def detect_keywords(
       text: str,
       stream_id: str,
       rules: list[KeywordRule],
   ) -> list[KeywordMatchEvent]:
       """Detect keyword matches in the given text using all configured rules.

       Args:
           text: The transcript text to scan.
           stream_id: The stream this text belongs to.
           rules: List of active keyword rules to match against.

       Returns:
           List of KeywordMatchEvent objects for all matches found.

       Raises:
           InvalidRuleError: If a rule has an invalid regex pattern.
       """
   ```

3. **Inline comments** only for non-obvious logic. Do not comment obvious code. When commenting, explain *why*, not *what*.

4. **Type hints on all function signatures**. Use `from __future__ import annotations` for forward references. Use modern syntax: `list[str]` not `List[str]`, `str | None` not `Optional[str]`.

### Error Handling Strategy

1. **Define service-specific exception hierarchies** inheriting from a base `VoxSentinelError`:
   ```python
   class VoxSentinelError(Exception):
       """Base exception for all VoxSentinel errors."""

   class ASRConnectionError(VoxSentinelError):
       """Failed to connect to ASR backend."""

   class ASRTimeoutError(VoxSentinelError):
       """ASR backend did not respond within timeout."""

   class InvalidRuleError(VoxSentinelError):
       """Keyword rule configuration is invalid."""
   ```

2. **Never catch bare `Exception`** except at the top-level service entry point for logging and graceful degradation.

3. **Always log exceptions with context** (stream_id, session_id, backend name) using structured logging.

4. **Retry transient errors** (network timeouts, connection resets) with exponential backoff. Use `tenacity` library for retry decorators:
   ```python
   from tenacity import retry, stop_after_attempt, wait_exponential

   @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
   async def send_webhook(url: str, payload: dict) -> None:
       ...
   ```

5. **Fail fast on configuration errors** at startup. If a required environment variable is missing or invalid, the service should exit immediately with a clear error message.

6. **Circuit breaker pattern** for external dependencies (ASR APIs, Elasticsearch). After N consecutive failures, stop calling the dependency for a cooldown period before retrying.

### Logging Conventions

1. Use `structlog` for structured JSON logging in all services.

2. **Every log line must include** at minimum: `timestamp`, `level`, `service`, `event` (message).

3. **Context fields** bound per-stream: `stream_id`, `session_id`. Bind these at the start of processing each chunk:
   ```python
   import structlog

   logger = structlog.get_logger()

   async def process_chunk(chunk: AudioChunk) -> None:
       log = logger.bind(
           stream_id=chunk.stream_id,
           session_id=chunk.session_id,
       )
       log.info("processing_audio_chunk", chunk_size_ms=chunk.duration_ms)
   ```

4. **Log levels**:
   - `DEBUG`: Detailed processing steps (token received, VAD classification). Disabled in production.
   - `INFO`: Normal operations (stream started, stream stopped, keyword matched, alert sent).
   - `WARNING`: Degraded but recoverable situations (ASR fallback triggered, reconnection attempt).
   - `ERROR`: Failures requiring attention (ASR backend unreachable, alert delivery failed after retries).
   - `CRITICAL`: System-level failures (database connection lost, out of GPU memory).

5. **Never log PII or secrets.** Log redacted versions or entity type only.

---

## 5. Constraints & Hard Rules

### Absolute Rules (Never Violate)

1. **Secrets MUST come from environment variables or a secrets manager.** Never hardcode API keys, passwords, tokens, or connection strings in source code, configuration files, or comments. Use `pydantic-settings` to load from `.env` or environment.

2. **Never store unredacted PII in general-access database tables.** The `text_original` column is restricted-access and encrypted at rest. All other consumers see `text_redacted` only.

3. **All database writes MUST go through SQLAlchemy ORM models.** No raw SQL strings constructed via string concatenation or f-strings. Parameterized queries only. Alembic for all schema changes.

4. **All external input MUST be validated via Pydantic models** before processing. This includes API request bodies, query parameters, WebSocket messages, and configuration files.

5. **No synchronous blocking I/O in async functions.** If a library only offers sync I/O, wrap it in `asyncio.to_thread()`.

6. **Every service MUST expose a `/health` endpoint** returning `200` when healthy and `503` when not.

7. **Every service MUST emit Prometheus metrics** for: requests processed, errors, latency histograms, and service-specific metrics (e.g., `asr_tokens_per_second`, `keywords_matched_total`).

8. **No `print()` statements.** Use structured logging (`structlog`) exclusively.

9. **All inter-service data contracts use Pydantic models** serialized as JSON. No pickle, no custom binary formats, no untyped dicts.

10. **Docker images MUST be multi-stage builds** with a minimal final image. No development tools, test dependencies, or source code in production images.

### Strong Preferences (Follow Unless There's a Compelling Reason)

1. **Prefer existing utility functions** in `tg-common` before writing new ones.

2. **Prefer composition over inheritance.** Use abstract base classes for pluggable interfaces only; avoid deep class hierarchies.

3. **Prefer small, focused functions** (<30 lines). If a function exceeds 50 lines, it should be refactored.

4. **Prefer `httpx` over `aiohttp`** for HTTP client operations (consistency across codebase).

5. **Prefer `datetime.datetime` with timezone (`UTC`)** for all timestamps. Never use naive datetimes. Use `datetime.timezone.utc` or `zoneinfo`.

6. **Prefer `UUID` for all primary keys** (except `AuditAnchor` which uses `BIGSERIAL` for append-only ordering).

7. **Prefer explicit imports** over wildcard imports. Never use `from module import *`.

8. **Configuration values that might change per environment** MUST be in environment variables, not hardcoded constants.

9. **Every public function MUST have type hints** on all parameters and return type.

10. **Every Pydantic model MUST have `model_config` with `from_attributes = True`** for ORM compatibility.

---

## 6. Testing Strategy

### Testing Pyramid

```
         ┌──────────┐
         │   E2E    │  < 10 tests: Full pipeline (RTSP → Dashboard alert)
         │  Tests   │  Slow, run in CI nightly or pre-release
         ├──────────┤
         │Integration│  ~50 tests: Service-to-service, service-to-DB,
         │  Tests   │  service-to-Elasticsearch. Use testcontainers.
         ├──────────┤
         │  Unit    │  ~300+ tests: Pure logic, mocked dependencies.
         │  Tests   │  Fast, run on every commit and PR.
         └──────────┘
```

### Unit Tests

- **Scope**: Test individual functions and classes in isolation. All external dependencies (DB, Redis, HTTP APIs, ASR backends) are mocked.
- **Framework**: `pytest` + `pytest-asyncio` + `pytest-mock`
- **Location**: `services/<service>/tests/test_<module>.py`
- **Naming**: `test_<function_or_behavior>_<scenario>_<expected_result>`
  ```python
  # Example: services/nlp/tests/test_keyword_engine.py
  async def test_exact_match_single_keyword_returns_match():
      ...

  async def test_fuzzy_match_below_threshold_returns_no_match():
      ...

  async def test_regex_pattern_with_invalid_syntax_raises_error():
      ...
  ```
- **Coverage target**: ≥85% line coverage per service; ≥90% for `nlp` and `asr` services.
- **Data factories**: Use `factory-boy` for generating test data (streams, sessions, segments, rules).

### Integration Tests

- **Scope**: Test interactions between services and real infrastructure (PostgreSQL, Redis, Elasticsearch).
- **Framework**: `pytest` + `testcontainers` (spins up disposable Docker containers).
- **Location**: `tests/integration/test_<interaction>.py`
- **Examples**:
  - `test_ingestion_to_asr.py`: Audio chunks flow from ingestion mock to ASR service and produce tokens.
  - `test_nlp_to_alerts.py`: Keyword match events trigger alert dispatch to a mock webhook server.
  - `test_storage_search.py`: Transcript segments are stored and then searchable via Elasticsearch.
- **Database**: Each test gets a fresh database schema via Alembic migrations run against a testcontainer PostgreSQL.

### End-to-End Tests

- **Scope**: Full pipeline from RTSP stream simulation to dashboard alert delivery.
- **Framework**: `pytest` + Docker Compose (full stack).
- **Location**: `tests/e2e/`
- **Examples**:
  - `test_rtsp_to_dashboard.py`: Simulated RTSP stream with known audio → verify keyword alert appears on WebSocket.
  - `test_pii_redaction_audit.py`: Audio containing PII → verify redacted transcript stored, original encrypted, audit hash computed.
- **Run frequency**: Nightly CI or pre-release; not on every PR (too slow).

### Test Data

- `scripts/generate_test_audio.py`: Generates WAV files with known spoken keywords (using TTS) for deterministic testing.
- `scripts/seed_db.py`: Populates development database with sample streams, rules, sessions, and transcripts.

### Running Tests

```bash
# Unit tests (fast, run on every PR)
make test-unit

# Integration tests (requires Docker)
make test-integration

# E2E tests (requires full Docker Compose stack)
make test-e2e

# All tests with coverage
make test-all

# Specific service
pytest services/nlp/tests/ -v --cov=services/nlp/src

# Specific test
pytest services/nlp/tests/test_keyword_engine.py::test_exact_match_single_keyword_returns_match -v
```

---

## 7. Git & Contribution Conventions

### Branch Naming

```
<type>/<ticket-number>-<short-description>

# Examples:
feat/TG-42-add-deepgram-nova2-backend
fix/TG-87-vad-threshold-not-applied
refactor/TG-103-extract-sliding-window
docs/TG-15-api-reference
chore/TG-200-upgrade-fastapi
test/TG-55-add-keyword-engine-fuzzy-tests
```

**Types**: `feat`, `fix`, `refactor`, `docs`, `chore`, `test`, `ci`, `perf`

### Commit Message Format

Follow [Conventional Commits](https://www.conventionalcommits.org/) v1.0:

```
<type>(<scope>): <short summary>

<optional body>

<optional footer>
```

**Rules**:
- **Type**: `feat`, `fix`, `refactor`, `docs`, `chore`, `test`, `ci`, `perf`, `build`
- **Scope**: service name or component (`asr`, `nlp`, `alerts`, `api`, `ingestion`, `common`, `dashboard`, `ci`)
- **Summary**: imperative, lowercase, no period, ≤72 characters
- **Body**: explain *what* and *why*, not *how*. Wrap at 80 characters.
- **Footer**: reference ticket numbers: `Refs: TG-42` or `Closes: TG-42`

```
# Examples:
feat(asr): add Deepgram Nova-2 streaming backend

Implement the ASREngine interface for Deepgram Nova-2 using WebSocket
streaming. Includes automatic reconnection on connection loss and
configurable chunk size.

Refs: TG-42

---

fix(nlp): correct fuzzy threshold comparison operator

The fuzzy match was using > instead of >= for threshold comparison,
causing matches at exactly the threshold score to be dropped.

Closes: TG-87

---

test(nlp): add unit tests for Aho-Corasick multi-pattern matching

Cover edge cases: overlapping patterns, Unicode keywords, empty
input, and automaton rebuild on rule hot-reload.

Refs: TG-55
```

### Pull Request Checklist

Every PR must satisfy the following before merge:

- [ ] **Title** follows commit message format: `<type>(<scope>): <summary>`
- [ ] **Description** includes:
  - What changed and why
  - Link to ticket/issue
  - Screenshots/logs if UI or output changes
  - Breaking changes (if any)
- [ ] **All unit tests pass** (`make test-unit`)
- [ ] **New code has tests** with ≥85% coverage of new lines
- [ ] **No linting errors** (`ruff check .` and `mypy .` pass)
- [ ] **No new `# type: ignore`** without explanation comment
- [ ] **No hardcoded secrets** or PII in code, tests, or comments
- [ ] **Pydantic models** used for all new data structures crossing service boundaries
- [ ] **Structured logging** used (no `print()`)
- [ ] **Docstrings** on all new public functions and classes
- [ ] **Database changes** have an Alembic migration (if applicable)
- [ ] **API changes** reflected in Pydantic schemas (auto-docs update)
- [ ] **AGENTS.md updated** if architectural decisions or conventions change
- [ ] **Reviewed by at least 1 team member**
- [ ] **CI pipeline green** (lint + type-check + unit tests + integration tests)

### Merge Strategy

- **Squash merge** for feature branches → `main` (clean history).
- **Merge commit** for release branches → `main` (preserve release history).
- **Never force-push** to `main` or release branches.
- **Delete branch after merge.**

### Release Versioning

Follow [Semantic Versioning](https://semver.org/) 2.0:
- `MAJOR.MINOR.PATCH` (e.g., `1.0.0`, `1.1.0`, `1.1.1`)
- `MAJOR`: Breaking API changes
- `MINOR`: New features, backward-compatible
- `PATCH`: Bug fixes, backward-compatible

Tags: `v1.0.0`, `v1.1.0`, etc.

---

## 8. Recent Feature Additions

### 8.1 AI-Powered Keyword Suggestions (Groq / Llama 3.3 70B)

**Endpoint:** `POST /file-analyze/{job_id}/suggest-keywords`

Uses the Groq API (model `llama-3.3-70b-versatile`) to analyze a file-analyze transcript and return contextually relevant keyword suggestions. The endpoint reads the first 3 000 words of the transcript, sends them to Groq with a system prompt requesting ≤20 single-word or short-phrase keywords, and returns a JSON list.

**Flow:**
```
Dashboard "AI Keywords" sub-tab  →  POST /file-analyze/{job_id}/suggest-keywords
                                       │
                                       ├─ load transcript from DB
                                       ├─ call Groq chat completion
                                       └─ return { keywords: [...] }
```

**Frontend:** New "AI Keywords" sub-tab in `FileJobDetail`. Keywords render as clickable pill buttons — clicking a keyword adds it as a new rule.

**Env var:** `GROQ_API_KEY` (free at https://console.groq.com)

### 8.2 Keyword / Rule Export & Import

**Endpoints:**
- `GET  /rules/export` → returns all rules as a JSON array download (`voxsentinel_rules.json`)
- `POST /rules/import` → accepts a JSON file upload, creates rules (skips duplicates by keyword)

**Frontend:** Export/Import buttons in the Rules sub-panel header. Export triggers a browser download; Import opens a file picker for `.json` files.

### 8.3 YouTube Media Worker (Separate Service)

**Problem:** Railway (and many cloud providers) cannot run `yt-dlp` or `ffmpeg` due to network restrictions / missing binaries. YouTube operations (resolve, download audio, capture live chunks) must happen on a machine with unrestricted access.

**Architecture:**
```
┌──────────── Railway ────────────┐      ┌──── Home PC / VPS ────┐
│  VoxSentinel API (port 8010)    │      │  yt_worker (port 8787) │
│                                 │      │                        │
│  youtube.py                     │ HTTP │  /resolve              │
│    _worker_resolve()  ─────────────►   │  /download-audio       │
│    _worker_download_audio()  ──────►   │  /capture-chunk        │
│    _worker_capture_chunk()  ───────►   │                        │
│                                 │      │  yt-dlp + ffmpeg       │
└─────────────────────────────────┘      └────────────────────────┘
```

**Worker location:** `yt_worker/` directory in the repo root.

**Worker endpoints:**
| Method | Path | Description |
|--------|------|-------------|
| POST | `/resolve` | Resolves YouTube URL → title, formats, duration |
| POST | `/download-audio` | Downloads full audio as WAV, returns base64 |
| POST | `/capture-chunk` | Captures a live-stream chunk as WAV, returns base64 |

**Authentication:** `Authorization: Bearer <YT_WORKER_SECRET>` header on every request.

**Env vars (API side):** `YT_WORKER_URL`, `YT_WORKER_SECRET`
**Env vars (Worker side):** `WORKER_PORT` (default 8787), `WORKER_SECRET`

**Fallback:** If `YT_WORKER_URL` is not set, `youtube.py` falls back to local `yt-dlp`/`ffmpeg` (works for local dev).

---