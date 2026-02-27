"""Tests for storage.audit_hasher."""

from __future__ import annotations

import asyncio
import hashlib
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest


# ─── build_merkle_root ────────────────────────────────────────────


class TestBuildMerkleRoot:
    def test_single_hash(self):
        from storage.audit_hasher import build_merkle_root

        h = hashlib.sha256(b"test").hexdigest()
        assert build_merkle_root([h]) == h

    def test_two_hashes(self):
        from storage.audit_hasher import build_merkle_root

        h1 = hashlib.sha256(b"a").hexdigest()
        h2 = hashlib.sha256(b"b").hexdigest()
        expected = hashlib.sha256((h1 + h2).encode()).hexdigest()
        assert build_merkle_root([h1, h2]) == expected

    def test_three_hashes_duplicates_last(self):
        from storage.audit_hasher import build_merkle_root

        h1 = hashlib.sha256(b"a").hexdigest()
        h2 = hashlib.sha256(b"b").hexdigest()
        h3 = hashlib.sha256(b"c").hexdigest()
        # Layer 1: hash(h1+h2), hash(h3+h3)
        left = hashlib.sha256((h1 + h2).encode()).hexdigest()
        right = hashlib.sha256((h3 + h3).encode()).hexdigest()
        # Root: hash(left + right)
        expected = hashlib.sha256((left + right).encode()).hexdigest()
        assert build_merkle_root([h1, h2, h3]) == expected

    def test_four_hashes(self):
        from storage.audit_hasher import build_merkle_root

        hashes = [hashlib.sha256(f"seg{i}".encode()).hexdigest() for i in range(4)]
        left = hashlib.sha256((hashes[0] + hashes[1]).encode()).hexdigest()
        right = hashlib.sha256((hashes[2] + hashes[3]).encode()).hexdigest()
        expected = hashlib.sha256((left + right).encode()).hexdigest()
        assert build_merkle_root(hashes) == expected

    def test_empty_raises(self):
        from storage.audit_hasher import build_merkle_root

        with pytest.raises(ValueError, match="empty"):
            build_merkle_root([])

    def test_deterministic(self):
        from storage.audit_hasher import build_merkle_root

        hashes = [hashlib.sha256(f"h{i}".encode()).hexdigest() for i in range(5)]
        assert build_merkle_root(hashes) == build_merkle_root(hashes)

    def test_order_matters(self):
        from storage.audit_hasher import build_merkle_root

        h1 = hashlib.sha256(b"a").hexdigest()
        h2 = hashlib.sha256(b"b").hexdigest()
        assert build_merkle_root([h1, h2]) != build_merkle_root([h2, h1])

    def test_large_batch(self):
        from storage.audit_hasher import build_merkle_root

        hashes = [hashlib.sha256(f"seg{i}".encode()).hexdigest() for i in range(100)]
        root = build_merkle_root(hashes)
        assert len(root) == 64
        # Deterministic
        assert root == build_merkle_root(hashes)


# ─── AuditHasher.anchor ──────────────────────────────────────────


def _make_segment_row(seg_hash: str, seg_id=None, created_at=None):
    """Return a simple namespace that mimics a DB row tuple."""
    return SimpleNamespace(
        segment_id=seg_id or uuid4(),
        segment_hash=seg_hash,
        created_at=created_at or datetime.now(timezone.utc),
    )


class TestAnchor:
    async def test_no_segments_returns_none(self, mock_db_session, mock_db_session_factory):
        from storage.audit_hasher import AuditHasher

        # No prior anchors; no new segments.
        _mock_last_anchor_result = AsyncMock()
        _mock_last_anchor_result.scalar_one_or_none = MagicMock(return_value=None)

        _mock_segments_result = AsyncMock()
        _mock_segments_result.all = MagicMock(return_value=[])

        mock_db_session.execute = AsyncMock(
            side_effect=[_mock_last_anchor_result, _mock_segments_result],
        )

        hasher = AuditHasher(session_factory=mock_db_session_factory)
        result = await hasher.anchor(db_session=mock_db_session)

        assert result is None
        mock_db_session.add.assert_not_called()

    async def test_writes_anchor_with_correct_root(
        self, mock_db_session, mock_db_session_factory,
    ):
        from storage.audit_hasher import AuditHasher, build_merkle_root

        h1 = hashlib.sha256(b"seg1").hexdigest()
        h2 = hashlib.sha256(b"seg2").hexdigest()
        id1, id2 = uuid4(), uuid4()
        rows = [
            _make_segment_row(h1, seg_id=id1),
            _make_segment_row(h2, seg_id=id2),
        ]

        _mock_last = AsyncMock()
        _mock_last.scalar_one_or_none = MagicMock(return_value=None)

        _mock_segs = AsyncMock()
        _mock_segs.all = MagicMock(return_value=rows)

        mock_db_session.execute = AsyncMock(
            side_effect=[_mock_last, _mock_segs],
        )

        hasher = AuditHasher(session_factory=mock_db_session_factory)
        result = await hasher.anchor(db_session=mock_db_session)

        assert result is not None
        assert result.merkle_root == build_merkle_root([h1, h2])
        assert result.segment_count == 2
        assert result.first_segment_id == id1
        assert result.last_segment_id == id2
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_awaited_once()

    async def test_respects_last_anchor_time(
        self, mock_db_session, mock_db_session_factory,
    ):
        from storage.audit_hasher import AuditHasher

        past = datetime(2025, 1, 1, tzinfo=timezone.utc)
        h = hashlib.sha256(b"new").hexdigest()
        rows = [_make_segment_row(h)]

        _mock_last = AsyncMock()
        _mock_last.scalar_one_or_none = MagicMock(return_value=past)

        _mock_segs = AsyncMock()
        _mock_segs.all = MagicMock(return_value=rows)

        mock_db_session.execute = AsyncMock(
            side_effect=[_mock_last, _mock_segs],
        )

        hasher = AuditHasher(session_factory=mock_db_session_factory)
        result = await hasher.anchor(db_session=mock_db_session)

        assert result is not None
        assert result.segment_count == 1

    async def test_rollback_on_error(self, mock_db_session, mock_db_session_factory):
        from storage.audit_hasher import AuditHasher

        h = hashlib.sha256(b"seg").hexdigest()
        rows = [_make_segment_row(h)]

        _mock_last = AsyncMock()
        _mock_last.scalar_one_or_none = MagicMock(return_value=None)
        _mock_segs = AsyncMock()
        _mock_segs.all = MagicMock(return_value=rows)

        mock_db_session.execute = AsyncMock(
            side_effect=[_mock_last, _mock_segs],
        )
        mock_db_session.commit = AsyncMock(side_effect=RuntimeError("DB error"))

        hasher = AuditHasher(session_factory=mock_db_session_factory)

        with pytest.raises(RuntimeError, match="DB error"):
            await hasher.anchor(db_session=mock_db_session)

        mock_db_session.rollback.assert_awaited_once()

    async def test_creates_own_session_when_none(self, mock_db_session_factory):
        from storage.audit_hasher import AuditHasher

        mock_session = mock_db_session_factory.return_value
        _mock_last = AsyncMock()
        _mock_last.scalar_one_or_none = MagicMock(return_value=None)
        _mock_segs = AsyncMock()
        _mock_segs.all = MagicMock(return_value=[])

        mock_session.execute = AsyncMock(
            side_effect=[_mock_last, _mock_segs],
        )

        hasher = AuditHasher(session_factory=mock_db_session_factory)
        await hasher.anchor()

        mock_db_session_factory.assert_called_once()
        mock_session.close.assert_awaited_once()

    async def test_single_segment_root_equals_hash(
        self, mock_db_session, mock_db_session_factory,
    ):
        """When there's only one segment, the Merkle root is the hash itself."""
        from storage.audit_hasher import AuditHasher

        h = hashlib.sha256(b"only").hexdigest()
        rows = [_make_segment_row(h)]

        _mock_last = AsyncMock()
        _mock_last.scalar_one_or_none = MagicMock(return_value=None)
        _mock_segs = AsyncMock()
        _mock_segs.all = MagicMock(return_value=rows)

        mock_db_session.execute = AsyncMock(
            side_effect=[_mock_last, _mock_segs],
        )

        hasher = AuditHasher(session_factory=mock_db_session_factory)
        result = await hasher.anchor(db_session=mock_db_session)

        assert result is not None
        assert result.merkle_root == h


# ─── AuditHasher.start / stop ────────────────────────────────────


class TestPeriodicRunner:
    async def test_start_and_stop(self, mock_db_session_factory):
        from storage.audit_hasher import AuditHasher

        mock_session = mock_db_session_factory.return_value
        _mock_last = AsyncMock()
        _mock_last.scalar_one_or_none = MagicMock(return_value=None)
        _mock_segs = AsyncMock()
        _mock_segs.all = MagicMock(return_value=[])
        mock_session.execute = AsyncMock(
            side_effect=[_mock_last, _mock_segs] * 10,
        )

        hasher = AuditHasher(session_factory=mock_db_session_factory, interval_s=0.01)
        hasher.start()
        await asyncio.sleep(0.05)
        await hasher.stop()

        # anchor was called at least once
        assert mock_session.execute.await_count >= 2  # min 1 pair of calls

    async def test_stop_without_start(self, mock_db_session_factory):
        from storage.audit_hasher import AuditHasher

        hasher = AuditHasher(session_factory=mock_db_session_factory)
        # Should not raise
        await hasher.stop()
