"""Shared fixtures for ingestion service tests."""

from __future__ import annotations

import os
import sys
import uuid
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock

import pytest

# ── Mock the ``av`` module so tests can import ingestion.audio_extractor ──
# PyAV requires FFmpeg DLLs at import time; on CI / Windows without FFmpeg
# the import would fail.  We pre-populate sys.modules with a lightweight
# mock before any application code is imported.

_av_mock = MagicMock()
_av_audio = MagicMock()
_av_audio_resampler = MagicMock()
_av_mock.audio = _av_audio
_av_mock.audio.resampler = _av_audio_resampler

# Make `import av` / `import av.audio.resampler` work.
sys.modules.setdefault("av", _av_mock)
sys.modules.setdefault("av.audio", _av_audio)
sys.modules.setdefault("av.audio.resampler", _av_audio_resampler)
sys.modules.setdefault("av.container", MagicMock())
sys.modules.setdefault("av.error", MagicMock())

# Set env vars before any tg_common import so Settings doesn't error.
os.environ.setdefault("TG_DB_URI", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("TG_REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("TG_API_HOST", "127.0.0.1")
os.environ.setdefault("TG_API_PORT", "8000")


@pytest.fixture()
def stream_id() -> uuid.UUID:
    """A deterministic stream UUID for tests."""
    return uuid.UUID("12345678-1234-5678-1234-567812345678")


@pytest.fixture()
def session_id() -> uuid.UUID:
    """A deterministic session UUID for tests."""
    return uuid.UUID("abcdefab-cdef-abcd-efab-cdefabcdefab")


@pytest.fixture()
def mock_redis() -> AsyncMock:
    """A mock RedisClient with async methods."""
    redis = AsyncMock()
    redis.connect = AsyncMock()
    redis.close = AsyncMock()
    redis.xadd = AsyncMock(return_value="1-0")
    redis.publish = AsyncMock(return_value=1)
    redis.health_check = AsyncMock(return_value=True)
    return redis
