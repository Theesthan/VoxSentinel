"""
Compiled regex pattern manager for VoxSentinel.

Manages the lifecycle of compiled regex patterns for keyword detection.
Validates patterns at configuration load time and applies them against
transcript windows.
"""

from __future__ import annotations

import re
