"""
Database connection and ORM utilities for VoxSentinel.

This package provides async database connection management via SQLAlchemy,
ORM model definitions for PostgreSQL/TimescaleDB, and Alembic migration support.
"""

from tg_common.db.connection import (
    build_engine,
    build_session_factory,
    check_database_health,
    get_engine,
    get_session,
    get_session_factory,
)
from tg_common.db.orm_models import (
    AlertChannelConfigORM,
    AlertORM,
    AuditAnchorORM,
    Base,
    KeywordRuleORM,
    SessionORM,
    StreamORM,
    TranscriptSegmentORM,
)

__all__ = [
    "AlertChannelConfigORM",
    "AlertORM",
    "AuditAnchorORM",
    "Base",
    "KeywordRuleORM",
    "SessionORM",
    "StreamORM",
    "TranscriptSegmentORM",
    "build_engine",
    "build_session_factory",
    "check_database_health",
    "get_engine",
    "get_session",
    "get_session_factory",
]
