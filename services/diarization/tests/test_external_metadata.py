"""Tests for diarization.external_metadata module."""

from __future__ import annotations

from diarization.external_metadata import ExternalMetadataStore, SpeakerInfo


class TestExternalMetadataStore:
    def test_resolve_without_metadata_returns_label(self) -> None:
        store = ExternalMetadataStore()
        assert store.resolve("stream-1", "SPEAKER_00") == "SPEAKER_00"

    def test_resolve_with_metadata_returns_display_name(self) -> None:
        store = ExternalMetadataStore()
        store.load("stream-1", {
            "SPEAKER_00": SpeakerInfo(label="SPEAKER_00", display_name="Alice", role="agent"),
        })
        assert store.resolve("stream-1", "SPEAKER_00") == "Alice"

    def test_resolve_unknown_speaker_returns_label(self) -> None:
        store = ExternalMetadataStore()
        store.load("stream-1", {
            "SPEAKER_00": SpeakerInfo(label="SPEAKER_00", display_name="Alice"),
        })
        assert store.resolve("stream-1", "SPEAKER_01") == "SPEAKER_01"

    def test_resolve_unknown_stream_returns_label(self) -> None:
        store = ExternalMetadataStore()
        store.load("stream-1", {
            "SPEAKER_00": SpeakerInfo(label="SPEAKER_00", display_name="Alice"),
        })
        assert store.resolve("stream-X", "SPEAKER_00") == "SPEAKER_00"

    def test_remove_clears_stream_metadata(self) -> None:
        store = ExternalMetadataStore()
        store.load("stream-1", {
            "SPEAKER_00": SpeakerInfo(label="SPEAKER_00", display_name="Alice"),
        })
        store.remove("stream-1")
        assert store.resolve("stream-1", "SPEAKER_00") == "SPEAKER_00"

    def test_clear_removes_all(self) -> None:
        store = ExternalMetadataStore()
        store.load("stream-1", {
            "SPEAKER_00": SpeakerInfo(label="SPEAKER_00", display_name="Alice"),
        })
        store.load("stream-2", {
            "SPEAKER_00": SpeakerInfo(label="SPEAKER_00", display_name="Bob"),
        })
        store.clear()
        assert store.resolve("stream-1", "SPEAKER_00") == "SPEAKER_00"
        assert store.resolve("stream-2", "SPEAKER_00") == "SPEAKER_00"

    def test_load_overwrites_existing(self) -> None:
        store = ExternalMetadataStore()
        store.load("stream-1", {
            "SPEAKER_00": SpeakerInfo(label="SPEAKER_00", display_name="Alice"),
        })
        store.load("stream-1", {
            "SPEAKER_00": SpeakerInfo(label="SPEAKER_00", display_name="Bob"),
        })
        assert store.resolve("stream-1", "SPEAKER_00") == "Bob"

    def test_speaker_info_role(self) -> None:
        info = SpeakerInfo(label="SPEAKER_00", display_name="Alice", role="agent")
        assert info.role == "agent"

    def test_speaker_info_role_default(self) -> None:
        info = SpeakerInfo(label="SPEAKER_00", display_name="Alice")
        assert info.role is None
