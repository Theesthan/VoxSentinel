"""
FastAPI dependency injection providers for VoxSentinel API.

Defines reusable Depends() callables for authentication, database
sessions, Redis connections, and other shared resources.
"""

from __future__ import annotations

from fastapi import Depends
