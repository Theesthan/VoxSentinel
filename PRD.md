# Product Requirements Document (PRD)
## Real-Time Multi-Source Transcription, Analytics, and Alerting Platform

**Version:** 1.0
**Date:** 2026-02-27
**Author:** Theesthan
**Status:** Draft

---

## 1. Overview

### Project Name
**VoxSentinel** — Real-Time Multi-Source Transcription, Analytics & Alerting Platform

### One-Liner
A low-latency, pluggable platform that ingests live audio/video streams from CCTV, contact centers, classrooms, and meetings, transcribes speech in real time, monitors for configurable keywords/intents/sentiment, and dispatches multi-channel alerts and agent-assist signals within 300 ms end-to-end.

### Purpose
Organizations operating surveillance systems, contact centers, educational institutions, and corporate meeting environments need continuous, automated monitoring of spoken content. Manual monitoring is expensive, error-prone, and does not scale. This platform automates speech-to-text conversion, keyword/intent detection, sentiment analysis, compliance checking, PII redaction, and alerting — all in real time across dozens of concurrent streams.

### Problem Being Solved
- **Latency**: Existing batch-transcription tools (30–60 s chunk-based) introduce unacceptable delays for safety-critical or compliance-critical alerting.
- **Fragmentation**: Teams currently stitch together separate tools for ASR, keyword search, sentiment, diarization, and alerting with no unified pipeline.
- **Vendor Lock-In**: Relying on a single ASR vendor creates risk; there is no easy way to swap engines per stream based on language, cost, or accuracy requirements.
- **Compliance Gaps**: PII leaks into transcripts, audit trails are missing, and there is no automated compliance keyword monitoring.
- **Scalability**: Current approaches cannot handle ≥20 concurrent streams per GPU node with sub-300 ms latency.

### Who It's For
| Persona | Description |
|---------|-------------|
| **Security Operator** | Monitors CCTV audio feeds for threat keywords (e.g., "gun," "fire," "help") |
| **Contact Center Supervisor** | Monitors agent calls for compliance violations, customer frustration, and upsell opportunities |
| **Compliance Officer** | Needs audit trails, PII-redacted transcripts, and regulatory keyword alerts |
| **Educator / Administrator** | Monitors online class sessions for inappropriate language or safety concerns |
| **DevOps / Platform Engineer** | Deploys, scales, and maintains the platform infrastructure |

---

## 2. Goals & Non-Goals

### Goals
1. **Sub-300 ms end-to-end latency** from audio capture to keyword alert delivery on live streams.
2. **Pluggable ASR abstraction layer** supporting ≥3 managed APIs (Deepgram Nova-2, Lightning ASR, AssemblyAI) and ≥3 self-hosted models (Whisper V3 Turbo, Parakeet TDT, Canary Qwen 2.5B).
3. **≥20 concurrent streams per GPU node** with per-stream ASR engine selection.
4. **Multi-channel session support**: dual-channel (agent vs. customer), multi-feed CCTV, mic vs. system audio.
5. **Real-time keyword detection** via exact match (Aho-Corasick), fuzzy match (RapidFuzz), and regex patterns with hot-reloadable rule configurations.
6. **Real-time sentiment and intent classification** using DistilBERT-class models with configurable escalation thresholds.
7. **Speaker diarization** via pyannote.audio 3.x with external speaker metadata merging (meeting platform APIs).
8. **Multi-channel alerting**: WebSockets, webhooks, Slack, Teams, email, SMS, Signal/WhatsApp.
9. **Agent-assist hooks**: structured event payloads for driving in-UI suggestions, compliance checklists, and next-best-action prompts.
10. **PII redaction** via Microsoft Presidio + spaCy/GLiNER before general-access storage.
11. **Immutable audit trail** with cryptographic hashing per transcript segment.
12. **Full-text search** over historical transcripts via Elasticsearch/OpenSearch.
13. **Post-session analytics dashboards** with keyword heatmaps, sentiment timelines, speaker contribution charts, and alert logs.
14. **Automatic language detection** with per-language keyword banks and model routing.

### Non-Goals
1. **Video analytics / computer vision** — this platform processes audio only; video frames are not analyzed.
2. **Custom ASR model training** — the platform consumes pre-trained models; fine-tuning pipelines are out of scope.
3. **Real-time translation** — language detection and per-language keyword banks are supported, but live translation between languages is not included.
4. **End-user mobile apps** — the operator dashboard is web-based; native iOS/Android apps are deferred.
5. **Telephony PBX replacement** — the system ingests audio from existing telephony infrastructure but does not replace it.
6. **General-purpose chatbot / conversational AI** — agent-assist provides structured suggestions, not open-ended conversational responses.
7. **On-device / edge-only deployment** — the platform assumes server/cloud infrastructure with GPU access.

---

## 3. V1 Scope

### V1 Definition of Done
V1 is complete when the platform can ingest ≥5 concurrent RTSP/HLS audio streams, transcribe them in real time using at least two ASR backends (one managed, one self-hosted), detect keywords via all three matching modes, dispatch alerts to WebSockets and at least one external channel (Slack or webhook), store transcripts with PII redaction, and serve a functional operator dashboard.

### V1 Features (Included)
| Feature | Priority |
|---------|----------|
| RTSP and HLS audio ingestion via FFmpeg + PyAV | P0 |
| Silero VAD integration | P0 |
| ASR abstraction layer with Deepgram Nova-2 and Whisper V3 Turbo backends | P0 |
| Aho-Corasick exact keyword matching | P0 |
| RapidFuzz fuzzy keyword matching | P0 |
| Regex pattern matching | P0 |
| WebSocket alert delivery to dashboard | P0 |
| Webhook alert delivery | P0 |
| Slack alert integration | P1 |
| DistilBERT sentiment classification | P1 |
| PostgreSQL + TimescaleDB transcript storage | P0 |
| Microsoft Presidio PII redaction | P0 |
| Elasticsearch transcript indexing and search | P1 |
| Operator dashboard (React + Vite + shadcn/ui + Framer Motion) | P1 |
| pyannote.audio 3.x diarization | P1 |
| Hot-reloadable keyword/rule configuration via REST API | P1 |
| Cryptographic audit hashing per segment | P1 |
| Docker Compose deployment for development | P0 |
| Kubernetes Helm chart for production | P1 |

### Deferred to V2+
| Feature | Version |
|---------|---------|
| WebRTC and SIP ingestion | V2 |
| Meeting platform relay (Recall.ai) integration | V2 |
| GStreamer pipelines for complex routing | V2 |
| Wake-word gating (RealtimeSTT / Picovoice) | V2 |
| Additional ASR backends (Lightning ASR, AssemblyAI, Parakeet TDT, Canary Qwen, Riva) | V2 |
| Agent-assist hook system | V2 |
| Teams, email, SMS, Signal, WhatsApp alert channels | V2 |
| Multi-language keyword bank routing | V2 |
| Power BI / Grafana export APIs | V2 |
| Kafka/Redpanda event bus (replacing direct queues) | V2 |
| Horizontal auto-scaling policies | V3 |
| Multi-region deployment | V3 |
| Federated/edge processing | V3 |

---

## 4. Feature List

### F1: Multi-Source Audio Ingestion
**Description:** Accept live audio from RTSP cameras, HLS/DASH streams, and uploaded audio/video files. Extract audio tracks, normalize to 16 kHz mono PCM, and push chunks into the processing pipeline.

**User Story:** As a security operator, I want to connect my RTSP CCTV feeds to the platform so that audio from all cameras is continuously transcribed.

**Priority:** P0

**Acceptance Criteria:**
- System accepts RTSP URLs and begins audio extraction within 2 seconds of stream start.
- System accepts HLS/DASH manifest URLs and begins extraction within 3 seconds.
- System accepts uploaded MP4/MKV/WAV files and queues them for batch processing.
- Audio is normalized to 16 kHz, mono, 16-bit PCM regardless of source format.
- Audio chunks of 240–320 ms are produced for streaming ASR; 30–60 s chunks for batch mode.
- Hardware-accelerated decoding (NVDEC) is used when available and falls back to CPU gracefully.
- System handles stream disconnections with automatic reconnection (exponential backoff, max 5 retries).
- Each stream has a unique session UUID assigned at creation.

---

### F2: Voice Activity Detection (VAD)
**Description:** Apply VAD to each audio stream to identify speech segments and suppress silence/noise, reducing unnecessary ASR processing and cost.

**User Story:** As a platform engineer, I want the system to skip transcription during silence so that GPU resources are not wasted on empty audio.

**Priority:** P0

**Acceptance Criteria:**
- Silero VAD is applied to every audio chunk before ASR submission.
- Chunks classified as non-speech (confidence < configurable threshold, default 0.5) are dropped.
- VAD latency adds no more than 10 ms per chunk.
- VAD threshold is configurable per stream via the stream configuration API.
- Metrics are emitted: `vad_speech_ratio` (% of chunks passed through) per stream per minute.

---

### F3: ASR Engine Abstraction Layer
**Description:** A unified internal interface that routes audio chunks to a chosen ASR backend and returns standardized transcript tokens with word-level timestamps, language ID, and confidence scores. V1 supports Deepgram Nova-2 (managed) and Whisper Large V3 Turbo (self-hosted).

**User Story:** As a platform engineer, I want to swap ASR engines per stream without changing downstream code so that I can optimize for cost, latency, or accuracy per use case.

**Priority:** P0

**Acceptance Criteria:**
- A Python abstract base class `ASREngine` defines the interface: `stream_audio(chunk) → AsyncIterator[TranscriptToken]`.
- `TranscriptToken` includes: `text`, `is_final`, `start_time`, `end_time`, `confidence`, `language`, `word_timestamps[]`.
- Deepgram Nova-2 backend connects via WebSocket, sends 240 ms chunks, and returns partial/final tokens.
- Whisper V3 Turbo backend runs on a local GPU server (WhisperLive-style), accepts chunks via WebSocket, and returns tokens in the same format.
- Backend selection is specified per stream in the stream configuration.
- If the selected backend is unavailable, the system falls back to the next configured backend and logs a warning.
- Adding a new backend requires only implementing the `ASREngine` interface and registering it; no changes to downstream consumers.

---

### F4: Real-Time Keyword Detection Engine
**Description:** Continuously monitor the rolling transcript of each stream for configurable keywords and phrases using three matching modes: exact (Aho-Corasick), fuzzy (RapidFuzz), and regex.

**User Story:** As a security operator, I want to be alerted within 300 ms when someone says "gun," "fire," or "help" on any camera feed so that I can respond immediately.

**Priority:** P0

**Acceptance Criteria:**
- The engine maintains a sliding window of the last N seconds (default 10 s, configurable) of finalized transcript text per stream.
- Aho-Corasick automaton is rebuilt on keyword configuration change and matches exact phrases in O(n) time.
- RapidFuzz `token_set_ratio` is applied with configurable similarity threshold (default 80%) for fuzzy matches.
- Regex patterns are compiled at configuration load time and applied per window update.
- A keyword match event includes: `keyword`, `match_type` (exact/fuzzy/regex), `similarity_score`, `matched_text`, `stream_id`, `session_id`, `timestamp`, `speaker_id` (if available), `surrounding_context` (±5 s of transcript).
- Multiple matches in the same window are emitted as separate events.
- Configurable deduplication: same keyword not re-alerted within N seconds (default 10 s) unless the surrounding context changes by more than 30% (Jaccard distance).
- Keyword configuration supports CRUD operations via REST API with hot-reload (no restart required).
- Keyword detection latency from token receipt to event emission: <50 ms.

---

### F5: Sentiment & Intent Classification
**Description:** Run lightweight NLP models on transcript segments to classify sentiment (positive/neutral/negative) and detect intents (e.g., cancellation risk, complaint, urgency).

**User Story:** As a contact center supervisor, I want to see real-time sentiment scores per call so that I can intervene when a customer becomes frustrated.

**Priority:** P1

**Acceptance Criteria:**
- DistilBERT-based sentiment model classifies 3–5-second transcript spans into positive/neutral/negative with confidence scores.
- Inference latency per span: <30 ms on GPU, <100 ms on CPU.
- Sentiment scores are attached to transcript segments and emitted as events.
- Configurable escalation rule: if negative sentiment persists for >N consecutive spans (default 3), an escalation alert is triggered.
- Intent detection supports a configurable set of intent labels loaded from configuration.
- Sentiment and intent events include: `stream_id`, `session_id`, `speaker_id`, `timestamp`, `sentiment_label`, `sentiment_score`, `intent_label`, `intent_confidence`.

---

### F6: Speaker Diarization
**Description:** Identify and label different speakers within each audio stream, enabling per-speaker transcript attribution, sentiment, and keyword alerts.

**User Story:** As a compliance officer reviewing a contact center call, I want to know which speaker (agent vs. customer) said a flagged keyword so that I can take appropriate action.

**Priority:** P1

**Acceptance Criteria:**
- pyannote.audio 3.x pipeline runs on 0.5-second overlapping windows.
- Speaker segments are intersected with ASR word timestamps to assign `speaker_id` per word.
- Default speaker labels: `SPEAKER_00`, `SPEAKER_01`, etc.
- When external speaker metadata is provided (via API), labels are replaced with real names/roles.
- Diarization Error Rate (DER) target: ≤8% on clean 2-speaker audio (validated against AMI corpus subset).
- Diarization adds no more than 200 ms to end-to-end pipeline latency.
- Speaker IDs are included in all downstream events (keyword matches, sentiment, alerts).

---

### F7: PII Redaction & Compliance
**Description:** Automatically detect and redact personally identifiable information from transcripts before storage, and monitor for compliance-related keywords.

**User Story:** As a compliance officer, I want all phone numbers, account IDs, and names to be automatically redacted from stored transcripts so that we comply with data protection regulations.

**Priority:** P0

**Acceptance Criteria:**
- Microsoft Presidio with spaCy and GLiNER recognizers detects: person names, phone numbers, email addresses, physical addresses, account/ID numbers, credit card numbers, SSNs.
- Redacted text replaces detected entities with typed placeholders: `[PERSON]`, `[PHONE]`, `[EMAIL]`, `[ADDRESS]`, `[ACCOUNT_ID]`, `[CREDIT_CARD]`, `[SSN]`.
- Original (unredacted) transcript is stored in a restricted-access table with encryption at rest; redacted version is stored in the general-access table.
- Compliance keyword libraries are configurable per jurisdiction/industry (e.g., SEBI terms, HIPAA terms) and loaded into the same Aho-Corasick pipeline as functional keywords.
- PII redaction processing time: <20 ms per transcript segment.
- Redaction accuracy: ≥95% recall on standard PII benchmarks (e.g., Microsoft Presidio test suite).

---

### F8: Alert Dispatch System
**Description:** Route keyword matches, sentiment escalations, compliance violations, and other events to configured alert channels with throttling and deduplication.

**User Story:** As a security operator, I want to receive a Slack notification with the transcript context when a threat keyword is detected so that I can act without watching the dashboard constantly.

**Priority:** P0 (WebSocket + Webhook), P1 (Slack)

**Acceptance Criteria:**
- WebSocket channel pushes alert events to connected dashboard clients in <50 ms from event generation.
- Webhook channel sends HTTP POST to configured URLs with JSON payload and retries (3 attempts, exponential backoff).
- Slack channel sends formatted messages to configured Slack channels via incoming webhook or bot API.
- Each alert payload includes: `alert_id`, `alert_type` (keyword/sentiment/compliance/intent), `stream_id`, `session_id`, `timestamp`, `speaker_id`, `channel`, `matched_keyword_or_rule`, `match_type`, `similarity_score`, `surrounding_context`, `sentiment_scores`, `confidence`, `asr_backend_used`.
- Deduplication: same `(stream_id, keyword, match_type)` tuple suppressed for N seconds (default 10 s, configurable).
- Throttling: max N alerts per stream per minute (default 30, configurable) with overflow logged and oldest alerts dropped.
- Failed alert deliveries are logged and retried via Celery + Redis task queue.

---

### F9: Transcript Storage & Search
**Description:** Persist all transcripts, alerts, and events in a time-series database and index them for full-text search.

**User Story:** As a compliance officer, I want to search historical transcripts for a specific phrase and see highlighted results so that I can investigate past incidents.

**Priority:** P0 (PostgreSQL), P1 (Elasticsearch)

**Acceptance Criteria:**
- Transcript segments are stored in PostgreSQL + TimescaleDB as time-series records partitioned by day.
- Each segment record includes: `segment_id`, `session_id`, `stream_id`, `speaker_id`, `start_time`, `end_time`, `text_redacted`, `text_original` (restricted), `sentiment_label`, `sentiment_score`, `language`, `asr_backend`, `confidence`, `segment_hash`, `created_at`.
- Alerts are stored in a separate table with foreign keys to segments.
- Elasticsearch indexes redacted transcript text with session, stream, speaker, and timestamp metadata.
- Full-text search supports: exact phrase, fuzzy, regex, and Boolean queries.
- Search results include highlighted matching text, surrounding context, and metadata.
- Segment hashes (SHA-256 of `segment_id + text_original + timestamp`) are computed at write time and stored for audit verification.
- Query response time: <500 ms for searches across 30 days of data (up to 10 M segments).

---

### F10: Operator Dashboard
**Description:** A web-based UI showing live transcripts, active alerts, sentiment gauges, stream status, and historical search.

**User Story:** As a security operator, I want a dashboard showing all my camera feeds' live transcripts with highlighted keywords so that I can monitor everything from one screen.

**Priority:** P1 (React + Vite SPA)

**Acceptance Criteria:**
- Landing page with preloader sequence, masked text reveal hero, scroll-linked word opacity reveal, stats banner, sticky scroll pipeline section, and bento feature grid.
- Design language: ultra-premium dark mode (#000000 bg), stark white typography, razor-thin borders (border-white/10), geometric sans-serif (Inter), brutal yet elegant layout.
- Framer Motion animations: useScroll + useTransform for scroll-linked reveals, staggered fade-ins, text mask slides (y: 100% → 0%), AnimatePresence for preloader exit.
- Dashboard displays a list of active streams with status indicators (active/paused/error).
- Clicking a stream shows its live transcript with keyword highlights (color-coded by match type and speaker).
- Alert panel shows recent alerts sorted by recency with severity indicators and animated entrance.
- Sentiment gauge shows real-time sentiment per stream (rolling 30 s average).
- Search tab provides full-text search across historical transcripts with result highlighting.
- Dashboard updates in real time via WebSocket connection proxied through nginx.
- Dashboard is usable by a non-technical operator without training (clear labels, intuitive layout).
- Responsive design supporting 1080p+ desktop screens (mobile not required for V1).
- Built with Vite 6, React 19, TypeScript strict mode, Tailwind CSS 3.4, shadcn/ui (Button, Card, Badge), and Framer Motion 11.
- Served via nginx multi-stage Docker build; SPA routing fallback; /api and /ws proxied to the API gateway.

---

### F11: Stream Configuration API
**Description:** REST API for managing streams, keyword rules, alert channels, and system configuration.

**User Story:** As a platform engineer, I want to add a new RTSP stream and its keyword rules via API so that I can automate deployment of new camera feeds.

**Priority:** P1

**Acceptance Criteria:**
- CRUD endpoints for streams: create, read, update, delete, list.
- CRUD endpoints for keyword rule sets: create, read, update, delete, list; changes take effect within 5 seconds (hot-reload).
- CRUD endpoints for alert channel configurations.
- All endpoints require authentication (API key or JWT).
- Request validation with clear error messages (422 for invalid input).
- OpenAPI/Swagger documentation auto-generated from endpoint definitions.
- Rate limiting: 100 requests/minute per API key.

---

### F12: Cryptographic Audit Trail
**Description:** Every stored transcript segment is hashed and the hashes are periodically anchored to an append-only audit table to prove non-tampering.

**User Story:** As a compliance officer, I want cryptographic proof that transcripts have not been altered after storage so that they are admissible as evidence.

**Priority:** P1

**Acceptance Criteria:**
- Each transcript segment has a SHA-256 hash computed from `segment_id + text_original + start_time + session_id`.
- Hashes are stored alongside segments in the `segment_hash` column.
- Every 60 seconds, a Merkle root is computed from all new segment hashes since the last anchor and written to an append-only `audit_anchors` table.
- An audit verification endpoint accepts a `segment_id` and returns the segment's hash, its Merkle proof, and the anchor record.
- The `audit_anchors` table is append-only (no UPDATE/DELETE permissions granted to application roles).

---

## 5. Non-Functional Requirements

### Performance
- **End-to-end latency** (audio chunk captured → alert delivered): <300 ms for live streaming mode using streaming-optimized ASR backends.
- **ASR latency** (chunk sent → partial token received): <150 ms for managed APIs, <200 ms for self-hosted Whisper V3 Turbo.
- **Keyword detection latency** (token received → match event emitted): <50 ms.
- **Alert delivery latency** (match event → WebSocket push): <50 ms.
- **Sentiment inference latency**: <30 ms per 3–5 s span on GPU.
- **PII redaction latency**: <20 ms per segment.
- **Transcript search**: <500 ms for queries across 30 days / 10 M segments.

### Scalability
- **Concurrent streams**: ≥20 per GPU node (NVIDIA A10G or equivalent) in V1; ≥100 with horizontal scaling in V2.
- **Horizontal scaling**: stateless microservices behind a load balancer; stream state held in Redis or Kafka.
- **Storage scaling**: TimescaleDB compression and retention policies; Elasticsearch index lifecycle management.
- **ASR scaling**: multiple ASR worker pods per backend; auto-scaling based on stream count and GPU utilization.

### Security
- All external communication over TLS 1.3.
- API authentication via API keys (V1) and JWT/OAuth2 (V2).
- Secrets (API keys, DB credentials, ASR tokens) stored in environment variables or a secrets manager (e.g., HashiCorp Vault, AWS Secrets Manager); never in code or config files.
- PII-containing tables encrypted at rest (AES-256) and access-controlled via database roles.
- RBAC for dashboard access: operator (view streams/alerts), supervisor (view + configure), admin (full access).
- Audit logging for all API mutations and dashboard logins.

### Reliability
- **Uptime target**: 99.5% (measured monthly).
- Stream ingestion auto-reconnects on failure with exponential backoff.
- ASR backend failover: if primary backend is unavailable, fallback to secondary within 5 seconds.
- Alert delivery retries: 3 attempts with exponential backoff; failed alerts logged and queryable.
- No data loss on graceful shutdown: in-flight transcript segments flushed to storage before process exit.
- Health check endpoints for all services; Kubernetes liveness and readiness probes.

### Maintainability
- Modular microservice architecture: each layer (ingestion, VAD, ASR, NLP, storage, alerts) is a separate service/container.
- Shared library for data models, configuration, and utilities.
- Comprehensive logging (structured JSON) with correlation IDs per stream/session.
- Metrics exported to Prometheus; dashboards in Grafana.
- CI/CD pipeline with automated tests, linting, and container builds.

### Accessibility
- Dashboard meets WCAG 2.1 AA for color contrast, keyboard navigation, and screen reader labels.
- High-contrast monochrome design inherently meets AA contrast ratios for text.

---

## 6. Data Models / Entities

### Stream
| Field | Type | Description |
|-------|------|-------------|
| `stream_id` | UUID (PK) | Unique identifier |
| `name` | VARCHAR(255) | Human-readable name |
| `source_type` | ENUM('rtsp', 'hls', 'dash', 'webrtc', 'sip', 'file', 'meeting_relay') | Input source type |
| `source_url` | TEXT | Connection URL or file path |
| `asr_backend` | VARCHAR(100) | Selected ASR engine identifier |
| `asr_fallback_backend` | VARCHAR(100) | Fallback ASR engine |
| `language_override` | VARCHAR(10) | Force language (null = auto-detect) |
| `vad_threshold` | FLOAT | VAD confidence threshold (0.0–1.0) |
| `chunk_size_ms` | INT | Audio chunk size in ms (default 280) |
| `status` | ENUM('active', 'paused', 'error', 'stopped') | Current status |
| `session_id` | UUID | Current active session |
| `created_at` | TIMESTAMPTZ | Creation time |
| `updated_at` | TIMESTAMPTZ | Last update time |
| `metadata` | JSONB | Additional key-value metadata |

### Session
| Field | Type | Description |
|-------|------|-------------|
| `session_id` | UUID (PK) | Unique identifier for this session |
| `stream_id` | UUID (FK → Stream) | Parent stream |
| `started_at` | TIMESTAMPTZ | Session start |
| `ended_at` | TIMESTAMPTZ | Session end (null if active) |
| `asr_backend_used` | VARCHAR(100) | ASR backend for this session |
| `total_segments` | INT | Count of transcript segments |
| `total_alerts` | INT | Count of alerts generated |

### TranscriptSegment
| Field | Type | Description |
|-------|------|-------------|
| `segment_id` | UUID (PK) | Unique identifier |
| `session_id` | UUID (FK → Session) | Parent session |
| `stream_id` | UUID (FK → Stream) | Parent stream |
| `speaker_id` | VARCHAR(100) | Speaker label |
| `start_time` | TIMESTAMPTZ | Segment start (absolute) |
| `end_time` | TIMESTAMPTZ | Segment end (absolute) |
| `start_offset_ms` | BIGINT | Offset from session start |
| `end_offset_ms` | BIGINT | Offset from session start |
| `text_redacted` | TEXT | PII-redacted transcript |
| `text_original` | TEXT | Original transcript (restricted access) |
| `word_timestamps` | JSONB | Array of {word, start_ms, end_ms, confidence} |
| `language` | VARCHAR(10) | Detected language code |
| `asr_backend` | VARCHAR(100) | ASR engine used |
| `asr_confidence` | FLOAT | Overall confidence |
| `sentiment_label` | VARCHAR(20) | positive/neutral/negative |
| `sentiment_score` | FLOAT | Sentiment confidence |
| `intent_labels` | JSONB | Array of detected intents |
| `pii_entities_found` | JSONB | Array of PII entity types detected |
| `segment_hash` | VARCHAR(64) | SHA-256 hash for audit |
| `created_at` | TIMESTAMPTZ | Storage time |

### Alert
| Field | Type | Description |
|-------|------|-------------|
| `alert_id` | UUID (PK) | Unique identifier |
| `session_id` | UUID (FK → Session) | Parent session |
| `stream_id` | UUID (FK → Stream) | Parent stream |
| `segment_id` | UUID (FK → TranscriptSegment) | Triggering segment |
| `alert_type` | ENUM('keyword', 'sentiment', 'compliance', 'intent') | Alert category |
| `severity` | ENUM('low', 'medium', 'high', 'critical') | Severity level |
| `matched_rule` | VARCHAR(255) | Keyword/rule that triggered |
| `match_type` | ENUM('exact', 'fuzzy', 'regex', 'sentiment_threshold', 'intent') | How it was matched |
| `similarity_score` | FLOAT | Fuzzy match score (null for exact/regex) |
| `matched_text` | TEXT | Text that matched |
| `surrounding_context` | TEXT | ±5 s of surrounding transcript |
| `speaker_id` | VARCHAR(100) | Speaker who triggered |
| `channel` | VARCHAR(50) | Audio channel (if multi-channel) |
| `sentiment_scores` | JSONB | Sentiment at time of alert |
| `asr_backend_used` | VARCHAR(100) | ASR backend at time of alert |
| `delivered_to` | JSONB | Array of channels alert was sent to |
| `delivery_status` | JSONB | Per-channel delivery status |
| `deduplicated` | BOOLEAN | Whether this was suppressed by dedup |
| `created_at` | TIMESTAMPTZ | Alert creation time |

### KeywordRule
| Field | Type | Description |
|-------|------|-------------|
| `rule_id` | UUID (PK) | Unique identifier |
| `rule_set_name` | VARCHAR(255) | Logical grouping name |
| `keyword` | TEXT | Keyword, phrase, or regex pattern |
| `match_type` | ENUM('exact', 'fuzzy', 'regex') | Matching mode |
| `fuzzy_threshold` | FLOAT | Similarity threshold for fuzzy (0.0–1.0) |
| `severity` | ENUM('low', 'medium', 'high', 'critical') | Alert severity |
| `category` | VARCHAR(100) | Category (security, compliance, sales, etc.) |
| `language` | VARCHAR(10) | Language code (null = all languages) |
| `enabled` | BOOLEAN | Active flag |
| `created_at` | TIMESTAMPTZ | Creation time |
| `updated_at` | TIMESTAMPTZ | Last update time |

### AlertChannelConfig
| Field | Type | Description |
|-------|------|-------------|
| `channel_id` | UUID (PK) | Unique identifier |
| `channel_type` | ENUM('websocket', 'webhook', 'slack', 'teams', 'email', 'sms', 'signal') | Channel type |
| `config` | JSONB | Channel-specific config (URL, token, etc.) |
| `min_severity` | ENUM('low', 'medium', 'high', 'critical') | Minimum severity to trigger |
| `alert_types` | JSONB | Array of alert types to receive |
| `stream_ids` | JSONB | Array of stream IDs (null = all) |
| `enabled` | BOOLEAN | Active flag |
| `created_at` | TIMESTAMPTZ | Creation time |

### AuditAnchor
| Field | Type | Description |
|-------|------|-------------|
| `anchor_id` | BIGSERIAL (PK) | Auto-incrementing ID |
| `merkle_root` | VARCHAR(64) | SHA-256 Merkle root |
| `segment_count` | INT | Number of segments in this anchor |
| `first_segment_id` | UUID | First segment in range |
| `last_segment_id` | UUID | Last segment in range |
| `anchored_at` | TIMESTAMPTZ | Anchor creation time |

### Relationships
```
Stream 1 ──── * Session
Session 1 ──── * TranscriptSegment
Session 1 ──── * Alert
TranscriptSegment 1 ──── * Alert
Stream * ──── * KeywordRule (via stream_rule_assignments join table or JSONB)
Stream * ──── * AlertChannelConfig (via channel assignments)
AuditAnchor covers TranscriptSegment range [first_segment_id ... last_segment_id]
```

---

## 7. API / Interface Contracts

### Base URL
`/api/v1`

### Authentication
All endpoints require `Authorization: Bearer <api_key>` header.

### Streams

#### `POST /streams`
Create a new stream.
```json
// Request
{
  "name": "Lobby Camera 1",
  "source_type": "rtsp",
  "source_url": "rtsp://192.168.1.100:554/stream1",
  "asr_backend": "deepgram_nova2",
  "asr_fallback_backend": "whisper_v3_turbo",
  "language_override": null,
  "vad_threshold": 0.5,
  "chunk_size_ms": 280,
  "keyword_rule_set_names": ["security_default", "compliance_financial"],
  "alert_channel_ids": ["uuid-1", "uuid-2"],
  "metadata": {"location": "Building A", "floor": 1}
}

// Response 201
{
  "stream_id": "uuid",
  "status": "active",
  "session_id": "uuid",
  "created_at": "2026-02-27T10:00:00Z"
}
```

#### `GET /streams`
List all streams with status.
```json
// Response 200
{
  "streams": [
    {
      "stream_id": "uuid",
      "name": "Lobby Camera 1",
      "status": "active",
      "source_type": "rtsp",
      "asr_backend": "deepgram_nova2",
      "session_id": "uuid",
      "created_at": "2026-02-27T10:00:00Z"
    }
  ],
  "total": 1
}
```

#### `GET /streams/{stream_id}`
Get stream details including current session info.

#### `PATCH /streams/{stream_id}`
Update stream configuration. Supports partial updates.

#### `DELETE /streams/{stream_id}`
Stop and remove a stream. Active session is ended.

#### `POST /streams/{stream_id}/pause`
Pause a stream (stop ASR but keep connection alive).

#### `POST /streams/{stream_id}/resume`
Resume a paused stream.

---

### Keyword Rules

#### `POST /rules`
```json
// Request
{
  "rule_set_name": "security_default",
  "keyword": "gun",
  "match_type": "exact",
  "severity": "critical",
  "category": "security",
  "language": null,
  "enabled": true
}

// Response 201
{
  "rule_id": "uuid",
  "created_at": "2026-02-27T10:00:00Z"
}
```

#### `GET /rules?rule_set_name=security_default`
List rules, optionally filtered by rule set, category, or language.

#### `PATCH /rules/{rule_id}`
Update a rule. Changes take effect within 5 seconds.

#### `DELETE /rules/{rule_id}`
Delete a rule.

---

### Alert Channels

#### `POST /alert-channels`
```json
// Request
{
  "channel_type": "slack",
  "config": {
    "webhook_url": "https://hooks.slack.com/services/T.../B.../xxx"
  },
  "min_severity": "high",
  "alert_types": ["keyword", "compliance"],
  "stream_ids": null,
  "enabled": true
}

// Response 201
{
  "channel_id": "uuid",
  "created_at": "2026-02-27T10:00:00Z"
}
```

#### `GET /alert-channels`
#### `PATCH /alert-channels/{channel_id}`
#### `DELETE /alert-channels/{channel_id}`

---

### Transcripts & Search

#### `GET /sessions/{session_id}/transcript`
Retrieve transcript segments for a session.
```json
// Query params: ?from=2026-02-27T10:00:00Z&to=2026-02-27T10:05:00Z&speaker_id=SPEAKER_00
// Response 200
{
  "session_id": "uuid",
  "segments": [
    {
      "segment_id": "uuid",
      "speaker_id": "SPEAKER_00",
      "start_time": "2026-02-27T10:00:01Z",
      "end_time": "2026-02-27T10:00:04Z",
      "text": "I need to report a [PERSON] at the front desk.",
      "sentiment_label": "negative",
      "sentiment_score": 0.82,
      "language": "en",
      "confidence": 0.94
    }
  ],
  "total": 1
}
```

#### `POST /search`
Full-text search across transcripts.
```json
// Request
{
  "query": "report suspicious",
  "search_type": "fuzzy",
  "stream_ids": ["uuid-1", "uuid-2"],
  "date_from": "2026-02-20T00:00:00Z",
  "date_to": "2026-02-27T23:59:59Z",
  "speaker_id": null,
  "language": null,
  "limit": 50,
  "offset": 0
}

// Response 200
{
  "results": [
    {
      "segment_id": "uuid",
      "session_id": "uuid",
      "stream_id": "uuid",
      "stream_name": "Lobby Camera 1",
      "speaker_id": "SPEAKER_01",
      "timestamp": "2026-02-25T14:32:10Z",
      "text": "I want to <em>report</em> something <em>suspicious</em> near gate 3.",
      "sentiment_label": "negative",
      "score": 0.91
    }
  ],
  "total": 1
}
```

---

### Alerts

#### `GET /alerts`
List alerts with filters.
```json
// Query params: ?stream_id=uuid&alert_type=keyword&severity=critical&from=...&to=...&limit=50
// Response 200
{
  "alerts": [
    {
      "alert_id": "uuid",
      "stream_id": "uuid",
      "stream_name": "Lobby Camera 1",
      "alert_type": "keyword",
      "severity": "critical",
      "matched_rule": "gun",
      "match_type": "exact",
      "matched_text": "he has a gun",
      "speaker_id": "SPEAKER_01",
      "surrounding_context": "...I saw someone, he has a gun near the entrance...",
      "created_at": "2026-02-27T10:01:23Z",
      "delivery_status": {"websocket": "delivered", "slack": "delivered"}
    }
  ],
  "total": 1
}
```

#### `GET /alerts/{alert_id}`
Get full alert details.

---

### Audit

#### `GET /audit/verify/{segment_id}`
Verify the integrity of a transcript segment.
```json
// Response 200
{
  "segment_id": "uuid",
  "segment_hash": "sha256...",
  "anchor_id": 42,
  "merkle_root": "sha256...",
  "merkle_proof": ["sha256...", "sha256..."],
  "verified": true,
  "anchored_at": "2026-02-27T10:02:00Z"
}
```

---

### Health & Metrics

#### `GET /health`
```json
// Response 200
{
  "status": "healthy",
  "services": {
    "database": "ok",
    "elasticsearch": "ok",
    "redis": "ok",
    "asr_deepgram": "ok",
    "asr_whisper": "ok"
  },
  "active_streams": 12,
  "uptime_seconds": 86400
}
```

#### `GET /metrics`
Prometheus-format metrics endpoint.

---

### WebSocket: Live Transcript & Alerts

#### `WS /ws/streams/{stream_id}/transcript`
Stream live transcript tokens for a specific stream.
```json
// Server → Client messages
{"type": "token", "data": {"text": "hello", "is_final": true, "speaker_id": "SPEAKER_00", "timestamp": "...", "confidence": 0.95}}
{"type": "alert", "data": {"alert_id": "uuid", "alert_type": "keyword", "severity": "critical", "matched_rule": "gun", "matched_text": "he has a gun", "speaker_id": "SPEAKER_01", "surrounding_context": "..."}}
{"type": "sentiment", "data": {"speaker_id": "SPEAKER_00", "label": "negative", "score": 0.85, "timestamp": "..."}}
```

#### `WS /ws/alerts`
Stream all alerts across all streams for dashboard consumption.

---

## 8. Success Metrics

### Quantitative KPIs

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| End-to-end latency (audio → alert) | <300 ms (p95) | Instrumented timing from audio chunk timestamp to WebSocket alert delivery |
| ASR Word Error Rate (clean audio) | ≤8% | Periodic evaluation against curated test set (LibriSpeech, internal recordings) |
| ASR Word Error Rate (noisy audio) | ≤15% | Evaluation against noisy test set (CHiME-6, internal noisy recordings) |
| Keyword detection recall | ≥95% | Evaluated against labeled test transcripts with known keywords |
| Keyword detection precision | ≥90% | False positive rate measured against labeled test transcripts |
| PII redaction recall | ≥95% | Evaluated against Microsoft Presidio test suite and internal labeled data |
| Diarization Error Rate | ≤8% | Evaluated against AMI corpus subset |
| Concurrent streams per GPU node | ≥20 | Load test with 20 simultaneous RTSP streams |
| System uptime | ≥99.5% | Monthly uptime tracking via health endpoint pings |
| Alert delivery success rate | ≥99% | Ratio of successfully delivered alerts to total generated |
| Transcript search response time | <500 ms (p95) | Measured under load with 10 M segments indexed |
| Mean time to first transcript token | <500 ms | From stream creation API call to first WebSocket token delivery |

### Qualitative Success Criteria
- Security operators report reduced response time to incidents compared to manual monitoring.
- Compliance officers can generate audit-ready transcript reports within 2 minutes.
- Platform engineers can add a new stream and keyword rule set in <5 minutes via API.
- The ASR backend can be swapped for a stream without any downstream service changes.

---

## 9. Risks & Mitigations

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| 1 | **ASR API vendor outage** (Deepgram, AssemblyAI) causes transcription failure | Medium | High | Pluggable ASR layer with automatic failover to self-hosted Whisper V3 Turbo; health monitoring per backend with circuit breaker pattern |
| 2 | **GPU resource exhaustion** with >20 streams on Whisper V3 Turbo | Medium | High | VAD pre-filtering reduces ASR load by 30–60%; batching strategies; priority queuing; auto-scaling policies in K8s |
| 3 | **High false positive rate** in keyword detection due to ASR errors | Medium | Medium | Fuzzy matching with tunable thresholds; confidence-weighted scoring; deduplication; user feedback loop to tune rules |
| 4 | **PII leaks** if Presidio misses entities | Low | Critical | Defense in depth: Presidio + regex-based secondary pass + manual review queue for high-risk sessions; encryption at rest for all transcripts |
| 5 | **Network latency/jitter** on RTSP streams causes audio gaps | Medium | Medium | Adaptive buffering in FFmpeg; gap detection and logging; jitter buffer tuning per stream |
| 6 | **Elasticsearch index grows unbounded** | Medium | Medium | Index lifecycle management (ILM) with hot/warm/cold/delete phases; configurable retention policies per stream |
| 7 | **WebSocket connection drops** cause missed alerts | Medium | High | Alert state stored in Redis; clients reconnect and receive missed alerts since last acknowledged timestamp; webhook/Slack as reliable backup channels |
| 8 | **ASR model accuracy degrades** on domain-specific vocabulary (medical, legal, financial) | Medium | Medium | Custom vocabulary injection where supported (Deepgram, Riva); post-ASR text correction pipeline (V2); regular accuracy benchmarking |
| 9 | **Compliance requirements change** across jurisdictions | Low | Medium | Configurable compliance rule libraries per jurisdiction; regular review and update cycle; separation of compliance rules from core logic |
| 10 | **Team unfamiliarity with GPU/ML infrastructure** | Medium | Medium | Use managed ASR APIs (Deepgram, AssemblyAI) as primary backends for V1; self-hosted models as secondary; comprehensive deployment documentation |

---

## 10. Open Questions

| # | Question | Owner | Status | Notes |
|---|----------|-------|--------|-------|
| 1 | Which specific GPU instance type for self-hosted ASR? (A10G, A100, L4, T4) | Platform Eng. | Open | Depends on budget and concurrent stream target; A10G is recommended baseline |
| 2 | What is the data retention policy for transcripts and alerts? | Compliance | Open | Likely 90 days for general access, 1 year for compliance-flagged sessions; needs legal review |
| 3 | Should the system support real-time transcript editing/correction by operators? | Product | Open | Useful for compliance but adds complexity; may be V2+ |
| 4 | Which meeting platform relay service to use for V2? (Recall.ai, custom, or direct API?) | Engineering | Open | Recall.ai is the established option; evaluate cost and API stability |
| 5 | What is the deployment target for V1? (Single cloud provider? Which one?) | Platform Eng. | Open | AWS (EKS + GPU instances) is the assumed default; needs confirmation |
| 6 | How should multi-tenancy be handled? (Separate databases? Schema-level isolation? Row-level?) | Architecture | Open | Row-level with tenant_id is simplest for V1; evaluate schema-level for V2 |
| 7 | What is the budget allocation for managed ASR APIs? | Finance/Product | Open | Deepgram pricing is per-audio-hour; need to estimate monthly audio volume |
| 8 | Should wake-word gating be prioritized for V1 in contact center scenarios? | Product | Open | Currently deferred to V2; may be P1 if contact center is the primary V1 use case |
| 9 | What languages must be supported at launch? | Product | Open | English is mandatory; need to determine if Spanish, Hindi, Arabic are V1 requirements |
| 10 | Is there a requirement for on-premises deployment (no cloud) for any customer? | Sales/Product | Open | Affects self-hosted model priority and Kubernetes vs. bare-metal deployment |

---

Assumptions & Constraints (Current Free Scope)

- **Deployment:** GCP (Cloud Run + T4 GPU via Vertex AI or Colab for ASR)
- **ASR:** OpenAI Whisper API ($0.006/min) for managed; self-hosted Whisper medium as fallback
- **Meeting relay:** MeetingBaaS open-source (self-hosted) for V1; Recall.ai evaluated for V2
- **Multi-tenancy:** Row-level isolation via `tenant_id` in PostgreSQL
- **Data retention:** 90-day default, configurable via env variable
- **Languages:** English only at V1 launch
- **No on-prem requirement for V1**
- **Wake-word gating and transcript editing deferred to V2**
