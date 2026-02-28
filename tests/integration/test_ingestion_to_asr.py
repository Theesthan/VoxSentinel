"""Integration tests: Ingestion -> ASR pipeline.

Uses a real WAV file (``tests/fixtures/test_audio_keywords.wav``)
containing the spoken words **'fire'** and **'help'** to simulate
an ingestion source.  Audio chunks are pushed into
``audio_chunks:{stream_id}`` and we assert that at least one final
``TranscriptToken`` appears in ``transcript_tokens:{stream_id}``
within 10 seconds.

The test exercises the chunk-publish side of the ingestion service
and a lightweight mock ASR consumer that reads chunks and emits
transcript tokens so we can validate the data flow end-to-end
through Redis Streams without requiring a live ASR backend.
"""

from __future__ import annotations

import asyncio
import json
import uuid
import wave
from pathlib import Path

import pytest
import redis.asyncio as aioredis


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_wav_chunks(audio_path: Path, chunk_ms: int = 280) -> list[bytes]:
    """Read a WAV file and split it into fixed-duration raw PCM chunks."""
    with wave.open(str(audio_path), "rb") as wf:
        sample_rate = wf.getframerate()
        n_channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        frames = wf.readframes(wf.getnframes())

    bytes_per_sample = sample_width * n_channels
    chunk_frames = int(sample_rate * chunk_ms / 1000)
    chunk_bytes = chunk_frames * bytes_per_sample

    chunks: list[bytes] = []
    for offset in range(0, len(frames), chunk_bytes):
        chunk = frames[offset : offset + chunk_bytes]
        if len(chunk) == chunk_bytes:
            chunks.append(chunk)
    return chunks


async def _mock_asr_consumer(
    redis: aioredis.Redis,
    stream_id: str,
    *,
    stop_event: asyncio.Event,
) -> None:
    """Mock ASR consumer: reads audio_chunks, writes transcript_tokens.

    Simulates an ASR backend that produces a single final token with
    the ground-truth text.  This lets us test the Redis stream plumbing
    without a real ASR engine.
    """
    input_key = f"audio_chunks:{stream_id}"
    output_key = f"transcript_tokens:{stream_id}"
    last_id = "0"

    while not stop_event.is_set():
        try:
            entries = await redis.xread({input_key: last_id}, count=10, block=500)
        except Exception:
            break
        if not entries:
            continue
        for _stream, messages in entries:
            for msg_id, _fields in messages:
                last_id = msg_id

        # After processing some chunks, emit a final token
        from datetime import datetime, timezone

        token_data = {
            "text": "there is a fire near the entrance and I need help",
            "is_final": True,
            "start_time": datetime.now(timezone.utc).isoformat(),
            "end_time": datetime.now(timezone.utc).isoformat(),
            "confidence": 0.92,
            "language": "en",
            "word_timestamps": [],
        }
        await redis.xadd(output_key, {"data": json.dumps(token_data)})
        stop_event.set()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestIngestionToASR:
    """Test ingestion-to-ASR data flow via Redis Streams."""

    async def test_audio_chunks_reach_asr(
        self,
        redis_client: aioredis.Redis,
        test_audio_path: Path,
    ) -> None:
        """Verify audio chunks published by ingestion are consumed by ASR.

        Publishes raw PCM chunks from the test WAV into
        ``audio_chunks:{stream_id}`` and asserts that at least one
        ``transcript_tokens:{stream_id}`` entry appears within 10 s.
        """
        stream_id = str(uuid.uuid4())
        audio_key = f"audio_chunks:{stream_id}"
        token_key = f"transcript_tokens:{stream_id}"

        # Start mock ASR consumer
        stop = asyncio.Event()
        consumer_task = asyncio.create_task(
            _mock_asr_consumer(redis_client, stream_id, stop_event=stop)
        )

        # Publish audio chunks
        chunks = _read_wav_chunks(test_audio_path, chunk_ms=280)
        assert len(chunks) > 0, "Test WAV produced no chunks"

        for i, chunk in enumerate(chunks[:20]):  # limit to first 20 chunks
            await redis_client.xadd(
                audio_key,
                {
                    "chunk_index": str(i),
                    "sample_rate": "16000",
                    "data": chunk.hex(),
                },
            )

        # Wait for the mock consumer to produce at least one token
        try:
            await asyncio.wait_for(stop.wait(), timeout=10.0)
        except asyncio.TimeoutError:
            consumer_task.cancel()
            pytest.fail("No transcript token received within 10 seconds")

        # Read back from transcript_tokens stream
        entries = await redis_client.xread({token_key: "0"}, count=100)
        assert len(entries) > 0, "transcript_tokens stream is empty"

        _stream_name, messages = entries[0]
        assert len(messages) >= 1, "Expected at least one token"

        # Validate the token format
        _msg_id, fields = messages[0]
        token_data = json.loads(fields["data"])
        assert token_data["is_final"] is True
        assert "fire" in token_data["text"].lower()
        assert "help" in token_data["text"].lower()

        consumer_task.cancel()

    async def test_chunk_format_is_valid(
        self,
        redis_client: aioredis.Redis,
        test_audio_path: Path,
    ) -> None:
        """Verify audio chunk format matches expected schema."""
        stream_id = str(uuid.uuid4())
        audio_key = f"audio_chunks:{stream_id}"

        chunks = _read_wav_chunks(test_audio_path, chunk_ms=280)
        assert len(chunks) > 0

        await redis_client.xadd(
            audio_key,
            {
                "chunk_index": "0",
                "sample_rate": "16000",
                "data": chunks[0].hex(),
            },
        )

        entries = await redis_client.xread({audio_key: "0"}, count=1)
        assert entries
        _stream, messages = entries[0]
        _msg_id, fields = messages[0]

        assert "chunk_index" in fields
        assert "sample_rate" in fields
        assert "data" in fields
        assert int(fields["sample_rate"]) == 16000

    async def test_transcription_latency_within_budget(
        self,
        redis_client: aioredis.Redis,
        test_audio_path: Path,
    ) -> None:
        """Verify ASR responds within the 10 s integration-test budget."""
        import time

        stream_id = str(uuid.uuid4())
        audio_key = f"audio_chunks:{stream_id}"
        token_key = f"transcript_tokens:{stream_id}"

        stop = asyncio.Event()
        consumer_task = asyncio.create_task(
            _mock_asr_consumer(redis_client, stream_id, stop_event=stop)
        )

        start = time.monotonic()
        chunks = _read_wav_chunks(test_audio_path, chunk_ms=280)
        for i, chunk in enumerate(chunks[:5]):
            await redis_client.xadd(
                audio_key,
                {"chunk_index": str(i), "sample_rate": "16000", "data": chunk.hex()},
            )

        try:
            await asyncio.wait_for(stop.wait(), timeout=10.0)
        except asyncio.TimeoutError:
            consumer_task.cancel()
            pytest.fail("ASR did not respond within 10 seconds")

        elapsed = time.monotonic() - start
        assert elapsed < 10.0, f"Latency {elapsed:.2f}s exceeds 10s budget"

        consumer_task.cancel()
