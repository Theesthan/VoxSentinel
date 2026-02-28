"""
Celery application configuration for VoxSentinel.

Defines the shared Celery app instance used by all services for
distributed task execution, including alert retry tasks and
background processing jobs. Uses Redis as broker and result backend.
"""

from __future__ import annotations

import os

from celery import Celery

_broker = os.environ.get("TG_CELERY_BROKER_URL", "redis://localhost:6379/1")
_backend = os.environ.get("TG_CELERY_RESULT_BACKEND", "redis://localhost:6379/2")

celery = Celery(
    "voxsentinel",
    broker=_broker,
    backend=_backend,
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

# Auto-discover tasks in the alerts service package.
celery.autodiscover_tasks(["alerts"], related_name="retry")

