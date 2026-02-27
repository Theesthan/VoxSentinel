"""
Tests for the Deepgram Nova-2 ASR engine.

Validates WebSocket connection handling, chunk streaming, and
TranscriptToken output format for the Deepgram backend.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from asr.engines.deepgram_nova2 import DeepgramNova2Engine

from conftest import make_deepgram_result


class TestDeepgramNova2Engine:
    """Tests for DeepgramNova2Engine."""

    def test_engine_name(self) -> None:
        """Engine name is 'deepgram_nova2'."""
        engine = DeepgramNova2Engine(api_key="test-key")
        assert engine.name == "deepgram_nova2"

    async def test_health_check_before_connect(self) -> None:
        """health_check returns False before connect()."""
        engine = DeepgramNova2Engine(api_key="test-key")
        assert await engine.health_check() is False

    async def test_connect_success(
        self,
        mock_deepgram_client: MagicMock,
        mock_deepgram_connection: AsyncMock,
    ) -> None:
        """connect() establishes a live WebSocket connection."""
        engine = DeepgramNova2Engine(api_key="test-key")

        with patch("asr.engines.deepgram_nova2.DeepgramClient", return_value=mock_deepgram_client):
            await engine.connect()

        assert await engine.health_check() is True
        mock_deepgram_connection.start.assert_awaited_once()
        # Verify event handlers were registered.
        assert mock_deepgram_connection.on.call_count == 3

    async def test_connect_failure(
        self,
        mock_deepgram_client: MagicMock,
        mock_deepgram_connection: AsyncMock,
    ) -> None:
        """connect() raises RuntimeError when start returns falsy."""
        mock_deepgram_connection.start = AsyncMock(return_value=False)
        engine = DeepgramNova2Engine(api_key="test-key")

        with patch("asr.engines.deepgram_nova2.DeepgramClient", return_value=mock_deepgram_client):
            with pytest.raises(RuntimeError, match="Failed to start"):
                await engine.connect()

        assert await engine.health_check() is False

    async def test_disconnect(
        self,
        mock_deepgram_client: MagicMock,
        mock_deepgram_connection: AsyncMock,
    ) -> None:
        """disconnect() closes the WebSocket and marks engine disconnected."""
        engine = DeepgramNova2Engine(api_key="test-key")

        with patch("asr.engines.deepgram_nova2.DeepgramClient", return_value=mock_deepgram_client):
            await engine.connect()
            await engine.disconnect()

        assert await engine.health_check() is False
        mock_deepgram_connection.finish.assert_awaited_once()

    async def test_disconnect_handles_error(
        self,
        mock_deepgram_client: MagicMock,
        mock_deepgram_connection: AsyncMock,
    ) -> None:
        """disconnect() handles finish() errors gracefully."""
        mock_deepgram_connection.finish = AsyncMock(side_effect=Exception("ws error"))
        engine = DeepgramNova2Engine(api_key="test-key")

        with patch("asr.engines.deepgram_nova2.DeepgramClient", return_value=mock_deepgram_client):
            await engine.connect()
            await engine.disconnect()  # Should not raise

        assert await engine.health_check() is False

    async def test_stream_audio_not_connected_raises(self) -> None:
        """stream_audio raises RuntimeError when not connected."""
        engine = DeepgramNova2Engine(api_key="test-key")

        with pytest.raises(RuntimeError, match="not connected"):
            async for _ in engine.stream_audio(b"\x00\x00"):
                pass

    async def test_stream_audio_sends_chunk(
        self,
        mock_deepgram_client: MagicMock,
        mock_deepgram_connection: AsyncMock,
        sample_pcm_bytes: bytes,
    ) -> None:
        """stream_audio sends the chunk via the connection."""
        engine = DeepgramNova2Engine(api_key="test-key")

        with patch("asr.engines.deepgram_nova2.DeepgramClient", return_value=mock_deepgram_client):
            await engine.connect()
            tokens = [t async for t in engine.stream_audio(sample_pcm_bytes)]

        mock_deepgram_connection.send.assert_awaited_once_with(sample_pcm_bytes)
        # No tokens in queue yet (no callback fired).
        assert tokens == []

    async def test_on_transcript_produces_token(
        self,
        mock_deepgram_client: MagicMock,
        mock_deepgram_connection: AsyncMock,
    ) -> None:
        """_on_transcript callback parses a result into a TranscriptToken."""
        engine = DeepgramNova2Engine(api_key="test-key")

        with patch("asr.engines.deepgram_nova2.DeepgramClient", return_value=mock_deepgram_client):
            await engine.connect()

        result = make_deepgram_result(
            transcript="testing one two",
            confidence=0.96,
            is_final=True,
            start=1.0,
            duration=1.5,
            words=[
                {"word": "testing", "start": 1.0, "end": 1.3, "confidence": 0.95},
                {"word": "one", "start": 1.4, "end": 1.6, "confidence": 0.97},
                {"word": "two", "start": 1.7, "end": 2.0, "confidence": 0.96},
            ],
        )

        await engine._on_transcript(None, result)

        assert not engine._token_queue.empty()
        token = engine._token_queue.get_nowait()
        assert token.text == "testing one two"
        assert token.is_final is True
        assert token.confidence == 0.96
        assert len(token.word_timestamps) == 3
        assert token.word_timestamps[0].word == "testing"
        assert token.word_timestamps[0].start_ms == 1000
        assert token.word_timestamps[0].end_ms == 1300

    async def test_on_transcript_empty_transcript_ignored(
        self,
        mock_deepgram_client: MagicMock,
        mock_deepgram_connection: AsyncMock,
    ) -> None:
        """_on_transcript ignores results with empty transcript text."""
        engine = DeepgramNova2Engine(api_key="test-key")

        with patch("asr.engines.deepgram_nova2.DeepgramClient", return_value=mock_deepgram_client):
            await engine.connect()

        result = make_deepgram_result(transcript="")
        await engine._on_transcript(None, result)
        assert engine._token_queue.empty()

    async def test_on_transcript_no_alternatives_ignored(
        self,
        mock_deepgram_client: MagicMock,
        mock_deepgram_connection: AsyncMock,
    ) -> None:
        """_on_transcript ignores results with empty alternatives."""
        engine = DeepgramNova2Engine(api_key="test-key")

        with patch("asr.engines.deepgram_nova2.DeepgramClient", return_value=mock_deepgram_client):
            await engine.connect()

        result = MagicMock()
        result.channel.alternatives = []
        await engine._on_transcript(None, result)
        assert engine._token_queue.empty()

    async def test_on_transcript_handles_parse_error(
        self,
        mock_deepgram_client: MagicMock,
        mock_deepgram_connection: AsyncMock,
    ) -> None:
        """_on_transcript handles unexpected result structures gracefully."""
        engine = DeepgramNova2Engine(api_key="test-key")

        with patch("asr.engines.deepgram_nova2.DeepgramClient", return_value=mock_deepgram_client):
            await engine.connect()

        # Pass a broken result — should not raise.
        result = MagicMock()
        result.channel = None  # Will cause AttributeError
        await engine._on_transcript(None, result)
        assert engine._token_queue.empty()

    async def test_on_error_sets_disconnected(
        self,
        mock_deepgram_client: MagicMock,
        mock_deepgram_connection: AsyncMock,
    ) -> None:
        """_on_error marks the engine as disconnected."""
        engine = DeepgramNova2Engine(api_key="test-key")

        with patch("asr.engines.deepgram_nova2.DeepgramClient", return_value=mock_deepgram_client):
            await engine.connect()
            assert await engine.health_check() is True

        await engine._on_error(None, "timeout")
        assert await engine.health_check() is False

    async def test_on_close_sets_disconnected(
        self,
        mock_deepgram_client: MagicMock,
        mock_deepgram_connection: AsyncMock,
    ) -> None:
        """_on_close marks the engine as disconnected."""
        engine = DeepgramNova2Engine(api_key="test-key")

        with patch("asr.engines.deepgram_nova2.DeepgramClient", return_value=mock_deepgram_client):
            await engine.connect()

        await engine._on_close(None, "normal closure")
        assert await engine.health_check() is False

    async def test_stream_audio_yields_queued_tokens(
        self,
        mock_deepgram_client: MagicMock,
        mock_deepgram_connection: AsyncMock,
        sample_pcm_bytes: bytes,
    ) -> None:
        """stream_audio yields tokens that were queued by the callback."""
        engine = DeepgramNova2Engine(api_key="test-key")

        with patch("asr.engines.deepgram_nova2.DeepgramClient", return_value=mock_deepgram_client):
            await engine.connect()

        # Simulate callback firing before stream_audio drains.
        result = make_deepgram_result(transcript="pre-queued")
        await engine._on_transcript(None, result)

        tokens = [t async for t in engine.stream_audio(sample_pcm_bytes)]
        assert len(tokens) == 1
        assert tokens[0].text == "pre-queued"

    async def test_partial_and_final_tokens(
        self,
        mock_deepgram_client: MagicMock,
        mock_deepgram_connection: AsyncMock,
        sample_pcm_bytes: bytes,
    ) -> None:
        """Both partial and final tokens are yielded correctly."""
        engine = DeepgramNova2Engine(api_key="test-key")

        with patch("asr.engines.deepgram_nova2.DeepgramClient", return_value=mock_deepgram_client):
            await engine.connect()

        partial = make_deepgram_result(transcript="hel", is_final=False)
        final = make_deepgram_result(transcript="hello", is_final=True)
        await engine._on_transcript(None, partial)
        await engine._on_transcript(None, final)

        tokens = [t async for t in engine.stream_audio(sample_pcm_bytes)]
        assert len(tokens) == 2
        assert tokens[0].is_final is False
        assert tokens[1].is_final is True
