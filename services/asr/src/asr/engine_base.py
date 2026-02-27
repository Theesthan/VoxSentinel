"""
Abstract base class for ASR engine backends in VoxSentinel.

Defines the ASREngine interface that all backends must implement,
including the stream_audio method that accepts audio chunks and
yields unified TranscriptToken objects.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from tg_common.models import TranscriptToken


class ASREngine(ABC):
    """Abstract base class that every ASR backend must implement.

    Subclasses provide :meth:`connect`, :meth:`disconnect`,
    :meth:`stream_audio`, and :meth:`health_check` methods.  The
    :attr:`name` property returns a unique engine identifier used
    by the registry and failover manager.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the engine identifier string (e.g. ``'deepgram_nova2'``)."""
        ...  # pragma: no cover

    @abstractmethod
    async def connect(self) -> None:
        """Initialise the engine connection or load the model.

        Raises:
            RuntimeError: If the engine cannot be initialised.
        """
        ...  # pragma: no cover

    @abstractmethod
    async def disconnect(self) -> None:
        """Tear down the engine connection or unload the model."""
        ...  # pragma: no cover

    @abstractmethod
    async def stream_audio(self, chunk: bytes) -> AsyncIterator[TranscriptToken]:
        """Send an audio chunk and yield ``TranscriptToken`` objects.

        Args:
            chunk: Raw 16-bit PCM audio bytes.

        Yields:
            :class:`TranscriptToken` objects (partial or final).

        Raises:
            RuntimeError: If the engine is not connected.
        """
        ...  # pragma: no cover
        yield  # type: ignore[misc]  # pragma: no cover

    @abstractmethod
    async def health_check(self) -> bool:
        """Return ``True`` if the engine is ready to process audio."""
        ...  # pragma: no cover
