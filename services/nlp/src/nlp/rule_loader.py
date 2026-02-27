"""
Keyword rule hot-reload loader for VoxSentinel.

Loads keyword rule configurations from the database or REST API and
watches for changes to trigger automaton rebuilds and pattern
recompilation without service restarts.
"""

from __future__ import annotations

import structlog
