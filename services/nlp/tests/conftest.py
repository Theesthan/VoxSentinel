"""Shared fixtures for NLP service tests."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

# Make helpers in this module importable from test files
# (needed with --import-mode=importlib).
# Use *append* (not insert-0) to avoid shadowing other services' conftests.
sys.path.append(str(Path(__file__).resolve().parent))

# ─── Mock heavy deps before any application code is imported ───

# transformers (HuggingFace)
_transformers_mock = MagicMock(name="transformers")


def _mock_pipeline(*args: Any, **kwargs: Any) -> MagicMock:
    """Return a callable mock that simulates HF pipeline output."""
    pipe = MagicMock(name="sentiment_pipeline")
    pipe.return_value = [{"label": "POSITIVE", "score": 0.95}]
    return pipe


_transformers_mock.pipeline = _mock_pipeline
sys.modules.setdefault("transformers", _transformers_mock)

# presidio_analyzer
_presidio_analyzer_mock = MagicMock(name="presidio_analyzer")
_analyzer_engine_cls = MagicMock(name="AnalyzerEngine")
_presidio_analyzer_mock.AnalyzerEngine = _analyzer_engine_cls
sys.modules.setdefault("presidio_analyzer", _presidio_analyzer_mock)
sys.modules.setdefault("presidio_analyzer.nlp_engine", MagicMock())

# presidio_anonymizer
_presidio_anonymizer_mock = MagicMock(name="presidio_anonymizer")
_anonymizer_engine_cls = MagicMock(name="AnonymizerEngine")
_presidio_anonymizer_mock.AnonymizerEngine = _anonymizer_engine_cls

# OperatorConfig mock
_operator_config_mock = MagicMock(name="OperatorConfig")
_entities_mock = MagicMock(name="presidio_anonymizer.entities")
_entities_mock.OperatorConfig = _operator_config_mock
_presidio_anonymizer_mock.entities = _entities_mock
sys.modules.setdefault("presidio_anonymizer", _presidio_anonymizer_mock)
sys.modules.setdefault("presidio_anonymizer.entities", _entities_mock)

# spacy
sys.modules.setdefault("spacy", MagicMock(name="spacy"))

# torch
_torch_mock = MagicMock(name="torch")
_torch_mock.cuda.is_available.return_value = False
sys.modules.setdefault("torch", _torch_mock)
sys.modules.setdefault("torch.nn", MagicMock())
sys.modules.setdefault("torch.hub", MagicMock())

# ahocorasick — lightweight, use real if installed; else mock
try:
    import ahocorasick  # noqa: F401
except ImportError:
    _ac_mock = MagicMock(name="ahocorasick")
    sys.modules.setdefault("ahocorasick", _ac_mock)

# rapidfuzz — lightweight, use real if installed; else mock
try:
    from rapidfuzz import fuzz  # noqa: F401
except ImportError:
    _rf_mock = MagicMock(name="rapidfuzz")
    _rf_fuzz_mock = MagicMock(name="rapidfuzz.fuzz")
    _rf_fuzz_mock.token_set_ratio = MagicMock(return_value=100.0)
    _rf_mock.fuzz = _rf_fuzz_mock
    sys.modules.setdefault("rapidfuzz", _rf_mock)
    sys.modules.setdefault("rapidfuzz.fuzz", _rf_fuzz_mock)

# Set env vars before any tg_common import.
os.environ.setdefault("TG_DB_URI", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("TG_REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("TG_API_HOST", "127.0.0.1")
os.environ.setdefault("TG_API_PORT", "8000")
os.environ.setdefault("TG_API_KEY", "test-key")

# ─── Fixtures ────────────────────────────────────────────────


@pytest.fixture()
def stream_id() -> str:
    """A deterministic stream UUID string for tests."""
    return "12345678-1234-5678-1234-567812345678"


@pytest.fixture()
def session_id() -> str:
    """A deterministic session UUID string for tests."""
    return "87654321-4321-8765-4321-876543218765"


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
