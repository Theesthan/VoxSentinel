"""
pyannote.audio 3.x pipeline wrapper for VoxSentinel.

Loads the pyannote/speaker-diarization-3.1 pipeline once at startup using
the HuggingFace token (``TG_HF_TOKEN``).  Inference is offloaded to a
thread via ``asyncio.to_thread()`` so the event loop is never blocked.
"""

from __future__ import annotations

import asyncio
import io
import wave
from dataclasses import dataclass

import numpy as np
import structlog
import torch
from pyannote.audio import Pipeline

logger = structlog.get_logger()

# ── Constants ────────────────────────────────────────────────
SAMPLE_RATE = 16_000  # 16 kHz mono PCM expected
BYTES_PER_SAMPLE = 2  # 16-bit signed
MODEL_ID = "pyannote/speaker-diarization-3.1"


@dataclass(frozen=True, slots=True)
class SpeakerSegment:
    """A speaker turn identified by diarization.

    Attributes:
        speaker_id: Label such as ``SPEAKER_00``, ``SPEAKER_01``, etc.
        start_ms: Segment start offset in milliseconds.
        end_ms: Segment end offset in milliseconds.
    """

    speaker_id: str
    start_ms: int
    end_ms: int


class PyannotePipeline:
    """Wrapper around the pyannote.audio speaker diarization pipeline.

    The model is loaded **once** during ``load()`` and cached for the
    lifetime of the service.

    Args:
        hf_token: HuggingFace API token used to download the gated model.
                  Falls back to the ``TG_HF_TOKEN`` environment variable.
        device: PyTorch device string (``"cpu"`` or ``"cuda"``).
    """

    def __init__(
        self,
        hf_token: str | None = None,
        device: str | None = None,
    ) -> None:
        self._hf_token = hf_token
        self._device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self._pipeline: Pipeline | None = None

    # ── Lifecycle ─────────────────────────────────────────────

    def load(self) -> None:
        """Download / load the pyannote pipeline once (blocking).

        This should be called during service startup, **not** per-request.
        If the Hugging Face token is missing or the model cannot be
        downloaded, the service starts in degraded mode and logs a warning.
        """
        if self._pipeline is not None:
            return

        import os

        token = self._hf_token or os.environ.get("TG_HF_TOKEN", "")
        if not token:
            logger.warning(
                "pyannote_skipped",
                reason="TG_HF_TOKEN not set – diarization will return empty results",
            )
            return

        try:
            logger.info("pyannote_loading", model=MODEL_ID, device=self._device)
            self._pipeline = Pipeline.from_pretrained(MODEL_ID, token=token)
            self._pipeline.to(torch.device(self._device))
            logger.info("pyannote_loaded", model=MODEL_ID, device=self._device)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "pyannote_load_failed",
                error=str(exc),
                hint="Ensure TG_HF_TOKEN is valid and you accepted the model terms "
                "at https://hf.co/pyannote/speaker-diarization-3.1",
            )
            self._pipeline = None

    @property
    def is_ready(self) -> bool:
        """Return ``True`` if the pipeline has been loaded."""
        return self._pipeline is not None

    # ── Inference ────────────────────────────────────────────

    def _diarize_sync(self, audio_bytes: bytes) -> list[SpeakerSegment]:
        """Run diarization synchronously (called via ``to_thread``)."""
        if self._pipeline is None:
            raise RuntimeError("Pipeline not loaded. Call load() first.")

        # Convert raw 16-bit PCM → WAV in-memory so pyannote can read it.
        wav_buf = io.BytesIO()
        with wave.open(wav_buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(BYTES_PER_SAMPLE)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(audio_bytes)
        wav_buf.seek(0)

        # pyannote accepts a dict with "waveform" and "sample_rate" keys
        samples = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        waveform = torch.from_numpy(samples).unsqueeze(0)  # (1, T)

        annotation = self._pipeline(
            {"waveform": waveform, "sample_rate": SAMPLE_RATE}
        )

        segments: list[SpeakerSegment] = []
        for turn, _track, speaker in annotation.itertracks(yield_label=True):
            segments.append(
                SpeakerSegment(
                    speaker_id=speaker,
                    start_ms=int(turn.start * 1000),
                    end_ms=int(turn.end * 1000),
                )
            )
        return segments

    async def diarize(self, audio_bytes: bytes) -> list[SpeakerSegment]:
        """Run speaker diarization on raw 16 kHz 16-bit mono PCM.

        The heavy inference is offloaded to a worker thread so the
        event loop remains responsive.

        Args:
            audio_bytes: Raw PCM audio bytes (16 kHz, 16-bit, mono).

        Returns:
            Sorted list of ``SpeakerSegment`` objects.
        """
        return await asyncio.to_thread(self._diarize_sync, audio_bytes)
