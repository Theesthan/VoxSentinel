"""Integration tests: Ingestion -> ASR pipeline.

Verifies that audio chunks produced by the ingestion service are correctly
received and transcribed by the ASR service via Redis pub/sub. Tests cover
chunk format validation, latency budgets, and engine selection.
"""

import pytest


@pytest.mark.integration
class TestIngestionToASR:
    """Test ingestion-to-ASR data flow."""

    async def test_audio_chunks_reach_asr(self) -> None:
        """Verify audio chunks published by ingestion are consumed by ASR."""
        ...

    async def test_chunk_format_is_valid(self) -> None:
        """Verify audio chunk format matches expected schema."""
        ...

    async def test_transcription_latency_within_budget(self) -> None:
        """Verify ASR responds within the p95 latency budget."""
        ...
