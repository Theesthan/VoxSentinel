"""
Keyword rule management API router for VoxSentinel.

CRUD endpoints for creating, reading, updating, and deleting keyword
detection rules with hot-reload support (changes effective within 5 s).
"""

from __future__ import annotations

from fastapi import APIRouter
