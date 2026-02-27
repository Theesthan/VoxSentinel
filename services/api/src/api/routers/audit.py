"""
Audit verification API router for VoxSentinel.

Endpoints for verifying transcript segment integrity via SHA-256
hashes, Merkle proofs, and audit anchor records.
"""

from __future__ import annotations

from fastapi import APIRouter
