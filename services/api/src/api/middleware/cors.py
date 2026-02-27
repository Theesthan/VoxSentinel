"""
CORS middleware configuration for VoxSentinel API.

Configures Cross-Origin Resource Sharing headers to allow
dashboard and external client access to the API.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def add_cors(app: FastAPI) -> None:
    """Attach CORS middleware allowing all origins in dev mode."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
