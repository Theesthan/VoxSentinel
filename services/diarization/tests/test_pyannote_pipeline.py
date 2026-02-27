"""Tests for diarization.pyannote_pipeline module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from diarization.pyannote_pipeline import (
    BYTES_PER_SAMPLE,
    MODEL_ID,
    SAMPLE_RATE,
    PyannotePipeline,
    SpeakerSegment,
)


# ── Helpers ──────────────────────────────────────────────────

def _make_pcm(duration_s: float = 1.0) -> bytes:
    """Create silent PCM bytes of the given duration."""
    n_samples = int(SAMPLE_RATE * duration_s)
    return b"\x00\x00" * n_samples


# Reusable fake annotation components from conftest
import sys
_pa = sys.modules["pyannote.audio"]
_FakeAnnotation = _pa._FakeAnnotation
_FakeTurn = _pa._FakeTurn


# ── TestSpeakerSegment ───────────────────────────────────────

class TestSpeakerSegment:
    def test_creation(self) -> None:
        seg = SpeakerSegment(speaker_id="SPEAKER_00", start_ms=0, end_ms=1000)
        assert seg.speaker_id == "SPEAKER_00"
        assert seg.start_ms == 0
        assert seg.end_ms == 1000

    def test_frozen(self) -> None:
        seg = SpeakerSegment(speaker_id="SPEAKER_00", start_ms=0, end_ms=500)
        with pytest.raises(AttributeError):
            seg.speaker_id = "X"  # type: ignore[misc]


# ── TestPyannotePipeline ─────────────────────────────────────

class TestPyannotePipelineLoad:
    def test_not_ready_before_load(self) -> None:
        p = PyannotePipeline(hf_token="tok")
        assert p.is_ready is False

    def test_load_sets_ready(self) -> None:
        p = PyannotePipeline(hf_token="tok", device="cpu")
        p.load()
        assert p.is_ready is True

    def test_load_is_idempotent(self) -> None:
        """Calling load() twice should not re-download."""
        p = PyannotePipeline(hf_token="tok", device="cpu")
        p.load()
        p.load()  # second call — no error
        assert p.is_ready is True


class TestPyannotePipelineDiarize:
    def _make_pipeline_with_annotation(
        self,
        tracks: list[tuple[float, float, str]],
    ) -> PyannotePipeline:
        """Return a pipeline whose internal model returns the given tracks."""
        p = PyannotePipeline(hf_token="tok", device="cpu")
        p.load()

        fake_ann = _FakeAnnotation(
            [(_FakeTurn(s, e), spk) for s, e, spk in tracks]
        )
        # Replace the loaded mock pipeline's __call__
        p._pipeline.return_value = fake_ann  # type: ignore[union-attr]
        return p

    def test_diarize_sync_returns_segments(self) -> None:
        p = self._make_pipeline_with_annotation([
            (0.0, 1.5, "SPEAKER_00"),
            (1.5, 3.0, "SPEAKER_01"),
        ])
        segments = p._diarize_sync(_make_pcm(3.0))
        assert len(segments) == 2
        assert segments[0] == SpeakerSegment("SPEAKER_00", 0, 1500)
        assert segments[1] == SpeakerSegment("SPEAKER_01", 1500, 3000)

    def test_diarize_sync_empty_audio(self) -> None:
        p = self._make_pipeline_with_annotation([])
        segments = p._diarize_sync(_make_pcm(0.1))
        assert segments == []

    @pytest.mark.asyncio
    async def test_diarize_async_wraps_to_thread(self) -> None:
        p = self._make_pipeline_with_annotation([
            (0.0, 2.0, "SPEAKER_00"),
        ])
        segments = await p.diarize(_make_pcm(2.0))
        assert len(segments) == 1
        assert segments[0].speaker_id == "SPEAKER_00"

    def test_diarize_sync_raises_when_not_loaded(self) -> None:
        p = PyannotePipeline(hf_token="tok")
        with pytest.raises(RuntimeError, match="not loaded"):
            p._diarize_sync(_make_pcm(1.0))

    def test_millisecond_conversion(self) -> None:
        p = self._make_pipeline_with_annotation([
            (0.123, 0.456, "SPEAKER_00"),
        ])
        segments = p._diarize_sync(_make_pcm(1.0))
        assert segments[0].start_ms == 123
        assert segments[0].end_ms == 456

    def test_multiple_speakers(self) -> None:
        p = self._make_pipeline_with_annotation([
            (0.0, 1.0, "SPEAKER_00"),
            (1.0, 2.0, "SPEAKER_01"),
            (2.0, 3.0, "SPEAKER_02"),
        ])
        segments = p._diarize_sync(_make_pcm(3.0))
        assert len(segments) == 3
        speakers = {s.speaker_id for s in segments}
        assert speakers == {"SPEAKER_00", "SPEAKER_01", "SPEAKER_02"}
