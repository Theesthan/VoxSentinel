"""
Tests for the ASR engine base class.

Validates that the abstract interface is correctly defined and that
concrete implementations must provide all required methods.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest

from tg_common.models import TranscriptToken

from asr.engine_base import ASREngine


# ── Helpers ─────────────────────────────────────────────────


class _IncompleteEngine(ASREngine):
    """Subclass that does NOT implement all abstract methods."""

    @property
    def name(self) -> str:
        return "incomplete"


class _CompleteEngine(ASREngine):
    """Minimal concrete implementation of ASREngine."""

    @property
    def name(self) -> str:
        return "complete_test"

    async def connect(self) -> None:
        pass

    async def disconnect(self) -> None:
        pass

    async def stream_audio(self, chunk: bytes) -> AsyncIterator[TranscriptToken]:
        return  # empty generator
        yield  # pragma: no cover  # makes it an async generator

    async def health_check(self) -> bool:
        return True


# ── Tests ───────────────────────────────────────────────────


class TestASREngineABC:
    """ASREngine abstract base class tests."""

    def test_cannot_instantiate_abc(self) -> None:
        """Direct instantiation of ASREngine raises TypeError."""
        with pytest.raises(TypeError):
            ASREngine()  # type: ignore[abstract]

    def test_incomplete_subclass_raises(self) -> None:
        """Subclass missing abstract methods cannot be instantiated."""
        with pytest.raises(TypeError):
            _IncompleteEngine()  # type: ignore[abstract]

    def test_complete_subclass_instantiates(self) -> None:
        """Concrete subclass with all methods can be created."""
        engine = _CompleteEngine()
        assert engine is not None

    def test_name_property(self) -> None:
        """The name property returns the expected identifier."""
        engine = _CompleteEngine()
        assert engine.name == "complete_test"

    async def test_connect(self) -> None:
        """connect() runs without error on complete engine."""
        engine = _CompleteEngine()
        await engine.connect()

    async def test_disconnect(self) -> None:
        """disconnect() runs without error on complete engine."""
        engine = _CompleteEngine()
        await engine.disconnect()

    async def test_stream_audio_returns_async_iterator(self) -> None:
        """stream_audio returns an async iterator."""
        engine = _CompleteEngine()
        result = engine.stream_audio(b"\x00\x00")
        assert isinstance(result, AsyncIterator)
        tokens = [t async for t in result]
        assert tokens == []

    async def test_health_check_returns_bool(self) -> None:
        """health_check returns a boolean."""
        engine = _CompleteEngine()
        result = await engine.health_check()
        assert result is True

    def test_is_subclass_of_abc(self) -> None:
        """_CompleteEngine is a proper subclass of ASREngine."""
        engine = _CompleteEngine()
        assert isinstance(engine, ASREngine)
