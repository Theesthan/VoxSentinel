"""
File Analyze API router for VoxSentinel.

Provides endpoints to upload audio/video files for asynchronous analysis.
Uses Deepgram's pre-recorded (batch) REST API for reliable file
transcription with speaker diarization.

Video files (.mp4, .mkv, .avi, .mov, .webm, .flv) have their audio track
extracted via FFmpeg before submission to Deepgram.

Jobs are tracked in an in-process dict (sufficient for single-instance
API gateway). For multi-instance deployments, move to Redis or DB.
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
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel

from api.dependencies import get_db_session, get_redis
from api.schemas.file_analyze_schemas import (
    FileAnalyzeAlert,
    FileAnalyzeJobSummary,
    FileAnalyzeKeywordHit,
    FileAnalyzeListResponse,
    FileAnalyzeSegment,
    FileAnalyzeStatusResponse,
    FileAnalyzeSubmitResponse,
    FileAnalyzeSummary,
)

from tg_common.db.orm_models import AlertChannelConfigORM, AlertORM, SessionORM, StreamORM, TranscriptSegmentORM

logger = structlog.get_logger()

router = APIRouter(prefix="/file-analyze", tags=["file-analyze"])

# ── In-process job store ──
# Maps job_id (str) → job dict
_jobs: dict[str, dict[str, Any]] = {}

UPLOAD_DIR = Path(tempfile.gettempdir()) / "voxsentinel_uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Audio MIME type mapping for Deepgram
_MIME_MAP: dict[str, str] = {
    ".wav": "audio/wav",
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".ogg": "audio/ogg",
    ".flac": "audio/flac",
    ".aac": "audio/aac",
    ".wma": "audio/x-ms-wma",
}

# Video extensions that need audio extraction via FFmpeg
_VIDEO_EXTENSIONS: set[str] = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".wmv", ".ts", ".m4v"}

# All allowed upload extensions
_ALLOWED_EXTENSIONS: set[str] = set(_MIME_MAP.keys()) | _VIDEO_EXTENSIONS


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _find_ffmpeg() -> str | None:
    """Return the path to ffmpeg executable, or None."""
    return shutil.which("ffmpeg")


async def _dispatch_alerts_to_channels(
    alerts_out: list[FileAnalyzeAlert],
    stream_name: str,
    db_session_factory: Any,
) -> None:
    """Dispatch alerts to all enabled alert channels (webhook, slack, email).

    Loads configured channels from DB and sends alert payloads to each one.
    """
    if not alerts_out or db_session_factory is None:
        return

    channels: list[dict] = []
    try:
        from sqlalchemy import select as sa_select
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
        logger.warning("dispatch_channels_load_failed")
        return

    if not channels:
        return

    severity_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}

    for alert in alerts_out:
        alert_payload = {
            "alert_id": str(alert.alert_id),
            "alert_type": alert.alert_type,
            "severity": alert.severity,
            "matched_text": alert.matched_text,
            "match_type": alert.match_type,
            "speaker_id": alert.speaker_id,
            "surrounding_context": alert.surrounding_context,
            "stream_name": stream_name,
            "timestamp": _utc_now().isoformat(),
        }

        for ch in channels:
            # Check severity filter
            min_sev = ch.get("min_severity")
            if min_sev and min_sev in severity_order:
                alert_sev = severity_order.get(alert.severity or "medium", 1)
                if alert_sev < severity_order[min_sev]:
                    continue

            # Check alert type filter
            allowed_types = ch.get("alert_types")
            if allowed_types and alert.alert_type not in allowed_types:
                continue

            config = ch.get("config", {})
            ch_type = ch["channel_type"]

            try:
                if ch_type == "webhook":
                    url = config.get("webhook_url") or config.get("url", "")
                    if url:
                        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
                            await client.post(url, json=alert_payload)
                        logger.info("alert_dispatched_webhook",
                                    channel_id=ch["channel_id"],
                                    alert_id=str(alert.alert_id))

                elif ch_type == "slack":
                    webhook_url = config.get("webhook_url") or config.get("url", "")
                    if webhook_url:
                        slack_msg = {
                            "text": (
                                f":rotating_light: *VoxSentinel Alert*\n"
                                f"*Type:* {alert.alert_type} | *Severity:* {alert.severity}\n"
                                f"*Match:* {alert.matched_text}\n"
                                f"*Stream:* {stream_name}\n"
                                f"*Context:* {(alert.surrounding_context or '')[:200]}"
                            ),
                        }
                        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
                            await client.post(webhook_url, json=slack_msg)
                        logger.info("alert_dispatched_slack",
                                    channel_id=ch["channel_id"],
                                    alert_id=str(alert.alert_id))

                elif ch_type == "email":
                    email_addr = config.get("email_address") or config.get("to", "") or config.get("to_address", "")
                    smtp_host = config.get("smtp_host") or os.getenv("TG_SMTP_HOST", "")
                    if smtp_host and email_addr:
                        # Use real SMTP email sending
                        from api.routers.youtube import _send_email_alert
                        match_info = {
                            "keyword": alert.matched_text or "",
                            "severity": alert.severity or "medium",
                            "match_type": alert.match_type or "exact",
                        }
                        try:
                            await _send_email_alert(config, match_info, alert.surrounding_context or "", stream_name)
                            logger.info("alert_dispatched_email",
                                        channel_id=ch["channel_id"],
                                        email=email_addr)
                        except Exception:
                            logger.exception("alert_email_send_error",
                                             channel_id=ch["channel_id"],
                                             email=email_addr)
                    else:
                        logger.info("alert_dispatch_email_skipped",
                                    channel_id=ch["channel_id"],
                                    email=email_addr,
                                    reason="smtp_host not configured in channel config")

            except Exception:
                logger.exception("alert_dispatch_error",
                                 channel_type=ch_type,
                                 channel_id=ch["channel_id"])


async def _extract_audio_from_video(video_path: Path, job_id: str) -> Path:
    """Extract audio track from a video file using FFmpeg.

    Returns path to a temporary WAV file containing the extracted audio.
    Raises RuntimeError if FFmpeg fails.
    """
    ffmpeg_bin = _find_ffmpeg()
    if not ffmpeg_bin:
        raise RuntimeError(
            "FFmpeg is not installed or not on PATH. "
            "Video file upload requires FFmpeg for audio extraction."
        )

    audio_path = UPLOAD_DIR / f"{job_id}_audio.wav"
    cmd = [
        ffmpeg_bin,
        "-i", str(video_path),
        "-vn",                    # no video
        "-acodec", "pcm_s16le",   # 16-bit PCM WAV
        "-ar", "16000",           # 16 kHz sample rate (good for speech)
        "-ac", "1",               # mono
        "-y",                     # overwrite
        str(audio_path),
    ]

    logger.info("ffmpeg_extract_start", job_id=job_id, cmd=" ".join(cmd))

    proc = await asyncio.to_thread(
        subprocess.run, cmd, capture_output=True, text=True, timeout=600,
    )
    if proc.returncode != 0:
        logger.error("ffmpeg_extract_failed", stderr=proc.stderr[:500])
        raise RuntimeError(f"FFmpeg audio extraction failed: {proc.stderr[:300]}")

    if not audio_path.exists() or audio_path.stat().st_size == 0:
        raise RuntimeError("FFmpeg produced empty audio output")

    logger.info(
        "ffmpeg_extract_done",
        job_id=job_id,
        audio_size=audio_path.stat().st_size,
    )
    return audio_path


async def _run_pipeline(
    job_id: str,
    file_path: Path,
    stream_id: _uuid.UUID,
    session_id: _uuid.UUID,
    asr_backend: str,
    redis: Any,
    db_session_factory: Any = None,
) -> None:
    """Background task: send audio to Deepgram pre-recorded API and
    collect transcript with speaker diarization.

    For video files the audio track is first extracted via FFmpeg.
    """
    job = _jobs[job_id]
    audio_tmp: Path | None = None   # temp WAV from video extraction

    try:
        job["status"] = "processing"
        job["progress_pct"] = 10

        ext = file_path.suffix.lower()

        # ── 1. If video, extract audio first ──
        if ext in _VIDEO_EXTENSIONS:
            logger.info("file_analyze_video_detected", job_id=job_id, ext=ext)
            job["progress_pct"] = 15
            audio_tmp = await _extract_audio_from_video(file_path, job_id)
            audio_data = await asyncio.to_thread(audio_tmp.read_bytes)
            mimetype = "audio/wav"
        else:
            audio_data = await asyncio.to_thread(file_path.read_bytes)
            mimetype = _MIME_MAP.get(ext, "audio/wav")

        logger.info(
            "file_analyze_start",
            job_id=job_id,
            size=len(audio_data),
            mime=mimetype,
        )
        job["progress_pct"] = 20

        # ── 2. Call Deepgram pre-recorded REST API ──
        api_key = os.getenv("TG_DEEPGRAM_API_KEY", "")
        if not api_key:
            raise RuntimeError("TG_DEEPGRAM_API_KEY not configured")

        job["progress_pct"] = 30

        async with httpx.AsyncClient(timeout=httpx.Timeout(300.0)) as client:
            resp = await client.post(
                "https://api.deepgram.com/v1/listen",
                headers={
                    "Authorization": f"Token {api_key}",
                    "Content-Type": mimetype,
                },
                params={
                    "model": "nova-2",
                    "smart_format": "true",
                    "diarize": "true",
                    "utterances": "true",
                    "punctuate": "true",
                    "detect_language": "true",
                },
                content=audio_data,
            )
            resp.raise_for_status()
            dg_result = resp.json()

        logger.info("file_analyze_deepgram_done", job_id=job_id)
        job["progress_pct"] = 80

        # ── 3. Parse Deepgram response ──
        results = dg_result.get("results", {})
        utterances = results.get("utterances") or []
        channels = results.get("channels") or []

        transcript_out: list[FileAnalyzeSegment] = []

        if utterances:
            # Prefer utterance-level output (has speaker diarization)
            for utt in utterances:
                speaker_raw = utt.get("speaker")
                transcript_out.append(
                    FileAnalyzeSegment(
                        segment_id=_uuid.uuid4(),
                        speaker_id=f"speaker_{speaker_raw}" if speaker_raw is not None else None,
                        start_offset_ms=int(float(utt.get("start", 0)) * 1000),
                        end_offset_ms=int(float(utt.get("end", 0)) * 1000),
                        text=utt.get("transcript", ""),
                        confidence=float(utt.get("confidence", 0.0)),
                        keywords_matched=[],
                    )
                )
        elif channels:
            # Fallback: group words into sentences from channel data
            try:
                alt = channels[0]["alternatives"][0]
                words = alt.get("words") or []
                current_words: list[dict] = []
                for w in words:
                    current_words.append(w)
                    pw = w.get("punctuated_word", w.get("word", ""))
                    if pw and pw[-1] in ".!?":
                        text = " ".join(
                            cw.get("punctuated_word", cw.get("word", ""))
                            for cw in current_words
                        )
                        spk = current_words[0].get("speaker")
                        transcript_out.append(
                            FileAnalyzeSegment(
                                segment_id=_uuid.uuid4(),
                                speaker_id=f"speaker_{spk}" if spk is not None else None,
                                start_offset_ms=int(float(current_words[0].get("start", 0)) * 1000),
                                end_offset_ms=int(float(current_words[-1].get("end", 0)) * 1000),
                                text=text,
                                confidence=sum(cw.get("confidence", 0) for cw in current_words) / max(len(current_words), 1),
                                keywords_matched=[],
                            )
                        )
                        current_words = []
                # Remaining words
                if current_words:
                    text = " ".join(
                        cw.get("punctuated_word", cw.get("word", ""))
                        for cw in current_words
                    )
                    spk = current_words[0].get("speaker")
                    transcript_out.append(
                        FileAnalyzeSegment(
                            segment_id=_uuid.uuid4(),
                            speaker_id=f"speaker_{spk}" if spk is not None else None,
                            start_offset_ms=int(float(current_words[0].get("start", 0)) * 1000),
                            end_offset_ms=int(float(current_words[-1].get("end", 0)) * 1000),
                            text=text,
                            confidence=sum(cw.get("confidence", 0) for cw in current_words) / max(len(current_words), 1),
                            keywords_matched=[],
                        )
                    )
            except Exception:
                logger.exception("file_analyze_channel_parse_error")

        # ── 4. Keyword matching ──
        job["progress_pct"] = 85
        alerts_out: list[FileAnalyzeAlert] = []

        # Fetch enabled rules from DB (simple approach — no heavy NLP engine needed)
        keyword_rules: list[dict] = []
        try:
            if db_session_factory is not None:
                from sqlalchemy import select as sa_select
                async with db_session_factory() as _db:
                    from tg_common.db.orm_models import KeywordRuleORM
                    stmt = sa_select(KeywordRuleORM).where(KeywordRuleORM.enabled == True)
                    res = await _db.execute(stmt)
                    rows = res.scalars().all()
                    keyword_rules = [
                        {
                            "rule_id": str(r.rule_id),
                            "keyword": r.keyword,
                            "match_type": r.match_type,
                            "severity": r.severity,
                            "category": r.category,
                            "fuzzy_threshold": r.fuzzy_threshold,
                        }
                        for r in rows
                    ]
                    logger.info("file_analyze_rules_loaded", count=len(keyword_rules))
        except Exception:
            logger.warning("file_analyze_rules_load_skipped", reason="Could not load rules from DB")

        # Match keywords against each segment
        import re as _re
        for seg in transcript_out:
            seg_text_lower = seg.text.lower()
            matched: list[FileAnalyzeKeywordHit] = []
            for rule in keyword_rules:
                kw = rule["keyword"]
                hit = False
                if rule["match_type"] == "exact":
                    hit = kw.lower() in seg_text_lower
                elif rule["match_type"] == "regex":
                    try:
                        hit = bool(_re.search(kw, seg.text, _re.IGNORECASE))
                    except _re.error:
                        pass
                elif rule["match_type"] == "fuzzy":
                    # Simple fuzzy: check if keyword words appear close together
                    kw_words = kw.lower().split()
                    hit = all(w in seg_text_lower for w in kw_words)
                elif rule["match_type"] == "phonetic":
                    hit = kw.lower() in seg_text_lower  # fallback to exact

                if hit:
                    matched.append(
                        FileAnalyzeKeywordHit(
                            keyword=kw,
                            match_type=rule["match_type"],
                            severity=rule["severity"],
                        )
                    )
                    # Create alert for each match
                    alerts_out.append(
                        FileAnalyzeAlert(
                            alert_id=_uuid.uuid4(),
                            alert_type="keyword",
                            severity=rule["severity"],
                            matched_rule=rule["rule_id"],
                            match_type=rule["match_type"],
                            matched_text=kw,
                            speaker_id=seg.speaker_id,
                            surrounding_context=seg.text[:200],
                            timestamp_offset_ms=seg.start_offset_ms,
                        )
                    )
            seg.keywords_matched = matched

        # ── 4b. Stream transcript segments to frontend via Redis (word-by-word) ──
        if redis and stream_id:
            try:
                delay = 0.03 if len(transcript_out) < 80 else 0.015
                for seg in transcript_out:
                    words = seg.text.split()
                    for wi, word in enumerate(words):
                        await redis.publish(
                            f"redacted_tokens:{stream_id}",
                            json.dumps({
                                "text": word,
                                "speaker_id": seg.speaker_id or "unknown",
                                "is_final": wi == len(words) - 1,
                                "is_word": True,
                                "confidence": seg.confidence,
                                "start_offset_ms": seg.start_offset_ms,
                            }),
                        )
                        await asyncio.sleep(delay)
                # signal end-of-transcript
                await redis.publish(
                    f"redacted_tokens:{stream_id}",
                    json.dumps({"type": "complete", "text": "", "is_final": True}),
                )
                logger.info("file_analyze_streamed_to_redis", job_id=job_id,
                            words_streamed=sum(len(s.text.split()) for s in transcript_out))
            except Exception:
                logger.warning("file_analyze_redis_stream_error", job_id=job_id)

        job["progress_pct"] = 95

        # ── 5. Build summary ──
        speakers: set[str] = set()
        for seg in transcript_out:
            if seg.speaker_id:
                speakers.add(seg.speaker_id)

        # Detect language from response metadata
        detected_lang = "en"
        try:
            detected_lang = channels[0]["detected_language"] if channels else "en"
        except (KeyError, IndexError):
            pass

        summary = FileAnalyzeSummary(
            total_segments=len(transcript_out),
            total_alerts=len(alerts_out),
            sentiments={},
            speakers_detected=len(speakers),
            languages_detected=[detected_lang] if detected_lang else ["en"],
        )

        # ── 6. Persist TranscriptSegmentORM + AlertORM to DB ──
        if db_session_factory is not None:
            try:
                async with db_session_factory() as db_sess:
                    base_time = _utc_now()
                    for seg in transcript_out:
                        seg_orm = TranscriptSegmentORM(
                            segment_id=seg.segment_id,
                            session_id=session_id,
                            stream_id=stream_id,
                            speaker_id=seg.speaker_id or "unknown",
                            start_time=base_time,
                            end_time=base_time,
                            start_offset_ms=seg.start_offset_ms,
                            end_offset_ms=seg.end_offset_ms,
                            text_redacted=seg.text,
                            text_original=seg.text,
                            language=detected_lang or "en",
                            asr_backend=asr_backend,
                            asr_confidence=seg.confidence,
                            sentiment_label=seg.sentiment_label,
                            sentiment_score=seg.sentiment_score,
                        )
                        db_sess.add(seg_orm)

                    for alert in alerts_out:
                        # Map alert_type: pipeline uses "keyword_match" but DB enum expects "keyword"
                        db_alert_type = "keyword"
                        if alert.alert_type in ("keyword", "sentiment", "compliance", "intent"):
                            db_alert_type = alert.alert_type

                        # Map match_type: ensure it's a valid DB enum value
                        db_match_type = alert.match_type or "exact"
                        if db_match_type not in ("exact", "fuzzy", "regex", "sentiment_threshold", "intent"):
                            db_match_type = "exact"

                        # Map severity
                        db_severity = (alert.severity or "medium").lower()
                        if db_severity not in ("low", "medium", "high", "critical"):
                            db_severity = "medium"

                        alert_orm = AlertORM(
                            alert_id=alert.alert_id,
                            session_id=session_id,
                            stream_id=stream_id,
                            alert_type=db_alert_type,
                            severity=db_severity,
                            matched_rule=alert.matched_rule or "",
                            match_type=db_match_type,
                            matched_text=alert.matched_text or "",
                            surrounding_context=alert.surrounding_context or "",
                            speaker_id=alert.speaker_id,
                            asr_backend_used=asr_backend,
                        )
                        db_sess.add(alert_orm)
                    await db_sess.commit()
                logger.info("file_analyze_db_persisted", job_id=job_id,
                            segments=len(transcript_out), alerts=len(alerts_out))
            except Exception:
                logger.exception("file_analyze_db_persist_error", job_id=job_id)

        # ── 6b. Dispatch alerts to configured channels ──
        if alerts_out:
            try:
                stream_name = job.get("file_name", "")
                await _dispatch_alerts_to_channels(alerts_out, stream_name, db_session_factory)
            except Exception:
                logger.exception("file_analyze_alert_dispatch_error", job_id=job_id)

        job["status"] = "completed"
        job["progress_pct"] = 100
        completed = _utc_now()
        job["completed_at"] = completed
        # Calculate duration
        created = job.get("created_at")
        if created and completed:
            job["duration_seconds"] = (completed - created).total_seconds()
        job["transcript"] = transcript_out
        job["alerts"] = alerts_out
        job["summary"] = summary

        logger.info(
            "file_analyze_complete",
            job_id=job_id,
            segments=len(transcript_out),
            speakers=len(speakers),
            alerts=len(alerts_out),
        )

    except Exception as exc:
        logger.exception("file_analyze_pipeline_error", job_id=job_id)
        job["status"] = "failed"
        job["error_message"] = str(exc)
    finally:
        # Cleanup temp files
        for p in (file_path, audio_tmp):
            try:
                if p and p.exists():
                    p.unlink()
            except Exception:
                pass


@router.post("", status_code=202, response_model=FileAnalyzeSubmitResponse)
async def submit_file(
    request: Request,
    file: UploadFile = File(...),
    name: str = Form(default=""),
    asr_backend: str = Form(default="deepgram_nova2"),
    keyword_rule_sets: str = Form(default=""),
    db: Any = Depends(get_db_session),
    redis: Any = Depends(get_redis),
) -> FileAnalyzeSubmitResponse:
    """Upload an audio or video file and start asynchronous analysis.

    Supported formats:
    - Audio: .wav, .mp3, .m4a, .ogg, .flac, .aac, .wma
    - Video: .mp4, .mkv, .avi, .mov, .webm, .flv, .wmv, .ts, .m4v
      (audio is extracted via FFmpeg before transcription)
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    # Validate file extension
    ext = Path(file.filename).suffix.lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(_ALLOWED_EXTENSIONS))}",
        )

    # Save uploaded file to temp directory
    job_id = _uuid.uuid4()
    stream_id = _uuid.uuid4()
    session_id = _uuid.uuid4()
    now = _utc_now()

    safe_name = file.filename.replace("/", "_").replace("\\", "_")
    file_path = UPLOAD_DIR / f"{job_id}_{safe_name}"

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    display_name = name or file.filename or "unnamed"

    # Create Stream + Session in DB
    stream = StreamORM(
        stream_id=stream_id,
        name=f"[File] {display_name}",
        source_type="file",
        source_url=str(file_path),
        asr_backend=asr_backend,
        status="active",
        session_id=session_id,
        metadata_={"job_id": str(job_id), "file_name": display_name},
    )
    session = SessionORM(
        session_id=session_id,
        stream_id=stream_id,
        asr_backend_used=asr_backend,
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
    asyncio.create_task(
        _run_pipeline(
            str(job_id), file_path, stream_id, session_id, asr_backend, redis,
            db_session_factory=db_factory,
        ),
    )

    return FileAnalyzeSubmitResponse(
        job_id=job_id,
        stream_id=stream_id,
        session_id=session_id,
        status="processing",
        file_name=display_name,
        created_at=now,
    )


@router.get("/{job_id}", response_model=FileAnalyzeStatusResponse)
async def get_job_status(job_id: _uuid.UUID) -> FileAnalyzeStatusResponse:
    """Get the status and results of a file analysis job."""
    job = _jobs.get(str(job_id))
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    return FileAnalyzeStatusResponse(
        job_id=job["job_id"],
        status=job["status"],
        progress_pct=job["progress_pct"],
        file_name=job["file_name"],
        stream_id=job.get("stream_id"),
        session_id=job.get("session_id"),
        duration_seconds=job.get("duration_seconds"),
        created_at=job["created_at"],
        completed_at=job.get("completed_at"),
        error_message=job.get("error_message"),
        transcript=job.get("transcript", []),
        alerts=job.get("alerts", []),
        summary=job.get("summary"),
    )


@router.get("", response_model=FileAnalyzeListResponse)
async def list_jobs(
    status: str | None = None,
    limit: int = 20,
) -> FileAnalyzeListResponse:
    """List all file analysis jobs."""
    all_jobs = list(_jobs.values())

    if status:
        all_jobs = [j for j in all_jobs if j["status"] == status]

    # Sort by created_at descending
    all_jobs.sort(key=lambda j: j["created_at"], reverse=True)
    all_jobs = all_jobs[:limit]

    summaries = [
        FileAnalyzeJobSummary(
            job_id=j["job_id"],
            status=j["status"],
            file_name=j["file_name"],
            duration_seconds=j.get("duration_seconds"),
            total_alerts=len(j.get("alerts", [])),
            created_at=j["created_at"],
            completed_at=j.get("completed_at"),
        )
        for j in all_jobs
    ]
    return FileAnalyzeListResponse(jobs=summaries, total=len(summaries))


# ────────────────────────────────────────────────────────
# AI Keyword Suggestion (Groq Llama 3.3 70B)
# ────────────────────────────────────────────────────────

class _SuggestedKeyword(BaseModel):
    keyword: str
    severity: str = "medium"
    reason: str = ""
    category: str = "general"
    match_type: str = "exact"


class SuggestKeywordsResponse(BaseModel):
    job_id: str
    suggestions: list[_SuggestedKeyword]


@router.post("/{job_id}/suggest-keywords", response_model=SuggestKeywordsResponse)
async def suggest_keywords(job_id: _uuid.UUID) -> SuggestKeywordsResponse:
    """Use Groq LLM (Llama 3.3 70B) to extract keyword suggestions from a
    completed transcript.  Returns keywords with severity and reason so the
    user can click to add them as rules.
    """
    job = _jobs.get(str(job_id))
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Job not completed yet")

    transcript: list[FileAnalyzeSegment] = job.get("transcript", [])
    if not transcript:
        return SuggestKeywordsResponse(job_id=str(job_id), suggestions=[])

    # Build transcript text for the LLM (cap at ~6000 chars to stay within context)
    full_text = "\n".join(
        f"[{seg.speaker_id or '?'}] {seg.text}" for seg in transcript
    )
    if len(full_text) > 6000:
        full_text = full_text[:6000] + "\n... (truncated)"

    groq_key = os.getenv("GROQ_API_KEY", "")
    if not groq_key:
        raise HTTPException(
            status_code=503,
            detail="GROQ_API_KEY not configured — cannot suggest keywords",
        )

    prompt = (
        "You are an expert analyst. Given the following transcript, extract "
        "the most important and notable keywords/phrases that would be useful "
        "for monitoring and alerting. For each keyword, assign:\n"
        "- severity: low, medium, high, or critical\n"
        "- category: e.g. security, compliance, legislation, finance, general, "
        "  medical, profanity, threat, sentiment, topic\n"
        "- match_type: 'exact' for specific terms, 'fuzzy' for concepts that "
        "  might appear in varied forms, 'regex' only if a pattern is needed\n"
        "- reason: brief explanation of why this keyword matters\n\n"
        "Return ONLY valid JSON — an array of objects with keys: "
        "keyword, severity, category, match_type, reason.\n"
        "Return 5-15 keywords. Focus on domain-specific, actionable terms.\n\n"
        f"TRANSCRIPT:\n{full_text}"
    )

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {groq_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 2000,
                    "response_format": {"type": "json_object"},
                },
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        logger.exception("groq_suggest_keywords_error")
        raise HTTPException(status_code=502, detail=f"Groq API error: {str(exc)[:200]}")

    # Parse LLM response
    try:
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        # Handle both {"keywords": [...]} and direct [...]
        items = parsed if isinstance(parsed, list) else parsed.get("keywords", parsed.get("suggestions", []))
        suggestions = []
        for item in items:
            if isinstance(item, dict) and "keyword" in item:
                sev = item.get("severity", "medium").lower()
                if sev not in ("low", "medium", "high", "critical"):
                    sev = "medium"
                mt = item.get("match_type", "exact").lower()
                if mt not in ("exact", "fuzzy", "regex"):
                    mt = "exact"
                suggestions.append(_SuggestedKeyword(
                    keyword=item["keyword"],
                    severity=sev,
                    reason=item.get("reason", ""),
                    category=item.get("category", "general"),
                    match_type=mt,
                ))
    except Exception:
        logger.warning("groq_response_parse_error", content=str(data)[:300])
        return SuggestKeywordsResponse(job_id=str(job_id), suggestions=[])

    logger.info("suggest_keywords_success", job_id=str(job_id), count=len(suggestions))
    return SuggestKeywordsResponse(job_id=str(job_id), suggestions=suggestions)
