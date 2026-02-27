"""Shared fixtures for diarization service tests."""

from __future__ import annotations

import os
import sys
from types import ModuleType
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

# Use *append* to avoid shadowing other services' conftests.
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))

# ─── Mock heavy deps before any application code is imported ───

# pyannote.audio
_pyannote_mock = MagicMock(name="pyannote")
_pyannote_audio_mock = MagicMock(name="pyannote.audio")


class _FakeAnnotation:
    """Minimal stand-in for pyannote ``Annotation``."""

    def __init__(self, tracks: list[tuple[Any, str]] | None = None) -> None:
        self._tracks = tracks or []

    def itertracks(self, yield_label: bool = False):
        for turn, speaker in self._tracks:
            yield turn, "_", speaker


class _FakeTurn:
    """Minimal stand-in for pyannote ``Segment`` (a turn)."""

    def __init__(self, start: float, end: float) -> None:
        self.start = start
        self.end = end


# Store helpers on the mock so tests can build annotations easily.
_pyannote_audio_mock._FakeAnnotation = _FakeAnnotation
_pyannote_audio_mock._FakeTurn = _FakeTurn

_pipeline_cls = MagicMock(name="Pipeline")
_pipeline_cls.from_pretrained.return_value = MagicMock(name="pipeline_instance")
_pyannote_audio_mock.Pipeline = _pipeline_cls

sys.modules.setdefault("pyannote", _pyannote_mock)
sys.modules.setdefault("pyannote.audio", _pyannote_audio_mock)

# speechbrain
sys.modules.setdefault("speechbrain", MagicMock(name="speechbrain"))

# torch
_torch_mock = MagicMock(name="torch")
_torch_mock.cuda.is_available.return_value = False
_torch_mock.device.return_value = MagicMock()


def _from_numpy_fake(arr: Any) -> MagicMock:
    m = MagicMock()
    m.unsqueeze.return_value = m
    return m


_torch_mock.from_numpy = _from_numpy_fake
sys.modules.setdefault("torch", _torch_mock)
sys.modules.setdefault("torch.nn", MagicMock())
sys.modules.setdefault("torch.hub", MagicMock())

# numpy — lightweight, use real
import numpy  # noqa: E402, F401

# wave — stdlib, no mock needed
# io — stdlib, no mock needed

# Set env vars before any tg_common import.
os.environ.setdefault("TG_DB_URI", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("TG_REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("TG_API_HOST", "127.0.0.1")
os.environ.setdefault("TG_API_PORT", "8000")
os.environ.setdefault("TG_API_KEY", "test-key")
os.environ.setdefault("TG_HF_TOKEN", "hf_test_token")

# ─── Fixtures ────────────────────────────────────────────────────


@pytest.fixture()
def stream_id() -> str:
    return "12345678-1234-5678-1234-567812345678"


@pytest.fixture()
def session_id() -> str:
    return "87654321-4321-8765-4321-876543218765"


@pytest.fixture()
def mock_redis() -> AsyncMock:
    redis = AsyncMock()
    redis.connect = AsyncMock()
    redis.close = AsyncMock()
    redis.xadd = AsyncMock(return_value="1-0")
    redis.xread = AsyncMock(return_value=[])
    redis.publish = AsyncMock(return_value=1)
    redis.health_check = AsyncMock(return_value=True)
    return redis
