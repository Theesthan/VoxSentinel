# VoxSentinel YouTube Media Worker

A lightweight standalone service that runs **yt-dlp** and **FFmpeg** on a machine where YouTube is not blocked (your home PC, college lab, or a VPS with residential IP).

The main VoxSentinel API on Railway delegates YouTube operations to this worker via HTTP, solving the "YouTube blocks datacenter IPs" problem.

## Architecture

```
┌─────────────────────┐          HTTP           ┌─────────────────────┐
│  Railway API        │ ──────────────────────→ │  YT Worker          │
│  (voxsentinel.up.   │                         │  (home PC / VPS)    │
│   railway.app)      │ ←────────────────────── │                     │
│                     │      WAV audio bytes     │  yt-dlp + FFmpeg    │
└─────────────────────┘                         └─────────────────────┘
```

**Backward-compatible**: If `YT_WORKER_URL` is not set on Railway, everything works as before (local yt-dlp).

## Quick Start (Windows)

```bash
cd yt_worker
start_worker.bat
```

## Quick Start (Manual)

```bash
cd yt_worker
pip install -r requirements.txt
python worker.py
```

## Configuration

| Env Var | Where | Description |
|---------|-------|-------------|
| `WORKER_PORT` | Worker machine | Port to listen on (default: `8787`) |
| `WORKER_SECRET` | Worker machine | Shared auth secret (optional but recommended) |
| `YT_WORKER_URL` | Railway API | Full URL to worker, e.g. `http://your-ip:8787` |
| `YT_WORKER_SECRET` | Railway API | Must match `WORKER_SECRET` on worker |
| `TG_COOKIES_FILE` | Worker machine | Path to YouTube cookies file (optional) |

## Exposing to the Internet

The worker needs to be reachable from Railway. Options:

### Option A: Port Forwarding (Home PC)
1. Forward port `8787` on your router to your PC's local IP
2. Set `YT_WORKER_URL=http://YOUR_PUBLIC_IP:8787` on Railway

### Option B: ngrok / Cloudflare Tunnel (easier, no router config)
```bash
# Install ngrok: https://ngrok.com/
ngrok http 8787
# Copy the https://xxxxx.ngrok-free.app URL
```
Set `YT_WORKER_URL=https://xxxxx.ngrok-free.app` on Railway.

### Option C: VPS with residential IP
Deploy on a cheap VPS (Oracle Cloud free tier, etc.) and set the public IP.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check — shows yt-dlp/FFmpeg status |
| POST | `/worker/resolve` | Resolve YouTube URL → metadata + HLS URL |
| POST | `/worker/download-audio` | Download VOD audio → returns WAV bytes |
| POST | `/worker/capture-chunk` | Capture HLS live chunk → returns WAV bytes |

## Setting Up on Railway

1. In your Railway project, go to your API service's **Variables** tab
2. Add:
   - `YT_WORKER_URL` = `http://your-worker-ip:8787` (or ngrok URL)
   - `YT_WORKER_SECRET` = your chosen secret (must match worker's `WORKER_SECRET`)
   - `GROQ_API_KEY` = your Groq API key (for AI keyword suggestions)
3. Redeploy the API service

The API will automatically try the worker first for all YouTube operations, falling back to local yt-dlp if the worker is unreachable.

## Security

- Set `WORKER_SECRET` on both the worker and Railway (`YT_WORKER_SECRET`) to prevent unauthorized use
- Use HTTPS (via ngrok/Cloudflare) if the worker is exposed to the public internet
- The worker only processes YouTube URLs — it doesn't store data or have access to your database
