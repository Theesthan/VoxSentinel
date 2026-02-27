"""
Tests for the webhook alert channel.

Validates HTTP POST delivery, retry logic with exponential backoff,
and error handling for failed deliveries.
"""

from __future__ import annotations
