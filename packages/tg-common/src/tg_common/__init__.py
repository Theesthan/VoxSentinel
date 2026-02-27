"""
tg-common: Shared library for VoxSentinel.

Provides common data models, configuration management, database connections,
messaging utilities, structured logging, and Prometheus metrics helpers
used across all VoxSentinel microservices.
"""

from tg_common.config import Settings, get_settings

__all__ = [
    "Settings",
    "get_settings",
]
