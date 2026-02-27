"""
ASR engine registry for VoxSentinel.

Maintains a registry of available ASR backend implementations,
enabling dynamic discovery and instantiation of engines by
identifier string.
"""

from __future__ import annotations

import structlog

from asr.engine_base import ASREngine

logger = structlog.get_logger()

# Global mapping of engine name → engine class.
_REGISTRY: dict[str, type[ASREngine]] = {}


def register_engine(name: str, cls: type[ASREngine]) -> None:
    """Register an ASR engine class under *name*.

    Args:
        name: Unique identifier (e.g. ``"deepgram_nova2"``).
        cls: A concrete :class:`ASREngine` subclass.

    Raises:
        TypeError: If *cls* is not a subclass of :class:`ASREngine`.
    """
    if not (isinstance(cls, type) and issubclass(cls, ASREngine)):
        raise TypeError(f"{cls!r} is not a subclass of ASREngine")
    _REGISTRY[name] = cls
    logger.info("asr_engine_registered", engine=name)


def get_engine_class(name: str) -> type[ASREngine]:
    """Look up a registered engine class by *name*.

    Args:
        name: The engine identifier.

    Returns:
        The registered :class:`ASREngine` subclass.

    Raises:
        KeyError: If *name* is not registered.
    """
    if name not in _REGISTRY:
        available = list(_REGISTRY.keys())
        raise KeyError(f"Unknown ASR engine '{name}'. Available: {available}")
    return _REGISTRY[name]


def list_engines() -> list[str]:
    """Return the names of all registered engines."""
    return list(_REGISTRY.keys())


def clear_registry() -> None:
    """Remove all registered engines (useful in tests)."""
    _REGISTRY.clear()
