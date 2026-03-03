"""
VoxSentinel YouTube Media Worker

A lightweight standalone FastAPI service that runs yt-dlp and FFmpeg
on a machine where YouTube is not blocked (home PC, college lab, VPS).

The main Railway API delegates YouTube operations to this worker via HTTP.

Endpoints:
  POST /worker/download-audio   — Download VOD audio → return WAV bytes
  POST /worker/resolve          — Resolve YouTube URL → JSON metadata
  POST /worker/capture-chunk    — Capture HLS live chunk → return WAV bytes

Run:
  pip install -r requirements.txt
  python worker.py              (or use start_worker.bat)

Env vars:
  WORKER_PORT     — Port to listen on (default 8787)
  WORKER_SECRET   — Shared secret for auth (must match YT_WORKER_SECRET on Railway)
"""

from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Header, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ── Config ──

WORKER_PORT = int(os.getenv("WORKER_PORT", "8787"))
WORKER_SECRET = os.getenv("WORKER_SECRET", "")
TEMP_DIR = Path(tempfile.gettempdir()) / "vox_yt_worker"
TEMP_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="VoxSentinel YT Worker", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Auth ──

def _check_secret(authorization: str | None = Header(default=None)):
    if WORKER_SECRET:
        token = (authorization or "").removeprefix("Bearer ").strip()
        if token != WORKER_SECRET:
            raise HTTPException(status_code=401, detail="Invalid worker secret")


# ── Schemas ──

class ResolveRequest(BaseModel):
    url: str


class ResolveResponse(BaseModel):
    is_live: bool = False
    title: str = "Unknown"
    hls_url: str | None = None
    error: str | None = None


class DownloadRequest(BaseModel):
    url: str
    job_id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class CaptureChunkRequest(BaseModel):
    hls_url: str
    duration: int = 10
    stream_id: str = ""


# ── Helpers ──

_PLAYER_CLIENTS: list[list[str]] = [
    ["tv_embedded"],
    ["mweb"],
    ["android"],
    ["web"],
]


def _find_cookies_file() -> Path | None:
    """Look for a cookies file in common locations."""
    candidates = [
        Path(os.getenv("TG_COOKIES_FILE", "")),
        Path("cookies/vidcookie.txt"),
        Path.home() / "vidcookie.txt",
    ]
    for p in candidates:
        if p and p.exists():
            return p
    return None


async def _yt_dlp_resolve(url: str) -> dict | None:
    """Resolve YouTube URL metadata via yt-dlp."""
    import yt_dlp

    cookies = _find_cookies_file()
    base_opts: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": False,
        "geo_bypass": True,
        "nocheckcertificate": True,
    }
    if cookies:
        base_opts["cookiefile"] = str(cookies)

    for pc in _PLAYER_CLIENTS:
        opts = {
            **base_opts,
            "extractor_args": {"youtube": {"player_client": pc}},
        }
        try:
            def _extract(o=opts):
                with yt_dlp.YoutubeDL(o) as ydl:
                    return ydl.extract_info(url, download=False)
            return await asyncio.to_thread(_extract)
        except Exception:
            continue

    # Bare fallback
    try:
        def _extract_bare():
            with yt_dlp.YoutubeDL(base_opts) as ydl:
                return ydl.extract_info(url, download=False)
        return await asyncio.to_thread(_extract_bare)
    except Exception:
        return None


async def _yt_dlp_download(url: str, job_id: str) -> Path:
    """Download YouTube audio as WAV."""
    import yt_dlp

    output_path = TEMP_DIR / f"{job_id}_audio.wav"
    outtmpl = str(TEMP_DIR / f"{job_id}_raw.%(ext)s")
    cookies = _find_cookies_file()

    base_opts: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "geo_bypass": True,
        "nocheckcertificate": True,
        "outtmpl": outtmpl,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "wav",
            "preferredquality": "0",
        }],
    }
    if cookies:
        base_opts["cookiefile"] = str(cookies)

    format_selectors = ["bestaudio/best", "bestaudio*", "best"]
    strategies: list[dict[str, Any]] = []
    for pc in _PLAYER_CLIENTS:
        for fmt in format_selectors:
            strategies.append({
                **base_opts,
                "format": fmt,
                "extractor_args": {"youtube": {"player_client": pc}},
            })
    for fmt in format_selectors:
        strategies.append({**base_opts, "format": fmt})

    last_err: Exception | None = None
    for strat in strategies:
        # Cleanup leftover files
        for f in TEMP_DIR.glob(f"{job_id}_raw.*"):
            try:
                f.unlink()
            except Exception:
                pass

        try:
            def _dl(opts=strat):
                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.download([url])
            await asyncio.to_thread(_dl)

            wav = TEMP_DIR / f"{job_id}_raw.wav"
            if wav.exists():
                wav.rename(output_path)
                return output_path
            for f in TEMP_DIR.glob(f"{job_id}_raw.*"):
                f.rename(output_path)
                return output_path
        except Exception as exc:
            last_err = exc
            continue

    # Subprocess fallback
    for pc in _PLAYER_CLIENTS:
        for f in TEMP_DIR.glob(f"{job_id}_raw.*"):
            try:
                f.unlink()
            except Exception:
                pass
        cookie_args = ["--cookies", str(cookies)] if cookies and cookies.exists() else []
        cmd = [
            "yt-dlp", "--geo-bypass", "--no-check-certificates",
            "--extractor-args", f"youtube:player_client={','.join(pc)}",
            "-f", "bestaudio/best", "--extract-audio", "--audio-format", "wav",
            "-o", outtmpl, *cookie_args, url,
        ]
        try:
            proc = await asyncio.to_thread(
                subprocess.run, cmd, capture_output=True, text=True, timeout=300,
            )
            if proc.returncode == 0:
                wav = TEMP_DIR / f"{job_id}_raw.wav"
                if wav.exists():
                    wav.rename(output_path)
                    return output_path
                for f in TEMP_DIR.glob(f"{job_id}_raw.*"):
                    f.rename(output_path)
                    return output_path
        except Exception as exc:
            last_err = exc
            continue

    raise RuntimeError(f"All download strategies failed: {str(last_err)[:200]}")


# ── Endpoints ──

@app.get("/health")
async def health():
    yt_dlp_ok = shutil.which("yt-dlp") is not None
    ffmpeg_ok = shutil.which("ffmpeg") is not None
    return {
        "status": "ok",
        "yt_dlp": yt_dlp_ok,
        "ffmpeg": ffmpeg_ok,
        "temp_dir": str(TEMP_DIR),
    }


@app.post("/worker/resolve", response_model=ResolveResponse)
async def resolve(body: ResolveRequest, authorization: str | None = Header(default=None)):
    _check_secret(authorization)

    info = await _yt_dlp_resolve(body.url)
    if info is None:
        return ResolveResponse(error="Could not resolve YouTube URL")

    is_live = info.get("is_live", False) or info.get("live_status") == "is_live"
    title = info.get("title", "Unknown")

    hls_url = None
    if is_live:
        hls_url = info.get("manifest_url") or info.get("url")
        if not hls_url:
            for fmt in info.get("formats", []):
                if fmt.get("protocol") in ("m3u8", "m3u8_native") or "m3u8" in fmt.get("url", ""):
                    hls_url = fmt["url"]
                    break
            if not hls_url:
                for fmt in reversed(info.get("formats", [])):
                    if fmt.get("acodec") != "none":
                        hls_url = fmt["url"]
                        break

    return ResolveResponse(is_live=is_live, title=title, hls_url=hls_url)


@app.post("/worker/download-audio")
async def download_audio(body: DownloadRequest, authorization: str | None = Header(default=None)):
    """Download YouTube VOD audio and return WAV bytes."""
    _check_secret(authorization)

    try:
        audio_path = await _yt_dlp_download(body.url, body.job_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Download failed: {str(exc)[:300]}")

    try:
        audio_bytes = audio_path.read_bytes()
    finally:
        # Cleanup
        try:
            audio_path.unlink()
        except Exception:
            pass
        for f in TEMP_DIR.glob(f"{body.job_id}_*"):
            try:
                f.unlink()
            except Exception:
                pass

    return Response(
        content=audio_bytes,
        media_type="audio/wav",
        headers={"X-File-Size": str(len(audio_bytes))},
    )


@app.post("/worker/capture-chunk")
async def capture_chunk(body: CaptureChunkRequest, authorization: str | None = Header(default=None)):
    """Capture an HLS live audio chunk using FFmpeg and return WAV bytes."""
    _check_secret(authorization)

    ffmpeg_bin = shutil.which("ffmpeg")
    if not ffmpeg_bin:
        raise HTTPException(status_code=500, detail="FFmpeg not found on worker")

    chunk_id = str(uuid.uuid4())[:8]
    chunk_path = TEMP_DIR / f"chunk_{chunk_id}.wav"

    cmd = [
        ffmpeg_bin, "-y",
        "-headers", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36\r\n",
        "-i", body.hls_url,
        "-t", str(body.duration),
        "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
        str(chunk_path),
    ]

    try:
        proc = await asyncio.to_thread(
            subprocess.run, cmd, capture_output=True, text=True,
            timeout=body.duration + 30,
        )
        if proc.returncode != 0 or not chunk_path.exists() or chunk_path.stat().st_size == 0:
            raise HTTPException(
                status_code=500,
                detail=f"FFmpeg capture failed (rc={proc.returncode}): {(proc.stderr or '')[:200]}",
            )

        audio_bytes = chunk_path.read_bytes()
    finally:
        try:
            chunk_path.unlink()
        except Exception:
            pass

    return Response(
        content=audio_bytes,
        media_type="audio/wav",
        headers={"X-File-Size": str(len(audio_bytes))},
    )


# ── Run ──

if __name__ == "__main__":
    print(f"\n  VoxSentinel YouTube Media Worker")
    print(f"  Listening on http://0.0.0.0:{WORKER_PORT}")
    print(f"  Auth: {'enabled' if WORKER_SECRET else 'disabled (set WORKER_SECRET to secure)'}")
    print(f"  yt-dlp: {'found' if shutil.which('yt-dlp') else 'NOT FOUND'}")
    print(f"  FFmpeg: {'found' if shutil.which('ffmpeg') else 'NOT FOUND'}\n")

    uvicorn.run(app, host="0.0.0.0", port=WORKER_PORT)
