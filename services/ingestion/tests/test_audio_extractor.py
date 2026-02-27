"""
Tests for the audio extractor module.

Validates audio decoding, resampling to 16 kHz mono PCM, and graceful
error handling — all with a fully mocked PyAV layer so no real
RTSP/HLS connection is needed.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from ingestion.audio_extractor import (
    TARGET_FORMAT,
    TARGET_LAYOUT,
    TARGET_SAMPLE_RATE,
    _select_audio_stream,
    extract_audio,
)


# ── helpers ──


def _make_mock_frame(samples: int = 1600) -> MagicMock:
    """Create a mock audio frame whose ndarray matches 16-bit PCM."""
    frame = MagicMock()
    pcm = np.zeros(samples, dtype=np.int16)
    frame.to_ndarray.return_value = pcm.astype(np.int16)
    return frame


def _make_resampled(frames: list[MagicMock]) -> list[MagicMock]:
    return frames


# ── tests ──


class TestExtractAudio:
    """Test suite for ``extract_audio``."""

    @pytest.mark.asyncio
    async def test_yields_pcm_bytes(self) -> None:
        """extract_audio should yield bytes from resampled frames."""
        mock_frame = _make_mock_frame(800)
        mock_resampled_frame = _make_mock_frame(800)

        mock_packet = MagicMock()
        mock_packet.decode.return_value = [mock_frame]

        mock_audio_stream = MagicMock()
        mock_container = MagicMock()
        mock_container.streams.audio = [mock_audio_stream]
        mock_container.demux.return_value = [mock_packet]

        mock_resampler = MagicMock()
        mock_resampler.resample.return_value = [mock_resampled_frame]

        with (
            patch("ingestion.audio_extractor.av.open", return_value=mock_container),
            patch(
                "ingestion.audio_extractor.av.audio.resampler.AudioResampler",
                return_value=mock_resampler,
            ),
        ):
            chunks: list[bytes] = []
            async for pcm_bytes in extract_audio("rtsp://fake", stream_id="test"):
                chunks.append(pcm_bytes)

        assert len(chunks) == 1
        assert isinstance(chunks[0], bytes)
        assert len(chunks[0]) == 800 * 2  # int16 = 2 bytes per sample
        mock_container.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_closes_container_on_error(self) -> None:
        """Container should be closed even if decoding raises."""
        mock_audio_stream = MagicMock()
        mock_container = MagicMock()
        mock_container.streams.audio = [mock_audio_stream]
        mock_container.demux.side_effect = RuntimeError("decode failed")

        mock_resampler = MagicMock()

        with (
            patch("ingestion.audio_extractor.av.open", return_value=mock_container),
            patch(
                "ingestion.audio_extractor.av.audio.resampler.AudioResampler",
                return_value=mock_resampler,
            ),
            pytest.raises(RuntimeError, match="decode failed"),
        ):
            async for _ in extract_audio("rtsp://bad"):
                pass  # pragma: no cover

        mock_container.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_multiple_packets_and_frames(self) -> None:
        """Should yield one block per resampled frame across packets."""
        frame1 = _make_mock_frame(160)
        frame2 = _make_mock_frame(320)

        packet1 = MagicMock()
        packet1.decode.return_value = [frame1]
        packet2 = MagicMock()
        packet2.decode.return_value = [frame2]

        mock_audio_stream = MagicMock()
        mock_container = MagicMock()
        mock_container.streams.audio = [mock_audio_stream]
        mock_container.demux.return_value = [packet1, packet2]

        mock_resampler = MagicMock()
        mock_resampler.resample.side_effect = lambda f: [f]

        with (
            patch("ingestion.audio_extractor.av.open", return_value=mock_container),
            patch(
                "ingestion.audio_extractor.av.audio.resampler.AudioResampler",
                return_value=mock_resampler,
            ),
        ):
            chunks: list[bytes] = []
            async for pcm in extract_audio("rtsp://multi"):
                chunks.append(pcm)

        assert len(chunks) == 2
        assert len(chunks[0]) == 160 * 2
        assert len(chunks[1]) == 320 * 2

    @pytest.mark.asyncio
    async def test_resampler_params(self) -> None:
        """AudioResampler should be created with 16 kHz mono s16."""
        mock_audio_stream = MagicMock()
        mock_container = MagicMock()
        mock_container.streams.audio = [mock_audio_stream]
        mock_container.demux.return_value = []

        resampler_cls = MagicMock()

        with (
            patch("ingestion.audio_extractor.av.open", return_value=mock_container),
            patch(
                "ingestion.audio_extractor.av.audio.resampler.AudioResampler",
                resampler_cls,
            ),
        ):
            async for _ in extract_audio("rtsp://params"):
                pass  # pragma: no cover

        resampler_cls.assert_called_once_with(
            format=TARGET_FORMAT,
            layout=TARGET_LAYOUT,
            rate=TARGET_SAMPLE_RATE,
        )


class TestSelectAudioStream:
    """Test suite for ``_select_audio_stream``."""

    def test_returns_first_audio_stream(self) -> None:
        """Should return the first audio stream."""
        stream_a = MagicMock()
        stream_b = MagicMock()
        container = MagicMock()
        container.streams.audio = [stream_a, stream_b]

        result = _select_audio_stream(container)
        assert result is stream_a

    def test_raises_on_no_audio(self) -> None:
        """Should raise ValueError when there is no audio stream."""
        container = MagicMock()
        container.streams.audio = []
        container.name = "test.mp4"

        with pytest.raises(ValueError, match="No audio stream"):
            _select_audio_stream(container)
