# API Reference

## VoxSentinel REST & WebSocket API

Base URL: `http://localhost:8000/api/v1`

---

### Streams

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/streams` | List all configured streams |
| `POST` | `/streams` | Add a new stream source |
| `GET` | `/streams/{id}` | Get stream details |
| `PUT` | `/streams/{id}` | Update stream configuration |
| `DELETE` | `/streams/{id}` | Remove a stream |
| `POST` | `/streams/{id}/start` | Start stream ingestion |
| `POST` | `/streams/{id}/stop` | Stop stream ingestion |

### Keyword Rules

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/rules` | List all keyword rules |
| `POST` | `/rules` | Create a new keyword rule |
| `GET` | `/rules/{id}` | Get rule details |
| `PUT` | `/rules/{id}` | Update a rule |
| `DELETE` | `/rules/{id}` | Delete a rule |

### Transcripts

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/transcripts` | List transcript segments (paginated) |
| `GET` | `/transcripts/{session_id}` | Get all segments for a session |

### Search

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/search` | Full-text search across transcripts |

### Alerts

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/alerts` | List alerts (paginated, filterable) |
| `GET` | `/alerts/{id}` | Get alert details |

### Alert Channels

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/alert-channels` | List configured alert channels |
| `POST` | `/alert-channels` | Configure a new alert channel |
| `PUT` | `/alert-channels/{id}` | Update channel configuration |
| `DELETE` | `/alert-channels/{id}` | Remove an alert channel |

### Audit

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/audit` | List audit log entries |
| `GET` | `/audit/verify/{session_id}` | Verify audit hash chain integrity |

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Aggregate health of all services |

### WebSocket

| Endpoint | Description |
|----------|-------------|
| `ws://localhost:8000/ws/live` | Real-time transcript and alert stream |

---

*Detailed request/response schemas are auto-generated from Pydantic models and available at `/docs` (Swagger UI) and `/redoc`.*
