"""
Abstract base class for alert channels in VoxSentinel.

Defines the AlertChannel interface that all channel implementations
must follow, ensuring consistent delivery semantics and error handling.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
