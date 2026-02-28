"""
Tests for the audit verification API router.

Validates segment integrity verification via Merkle proofs
and audit anchor lookups.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

SEGMENT_ID = "99999999-8888-7777-6666-555544443333"


# ─── Helpers ──────────────────────────────────────────────────

ANCHOR_ID = 42
MERKLE_ROOT = "aabbccdd" * 8  # 64 hex chars


def _hash_pair(a: str, b: str) -> str:
    combined = min(a, b) + max(a, b)
    return hashlib.sha256(combined.encode()).hexdigest()


def _make_segment_orm(segment_hash: str):
    obj = MagicMock()
    obj.segment_id = uuid.UUID(SEGMENT_ID)
    obj.segment_hash = segment_hash
    return obj


def _make_anchor_orm(merkle_root: str, first_seg=None, last_seg=None):
    obj = MagicMock()
    obj.anchor_id = ANCHOR_ID
    obj.merkle_root = merkle_root
    obj.first_segment_id = first_seg or uuid.UUID(SEGMENT_ID)
    obj.last_segment_id = last_seg or uuid.UUID(SEGMENT_ID)
    obj.segment_count = 1
    obj.anchored_at = datetime(2025, 6, 1, tzinfo=timezone.utc)
    return obj


# ─── GET /api/v1/audit/verify/{segment_id} ──────────────────


class TestVerifySegment:
    def test_segment_not_found_returns_404(self, client: TestClient, mock_db: AsyncMock):
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=result_mock)

        resp = client.get(f"/api/v1/audit/verify/{SEGMENT_ID}")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Segment not found"

    def test_no_anchor_returns_unverified(self, client: TestClient, mock_db: AsyncMock):
        seg = _make_segment_orm(segment_hash="abc123")
        # First call returns segment, second returns no anchor
        seg_result = MagicMock()
        seg_result.scalar_one_or_none.return_value = seg
        anchor_result = MagicMock()
        anchor_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(side_effect=[seg_result, anchor_result])

        resp = client.get(f"/api/v1/audit/verify/{SEGMENT_ID}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["segment_id"] == SEGMENT_ID
        assert data["segment_hash"] == "abc123"
        assert data["verified"] is False
        assert data["anchor_id"] is None

    def test_valid_single_segment_merkle_verified(
        self, client: TestClient, mock_db: AsyncMock,
    ):
        seg_hash = hashlib.sha256(b"some segment text").hexdigest()
        # Single segment => merkle root = the hash itself
        merkle_root = seg_hash

        seg = _make_segment_orm(segment_hash=seg_hash)
        anchor = _make_anchor_orm(merkle_root=merkle_root)

        seg_result = MagicMock()
        seg_result.scalar_one_or_none.return_value = seg

        anchor_result = MagicMock()
        anchor_result.scalar_one_or_none.return_value = anchor

        range_result = MagicMock()
        range_result.all.return_value = [(seg_hash,)]

        mock_db.execute = AsyncMock(
            side_effect=[seg_result, anchor_result, range_result],
        )

        resp = client.get(f"/api/v1/audit/verify/{SEGMENT_ID}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["verified"] is True
        assert data["anchor_id"] == ANCHOR_ID
        assert data["merkle_root"] == merkle_root

    def test_two_segment_merkle_verified(
        self, client: TestClient, mock_db: AsyncMock,
    ):
        h1 = hashlib.sha256(b"seg1").hexdigest()
        h2 = hashlib.sha256(b"seg2").hexdigest()
        root = _hash_pair(h1, h2)

        seg = _make_segment_orm(segment_hash=h1)
        second_seg_id = uuid.UUID("22222222-3333-4444-5555-666677778888")
        anchor = _make_anchor_orm(
            merkle_root=root,
            first_seg=uuid.UUID(SEGMENT_ID),
            last_seg=second_seg_id,
        )

        seg_result = MagicMock()
        seg_result.scalar_one_or_none.return_value = seg

        anchor_result = MagicMock()
        anchor_result.scalar_one_or_none.return_value = anchor

        range_result = MagicMock()
        range_result.all.return_value = [(h1,), (h2,)]

        mock_db.execute = AsyncMock(
            side_effect=[seg_result, anchor_result, range_result],
        )

        resp = client.get(f"/api/v1/audit/verify/{SEGMENT_ID}")
        data = resp.json()
        assert data["verified"] is True
        assert data["merkle_proof"] != []
        assert data["anchored_at"] is not None

    def test_tampered_segment_not_verified(
        self, client: TestClient, mock_db: AsyncMock,
    ):
        h1 = hashlib.sha256(b"seg1").hexdigest()
        h2 = hashlib.sha256(b"seg2").hexdigest()
        root = _hash_pair(h1, h2)

        # Segment has different hash (tampered)
        tampered_hash = hashlib.sha256(b"tampered").hexdigest()
        seg = _make_segment_orm(segment_hash=tampered_hash)
        anchor = _make_anchor_orm(merkle_root=root)

        seg_result = MagicMock()
        seg_result.scalar_one_or_none.return_value = seg

        anchor_result = MagicMock()
        anchor_result.scalar_one_or_none.return_value = anchor

        # The range hashes are the original untampered ones
        range_result = MagicMock()
        range_result.all.return_value = [(h1,), (h2,)]

        mock_db.execute = AsyncMock(
            side_effect=[seg_result, anchor_result, range_result],
        )

        resp = client.get(f"/api/v1/audit/verify/{SEGMENT_ID}")
        data = resp.json()
        # tampered_hash is not in [h1, h2] so proof will be empty
        assert data["verified"] is False

    def test_verify_response_shape(self, client: TestClient, mock_db: AsyncMock):
        seg_hash = "a" * 64
        seg = _make_segment_orm(segment_hash=seg_hash)
        seg_result = MagicMock()
        seg_result.scalar_one_or_none.return_value = seg
        anchor_result = MagicMock()
        anchor_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(side_effect=[seg_result, anchor_result])

        resp = client.get(f"/api/v1/audit/verify/{SEGMENT_ID}")
        data = resp.json()
        # All expected keys present
        for key in ["segment_id", "segment_hash", "anchor_id", "merkle_root",
                     "merkle_proof", "verified", "anchored_at"]:
            assert key in data
