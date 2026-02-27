"""
Audio chunk producer for VoxSentinel ingestion service.

Splits continuous audio streams into timestamped chunks of configurable
size (default 280 ms) for streaming ASR, or 30-60 second chunks for
batch processing mode.
"""

from __future__ import annotations

import numpy as np
