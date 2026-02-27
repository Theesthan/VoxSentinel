"""
CORS middleware configuration for VoxSentinel API.

Configures Cross-Origin Resource Sharing headers to allow
dashboard and external client access to the API.
"""

from __future__ import annotations

from fastapi.middleware.cors import CORSMiddleware
