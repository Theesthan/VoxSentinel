"""
Tests for the Whisper V3 Turbo ASR engine.

Validates self-hosted Whisper inference, chunk processing, and
TranscriptToken output format for the faster-whisper backend.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from asr.engines.whisper_v3_turbo import WhisperV3TurboEngine, _BYTES_PER_SAMPLE

from conftest import make_whisper_info, make_whisper_segment


class TestWhisperV3TurboEngine:
    """Tests for WhisperV3TurboEngine."""

    def test_engine_name(self) -> None:
        """Engine name is 'whisper_v3_turbo'."""
        engine = WhisperV3TurboEngine()
        assert engine.name == "whisper_v3_turbo"

    async def test_health_check_before_connect(self) -> None:
        """health_check returns False before connect()."""
        engine = WhisperV3TurboEngine()
        assert await engine.health_check() is False

    async def test_connect_loads_model_cpu(self) -> None:
        """connect() loads the Whisper model on CPU when CUDA unavailable."""
        mock_model = MagicMock()
        engine = WhisperV3TurboEngine(model_size="tiny")

        with patch("asr.engines.whisper_v3_turbo.WhisperModel", return_value=mock_model) as cls_mock:
            with patch("torch.cuda.is_available", return_value=False):
                await engine.connect()

        cls_mock.assert_called_once_with("tiny", device="cpu", compute_type="int8")
        assert await engine.health_check() is True

    async def test_connect_loads_model_cuda(self) -> None:
        """connect() loads the Whisper model on CUDA when available."""
        mock_model = MagicMock()
        engine = WhisperV3TurboEngine(model_size="large-v3-turbo", compute_type="float16")

        with patch("asr.engines.whisper_v3_turbo.WhisperModel", return_value=mock_model) as cls_mock:
            with patch("torch.cuda.is_available", return_value=True):
                await engine.connect()

        cls_mock.assert_called_once_with(
            "large-v3-turbo", device="cuda", compute_type="float16"
        )
        assert await engine.health_check() is True

    async def test_connect_explicit_device(self) -> None:
        """connect() uses the explicit device argument."""
        mock_model = MagicMock()
        engine = WhisperV3TurboEngine(device="cpu", compute_type="int8")

        with patch("asr.engines.whisper_v3_turbo.WhisperModel", return_value=mock_model) as cls_mock:
            await engine.connect()

        cls_mock.assert_called_once_with(
            "large-v3-turbo", device="cpu", compute_type="int8"
        )

    async def test_disconnect_clears_model(self) -> None:
        """disconnect() unloads the model and resets the buffer."""
        mock_model = MagicMock()
        mock_model.transcribe.return_value = (iter([]), make_whisper_info())
        engine = WhisperV3TurboEngine(device="cpu")

        with patch("asr.engines.whisper_v3_turbo.WhisperModel", return_value=mock_model):
            await engine.connect()
            await engine.disconnect()

        assert await engine.health_check() is False

    async def test_stream_audio_not_connected_raises(self) -> None:
        """stream_audio raises RuntimeError when model not loaded."""
        engine = WhisperV3TurboEngine()

        with pytest.raises(RuntimeError, match="not connected"):
            async for _ in engine.stream_audio(b"\x00\x00"):
                pass

    async def test_stream_audio_below_threshold_yields_nothing(
        self,
        sample_pcm_bytes: bytes,
    ) -> None:
        """stream_audio yields nothing when buffer is below accumulation threshold."""
        mock_model = MagicMock()
        engine = WhisperV3TurboEngine(accumulation_seconds=3.0, device="cpu")

        with patch("asr.engines.whisper_v3_turbo.WhisperModel", return_value=mock_model):
            await engine.connect()

        # 280 ms chunk (8960 bytes) < 3s threshold (96000 bytes).
        tokens = [t async for t in engine.stream_audio(sample_pcm_bytes)]
        assert tokens == []
        # Buffer should contain the data.
        assert len(engine._audio_buffer) == len(sample_pcm_bytes)

    async def test_stream_audio_above_threshold_yields_tokens(
        self,
        large_pcm_bytes: bytes,
    ) -> None:
        """stream_audio transcribes and yields tokens when buffer reaches threshold."""
        segment = make_whisper_segment(
            text=" hello world", start=0.0, end=1.0
        )
        info = make_whisper_info(language="en")

        mock_model = MagicMock()
        mock_model.transcribe.return_value = (iter([segment]), info)

        engine = WhisperV3TurboEngine(accumulation_seconds=3.0, device="cpu")

        with patch("asr.engines.whisper_v3_turbo.WhisperModel", return_value=mock_model):
            await engine.connect()

        tokens = [t async for t in engine.stream_audio(large_pcm_bytes)]

        assert len(tokens) == 1
        token = tokens[0]
        assert token.text == "hello world"
        assert token.is_final is True
        assert token.language == "en"
        assert len(token.word_timestamps) == 2
        assert token.word_timestamps[0].word == "hello"
        assert token.word_timestamps[1].word == "world"

    async def test_stream_audio_resets_buffer_after_transcription(
        self,
        large_pcm_bytes: bytes,
    ) -> None:
        """After transcription the audio buffer is cleared."""
        segment = make_whisper_segment()
        info = make_whisper_info()
        mock_model = MagicMock()
        mock_model.transcribe.return_value = (iter([segment]), info)

        engine = WhisperV3TurboEngine(accumulation_seconds=3.0, device="cpu")

        with patch("asr.engines.whisper_v3_turbo.WhisperModel", return_value=mock_model):
            await engine.connect()

        _ = [t async for t in engine.stream_audio(large_pcm_bytes)]
        assert len(engine._audio_buffer) == 0

    async def test_stream_audio_updates_total_samples(
        self,
        large_pcm_bytes: bytes,
    ) -> None:
        """After transcription total_samples_processed advances correctly."""
        segment = make_whisper_segment()
        info = make_whisper_info()
        mock_model = MagicMock()
        mock_model.transcribe.return_value = (iter([segment]), info)

        engine = WhisperV3TurboEngine(accumulation_seconds=3.0, device="cpu")

        with patch("asr.engines.whisper_v3_turbo.WhisperModel", return_value=mock_model):
            await engine.connect()

        _ = [t async for t in engine.stream_audio(large_pcm_bytes)]
        expected_samples = len(large_pcm_bytes) // _BYTES_PER_SAMPLE
        assert engine._total_samples_processed == expected_samples

    async def test_word_timestamps_include_offset(self) -> None:
        """Word timestamps account for previously processed audio offset."""
        segment = make_whisper_segment(
            text=" hi",
            start=0.0,
            end=0.5,
            words=[{"word": " hi", "start": 0.0, "end": 0.5, "probability": 0.9}],
        )
        info = make_whisper_info()
        mock_model = MagicMock()
        mock_model.transcribe.return_value = (iter([segment]), info)

        # Small threshold for easier testing.
        engine = WhisperV3TurboEngine(accumulation_seconds=0.1, device="cpu")

        with patch("asr.engines.whisper_v3_turbo.WhisperModel", return_value=mock_model):
            await engine.connect()

        # First batch: offset 0.
        chunk = b"\x00\x01" * 1600  # 0.1 s
        tokens1 = [t async for t in engine.stream_audio(chunk)]
        assert tokens1[0].word_timestamps[0].start_ms == 0

        # Second batch: offset = first batch samples / sample_rate.
        mock_model.transcribe.return_value = (
            iter([make_whisper_segment(
                text=" bye",
                start=0.0,
                end=0.5,
                words=[{"word": " bye", "start": 0.0, "end": 0.5, "probability": 0.9}],
            )]),
            info,
        )
        tokens2 = [t async for t in engine.stream_audio(chunk)]
        assert len(tokens2) == 1
        # Offset should be 0.1 s = 100 ms.
        assert tokens2[0].word_timestamps[0].start_ms == 100

    async def test_confidence_is_average_of_word_probabilities(
        self,
        large_pcm_bytes: bytes,
    ) -> None:
        """Token confidence is the mean of word probabilities."""
        segment = make_whisper_segment(
            words=[
                {"word": " a", "start": 0.0, "end": 0.3, "probability": 0.8},
                {"word": " b", "start": 0.4, "end": 0.6, "probability": 1.0},
            ],
        )
        info = make_whisper_info()
        mock_model = MagicMock()
        mock_model.transcribe.return_value = (iter([segment]), info)

        engine = WhisperV3TurboEngine(accumulation_seconds=3.0, device="cpu")

        with patch("asr.engines.whisper_v3_turbo.WhisperModel", return_value=mock_model):
            await engine.connect()

        tokens = [t async for t in engine.stream_audio(large_pcm_bytes)]
        assert abs(tokens[0].confidence - 0.9) < 0.001

    async def test_multiple_segments(self, large_pcm_bytes: bytes) -> None:
        """Multiple segments from one transcription yield multiple tokens."""
        seg1 = make_whisper_segment(text=" first", start=0.0, end=0.5)
        seg2 = make_whisper_segment(text=" second", start=0.6, end=1.2)
        info = make_whisper_info()
        mock_model = MagicMock()
        mock_model.transcribe.return_value = (iter([seg1, seg2]), info)

        engine = WhisperV3TurboEngine(accumulation_seconds=3.0, device="cpu")

        with patch("asr.engines.whisper_v3_turbo.WhisperModel", return_value=mock_model):
            await engine.connect()

        tokens = [t async for t in engine.stream_audio(large_pcm_bytes)]
        assert len(tokens) == 2
        assert tokens[0].text == "first"
        assert tokens[1].text == "second"
