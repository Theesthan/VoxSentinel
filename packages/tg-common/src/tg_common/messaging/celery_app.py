"""
Celery application configuration for VoxSentinel.

Defines the shared Celery app instance used by all services for
distributed task execution, including alert retry tasks and
background processing jobs. Uses Redis as broker and result backend.
"""

from __future__ import annotations

from celery import Celery
