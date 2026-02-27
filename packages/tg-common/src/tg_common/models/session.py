"""
Session data model re-export for VoxSentinel.

The ``Session`` model is defined in ``tg_common.models.stream`` alongside
``Stream`` as both are tightly coupled.  This module re-exports ``Session``
so that imports from ``tg_common.models.session`` remain valid.
"""

from __future__ import annotations

from tg_common.models.stream import Session

__all__ = ["Session"]
