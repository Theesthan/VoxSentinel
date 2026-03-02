"""
Silero VAD wrapper for VoxSentinel.

Loads the Silero VAD model via ``torch.hub.load`` and exposes a
simple async ``classify`` method returning speech probability
(0.0–1.0) for a raw PCM chunk.
"""

from __future__ import annotations

import threading

import structlog
import torch
import numpy as np

logger = structlog.get_logger()

# Audio constants matching the ingestion service output.
SAMPLE_RATE: int = 16_000
# Silero VAD requires exactly 512 samples per inference call at 16 kHz.
_SILERO_WINDOW_SAMPLES: int = 512


class SileroVADModel:
    """Thin wrapper around the Silero VAD model.

    The model is loaded once via ``load()`` and reused for all
    subsequent ``classify`` calls.  Because the underlying PyTorch
    inference is synchronous, callers should run ``classify`` inside
    ``asyncio.to_thread`` to avoid blocking the event loop.

    Args:
        repo_or_dir: ``torch.hub`` repository string.
        model_name: Model entry-point name.
    """

    def __init__(
        self,
        repo_or_dir: str = "snakers4/silero-vad",
        model_name: str = "silero_vad",
    ) -> None:
        self._repo = repo_or_dir
        self._model_name = model_name
        self._model: torch.nn.Module | None = None
        self._lock = threading.Lock()
        self._last_stream_id: str | None = None

    # ── lifecycle ──

    def load(self) -> None:
        """Download / cache and load the Silero VAD model."""
        model, _utils = torch.hub.load(
            self._repo,
            self._model_name,
            trust_repo=True,
        )
        self._model = model
        logger.info("silero_vad_loaded", repo=self._repo)

    @property
    def is_loaded(self) -> bool:
        """Return ``True`` if the model has been loaded."""
        return self._model is not None

    # ── inference ──

    def classify_sync(self, chunk_pcm: bytes, stream_id: str | None = None) -> float:
        """Classify a PCM audio chunk as speech/non-speech (synchronous).

        Silero VAD requires exactly 512 samples at 16 kHz.  If the
        incoming chunk is larger, it is split into 512-sample windows
        and the **maximum** speech probability across windows is returned
        (speech anywhere in the chunk → forward it).

        A threading lock serialises access so interleaved calls from
        different stream processors cannot corrupt the model's LSTM
        hidden state.  When the stream changes, the model state is
        automatically reset.

        Args:
            chunk_pcm: Raw 16 kHz mono s16 (signed 16-bit LE) PCM bytes.
            stream_id: Optional stream identifier for state-reset tracking.

        Returns:
            Speech probability between 0.0 and 1.0.

        Raises:
            RuntimeError: If the model has not been loaded yet.
        """
        if self._model is None:
            raise RuntimeError("SileroVADModel not loaded. Call load() first.")

        with self._lock:
            # Reset hidden state when we switch between streams.
            if stream_id is not None and stream_id != self._last_stream_id:
                self._model.reset_states()
                self._last_stream_id = stream_id

            # Convert raw bytes → float32 tensor in [-1, 1].
            audio_int16 = np.frombuffer(chunk_pcm, dtype=np.int16)
            audio_float = audio_int16.astype(np.float32) / 32768.0

            # Silero requires exactly WINDOW_SAMPLES samples per call.
            window = _SILERO_WINDOW_SAMPLES
            n_samples = len(audio_float)

            if n_samples <= window:
                # Pad to exactly `window` samples if shorter.
                if n_samples < window:
                    padded = np.zeros(window, dtype=np.float32)
                    padded[:n_samples] = audio_float
                    audio_float = padded
                tensor = torch.from_numpy(audio_float)
                with torch.no_grad():
                    return float(self._model(tensor, SAMPLE_RATE))

            # Chunk is larger → slide 512-sample windows, return max score.
            max_score: float = 0.0
            for start in range(0, n_samples - window + 1, window):
                segment = audio_float[start : start + window]
                tensor = torch.from_numpy(segment)
                with torch.no_grad():
                    score = float(self._model(tensor, SAMPLE_RATE))
                if score > max_score:
                    max_score = score
                if max_score >= 0.95:
                    break  # early-out: clearly speech
            return max_score

    async def classify(self, chunk_pcm: bytes, stream_id: str | None = None) -> float:
        """Classify a PCM audio chunk (async, offloaded to thread).

        Wraps ``classify_sync`` in ``asyncio.to_thread`` so the
        synchronous PyTorch call does not block the event loop.

        Args:
            chunk_pcm: Raw 16 kHz mono s16 PCM bytes.
            stream_id: Optional stream identifier for state-reset tracking.

        Returns:
            Speech probability between 0.0 and 1.0.
        """
        import asyncio

        return await asyncio.to_thread(self.classify_sync, chunk_pcm, stream_id)

    def reset_states(self) -> None:
        """Reset the model's internal hidden states between streams."""
        if self._model is not None:
            self._model.reset_states()
