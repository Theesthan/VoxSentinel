"""
YouTube URL resolution router for VoxSentinel.

Resolves YouTube URLs (live or VOD) so the frontend can either:
- Start live transcription (for live broadcasts)
- Submit audio for file-analyze (for VODs)
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import tempfile
import uuid as _uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from api.dependencies import get_db_session, get_redis

logger = structlog.get_logger()

router = APIRouter(prefix="/youtube", tags=["youtube"])

UPLOAD_DIR = Path(tempfile.gettempdir()) / "voxsentinel_uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Ensure Deno is in PATH for yt-dlp JS challenge solving
_deno_bin = Path.home() / ".deno" / "bin"
if _deno_bin.is_dir() and str(_deno_bin) not in os.environ.get("PATH", ""):
    os.environ["PATH"] = str(_deno_bin) + os.pathsep + os.environ.get("PATH", "")

# Track active live transcription tasks so they can be stopped
_live_tasks: dict[str, asyncio.Task] = {}

# Proxy for yt-dlp — set YT_DLP_PROXY on Railway to bypass datacenter IP blocks.
# Accepts HTTP/HTTPS/SOCKS5 e.g. "socks5://user:pass@host:port" or "http://host:port"
_PROXY: str | None = os.getenv("YT_DLP_PROXY") or os.getenv("TG_YT_PROXY") or None
if _PROXY:
    logger.info("youtube_proxy_configured", proxy=_PROXY[:30] + "...")
else:
    logger.warning("youtube_no_proxy", hint="Set YT_DLP_PROXY env var for reliable YouTube on cloud")

# Public Invidious instances — used as fallback for live stream HLS URL
_INVIDIOUS_INSTANCES = [
    "https://inv.nadeko.net",
    "https://invidious.nerdvpn.de",
    "https://invidious.lunar.icu",
    "https://iv.melmac.space",
    "https://invidious.privacyredirect.com",
]


import re as _re


def _extract_video_id(url: str) -> str | None:
    """Extract an 11-char YouTube video ID from any YouTube URL format."""
    patterns = [
        r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/|youtube\.com/v/)([a-zA-Z0-9_-]{11})",
        r"youtube\.com/shorts/([a-zA-Z0-9_-]{11})",
        r"youtube\.com/live/([a-zA-Z0-9_-]{11})",
    ]
    for pattern in patterns:
        m = _re.search(pattern, url)
        if m:
            return m.group(1)
    return None


async def _get_yt_captions(url: str) -> list[dict] | None:
    """
    Fetch YouTube's auto-generated (or manual) captions via youtube-transcript-api.
    Works from cloud/datacenter IPs because it only fetches the page HTML and caption
    XML — not the restricted video/audio streams.
    Returns a list of {text, start_ms, end_ms} dicts, or None if unavailable.
    """
    video_id = _extract_video_id(url)
    if not video_id:
        return None
    try:
        from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled

        proxy_dict = {"https": _PROXY, "http": _PROXY} if _PROXY else None

        def _fetch():
            api = YouTubeTranscriptApi()
            # Try English first, then any available language
            try:
                segments = api.fetch(video_id, languages=["en", "en-US", "en-GB"])
            except Exception:
                # Fall back to whatever language is available
                transcript_list = api.list(video_id)
                transcript = transcript_list.find_generated_transcript(
                    [t.language_code for t in transcript_list]
                )
                segments = transcript.fetch()
            return list(segments)

        raw = await asyncio.to_thread(_fetch)
        if not raw:
            return None

        result = []
        for seg in raw:
            # youtube-transcript-api v0.6+ returns FetchedTranscriptSnippet objects
            if hasattr(seg, "text"):
                text = seg.text
                start_s = getattr(seg, "start", 0) or 0
                dur_s = getattr(seg, "duration", 2) or 2
            else:
                text = seg.get("text", "")
                start_s = seg.get("start", 0)
                dur_s = seg.get("duration", 2)
            result.append({
                "text": text.strip(),
                "start_ms": int(start_s * 1000),
                "end_ms": int((start_s + dur_s) * 1000),
            })
        logger.info("yt_captions_fetched", video_id=video_id, segments=len(result))
        return result
    except Exception as exc:
        logger.warning("yt_captions_failed", video_id=video_id, error=str(exc)[:200])
        return None


async def _invidious_get_stream_url(url: str) -> str | None:
    """
    Try multiple public Invidious instances to get an HLS manifest or audio URL.
    Used as last-resort fallback for live streams when yt-dlp fails on cloud IPs.
    """
    video_id = _extract_video_id(url)
    if not video_id:
        return None
    async with httpx.AsyncClient(timeout=httpx.Timeout(15.0)) as client:
        for instance in _INVIDIOUS_INSTANCES:
            try:
                resp = await client.get(
                    f"{instance}/api/v1/videos/{video_id}",
                    params={"fields": "hlsUrl,adaptiveFormats,formatStreams"},
                    headers={"User-Agent": "VoxSentinel/1.0"},
                )
                if resp.status_code != 200:
                    continue
                data = resp.json()

                # For live streams: hlsUrl is the direct HLS manifest
                hls = data.get("hlsUrl")
                if hls:
                    logger.info("invidious_hls_found",
                                instance=instance, video_id=video_id)
                    return hls

                # For VOD: pick best audio-only adaptive format
                for fmt in data.get("adaptiveFormats", []):
                    if "audio" in fmt.get("type", "") and fmt.get("url"):
                        logger.info("invidious_audio_url_found",
                                    instance=instance, video_id=video_id)
                        return fmt["url"]

                # Last resort: first formatStream URL
                streams = data.get("formatStreams", [])
                if streams and streams[0].get("url"):
                    return streams[0]["url"]

            except Exception as exc:
                logger.warning("invidious_instance_failed",
                               instance=instance, error=str(exc)[:100])
                continue
    return None


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
    Falls back to HTTP scraping if yt-dlp fails (e.g. bot detection).
    """
    import re as _re

    import httpx

    # --- Try yt-dlp first (multiple strategies) ---
    info = None
    for strategy in _yt_dlp_strategies():
        try:
            info = await asyncio.to_thread(_yt_dlp_extract, url, strategy)
            break
        except Exception:
            continue

    # --- Fallback: yt-dlp subprocess (handles bot challenges better on cloud) ---
    if info is None:
        logger.warning("yt_dlp_library_failed_trying_subprocess", url=url)
        info = await _yt_dlp_subprocess_extract(url)

    if info is not None:
        is_live = info.get("is_live", False) or info.get("live_status") == "is_live"
        title = info.get("title", "Unknown")

        hls_url = None
        if is_live:
            hls_url = info.get("manifest_url") or info.get("url")
            if not hls_url:
                for fmt in info.get("formats", []):
                    if fmt.get("protocol") in ("m3u8", "m3u8_native") or "m3u8" in (fmt.get("url", "")):
                        hls_url = fmt["url"]
                        break
            if not hls_url:
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

    # --- Fallback: HTTP scrape for liveness ---
    logger.warning("yt_dlp_failed_all_strategies", url=url)
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url, follow_redirects=True, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        })
        html = resp.text

    # Check for live indicators in page source
    is_live = bool(
        _re.search(r'"isLive"\s*:\s*true', html)
        or _re.search(r'"isLiveNow"\s*:\s*true', html)
        or _re.search(r'"liveBroadcastDetails"', html)
        or _re.search(r'"style"\s*:\s*"LIVE"', html)
    )

    # Extract title
    title_match = _re.search(r'"title"\s*:\s*"([^"]+)"', html)
    title = title_match.group(1) if title_match else "Unknown"

    return {
        "is_live": is_live,
        "title": title,
        "hls_url": None,  # Can't get HLS without yt-dlp
        "formats": [],
        "info": {},
    }


# Path to Netscape cookies file for YouTube authentication.
# Priority: TG_COOKIES_FILE env var → /app/cookies/vidcookie.txt → relative to repo root
def _find_cookies_file() -> Path:
    env_path = os.getenv("TG_COOKIES_FILE")
    if env_path:
        p = Path(env_path)
        if p.exists():
            return p
    # Docker: files are at /app/cookies/vidcookie.txt
    docker_path = Path("/app/cookies/vidcookie.txt")
    if docker_path.exists():
        return docker_path
    # Local dev: VoxSentinel root = 5 levels up from this file
    root = Path(__file__).resolve().parents[5]
    return root / "cookies" / "vidcookie.txt"

_COOKIES_FILE = _find_cookies_file()
logger.info("youtube_cookies", path=str(_COOKIES_FILE), exists=_COOKIES_FILE.exists())

# Player clients ordered by reliability on datacenter IPs.
# tv_embedded & mweb bypass PO-token checks that block cloud servers.
_PLAYER_CLIENTS: list[list[str]] = [
    ["tv_embedded"],
    ["mweb"],
    ["tv"],
    ["mediaconnect"],
    ["android"],
    ["web"],
]


def _base_opts(*, skip_download: bool = False) -> dict[str, Any]:
    """Shared yt-dlp options for every strategy."""
    opts: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "geo_bypass": True,
        "nocheckcertificate": True,
        "socket_timeout": 45,
        "retries": 5,
        "fragment_retries": 5,
        "skip_download": skip_download,
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
        },
    }
    if _COOKIES_FILE.exists():
        opts["cookiefile"] = str(_COOKIES_FILE)
    if _PROXY:
        opts["proxy"] = _PROXY
    return opts


def _yt_dlp_strategies() -> list[dict]:
    """Return a list of yt-dlp option dicts to try in order (resolve / info-only)."""
    base = {**_base_opts(skip_download=True), "format": "bestaudio/best"}
    strategies: list[dict] = []
    for pc in _PLAYER_CLIENTS:
        strategies.append({**base, "extractor_args": {"youtube": {"player_client": pc}}})
    # bare fallback (default client)
    strategies.append(base)
    return strategies


def _yt_dlp_extract(url: str, opts: dict) -> dict:
    """Run yt-dlp extract_info synchronously (called via to_thread)."""
    import yt_dlp

    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)


# ── Subprocess fallbacks (handle bot-checks better on cloud IPs) ─────────────


def _subprocess_cookie_args() -> list[str]:
    """Return ["--cookies", path] if the cookie file exists, else []."""
    if _COOKIES_FILE.exists():
        return ["--cookies", str(_COOKIES_FILE)]
    return []


def _subprocess_proxy_args() -> list[str]:
    """Return ["--proxy", url] if proxy is configured, else []."""
    if _PROXY:
        return ["--proxy", _PROXY]
    return []


async def _yt_dlp_subprocess_extract(url: str) -> dict | None:
    """Try yt-dlp as a subprocess — often bypasses library limitations on cloud."""
    for pc in _PLAYER_CLIENTS:
        cmd = [
            "yt-dlp",
            "--dump-json",
            "--no-download",
            "--geo-bypass",
            "--no-check-certificates",
            "--extractor-args", f"youtube:player_client={','.join(pc)}",
            "-f", "bestaudio/best",
            *_subprocess_cookie_args(),
            *_subprocess_proxy_args(),
            url,
        ]
        try:
            proc = await asyncio.to_thread(
                subprocess.run, cmd,
                capture_output=True, text=True, timeout=45,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                first_line = proc.stdout.strip().split("\n")[0]
                return json.loads(first_line)
        except Exception as exc:
            logger.warning("yt_subprocess_extract_failed",
                           client=pc, error=str(exc)[:120])
            continue
    return None


async def _get_stream_url_subprocess(url: str) -> str | None:
    """Get a playable stream/HLS URL using yt-dlp --get-url subprocess."""
    for pc in _PLAYER_CLIENTS:
        cmd = [
            "yt-dlp",
            "--get-url",
            "--geo-bypass",
            "--no-check-certificates",
            "--extractor-args", f"youtube:player_client={','.join(pc)}",
            "-f", "bestaudio/best",
            *_subprocess_cookie_args(),
            *_subprocess_proxy_args(),
            url,
        ]
        try:
            proc = await asyncio.to_thread(
                subprocess.run, cmd,
                capture_output=True, text=True, timeout=30,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                return proc.stdout.strip().split("\n")[0]
        except Exception as exc:
            logger.warning("yt_subprocess_geturl_failed",
                           client=pc, error=str(exc)[:120])
            continue
    return None


async def _download_youtube_audio_subprocess(
    url: str, job_id: str, output_path: Path,
) -> Path | None:
    """Fallback: download audio via yt-dlp subprocess."""
    outtmpl = str(UPLOAD_DIR / f"{job_id}_yt_raw.%(ext)s")
    for pc in _PLAYER_CLIENTS:
        # Clean up leftovers
        for f in UPLOAD_DIR.glob(f"{job_id}_yt_raw.*"):
            try:
                f.unlink()
            except Exception:
                pass

        cmd = [
            "yt-dlp",
            "--geo-bypass",
            "--no-check-certificates",
            "--extractor-args", f"youtube:player_client={','.join(pc)}",
            "-f", "bestaudio/best",
            "--extract-audio",
            "--audio-format", "wav",
            "-o", outtmpl,
            *_subprocess_cookie_args(),
            *_subprocess_proxy_args(),
            url,
        ]
        try:
            proc = await asyncio.to_thread(
                subprocess.run, cmd,
                capture_output=True, text=True, timeout=300,
            )
            if proc.returncode == 0:
                wav = UPLOAD_DIR / f"{job_id}_yt_raw.wav"
                if wav.exists():
                    wav.rename(output_path)
                    return output_path
                for f in UPLOAD_DIR.glob(f"{job_id}_yt_raw.*"):
                    f.rename(output_path)
                    return output_path
        except Exception as exc:
            logger.warning("yt_subprocess_download_failed",
                           client=pc, error=str(exc)[:150])
            continue
    return None


async def _download_youtube_audio(url: str, job_id: str) -> Path:
    """Download audio from a YouTube VOD using yt-dlp + FFmpeg.

    Tries multiple player-client strategies to work around YouTube's
    format restrictions on cloud/datacenter IPs.  Returns path to the
    downloaded WAV file.
    """
    import yt_dlp

    output_path = UPLOAD_DIR / f"{job_id}_yt_audio.wav"

    dl_base: dict[str, Any] = {
        **_base_opts(skip_download=False),
        "outtmpl": str(UPLOAD_DIR / f"{job_id}_yt_raw.%(ext)s"),
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
                "preferredquality": "0",
            }
        ],
    }

    # Build strategies: each player-client × three format selectors, then bare
    format_selectors = ["bestaudio/best", "bestaudio*", "best"]
    strategies: list[dict[str, Any]] = []
    for pc in _PLAYER_CLIENTS:
        for fmt in format_selectors:
            strategies.append({
                **dl_base,
                "format": fmt,
                "extractor_args": {"youtube": {"player_client": pc}},
            })
    # bare fallback (default client) with all format selectors
    for fmt in format_selectors:
        strategies.append({**dl_base, "format": fmt})
    # absolute last resort: no format key at all (downloads whatever is available)
    strategies.append({k: v for k, v in dl_base.items() if k != "format"})

    last_err: Exception | None = None
    for strat in strategies:
        # Clean up any leftover files from previous attempts
        for f in UPLOAD_DIR.glob(f"{job_id}_yt_raw.*"):
            try:
                f.unlink()
            except Exception:
                pass

        try:
            def _download(opts: dict = strat):
                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.download([url])

            await asyncio.to_thread(_download)

            # Find the output file (yt-dlp may name it differently)
            wav_pattern = UPLOAD_DIR / f"{job_id}_yt_raw.wav"
            if wav_pattern.exists():
                wav_pattern.rename(output_path)
                return output_path

            for f in UPLOAD_DIR.glob(f"{job_id}_yt_raw.*"):
                f.rename(output_path)
                return output_path

        except Exception as exc:
            last_err = exc
            logger.warning("yt_download_strategy_failed",
                           strategy=strat.get("extractor_args", "default"),
                           format=strat.get("format"),
                           cookies=bool(strat.get("cookiefile")),
                           error=str(exc)[:300])
            continue

    # Last resort: yt-dlp subprocess (handles bot-check challenges better)
    logger.info("yt_download_trying_subprocess_fallback", url=url)
    sub_result = await _download_youtube_audio_subprocess(url, job_id, output_path)
    if sub_result:
        return sub_result

    logger.error("yt_download_all_strategies_exhausted",
                 url=url, total_strategies=len(strategies),
                 last_error=str(last_err)[:300])
    raise RuntimeError(
        f"All yt-dlp download strategies failed: {str(last_err)[:200]}"
    )


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

    Strategy (in order):
    1. youtube-transcript-api — uses YouTube's caption endpoint (works on cloud IPs)
    2. yt-dlp audio download — requires a proxy on cloud; good quality + Deepgram ASR
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
    )
    from api.schemas.file_analyze_schemas import (
        FileAnalyzeSegment,
        FileAnalyzeAlert,
        FileAnalyzeSummary,
        FileAnalyzeSubmitResponse,
    )
    from tg_common.db.orm_models import SessionORM, StreamORM

    job_id = _uuid.uuid4()
    stream_id = _uuid.uuid4()
    session_id = _uuid.uuid4()
    now = _utc_now()

    # Resolve title
    try:
        result = await _resolve_youtube(body.url)
        title = result["title"]
    except Exception:
        title = "YouTube Video"

    display_name = f"[YouTube] {title}"

    # ── Create Stream + Session in DB ──
    stream = StreamORM(
        stream_id=stream_id,
        name=display_name,
        source_type="file",
        source_url=body.url,
        asr_backend="youtube_captions",
        status="active",
        session_id=session_id,
        metadata_={"job_id": str(job_id), "file_name": display_name, "youtube_url": body.url},
    )
    session = SessionORM(
        session_id=session_id,
        stream_id=stream_id,
        asr_backend_used="youtube_captions",
    )
    if db is not None:
        db.add(stream)
        db.add(session)
        await db.commit()

    # ── Register job immediately so frontend polling doesn't 404 ──
    _jobs[str(job_id)] = {
        "job_id": job_id,
        "stream_id": stream_id,
        "session_id": session_id,
        "status": "processing",
        "progress_pct": 10,
        "file_name": display_name,
        "created_at": now,
        "completed_at": None,
        "error_message": None,
        "transcript": [],
        "alerts": [],
        "summary": None,
    }
    job = _jobs[str(job_id)]

    # ── Strategy 1: youtube-transcript-api (captions — works on any IP) ──
    captions = await _get_yt_captions(body.url)
    if captions:
        logger.info("yt_captions_path_taken", job_id=str(job_id), segments=len(captions))
        job["progress_pct"] = 50

        # Convert captions to FileAnalyzeSegment list
        transcript_out: list[FileAnalyzeSegment] = []
        for cap in captions:
            transcript_out.append(FileAnalyzeSegment(
                segment_id=_uuid.uuid4(),
                speaker_id=None,
                start_offset_ms=cap["start_ms"],
                end_offset_ms=cap["end_ms"],
                text=cap["text"],
                confidence=1.0,
            ))

        # Run keyword matching on combined caption text
        db_factory = getattr(request.app.state, "db_session_factory", None)
        keyword_rules = await _load_keyword_rules(db_factory)
        alerts_out: list[FileAnalyzeAlert] = []
        if keyword_rules:
            combined = " ".join(c["text"] for c in captions)
            matches = _match_keywords(combined, keyword_rules)
            for m in matches:
                alerts_out.append(FileAnalyzeAlert(
                    alert_id=_uuid.uuid4(),
                    alert_type="keyword",
                    severity=m.get("severity", "medium"),
                    matched_rule=m.get("rule_id"),
                    match_type=m.get("match_type", "exact"),
                    matched_text=m.get("keyword"),
                    surrounding_context=combined[:200],
                    timestamp_offset_ms=0,
                ))

        summary = FileAnalyzeSummary(
            total_segments=len(transcript_out),
            total_alerts=len(alerts_out),
            sentiments={},
            speakers_detected=0,
            languages_detected=["en"],
        )

        completed = _utc_now()
        job["status"] = "completed"
        job["progress_pct"] = 100
        job["completed_at"] = completed
        job["duration_seconds"] = (completed - now).total_seconds()
        job["transcript"] = transcript_out
        job["alerts"] = alerts_out
        job["summary"] = summary

        return {
            "job_id": str(job_id),
            "stream_id": str(stream_id),
            "session_id": str(session_id),
            "status": "processing",
            "file_name": display_name,
            "created_at": now.isoformat(),
        }

    # ── Strategy 2: yt-dlp audio download + Deepgram (requires proxy on cloud) ──
    logger.info("yt_captions_unavailable_trying_download", job_id=str(job_id))
    job["progress_pct"] = 20
    try:
        audio_path = await _download_youtube_audio(body.url, str(job_id))
    except Exception as exc:
        job["status"] = "failed"
        job["error_message"] = (
            f"YouTube captions are not available for this video, and audio download "
            f"also failed (likely blocked on cloud): {str(exc)[:200]}"
        )
        logger.error("youtube_both_strategies_failed", url=body.url, error=str(exc)[:200])
        raise HTTPException(
            status_code=500,
            detail=job["error_message"],
        )

    # Audio downloaded — run through Deepgram pipeline
    job["progress_pct"] = 40
    db_factory = getattr(request.app.state, "db_session_factory", None)
    asyncio.create_task(
        _run_pipeline(
            str(job_id), audio_path, stream_id, session_id,
            "deepgram_nova2", redis,
            db_session_factory=db_factory,
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


# ────────────────────────────────────────────────────────
# YouTube Live Stream Transcription
# ────────────────────────────────────────────────────────


async def _load_keyword_rules(db_session_factory: Any) -> list[dict]:
    """Load enabled keyword rules from DB."""
    if db_session_factory is None:
        return []
    try:
        from sqlalchemy import select as sa_select
        from tg_common.db.orm_models import KeywordRuleORM

        async with db_session_factory() as _db:
            stmt = sa_select(KeywordRuleORM).where(KeywordRuleORM.enabled == True)
            res = await _db.execute(stmt)
            rows = res.scalars().all()
            return [
                {
                    "rule_id": str(r.rule_id),
                    "keyword": r.keyword,
                    "match_type": r.match_type,
                    "severity": r.severity,
                    "category": r.category,
                }
                for r in rows
            ]
    except Exception:
        logger.warning("keyword_rules_load_failed")
        return []


def _match_keywords(text: str, rules: list[dict]) -> list[dict]:
    """Match text against keyword rules. Returns list of matching rule dicts with metadata."""
    import re as _re

    text_lower = text.lower()
    matches: list[dict] = []
    for rule in rules:
        kw = rule["keyword"]
        hit = False
        if rule["match_type"] == "exact":
            hit = kw.lower() in text_lower
        elif rule["match_type"] == "regex":
            try:
                hit = bool(_re.search(kw, text, _re.IGNORECASE))
            except _re.error:
                pass
        elif rule["match_type"] == "fuzzy":
            kw_words = kw.lower().split()
            hit = all(w in text_lower for w in kw_words)
        elif rule["match_type"] == "phonetic":
            hit = kw.lower() in text_lower

        if hit:
            matches.append({
                "rule_id": rule["rule_id"],
                "keyword": kw,
                "match_type": rule["match_type"],
                "severity": rule.get("severity", "medium"),
                "category": rule.get("category", ""),
            })
    return matches


async def _publish_and_dispatch_alerts(
    matches: list[dict],
    text: str,
    stream_id: str,
    session_id: str,
    stream_name: str,
    redis: Any,
    db_session_factory: Any,
) -> None:
    """Publish keyword match events to Redis and dispatch to alert channels."""
    if not matches:
        return

    for m in matches:
        alert_id = str(_uuid.uuid4())
        alert_payload = {
            "alert_id": alert_id,
            "alert_type": "keyword",
            "severity": m["severity"],
            "matched_text": m["keyword"],
            "match_type": m["match_type"],
            "surrounding_context": text[:200],
            "stream_id": stream_id,
            "stream_name": stream_name,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # Publish to match_events channel for WebSocket alert feed
        if redis:
            await redis.publish(
                f"match_events:{stream_id}",
                json.dumps(alert_payload),
            )

        # Persist alert to DB
        if db_session_factory is not None:
            try:
                from tg_common.db.orm_models import AlertORM
                async with db_session_factory() as _db:
                    db_severity = (m["severity"] or "medium").lower()
                    if db_severity not in ("low", "medium", "high", "critical"):
                        db_severity = "medium"
                    db_match_type = m["match_type"] or "exact"
                    if db_match_type not in ("exact", "fuzzy", "regex", "sentiment_threshold", "intent"):
                        db_match_type = "exact"

                    alert_orm = AlertORM(
                        alert_id=_uuid.UUID(alert_id),
                        session_id=_uuid.UUID(session_id),
                        stream_id=_uuid.UUID(stream_id),
                        alert_type="keyword",
                        severity=db_severity,
                        matched_rule=m["rule_id"],
                        match_type=db_match_type,
                        matched_text=m["keyword"],
                        surrounding_context=text[:200],
                        asr_backend_used="deepgram_nova2",
                    )
                    _db.add(alert_orm)
                    await _db.commit()
            except Exception:
                logger.exception("alert_db_persist_error", alert_id=alert_id)

    # Dispatch to external channels (webhook, slack, email)
    await _dispatch_to_external_channels(matches, text, stream_name, db_session_factory)


async def _dispatch_to_external_channels(
    matches: list[dict],
    text: str,
    stream_name: str,
    db_session_factory: Any,
) -> None:
    """Send alerts to configured external channels (webhook, slack, email)."""
    if db_session_factory is None:
        return

    # Load enabled channels
    channels: list[dict] = []
    try:
        from sqlalchemy import select as sa_select
        from tg_common.db.orm_models import AlertChannelConfigORM

        async with db_session_factory() as _db:
            stmt = sa_select(AlertChannelConfigORM).where(AlertChannelConfigORM.enabled == True)
            res = await _db.execute(stmt)
            rows = res.scalars().all()
            channels = [
                {
                    "channel_id": str(r.channel_id),
                    "channel_type": str(r.channel_type),
                    "config": r.config or {},
                    "min_severity": str(r.min_severity) if r.min_severity else None,
                    "alert_types": r.alert_types,
                }
                for r in rows
            ]
    except Exception:
        logger.warning("external_channels_load_failed")
        return

    if not channels:
        return

    severity_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}

    for m in matches:
        alert_payload = {
            "alert_type": "keyword",
            "severity": m["severity"],
            "matched_text": m["keyword"],
            "match_type": m["match_type"],
            "surrounding_context": text[:200],
            "stream_name": stream_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        for ch in channels:
            min_sev = ch.get("min_severity")
            if min_sev and min_sev in severity_order:
                alert_sev = severity_order.get(m["severity"] or "medium", 1)
                if alert_sev < severity_order[min_sev]:
                    continue

            allowed_types = ch.get("alert_types")
            if allowed_types and "keyword" not in allowed_types:
                continue

            config = ch.get("config", {})
            ch_type = ch["channel_type"]

            try:
                if ch_type == "webhook":
                    url = config.get("webhook_url") or config.get("url", "")
                    if url:
                        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
                            await client.post(url, json=alert_payload)
                        logger.info("live_alert_dispatched_webhook",
                                    channel_id=ch["channel_id"],
                                    keyword=m["keyword"])

                elif ch_type == "slack":
                    webhook_url = config.get("webhook_url") or config.get("url", "")
                    if webhook_url:
                        slack_msg = {
                            "text": (
                                f":rotating_light: *VoxSentinel Live Alert*\n"
                                f"*Type:* keyword | *Severity:* {m['severity']}\n"
                                f"*Match:* {m['keyword']}\n"
                                f"*Stream:* {stream_name}\n"
                                f"*Context:* {text[:200]}"
                            ),
                        }
                        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
                            await client.post(webhook_url, json=slack_msg)
                        logger.info("live_alert_dispatched_slack",
                                    channel_id=ch["channel_id"],
                                    keyword=m["keyword"])

                elif ch_type == "email":
                    await _send_email_alert(config, m, text, stream_name)

            except Exception:
                logger.exception("live_alert_dispatch_error",
                                 channel_type=ch_type,
                                 channel_id=ch["channel_id"])


async def _send_email_alert(
    config: dict,
    match: dict,
    text: str,
    stream_name: str,
) -> None:
    """Send an alert email via SMTP. Config must contain smtp_host, smtp_port,
    smtp_user, smtp_password, from_address, to_address."""
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    smtp_host = config.get("smtp_host") or os.getenv("TG_SMTP_HOST", "")
    smtp_port = int(config.get("smtp_port") or os.getenv("TG_SMTP_PORT", "587"))
    smtp_user = config.get("smtp_user") or config.get("username") or os.getenv("TG_SMTP_USER", "")
    smtp_pass = config.get("smtp_password") or config.get("password") or os.getenv("TG_SMTP_PASSWORD", "")
    from_addr = config.get("from_address") or config.get("from") or os.getenv("TG_SMTP_FROM", smtp_user)
    to_addr = config.get("to_address") or config.get("to") or config.get("email_address", "")

    if not smtp_host or not to_addr:
        logger.warning("email_alert_missing_config",
                       has_host=bool(smtp_host), has_to=bool(to_addr))
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[VoxSentinel] {match['severity'].upper()} Alert: {match['keyword']}"
    msg["From"] = from_addr
    msg["To"] = to_addr

    body_text = (
        f"VoxSentinel Keyword Alert\n"
        f"========================\n\n"
        f"Severity: {match['severity']}\n"
        f"Keyword:  {match['keyword']}\n"
        f"Match Type: {match['match_type']}\n"
        f"Stream:   {stream_name}\n\n"
        f"Context:\n{text[:500]}\n\n"
        f"Time: {datetime.now(timezone.utc).isoformat()}\n"
    )

    body_html = (
        f"<h2 style='color:#dc2626'>VoxSentinel Alert</h2>"
        f"<table style='border-collapse:collapse'>"
        f"<tr><td><b>Severity:</b></td><td>{match['severity']}</td></tr>"
        f"<tr><td><b>Keyword:</b></td><td>{match['keyword']}</td></tr>"
        f"<tr><td><b>Match Type:</b></td><td>{match['match_type']}</td></tr>"
        f"<tr><td><b>Stream:</b></td><td>{stream_name}</td></tr>"
        f"</table>"
        f"<p><b>Context:</b><br>{text[:500]}</p>"
        f"<p style='color:#666;font-size:12px'>{datetime.now(timezone.utc).isoformat()}</p>"
    )

    msg.attach(MIMEText(body_text, "plain"))
    msg.attach(MIMEText(body_html, "html"))

    def _send():
        use_ssl = smtp_port == 465
        if use_ssl:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=15)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=15)
            server.ehlo()
            server.starttls()
            server.ehlo()
        if smtp_user and smtp_pass:
            server.login(smtp_user, smtp_pass)
        server.sendmail(from_addr, [to_addr], msg.as_string())
        server.quit()

    await asyncio.to_thread(_send)
    logger.info("email_alert_sent", to=to_addr, keyword=match["keyword"])


async def _live_transcribe_loop(
    stream_id: str,
    session_id: str,
    youtube_url: str,
    redis: Any,
    db_session_factory: Any = None,
) -> None:
    """Background task: capture audio from a YouTube live stream in chunks
    and send each chunk to Deepgram pre-recorded API for transcription.

    Results are published to Redis so the WebSocket relay can forward them
    to connected dashboard clients.
    """
    ffmpeg_bin = shutil.which("ffmpeg")
    if not ffmpeg_bin:
        logger.error("ffmpeg_not_found_for_live")
        if redis:
            await redis.publish(
                f"redacted_tokens:{stream_id}",
                json.dumps({"text": "[Error: FFmpeg not found]", "is_final": True}),
            )
        return

    api_key = os.getenv("TG_DEEPGRAM_API_KEY", "")
    if not api_key:
        logger.error("deepgram_key_missing_for_live")
        return

    # Resolve HLS URL from YouTube (library → subprocess fallbacks)
    hls_url = None
    try:
        result = await _resolve_youtube(youtube_url)
        if not result["is_live"]:
            if redis:
                await redis.publish(
                    f"redacted_tokens:{stream_id}",
                    json.dumps({"text": "[Stream is not live]", "is_final": True}),
                )
            return
        hls_url = result.get("hls_url")
    except Exception as exc:
        logger.exception("live_resolve_error", url=youtube_url)

    # Fallback: yt-dlp subprocess --get-url
    if not hls_url:
        logger.info("live_hls_fallback_subprocess", stream_id=stream_id)
        hls_url = await _get_stream_url_subprocess(youtube_url)

    # Fallback: Invidious API (free third-party YouTube frontend)
    if not hls_url:
        logger.info("live_hls_fallback_invidious", stream_id=stream_id)
        hls_url = await _invidious_get_stream_url(youtube_url)

    if not hls_url:
        err_msg = (
            "[Could not get YouTube stream URL. "
            "This is an IP-level block by YouTube on cloud servers. "
            "Set YT_DLP_PROXY to a residential proxy in Railway env vars.]"
        )
        if redis:
            await redis.publish(
                f"redacted_tokens:{stream_id}",
                json.dumps({"text": err_msg, "is_final": True}),
            )
        return

    logger.info("live_transcription_starting", stream_id=stream_id, hls_url=hls_url[:80])

    chunk_duration = 10  # seconds per chunk
    chunk_counter = 0

    # Load keyword rules once at start (reload periodically)
    keyword_rules = await _load_keyword_rules(db_session_factory)
    rules_refresh_counter = 0

    try:
        while True:
            # Check if task has been cancelled
            if asyncio.current_task() and asyncio.current_task().cancelled():
                break

            chunk_path = UPLOAD_DIR / f"live_{stream_id}_{chunk_counter}.wav"
            try:
                # Use FFmpeg to capture a chunk of audio from the HLS stream
                # If a proxy is configured, route FFmpeg through it too
                ffmpeg_env = os.environ.copy()
                if _PROXY:
                    ffmpeg_env["http_proxy"] = _PROXY
                    ffmpeg_env["https_proxy"] = _PROXY

                cmd = [
                    ffmpeg_bin,
                    "-y",
                    "-headers", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36\r\n",
                    "-i", hls_url,
                    "-t", str(chunk_duration),
                    "-vn",
                    "-acodec", "pcm_s16le",
                    "-ar", "16000",
                    "-ac", "1",
                    str(chunk_path),
                ]

                proc = await asyncio.to_thread(
                    subprocess.run, cmd, capture_output=True, text=True,
                    timeout=chunk_duration + 30,
                    env=ffmpeg_env,
                )

                if proc.returncode != 0 or not chunk_path.exists() or chunk_path.stat().st_size == 0:
                    logger.warning("live_chunk_capture_failed",
                                   rc=proc.returncode, stderr=proc.stderr[:200] if proc.stderr else "")
                    # Brief pause before retry
                    await asyncio.sleep(2)
                    chunk_counter += 1
                    continue

                # Send chunk to Deepgram pre-recorded API
                audio_data = await asyncio.to_thread(chunk_path.read_bytes)

                async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
                    resp = await client.post(
                        "https://api.deepgram.com/v1/listen",
                        headers={
                            "Authorization": f"Token {api_key}",
                            "Content-Type": "audio/wav",
                        },
                        params={
                            "model": "nova-2",
                            "smart_format": "true",
                            "diarize": "true",
                            "utterances": "true",
                            "punctuate": "true",
                        },
                        content=audio_data,
                    )
                    resp.raise_for_status()
                    dg_result = resp.json()

                # Parse results and publish to Redis
                results = dg_result.get("results", {})
                utterances = results.get("utterances") or []
                published_count = 0
                chunk_texts: list[str] = []

                if utterances:
                    for utt in utterances:
                        speaker = utt.get("speaker")
                        text = utt.get("transcript", "").strip()
                        if text:
                            chunk_texts.append(text)
                            if redis:
                                await redis.publish(
                                    f"redacted_tokens:{stream_id}",
                                    json.dumps({
                                        "text": text,
                                        "speaker_id": f"speaker_{speaker}" if speaker is not None else None,
                                        "is_final": True,
                                        "confidence": utt.get("confidence", 0),
                                    }),
                                )
                                published_count += 1
                else:
                    # Try channels fallback
                    channels = results.get("channels") or []
                    if channels:
                        try:
                            alt = channels[0]["alternatives"][0]
                            text = alt.get("transcript", "").strip()
                            if text:
                                chunk_texts.append(text)
                                if redis:
                                    await redis.publish(
                                        f"redacted_tokens:{stream_id}",
                                        json.dumps({
                                            "text": text,
                                            "is_final": True,
                                            "confidence": alt.get("confidence", 0),
                                        }),
                                    )
                                    published_count += 1
                        except (KeyError, IndexError):
                            pass

                # ── Keyword matching on this chunk ──
                if chunk_texts and keyword_rules:
                    combined_text = " ".join(chunk_texts)
                    matches = _match_keywords(combined_text, keyword_rules)
                    if matches:
                        logger.info("live_keyword_match",
                                    stream_id=stream_id,
                                    chunk=chunk_counter,
                                    keywords=[m["keyword"] for m in matches])
                        await _publish_and_dispatch_alerts(
                            matches, combined_text,
                            stream_id, session_id,
                            stream_name=f"[YT Live] {youtube_url[:50]}",
                            redis=redis,
                            db_session_factory=db_session_factory,
                        )

                # Refresh rules every 30 chunks (~5 min)
                rules_refresh_counter += 1
                if rules_refresh_counter >= 30:
                    keyword_rules = await _load_keyword_rules(db_session_factory)
                    rules_refresh_counter = 0

                logger.info(
                    "live_chunk_transcribed",
                    stream_id=stream_id,
                    chunk=chunk_counter,
                    tokens_published=published_count,
                )
                chunk_counter += 1

            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.exception("live_chunk_error", stream_id=stream_id, chunk=chunk_counter)
                await asyncio.sleep(3)
                chunk_counter += 1
            finally:
                # Cleanup chunk file
                try:
                    if chunk_path.exists():
                        chunk_path.unlink()
                except Exception:
                    pass

    except asyncio.CancelledError:
        logger.info("live_transcription_cancelled", stream_id=stream_id)
    except Exception:
        logger.exception("live_transcription_fatal", stream_id=stream_id)
    finally:
        # Clean up task reference
        _live_tasks.pop(stream_id, None)
        logger.info("live_transcription_stopped", stream_id=stream_id)


class YouTubeLiveRequest(BaseModel):
    url: str = Field(..., description="YouTube live stream URL")
    name: str = Field(default="", description="Optional stream name")


@router.post("/live-transcribe")
async def start_live_transcription(
    request: Request,
    body: YouTubeLiveRequest,
    db: Any = Depends(get_db_session),
    redis: Any = Depends(get_redis),
) -> dict:
    """Start live transcription of a YouTube live stream.

    Resolves the URL, checks it's live, then starts a background task
    that captures audio in chunks and transcribes via Deepgram.
    Returns stream_id for WebSocket subscription.
    """
    if not _is_youtube_url(body.url):
        raise HTTPException(status_code=400, detail="URL does not appear to be a YouTube link")

    # Quick liveness check
    try:
        result = await _resolve_youtube(body.url)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not resolve YouTube URL: {str(exc)[:200]}")

    if not result["is_live"]:
        raise HTTPException(
            status_code=400,
            detail="This YouTube stream is not currently live. Use 'Download & Analyze' for recorded videos.",
        )

    from tg_common.db.orm_models import SessionORM, StreamORM

    stream_id = _uuid.uuid4()
    session_id = _uuid.uuid4()
    title = result.get("title", "YouTube Live")
    display_name = body.name or f"[YT Live] {title}"

    # Create Stream + Session in DB
    stream = StreamORM(
        stream_id=stream_id,
        name=display_name,
        source_type="hls",  # YouTube live is delivered via HLS
        source_url=body.url,
        asr_backend="deepgram_nova2",
        status="active",
        session_id=session_id,
        metadata_={"youtube_url": body.url, "title": title, "is_live": True, "stream_type": "youtube_live"},
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

    # Start background live transcription
    db_factory = getattr(request.app.state, "db_session_factory", None)
    task = asyncio.create_task(
        _live_transcribe_loop(
            str(stream_id), str(session_id), body.url, redis,
            db_session_factory=db_factory,
        )
    )
    _live_tasks[str(stream_id)] = task

    return {
        "stream_id": str(stream_id),
        "session_id": str(session_id),
        "name": display_name,
        "title": title,
        "is_live": True,
        "status": "active",
    }


@router.post("/stop-live/{stream_id}")
async def stop_live_transcription(
    stream_id: str,
    db: Any = Depends(get_db_session),
) -> dict:
    """Stop a running YouTube live transcription."""
    task = _live_tasks.get(stream_id)
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        _live_tasks.pop(stream_id, None)

    # Update stream status in DB
    if db is not None:
        from sqlalchemy import select
        from tg_common.db.orm_models import StreamORM

        result = await db.execute(
            select(StreamORM).where(StreamORM.stream_id == _uuid.UUID(stream_id))
        )
        stream = result.scalar_one_or_none()
        if stream:
            stream.status = "stopped"
            await db.commit()

    return {"status": "stopped", "stream_id": stream_id}


@router.get("/live-status/{stream_id}")
async def get_live_status(stream_id: str) -> dict:
    """Check if a YouTube live transcription is still running."""
    task = _live_tasks.get(stream_id)
    is_running = task is not None and not task.done()
    return {"stream_id": stream_id, "is_running": is_running}


@router.get("/diagnostics")
async def youtube_diagnostics() -> dict:
    """Debug endpoint — check YouTube/yt-dlp configuration on this instance."""
    import yt_dlp

    yt_dlp_version = getattr(yt_dlp.version, "__version__", "unknown")
    ffmpeg_path = shutil.which("ffmpeg")

    # Quick test: can yt-dlp list formats for a known public video?
    test_note = ""
    if _PROXY:
        test_note = f"Proxy configured: {_PROXY[:25]}..."
    else:
        test_note = "NO PROXY — YouTube will likely block datacenter IPs. Set YT_DLP_PROXY env var."

    return {
        "cookies_path": str(_COOKIES_FILE),
        "cookies_exists": _COOKIES_FILE.exists(),
        "cookies_size_bytes": _COOKIES_FILE.stat().st_size if _COOKIES_FILE.exists() else 0,
        "yt_dlp_version": yt_dlp_version,
        "ffmpeg_available": ffmpeg_path is not None,
        "ffmpeg_path": ffmpeg_path,
        "proxy": _PROXY[:30] + "..." if _PROXY else None,
        "note": test_note,
        "player_clients": _PLAYER_CLIENTS,
        "active_live_tasks": list(_live_tasks.keys()),
    }
