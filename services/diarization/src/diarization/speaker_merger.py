"""
Speaker-transcript merger for VoxSentinel.

Intersects speaker diarization segments with ASR word-level timestamps
to assign speaker_id labels per word and per transcript segment.

Assignment strategy:
  1. For each token, find the diarization segment that *contains*
     ``token.start_time`` (millisecond precision).
  2. If no segment contains the token (gap between speakers),
     assign the *nearest* segment's speaker by absolute distance
     to the token's midpoint.
"""

from __future__ import annotations

import bisect
from dataclasses import dataclass

from diarization.pyannote_pipeline import SpeakerSegment


@dataclass(frozen=True, slots=True)
class EnrichedToken:
    """A transcript token enriched with a speaker label.

    Mirrors the fields downstream consumers need, keeping the
    module decoupled from the full ``TranscriptToken`` Pydantic model.

    Attributes:
        text: The transcribed text.
        is_final: Whether this is a finalized token.
        start_ms: Token start offset in milliseconds.
        end_ms: Token end offset in milliseconds.
        confidence: ASR confidence (0.0–1.0).
        language: Detected language code.
        speaker_id: Assigned speaker label (e.g. ``SPEAKER_00``).
    """

    text: str
    is_final: bool
    start_ms: int
    end_ms: int
    confidence: float
    language: str
    speaker_id: str


class SpeakerMerger:
    """Merge speaker diarization segments with transcript tokens.

    Maintains the latest diarization window so that incoming tokens
    can be enriched immediately.
    """

    def __init__(self) -> None:
        self._segments: list[SpeakerSegment] = []
        # Pre-sorted start_ms values for fast bisect lookup.
        self._starts: list[int] = []

    # ── Public API ────────────────────────────────────────────

    def update_segments(self, segments: list[SpeakerSegment]) -> None:
        """Replace the current diarization window.

        Args:
            segments: Speaker segments sorted by ``start_ms`` ascending.
        """
        self._segments = sorted(segments, key=lambda s: s.start_ms)
        self._starts = [s.start_ms for s in self._segments]

    def assign_speaker(self, start_ms: int, end_ms: int) -> str:
        """Return the speaker label for a token at the given offsets.

        Uses containment first, then nearest-segment fallback.

        Args:
            start_ms: Token start millisecond offset.
            end_ms: Token end millisecond offset.

        Returns:
            Speaker label string.  Defaults to ``"SPEAKER_UNKNOWN"``
            when no segments are available.
        """
        if not self._segments:
            return "SPEAKER_UNKNOWN"

        # 1. Containment: find segment whose range covers start_ms.
        idx = bisect.bisect_right(self._starts, start_ms) - 1
        if idx >= 0 and self._segments[idx].end_ms >= start_ms:
            return self._segments[idx].speaker_id

        # Check the next segment as well (in case start_ms falls
        # exactly on or after a boundary).
        if idx + 1 < len(self._segments) and self._segments[idx + 1].start_ms <= end_ms:
            return self._segments[idx + 1].speaker_id

        # 2. Nearest-segment fallback (by midpoint distance).
        mid = (start_ms + end_ms) // 2
        best_seg = min(
            self._segments,
            key=lambda s: min(abs(s.start_ms - mid), abs(s.end_ms - mid)),
        )
        return best_seg.speaker_id

    def merge(
        self,
        tokens: list[dict],
    ) -> list[EnrichedToken]:
        """Enrich a list of raw token dicts with speaker labels.

        Each dict is expected to carry at least ``text``, ``is_final``,
        ``start_ms``, ``end_ms``, ``confidence``, and ``language``.

        Args:
            tokens: Raw token dictionaries from the Redis stream.

        Returns:
            List of ``EnrichedToken`` objects with ``speaker_id`` set.
        """
        enriched: list[EnrichedToken] = []
        for tok in tokens:
            start = int(tok.get("start_ms", 0))
            end = int(tok.get("end_ms", 0))
            speaker = self.assign_speaker(start, end)
            enriched.append(
                EnrichedToken(
                    text=tok.get("text", ""),
                    is_final=bool(tok.get("is_final", False)),
                    start_ms=start,
                    end_ms=end,
                    confidence=float(tok.get("confidence", 0.0)),
                    language=tok.get("language", "en"),
                    speaker_id=speaker,
                )
            )
        return enriched

    def clear(self) -> None:
        """Remove all stored segments."""
        self._segments.clear()
        self._starts.clear()
