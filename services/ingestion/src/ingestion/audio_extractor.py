"""
Audio extraction module for VoxSentinel ingestion service.

Uses PyAV bindings to decode audio from RTSP/HLS/DASH/file sources,
resample to 16 kHz mono PCM (16-bit signed LE), and yield raw PCM
byte frames.  Never shells out to FFmpeg via subprocess.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import av
import av.audio.resampler
import numpy as np
import structlog

logger = structlog.get_logger()

# Target PCM format
TARGET_SAMPLE_RATE: int = 16_000
TARGET_LAYOUT: str = "mono"
TARGET_FORMAT: str = "s16"  # signed 16-bit little-endian


async def extract_audio(
    source_url: str,
    *,
    stream_id: str = "",
    options: dict[str, str] | None = None,
) -> AsyncIterator[bytes]:
    """Open *source_url* with PyAV, decode audio, resample and yield PCM bytes.

    The function opens the container, selects the first audio stream,
    creates an ``AudioResampler`` targeting 16 kHz mono s16, and yields
    the raw ``bytes`` of every resampled frame.

    This is an ``async`` generator so callers can ``await`` between
    frames without blocking the event loop.  The heavy PyAV decode
    work is CPU-bound but each frame is small enough that cooperative
    yielding keeps latency acceptable.

    Args:
        source_url: RTSP, HLS, DASH URL or local file path.
        stream_id: Used only for structured logging context.
        options: Extra ``av.open`` options (e.g. RTSP transport).

    Yields:
        Raw PCM ``bytes`` blocks (16 kHz, mono, s16).

    Raises:
        av.error.ExitError: When the remote stream terminates.
        av.error.InvalidDataError: On corrupt/unreachable source.
    """
    log = logger.bind(stream_id=stream_id, source_url=source_url)
    log.info("audio_extractor_opening")

    av_options: dict[str, str] = {
        "rtsp_transport": "tcp",
        "analyzeduration": "2000000",
        "probesize": "2000000",
    }
    if options:
        av_options.update(options)

    container: av.container.InputContainer = av.open(
        source_url,
        options=av_options,
        timeout=10.0,
    )

    try:
        audio_stream = _select_audio_stream(container)
        resampler = av.audio.resampler.AudioResampler(
            format=TARGET_FORMAT,
            layout=TARGET_LAYOUT,
            rate=TARGET_SAMPLE_RATE,
        )

        log.info(
            "audio_extractor_started",
            codec=audio_stream.codec_context.name,
            sample_rate=audio_stream.codec_context.sample_rate,
            channels=audio_stream.codec_context.channels,
        )

        for packet in container.demux(audio_stream):
            for frame in packet.decode():
                resampled_frames = resampler.resample(frame)
                for rs_frame in resampled_frames:
                    pcm_bytes: bytes = rs_frame.to_ndarray().astype(np.int16).tobytes()
                    yield pcm_bytes

    finally:
        container.close()
        log.info("audio_extractor_closed")


def _select_audio_stream(container: av.container.InputContainer) -> Any:
    """Return the first audio stream in *container*.

    Args:
        container: An opened PyAV input container.

    Returns:
        The first audio ``av.stream.Stream``.

    Raises:
        ValueError: If the container has no audio stream.
    """
    audio_streams = container.streams.audio
    if not audio_streams:
        raise ValueError(f"No audio stream found in {container.name}")
    return audio_streams[0]
