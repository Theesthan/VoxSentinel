"""
SQLAlchemy ORM models for VoxSentinel.

Defines the database table mappings for streams, sessions, transcript
segments, alerts, keyword rules, alert channel configurations, and
audit anchors using SQLAlchemy 2.0 declarative style.
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase
