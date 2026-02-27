"""
External speaker metadata handler for VoxSentinel.

Merges platform-provided speaker metadata (real names, roles) from
meeting platform APIs with auto-generated speaker labels
(SPEAKER_00, SPEAKER_01, etc.).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SpeakerInfo:
    """Metadata for a known speaker.

    Attributes:
        label: Original diarization label (``SPEAKER_00``).
        display_name: Human-friendly name (e.g. ``"Alice"``).
        role: Optional role tag (``"agent"`` / ``"customer"``).
    """

    label: str
    display_name: str
    role: str | None = None


class ExternalMetadataStore:
    """In-memory store for external speaker metadata.

    When a meeting/contact-centre platform provides a participant
    manifest, the manifest is loaded here so that diarization labels
    can be replaced with real names/roles before downstream publish.
    """

    def __init__(self) -> None:
        # Key: stream_id → {diarization_label: SpeakerInfo}
        self._store: dict[str, dict[str, SpeakerInfo]] = {}

    def load(
        self,
        stream_id: str,
        mapping: dict[str, SpeakerInfo],
    ) -> None:
        """Register speaker metadata for a stream.

        Args:
            stream_id: Stream UUID string.
            mapping: Dict mapping diarization labels to ``SpeakerInfo``.
        """
        self._store[stream_id] = dict(mapping)

    def resolve(self, stream_id: str, speaker_label: str) -> str:
        """Return the display name for a speaker label, or the label itself.

        Args:
            stream_id: Stream UUID string.
            speaker_label: Diarization-assigned label (e.g. ``SPEAKER_00``).

        Returns:
            Display name if metadata is available, otherwise the raw label.
        """
        mapping = self._store.get(stream_id)
        if mapping and speaker_label in mapping:
            return mapping[speaker_label].display_name
        return speaker_label

    def remove(self, stream_id: str) -> None:
        """Remove metadata for a stream."""
        self._store.pop(stream_id, None)

    def clear(self) -> None:
        """Remove all stored metadata."""
        self._store.clear()
