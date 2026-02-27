"""
Cryptographic audit hasher for VoxSentinel storage service.

Computes SHA-256 hashes per transcript segment at write time and
periodically anchors Merkle roots to an append-only audit table
for tamper-proof verification.
"""

from __future__ import annotations

import hashlib
