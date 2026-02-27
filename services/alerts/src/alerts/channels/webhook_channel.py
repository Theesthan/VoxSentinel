"""
Webhook alert channel for VoxSentinel.

Sends HTTP POST requests with JSON alert payloads to configured
webhook URLs with retry logic (3 attempts, exponential backoff).
"""

from __future__ import annotations

import httpx
