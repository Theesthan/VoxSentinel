"""
Authentication middleware for VoxSentinel API.

Validates API key or JWT Bearer tokens on incoming requests
and enforces role-based access control.
"""

from __future__ import annotations

from fastapi import Request
