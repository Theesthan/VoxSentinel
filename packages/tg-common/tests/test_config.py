"""
Tests for tg-common configuration module.

Validates that environment-based configuration loading, default values,
and validation constraints work correctly via pydantic-settings.
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from tg_common.config import Settings, get_settings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clear_settings_cache() -> None:
    """Reset the ``get_settings`` lru_cache between tests."""
    get_settings.cache_clear()


# ---------------------------------------------------------------------------
# Tests: default values
# ---------------------------------------------------------------------------


class TestSettingsDefaults:
    """Verify that ``Settings`` populates sane defaults when no env vars are set."""

    @staticmethod
    def _clean_env():
        """Remove TG_ env vars so Settings reads only hardcoded defaults."""
        return {k: v for k, v in os.environ.items() if not k.startswith("TG_")}

    def test_default_db_uri(self) -> None:
        with patch.dict(os.environ, self._clean_env(), clear=True):
            s = Settings()
        assert s.db_uri == "postgresql+asyncpg://voxsentinel:changeme@localhost:5432/voxsentinel"

    def test_default_db_pool_size(self) -> None:
        with patch.dict(os.environ, self._clean_env(), clear=True):
            assert Settings().db_pool_size == 10

    def test_default_redis_url(self) -> None:
        with patch.dict(os.environ, self._clean_env(), clear=True):
            assert Settings().redis_url == "redis://localhost:6379/0"

    def test_default_vad_threshold(self) -> None:
        with patch.dict(os.environ, self._clean_env(), clear=True):
            assert Settings().vad_threshold == 0.5

    def test_default_api_port(self) -> None:
        with patch.dict(os.environ, self._clean_env(), clear=True):
            assert Settings().api_port == 8000

    def test_default_log_level(self) -> None:
        with patch.dict(os.environ, self._clean_env(), clear=True):
            assert Settings().log_level == "INFO"

    def test_default_retention_days(self) -> None:
        with patch.dict(os.environ, self._clean_env(), clear=True):
            assert Settings().retention_days == 90

    def test_default_asr_backend(self) -> None:
        with patch.dict(os.environ, self._clean_env(), clear=True):
            assert Settings().asr_default_backend == "deepgram_nova2"


# ---------------------------------------------------------------------------
# Tests: environment variable overrides
# ---------------------------------------------------------------------------


class TestSettingsFromEnv:
    """Verify that env vars with TG_ prefix override defaults."""

    def test_override_db_uri(self) -> None:
        with patch.dict(os.environ, {"TG_DB_URI": "postgresql+asyncpg://u:p@host/db"}):
            s = Settings()
        assert s.db_uri == "postgresql+asyncpg://u:p@host/db"

    def test_override_redis_url(self) -> None:
        with patch.dict(os.environ, {"TG_REDIS_URL": "redis://other:6380/1"}):
            s = Settings()
        assert s.redis_url == "redis://other:6380/1"

    def test_override_vad_threshold(self) -> None:
        with patch.dict(os.environ, {"TG_VAD_THRESHOLD": "0.7"}):
            s = Settings()
        assert s.vad_threshold == pytest.approx(0.7)

    def test_override_log_level(self) -> None:
        with patch.dict(os.environ, {"TG_LOG_LEVEL": "DEBUG"}):
            s = Settings()
        assert s.log_level == "DEBUG"

    def test_override_retention_days(self) -> None:
        with patch.dict(os.environ, {"TG_RETENTION_DAYS": "30"}):
            s = Settings()
        assert s.retention_days == 30


# ---------------------------------------------------------------------------
# Tests: validation constraints
# ---------------------------------------------------------------------------


class TestSettingsValidation:
    """Verify pydantic validators on ``Settings`` fields."""

    def test_vad_threshold_too_low(self) -> None:
        with pytest.raises(ValidationError):
            Settings(vad_threshold=-0.1)  # type: ignore[call-arg]

    def test_vad_threshold_too_high(self) -> None:
        with pytest.raises(ValidationError):
            Settings(vad_threshold=1.1)  # type: ignore[call-arg]

    def test_retention_days_zero(self) -> None:
        with pytest.raises(ValidationError):
            Settings(retention_days=0)  # type: ignore[call-arg]

    def test_retention_days_negative(self) -> None:
        with pytest.raises(ValidationError):
            Settings(retention_days=-5)  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# Tests: get_settings singleton
# ---------------------------------------------------------------------------


class TestGetSettings:
    """Verify the cached ``get_settings()`` helper."""

    def setup_method(self) -> None:
        _clear_settings_cache()

    def teardown_method(self) -> None:
        _clear_settings_cache()

    def test_returns_settings_instance(self) -> None:
        s = get_settings()
        assert isinstance(s, Settings)

    def test_cached(self) -> None:
        a = get_settings()
        b = get_settings()
        assert a is b
