"""Shared fixtures for alerts service tests."""

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

# websockets
_websockets_mock = MagicMock(name="websockets")
_websockets_mock.ConnectionClosed = type("ConnectionClosed", (Exception,), {})
sys.modules.setdefault("websockets", _websockets_mock)

# slack_sdk
_slack_sdk_mock = MagicMock(name="slack_sdk")
_slack_webhook_mock = MagicMock(name="slack_sdk.webhook")
_slack_webhook_async_mock = MagicMock(name="slack_sdk.webhook.async_client")
_mock_async_webhook_cls = MagicMock(name="AsyncWebhookClient")
_slack_webhook_async_mock.AsyncWebhookClient = _mock_async_webhook_cls
sys.modules.setdefault("slack_sdk", _slack_sdk_mock)
sys.modules.setdefault("slack_sdk.webhook", _slack_webhook_mock)
sys.modules.setdefault("slack_sdk.webhook.async_client", _slack_webhook_async_mock)

# tenacity — lightweight, use real (it's pure-python)
import tenacity  # noqa: E402, F401

# celery
_celery_mock = MagicMock(name="celery")
_celery_mock.shared_task = lambda *a, **kw: (lambda fn: fn) if not a else a[0]
sys.modules.setdefault("celery", _celery_mock)

# httpx — lightweight, use real
import httpx  # noqa: E402, F401

# Set env vars before any tg_common import.
os.environ.setdefault("TG_DB_URI", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("TG_REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("TG_API_HOST", "127.0.0.1")
os.environ.setdefault("TG_API_PORT", "8000")
os.environ.setdefault("TG_API_KEY", "test-key")

# ─── Fixtures ────────────────────────────────────────────────────


@pytest.fixture()
def stream_id() -> str:
    return "12345678-1234-5678-1234-567812345678"


@pytest.fixture()
def session_id() -> str:
    return "87654321-4321-8765-4321-876543218765"


@pytest.fixture()
def mock_redis() -> AsyncMock:
    """Async mock standing in for a ``redis.asyncio.Redis`` instance."""
    redis = AsyncMock()
    redis.connect = AsyncMock()
    redis.close = AsyncMock()
    redis.set = AsyncMock(return_value=True)  # NX set succeeded
    redis.get = AsyncMock(return_value=None)
    redis.zadd = AsyncMock(return_value=1)
    redis.zcard = AsyncMock(return_value=0)
    redis.zremrangebyscore = AsyncMock(return_value=0)
    redis.expire = AsyncMock(return_value=True)
    redis.publish = AsyncMock(return_value=1)
    redis.health_check = AsyncMock(return_value=True)

    # Pipeline mock — returns itself and collects results.
    pipe = AsyncMock()
    pipe.zadd = MagicMock(return_value=pipe)
    pipe.zcard = MagicMock(return_value=pipe)
    pipe.zremrangebyscore = MagicMock(return_value=pipe)
    pipe.expire = MagicMock(return_value=pipe)
    pipe.execute = AsyncMock(return_value=[0, 0])  # [zremrangebyscore, zcard]
    redis.pipeline = MagicMock(return_value=pipe)

    return redis


@pytest.fixture()
def sample_alert(stream_id: str, session_id: str):
    """A fully-populated sample Alert for testing."""
    from tg_common.models.alert import Alert, AlertType, MatchType, Severity

    return Alert(
        session_id=session_id,
        stream_id=stream_id,
        alert_type=AlertType.KEYWORD,
        severity=Severity.HIGH,
        matched_rule="gun",
        match_type=MatchType.EXACT,
        matched_text="he has a gun",
        surrounding_context="suspect says he has a gun near the entrance",
        speaker_id="SPEAKER_01",
    )
