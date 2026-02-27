"""
Audit data model for VoxSentinel.

Defines the Pydantic model for cryptographic audit anchors, including
Merkle root hashes and segment range references used to verify
transcript integrity and non-tampering.
"""

from __future__ import annotations

from pydantic import BaseModel
