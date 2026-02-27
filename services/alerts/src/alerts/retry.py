"""
Celery retry tasks for VoxSentinel alert service.

Defines Celery tasks for retrying failed alert deliveries with
exponential backoff, ensuring reliable delivery across all channels.
"""

from __future__ import annotations

from celery import shared_task
