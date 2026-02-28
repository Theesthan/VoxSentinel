"""Shared fixtures for ASR service tests."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

# Make helpers in this module importable from test files
# (needed with --import-mode=importlib).
sys.path.insert(0, str(Path(__file__).resolve().parent))

# ─── Mock heavy SDKs before any application code is imported ───

# Deepgram SDK
_deepgram_mock = MagicMock(name="deepgram")
_deepgram_mock.DeepgramClient = MagicMock(name="DeepgramClient")
_deepgram_mock.LiveTranscriptionEvents = MagicMock(name="LiveTranscriptionEvents")
_deepgram_mock.LiveTranscriptionEvents.Transcript = "Transcript"
_deepgram_mock.LiveTranscriptionEvents.Error = "Error"
_deepgram_mock.LiveTranscriptionEvents.Close = "Close"
_deepgram_mock.LiveOptions = MagicMock(name="LiveOptions")
sys.modules.setdefault("deepgram", _deepgram_mock)

# faster-whisper
_faster_whisper_mock = MagicMock(name="faster_whisper")
_faster_whisper_mock.WhisperModel = MagicMock(name="WhisperModel")
sys.modules.setdefault("faster_whisper", _faster_whisper_mock)

# torch (for Whisper CUDA detection)
_torch_mock = MagicMock(name="torch")
_torch_mock.cuda.is_available.return_value = False
sys.modules.setdefault("torch", _torch_mock)
sys.modules.setdefault("torch.nn", MagicMock())
sys.modules.setdefault("torch.hub", MagicMock())

# numpy — use real if available, otherwise mock
try:
    import numpy  # noqa: F401
except ImportError:
    sys.modules.setdefault("numpy", MagicMock(name="numpy"))

# circuitbreaker — lightweight, use real
# (already in deps)

# Set env vars before any tg_common import.
os.environ.setdefault("TG_DB_URI", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("TG_REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("TG_API_HOST", "127.0.0.1")
os.environ.setdefault("TG_API_PORT", "8000")
os.environ.setdefault("TG_DEEPGRAM_API_KEY", "test-api-key")
os.environ.setdefault("TG_ASR_DEFAULT_BACKEND", "deepgram_nova2")
os.environ.setdefault("TG_ASR_FALLBACK_BACKEND", "whisper_v3_turbo")

# ─── Fixtures ────────────────────────────────────────────────


@pytest.fixture()
def stream_id() -> str:
    """A deterministic stream UUID string for tests."""
    return "12345678-1234-5678-1234-567812345678"


@pytest.fixture()
def mock_redis() -> AsyncMock:
    """A mock RedisClient with async methods."""
    redis = AsyncMock()
    redis.connect = AsyncMock()
    redis.close = AsyncMock()
    redis.xadd = AsyncMock(return_value="1-0")
    redis.xread = AsyncMock(return_value=[])
    redis.publish = AsyncMock(return_value=1)
    redis.health_check = AsyncMock(return_value=True)
    return redis


@pytest.fixture()
def sample_pcm_bytes() -> bytes:
    """Small 16-bit PCM chunk (280 ms at 16 kHz mono = 8960 bytes)."""
    return b"\x00\x01" * 4480


@pytest.fixture()
def large_pcm_bytes() -> bytes:
    """3 seconds of 16-bit PCM at 16 kHz mono = 96000 bytes."""
    return b"\x00\x02" * 48000


@pytest.fixture()
def mock_deepgram_connection() -> AsyncMock:
    """A mock Deepgram asynclive connection."""
    conn = AsyncMock()
    conn.start = AsyncMock(return_value=True)
    conn.send = AsyncMock()
    conn.finish = AsyncMock()
    conn.on = MagicMock()
    return conn


@pytest.fixture()
def mock_deepgram_client(mock_deepgram_connection: AsyncMock) -> MagicMock:
    """A mock DeepgramClient that yields the mock connection."""
    client = MagicMock()
    client.listen.asynclive.v.return_value = mock_deepgram_connection
    return client


def make_deepgram_result(
    *,
    transcript: str = "hello world",
    confidence: float = 0.95,
    is_final: bool = True,
    start: float = 0.0,
    duration: float = 1.0,
    words: list[dict[str, Any]] | None = None,
) -> MagicMock:
    """Build a mock Deepgram LiveResultResponse."""
    if words is None:
        words = [
            {"word": "hello", "start": 0.0, "end": 0.5, "confidence": 0.98},
            {"word": "world", "start": 0.6, "end": 1.0, "confidence": 0.92},
        ]

    word_objs = []
    for w in words:
        wo = MagicMock()
        wo.word = w["word"]
        wo.start = w["start"]
        wo.end = w["end"]
        wo.confidence = w["confidence"]
        word_objs.append(wo)

    alt = MagicMock()
    alt.transcript = transcript
    alt.confidence = confidence
    alt.words = word_objs

    channel = MagicMock()
    channel.alternatives = [alt]

    result = MagicMock()
    result.channel = channel
    result.is_final = is_final
    result.start = start
    result.duration = duration
    return result


@pytest.fixture()
def deepgram_result() -> MagicMock:
    """A default mock Deepgram transcript result."""
    return make_deepgram_result()


def make_whisper_segment(
    *,
    text: str = " hello world",
    start: float = 0.0,
    end: float = 1.0,
    words: list[dict[str, Any]] | None = None,
) -> MagicMock:
    """Build a mock faster-whisper Segment."""
    if words is None:
        words = [
            {"word": " hello", "start": 0.0, "end": 0.5, "probability": 0.97},
            {"word": " world", "start": 0.6, "end": 1.0, "probability": 0.93},
        ]

    word_objs = []
    for w in words:
        wo = MagicMock()
        wo.word = w["word"]
        wo.start = w["start"]
        wo.end = w["end"]
        wo.probability = w["probability"]
        word_objs.append(wo)

    seg = MagicMock()
    seg.text = text
    seg.start = start
    seg.end = end
    seg.words = word_objs
    return seg


def make_whisper_info(*, language: str = "en") -> MagicMock:
    """Build a mock faster-whisper TranscriptionInfo."""
    info = MagicMock()
    info.language = language
    return info
