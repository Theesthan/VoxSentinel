"""
Cryptographic audit hasher for VoxSentinel storage service.

Computes SHA-256 hashes per transcript segment at write time and
periodically anchors Merkle roots to an append-only audit table
for tamper-proof verification.
"""

from __future__ import annotations

import asyncio
import hashlib
from datetime import datetime
from typing import Any, Callable

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tg_common.db.orm_models import AuditAnchorORM, TranscriptSegmentORM

logger = structlog.get_logger(__name__)

DEFAULT_INTERVAL_S = 60


def _hash_pair(left: str, right: str) -> str:
    """SHA-256 hash of two concatenated hex digests."""
    return hashlib.sha256((left + right).encode()).hexdigest()


def build_merkle_root(hashes: list[str]) -> str:
    """Build a Merkle root from an ordered list of hex-digest hashes.

    If the list has an odd number of elements the last element is
    duplicated.  Returns the single root hash.
    """
    if not hashes:
        raise ValueError("Cannot build Merkle root from empty list")
    if len(hashes) == 1:
        return hashes[0]

    layer = list(hashes)
    while len(layer) > 1:
        next_layer: list[str] = []
        for i in range(0, len(layer), 2):
            left = layer[i]
            right = layer[i + 1] if i + 1 < len(layer) else layer[i]
            next_layer.append(_hash_pair(left, right))
        layer = next_layer
    return layer[0]


class AuditHasher:
    """Periodically anchors transcript segment hashes into Merkle roots.

    Parameters
    ----------
    session_factory:
        Async callable returning an ``AsyncSession``.
    interval_s:
        Interval between anchor runs (default 60 s).
    """

    def __init__(
        self,
        session_factory: Callable[..., Any],
        interval_s: float = DEFAULT_INTERVAL_S,
    ) -> None:
        self._session_factory = session_factory
        self._interval = interval_s
        self._last_anchor_id: int | None = None
        self._running = False
        self._task: asyncio.Task[None] | None = None

    # ------------------------------------------------------------------
    # Core anchor logic
    # ------------------------------------------------------------------

    async def anchor(
        self,
        *,
        db_session: AsyncSession | None = None,
    ) -> AuditAnchorORM | None:
        """Collect new segment hashes and write a Merkle-root anchor.

        Returns ``None`` when there are no new segments since the last
        anchor.
        """
        own_session = db_session is None
        session: AsyncSession = db_session or self._session_factory()
        try:
            # Determine the cut-off: segments created after the last anchor.
            last_anchor_at = await self._last_anchor_time(session)

            stmt = (
                select(
                    TranscriptSegmentORM.segment_id,
                    TranscriptSegmentORM.segment_hash,
                    TranscriptSegmentORM.created_at,
                )
                .where(TranscriptSegmentORM.segment_hash.is_not(None))
                .order_by(TranscriptSegmentORM.created_at.asc())
            )
            if last_anchor_at is not None:
                stmt = stmt.where(TranscriptSegmentORM.created_at > last_anchor_at)

            result = await session.execute(stmt)
            rows = result.all()

            if not rows:
                logger.debug("audit_anchor_skip", reason="no_new_segments")
                return None

            seg_hashes = [r.segment_hash for r in rows]
            seg_ids = [r.segment_id for r in rows]
            merkle_root = build_merkle_root(seg_hashes)

            anchor = AuditAnchorORM(
                merkle_root=merkle_root,
                segment_count=len(rows),
                first_segment_id=seg_ids[0],
                last_segment_id=seg_ids[-1],
            )
            session.add(anchor)
            await session.commit()

            logger.info(
                "audit_anchor_written",
                merkle_root=merkle_root,
                segment_count=len(rows),
            )
            return anchor

        except Exception:
            await session.rollback()
            logger.exception("audit_anchor_failed")
            raise
        finally:
            if own_session:
                await session.close()

    async def _last_anchor_time(self, session: AsyncSession) -> datetime | None:
        """Return the ``anchored_at`` of the most recent anchor, or *None*."""
        stmt = (
            select(AuditAnchorORM.anchored_at)
            .order_by(AuditAnchorORM.anchor_id.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()
        return row

    # ------------------------------------------------------------------
    # Periodic runner
    # ------------------------------------------------------------------

    async def run_periodic(self) -> None:
        """Run the anchor loop every ``interval_s`` seconds."""
        self._running = True
        while self._running:
            try:
                await self.anchor()
            except Exception:
                logger.exception("periodic_anchor_error")
            await asyncio.sleep(self._interval)

    def start(self) -> None:
        """Launch the periodic task on the running event loop."""
        self._task = asyncio.ensure_future(self.run_periodic())

    async def stop(self) -> None:
        """Cancel the periodic task."""
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
