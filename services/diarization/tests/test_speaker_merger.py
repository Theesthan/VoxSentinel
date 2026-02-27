"""Tests for diarization.speaker_merger module."""

from __future__ import annotations

import pytest

from diarization.pyannote_pipeline import SpeakerSegment
from diarization.speaker_merger import EnrichedToken, SpeakerMerger


# ── Helpers ──────────────────────────────────────────────────

def _seg(speaker: str, start_ms: int, end_ms: int) -> SpeakerSegment:
    return SpeakerSegment(speaker_id=speaker, start_ms=start_ms, end_ms=end_ms)


def _tok(start_ms: int, end_ms: int, text: str = "hello") -> dict:
    return {
        "text": text,
        "is_final": True,
        "start_ms": start_ms,
        "end_ms": end_ms,
        "confidence": 0.95,
        "language": "en",
    }


# ── TestAssignSpeaker ────────────────────────────────────────

class TestAssignSpeaker:
    def test_no_segments_returns_unknown(self) -> None:
        m = SpeakerMerger()
        assert m.assign_speaker(100, 200) == "SPEAKER_UNKNOWN"

    def test_containment_match(self) -> None:
        m = SpeakerMerger()
        m.update_segments([_seg("SPEAKER_00", 0, 1000)])
        assert m.assign_speaker(100, 200) == "SPEAKER_00"

    def test_exact_start_boundary(self) -> None:
        m = SpeakerMerger()
        m.update_segments([_seg("SPEAKER_00", 0, 1000)])
        assert m.assign_speaker(0, 100) == "SPEAKER_00"

    def test_exact_end_boundary(self) -> None:
        m = SpeakerMerger()
        m.update_segments([_seg("SPEAKER_00", 0, 1000)])
        assert m.assign_speaker(1000, 1100) == "SPEAKER_00"

    def test_between_segments_gets_nearest(self) -> None:
        m = SpeakerMerger()
        m.update_segments([
            _seg("SPEAKER_00", 0, 1000),
            _seg("SPEAKER_01", 2000, 3000),
        ])
        # Token at 1200-1300 — closer to SPEAKER_00 (end=1000) than SPEAKER_01 (start=2000)
        assert m.assign_speaker(1200, 1300) == "SPEAKER_00"

    def test_between_segments_closer_to_second(self) -> None:
        m = SpeakerMerger()
        m.update_segments([
            _seg("SPEAKER_00", 0, 1000),
            _seg("SPEAKER_01", 2000, 3000),
        ])
        # Token at 1800-1900 — closer to SPEAKER_01
        assert m.assign_speaker(1800, 1900) == "SPEAKER_01"

    def test_multiple_speakers_selects_correct(self) -> None:
        m = SpeakerMerger()
        m.update_segments([
            _seg("SPEAKER_00", 0, 1000),
            _seg("SPEAKER_01", 1000, 2000),
            _seg("SPEAKER_02", 2000, 3000),
        ])
        assert m.assign_speaker(500, 600) == "SPEAKER_00"
        assert m.assign_speaker(1500, 1600) == "SPEAKER_01"
        assert m.assign_speaker(2500, 2600) == "SPEAKER_02"

    def test_update_replaces_segments(self) -> None:
        m = SpeakerMerger()
        m.update_segments([_seg("SPEAKER_00", 0, 1000)])
        m.update_segments([_seg("SPEAKER_99", 0, 1000)])
        assert m.assign_speaker(500, 600) == "SPEAKER_99"


# ── TestMerge ────────────────────────────────────────────────

class TestMerge:
    def test_merge_assigns_speaker(self) -> None:
        m = SpeakerMerger()
        m.update_segments([_seg("SPEAKER_00", 0, 5000)])
        enriched = m.merge([_tok(100, 200)])
        assert len(enriched) == 1
        assert enriched[0].speaker_id == "SPEAKER_00"
        assert enriched[0].text == "hello"

    def test_merge_multiple_tokens(self) -> None:
        m = SpeakerMerger()
        m.update_segments([
            _seg("SPEAKER_00", 0, 1000),
            _seg("SPEAKER_01", 1000, 2000),
        ])
        enriched = m.merge([_tok(500, 600), _tok(1500, 1600)])
        assert enriched[0].speaker_id == "SPEAKER_00"
        assert enriched[1].speaker_id == "SPEAKER_01"

    def test_merge_empty_tokens(self) -> None:
        m = SpeakerMerger()
        m.update_segments([_seg("SPEAKER_00", 0, 1000)])
        assert m.merge([]) == []

    def test_merge_preserves_token_fields(self) -> None:
        m = SpeakerMerger()
        m.update_segments([_seg("SPEAKER_00", 0, 5000)])
        enriched = m.merge([{
            "text": "world",
            "is_final": False,
            "start_ms": 100,
            "end_ms": 200,
            "confidence": 0.75,
            "language": "fr",
        }])
        tok = enriched[0]
        assert tok.text == "world"
        assert tok.is_final is False
        assert tok.confidence == 0.75
        assert tok.language == "fr"


# ── TestClear ────────────────────────────────────────────────

class TestClear:
    def test_clear_removes_segments(self) -> None:
        m = SpeakerMerger()
        m.update_segments([_seg("SPEAKER_00", 0, 1000)])
        m.clear()
        assert m.assign_speaker(500, 600) == "SPEAKER_UNKNOWN"


# ── TestEnrichedToken ────────────────────────────────────────

class TestEnrichedToken:
    def test_creation(self) -> None:
        et = EnrichedToken(
            text="hi",
            is_final=True,
            start_ms=0,
            end_ms=100,
            confidence=0.9,
            language="en",
            speaker_id="SPEAKER_00",
        )
        assert et.text == "hi"
        assert et.speaker_id == "SPEAKER_00"

    def test_frozen(self) -> None:
        et = EnrichedToken(
            text="hi",
            is_final=True,
            start_ms=0,
            end_ms=100,
            confidence=0.9,
            language="en",
            speaker_id="SPEAKER_00",
        )
        with pytest.raises(AttributeError):
            et.text = "bye"  # type: ignore[misc]
