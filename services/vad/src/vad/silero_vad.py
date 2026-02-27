"""
Silero VAD wrapper for VoxSentinel.

Loads the Silero VAD model via ``torch.hub.load`` and exposes a
simple async ``classify`` method returning speech probability
(0.0–1.0) for a raw PCM chunk.
"""

from __future__ import annotations

import structlog
import torch
import numpy as np

logger = structlog.get_logger()

# Audio constants matching the ingestion service output.
SAMPLE_RATE: int = 16_000


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

    def classify_sync(self, chunk_pcm: bytes) -> float:
        """Classify a PCM audio chunk as speech/non-speech (synchronous).

        Args:
            chunk_pcm: Raw 16 kHz mono s16 (signed 16-bit LE) PCM bytes.

        Returns:
            Speech probability between 0.0 and 1.0.

        Raises:
            RuntimeError: If the model has not been loaded yet.
        """
        if self._model is None:
            raise RuntimeError("SileroVADModel not loaded. Call load() first.")

        # Convert raw bytes → float32 tensor in [-1, 1].
        audio_int16 = np.frombuffer(chunk_pcm, dtype=np.int16)
        audio_float = audio_int16.astype(np.float32) / 32768.0
        tensor = torch.from_numpy(audio_float)

        with torch.no_grad():
            confidence = self._model(tensor, SAMPLE_RATE)

        # Silero returns a tensor; extract scalar float.
        score: float = float(confidence)
        return score

    async def classify(self, chunk_pcm: bytes) -> float:
        """Classify a PCM audio chunk (async, offloaded to thread).

        Wraps ``classify_sync`` in ``asyncio.to_thread`` so the
        synchronous PyTorch call does not block the event loop.

        Args:
            chunk_pcm: Raw 16 kHz mono s16 PCM bytes.

        Returns:
            Speech probability between 0.0 and 1.0.
        """
        import asyncio

        return await asyncio.to_thread(self.classify_sync, chunk_pcm)

    def reset_states(self) -> None:
        """Reset the model's internal hidden states between streams."""
        if self._model is not None:
            self._model.reset_states()
