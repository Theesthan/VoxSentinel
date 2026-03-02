"""
YouTube URL resolution router for VoxSentinel.

Resolves YouTube URLs (live or VOD) so the frontend can either:
- Create an HLS stream (for live broadcasts)
- Submit audio for file-analyze (for VODs)
"""

from __future__ import annotations

import asyncio
import os
import tempfile
import uuid as _uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from api.dependencies import get_db_session, get_redis

logger = structlog.get_logger()

router = APIRouter(prefix="/youtube", tags=["youtube"])

UPLOAD_DIR = Path(tempfile.gettempdir()) / "voxsentinel_uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class YouTubeResolveRequest(BaseModel):
    url: str = Field(..., description="YouTube video or live stream URL")


class YouTubeResolveResponse(BaseModel):
    is_live: bool
    title: str
    hls_url: str | None = None
    message: str


def _is_youtube_url(url: str) -> bool:
    """Check if URL looks like a YouTube link."""
    return any(
        domain in url.lower()
        for domain in ["youtube.com", "youtu.be", "youtube-nocookie.com"]
    )


async def _resolve_youtube(url: str) -> dict:
    """Use yt-dlp to extract info about a YouTube URL.

    Returns a dict with keys: is_live, title, hls_url (if live).
    """
    import yt_dlp

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "format": "bestaudio/best",
    }

    def _extract():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)

    info = await asyncio.to_thread(_extract)

    is_live = info.get("is_live", False) or info.get("live_status") == "is_live"
    title = info.get("title", "Unknown")

    hls_url = None
    if is_live:
        # Try to get the HLS manifest URL
        hls_url = info.get("manifest_url") or info.get("url")
        if not hls_url:
            # Fall back to formats with m3u8
            for fmt in info.get("formats", []):
                if fmt.get("protocol") == "m3u8" or "m3u8" in (fmt.get("url", "")):
                    hls_url = fmt["url"]
                    break
                if fmt.get("protocol") == "m3u8_native":
                    hls_url = fmt["url"]
                    break
        if not hls_url:
            # Last resort: get any format URL
            for fmt in reversed(info.get("formats", [])):
                if fmt.get("acodec") != "none":
                    hls_url = fmt["url"]
                    break

    return {
        "is_live": is_live,
        "title": title,
        "hls_url": hls_url,
        "formats": info.get("formats", []),
        "info": info,
    }


async def _download_youtube_audio(url: str, job_id: str) -> Path:
    """Download audio from a YouTube VOD using yt-dlp + FFmpeg.

    Returns path to the downloaded audio file.
    """
    import yt_dlp

    output_path = UPLOAD_DIR / f"{job_id}_yt_audio.wav"
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "format": "bestaudio/best",
        "outtmpl": str(UPLOAD_DIR / f"{job_id}_yt_raw.%(ext)s"),
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
                "preferredquality": "0",
            }
        ],
    }

    def _download():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

    await asyncio.to_thread(_download)

    # Find the output file (yt-dlp may name it differently)
    wav_pattern = UPLOAD_DIR / f"{job_id}_yt_raw.wav"
    if wav_pattern.exists():
        wav_pattern.rename(output_path)
    else:
        # Search for any file starting with the pattern
        for f in UPLOAD_DIR.glob(f"{job_id}_yt_raw.*"):
            f.rename(output_path)
            break
        else:
            raise RuntimeError("yt-dlp did not produce an audio output file")

    return output_path


@router.post("/resolve", response_model=YouTubeResolveResponse)
async def resolve_youtube_url(
    body: YouTubeResolveRequest,
) -> YouTubeResolveResponse:
    """Resolve a YouTube URL to determine if it's live or VOD.

    For live streams, returns the HLS URL that can be used to create a stream.
    For VODs, returns info so the frontend can trigger a file-analyze download.
    """
    if not _is_youtube_url(body.url):
        raise HTTPException(
            status_code=400,
            detail="URL does not appear to be a YouTube link",
        )

    try:
        result = await _resolve_youtube(body.url)
    except Exception as exc:
        logger.exception("youtube_resolve_error", url=body.url)
        raise HTTPException(
            status_code=400,
            detail=f"Could not resolve YouTube URL: {str(exc)[:200]}",
        )

    if result["is_live"]:
        return YouTubeResolveResponse(
            is_live=True,
            title=result["title"],
            hls_url=result["hls_url"],
            message="Live stream detected. Use the HLS URL to create a stream.",
        )
    else:
        return YouTubeResolveResponse(
            is_live=False,
            title=result["title"],
            hls_url=None,
            message="VOD detected. Use 'Download & Analyze' to transcribe.",
        )


@router.post("/download-analyze")
async def download_and_analyze(
    request: Request,
    body: YouTubeResolveRequest,
    db: Any = Depends(get_db_session),
    redis: Any = Depends(get_redis),
) -> dict:
    """Download a YouTube VOD's audio and submit it for file analysis.

    Returns the job_id for polling status.
    """
    if not _is_youtube_url(body.url):
        raise HTTPException(
            status_code=400,
            detail="URL does not appear to be a YouTube link",
        )

    # Import file_analyze internals
    from api.routers.file_analyze import (
        _jobs,
        _run_pipeline,
        _utc_now,
        FileAnalyzeSubmitResponse,
    )
    from tg_common.db.orm_models import SessionORM, StreamORM

    job_id = _uuid.uuid4()
    stream_id = _uuid.uuid4()
    session_id = _uuid.uuid4()
    now = _utc_now()

    # Resolve title first
    try:
        result = await _resolve_youtube(body.url)
        title = result["title"]
    except Exception:
        title = "YouTube Video"

    try:
        audio_path = await _download_youtube_audio(body.url, str(job_id))
    except Exception as exc:
        logger.exception("youtube_download_error", url=body.url)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to download YouTube audio: {str(exc)[:200]}",
        )

    display_name = f"[YouTube] {title}"

    # Create Stream + Session in DB
    stream = StreamORM(
        stream_id=stream_id,
        name=display_name,
        source_type="file",
        source_url=body.url,
        asr_backend="deepgram_nova2",
        status="active",
        session_id=session_id,
        metadata_={"job_id": str(job_id), "file_name": display_name, "youtube_url": body.url},
    )
    session = SessionORM(
        session_id=session_id,
        stream_id=stream_id,
        asr_backend_used="deepgram_nova2",
    )
    if db is not None:
        db.add(stream)
        db.add(session)
        await db.commit()

    # Store job metadata
    _jobs[str(job_id)] = {
        "job_id": job_id,
        "stream_id": stream_id,
        "session_id": session_id,
        "status": "queued",
        "progress_pct": 0,
        "file_name": display_name,
        "created_at": now,
        "completed_at": None,
        "error_message": None,
        "transcript": [],
        "alerts": [],
        "summary": None,
    }

    # Start background processing
    db_factory = getattr(request.app.state, "db_session_factory", None)
    es = getattr(request.app.state, "es_client", None)
    asyncio.create_task(
        _run_pipeline(
            str(job_id), audio_path, stream_id, session_id,
            "deepgram_nova2", redis,
            db_session_factory=db_factory,
            es_client=es,
        ),
    )

    return {
        "job_id": str(job_id),
        "stream_id": str(stream_id),
        "session_id": str(session_id),
        "status": "processing",
        "file_name": display_name,
        "created_at": now.isoformat(),
    }
