"""Shared fixtures for VAD service tests."""

from __future__ import annotations

import os
import sys
import uuid
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock

import pytest

# ── Mock ``torch`` before any application code is imported ──
# PyTorch is large and may not be installed in a lightweight test env.
_torch_mock = MagicMock()
_torch_nn = MagicMock()
_torch_mock.nn = _torch_nn
_torch_mock.nn.Module = MagicMock
_torch_mock.no_grad.return_value.__enter__ = MagicMock(return_value=None)
_torch_mock.no_grad.return_value.__exit__ = MagicMock(return_value=False)
_torch_mock.from_numpy = MagicMock(return_value=MagicMock())

sys.modules.setdefault("torch", _torch_mock)
sys.modules.setdefault("torch.nn", _torch_nn)
sys.modules.setdefault("torch.hub", MagicMock())

# Set env vars before any tg_common import so Settings doesn't error.
os.environ.setdefault("TG_DB_URI", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("TG_REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("TG_API_HOST", "127.0.0.1")
os.environ.setdefault("TG_API_PORT", "8000")
os.environ.setdefault("TG_VAD_THRESHOLD", "0.5")


@pytest.fixture()
def stream_id() -> str:
    """A deterministic stream UUID string for tests."""
    return "12345678-1234-5678-1234-567812345678"


@pytest.fixture()
def session_id() -> str:
    """A deterministic session UUID string for tests."""
    return "abcdefab-cdef-abcd-efab-cdefabcdefab"


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
def mock_vad_model() -> MagicMock:
    """A mock SileroVADModel with a configurable classify return value."""
    model = MagicMock()
    model.is_loaded = True
    model.classify = AsyncMock(return_value=0.85)
    model.classify_sync = MagicMock(return_value=0.85)
    model.load = MagicMock()
    model.reset_states = MagicMock()
    return model
