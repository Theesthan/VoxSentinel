"""
Environment-based configuration management for VoxSentinel.

Uses pydantic-settings to load configuration values from environment
variables and .env files. All services import their settings from this
module to ensure consistent configuration handling.

All environment variables are prefixed with ``TG_`` to avoid collisions.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration loaded from ``TG_``-prefixed environment variables.

    Attributes:
        db_uri: Async PostgreSQL connection string.
        db_pool_size: SQLAlchemy connection-pool size.
        redis_url: Redis connection URL (caching, pub/sub, state).
        es_url: Elasticsearch base URL.
        deepgram_api_key: API key for Deepgram Nova-2.
        whisper_host: Host:port for the self-hosted Whisper server.
        asr_default_backend: Default ASR engine identifier.
        asr_fallback_backend: Fallback ASR engine identifier.
        slack_webhook_url: Slack incoming-webhook URL for alerts.
        slack_bot_token: Slack bot OAuth token.
        vad_threshold: Silero VAD speech-confidence threshold (0.0–1.0).
        api_key: Platform API key used for authentication.
        api_host: Bind address for the API gateway.
        api_port: Bind port for the API gateway.
        celery_broker_url: Celery broker (Redis) URL.
        celery_result_backend: Celery result-backend (Redis) URL.
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        hf_token: Hugging Face token for pyannote.audio model access.
        retention_days: Number of days to retain transcripts and alerts.
    """

    model_config = SettingsConfigDict(
        env_prefix="TG_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Database ──
    db_uri: str = Field(
        default="postgresql+asyncpg://voxsentinel:changeme@localhost:5432/voxsentinel",
        description="Async PostgreSQL connection string.",
    )
    db_pool_size: int = Field(default=10, description="SQLAlchemy connection-pool size.")

    # ── Redis ──
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL.",
    )

    # ── Elasticsearch ──
    es_url: str = Field(
        default="http://localhost:9200",
        description="Elasticsearch base URL.",
    )

    # ── ASR Backends ──
    deepgram_api_key: str = Field(default="", description="Deepgram Nova-2 API key.")
    whisper_host: str = Field(
        default="localhost:9090",
        description="Host:port for self-hosted Whisper server.",
    )
    asr_default_backend: str = Field(
        default="deepgram_nova2",
        description="Default ASR engine identifier.",
    )
    asr_fallback_backend: str = Field(
        default="whisper_v3_turbo",
        description="Fallback ASR engine identifier.",
    )

    # ── Slack Alerts ──
    slack_webhook_url: str = Field(default="", description="Slack incoming-webhook URL.")
    slack_bot_token: str = Field(default="", description="Slack bot OAuth token.")

    # ── VAD ──
    vad_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Silero VAD speech-confidence threshold.",
    )

    # ── API ──
    api_key: str = Field(default="changeme", description="Platform API key.")
    api_host: str = Field(default="0.0.0.0", description="API gateway bind address.")
    api_port: int = Field(default=8000, ge=1, le=65535, description="API gateway bind port.")

    # ── Celery ──
    celery_broker_url: str = Field(
        default="redis://localhost:6379/1",
        description="Celery broker URL.",
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/2",
        description="Celery result-backend URL.",
    )

    # ── Logging ──
    log_level: str = Field(default="INFO", description="Logging level.")

    # ── Hugging Face ──
    hf_token: str = Field(default="", description="Hugging Face token for pyannote.audio.")

    # ── Data Retention ──
    retention_days: int = Field(
        default=90,
        ge=1,
        description="Number of days to retain transcripts and alerts.",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached application settings singleton.

    Returns:
        The global ``Settings`` instance.
    """
    return Settings()
