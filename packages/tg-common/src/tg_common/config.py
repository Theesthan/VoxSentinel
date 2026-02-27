"""
Environment-based configuration management for VoxSentinel.

Uses pydantic-settings to load configuration values from environment
variables and .env files. All services import their settings from this
module to ensure consistent configuration handling.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings
