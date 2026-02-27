"""
Alert channel implementations package for VoxSentinel.

Contains the abstract AlertChannel base class and concrete
implementations for each supported delivery channel.
"""

from .base import AlertChannel
from .slack_channel import SlackChannel
from .webhook_channel import WebhookChannel
from .websocket_channel import WebSocketChannel

__all__ = [
    "AlertChannel",
    "SlackChannel",
    "WebhookChannel",
    "WebSocketChannel",
]
