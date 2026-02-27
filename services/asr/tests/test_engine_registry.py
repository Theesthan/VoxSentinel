"""
Tests for the ASR engine registry.

Validates engine registration, lookup, listing, and clearing.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest

from tg_common.models import TranscriptToken

from asr.engine_base import ASREngine
from asr.engine_registry import (
    _REGISTRY,
    clear_registry,
    get_engine_class,
    list_engines,
    register_engine,
)


class _DummyEngine(ASREngine):
    """Minimal concrete engine for registry tests."""

    @property
    def name(self) -> str:
        return "dummy"

    async def connect(self) -> None:
        pass

    async def disconnect(self) -> None:
        pass

    async def stream_audio(self, chunk: bytes) -> AsyncIterator[TranscriptToken]:
        return
        yield  # pragma: no cover

    async def health_check(self) -> bool:
        return True


class TestEngineRegistry:
    """Tests for engine_registry module functions."""

    def setup_method(self) -> None:
        """Clear registry before each test."""
        clear_registry()

    def teardown_method(self) -> None:
        """Ensure clean state after each test."""
        clear_registry()

    def test_register_and_get(self) -> None:
        """register_engine stores and get_engine_class retrieves."""
        register_engine("dummy", _DummyEngine)
        assert get_engine_class("dummy") is _DummyEngine

    def test_get_unknown_raises_key_error(self) -> None:
        """get_engine_class raises KeyError for an unregistered name."""
        with pytest.raises(KeyError, match="Unknown ASR engine"):
            get_engine_class("nonexistent")

    def test_list_engines_empty(self) -> None:
        """list_engines returns empty list when nothing registered."""
        assert list_engines() == []

    def test_list_engines(self) -> None:
        """list_engines returns all registered names."""
        register_engine("a", _DummyEngine)
        register_engine("b", _DummyEngine)
        result = list_engines()
        assert "a" in result
        assert "b" in result

    def test_clear_registry(self) -> None:
        """clear_registry removes all entries."""
        register_engine("x", _DummyEngine)
        clear_registry()
        assert list_engines() == []

    def test_register_non_subclass_raises_type_error(self) -> None:
        """register_engine raises TypeError for non-ASREngine class."""
        with pytest.raises(TypeError, match="not a subclass"):
            register_engine("bad", str)  # type: ignore[arg-type]

    def test_register_overwrites(self) -> None:
        """Registering the same name again overwrites the previous entry."""
        register_engine("dup", _DummyEngine)
        register_engine("dup", _DummyEngine)
        assert get_engine_class("dup") is _DummyEngine
        assert list_engines().count("dup") == 1
