# ASR Backend Guide

## Adding a New ASR Engine to VoxSentinel

This guide explains how to add a new Automatic Speech Recognition (ASR) backend to the system.

### Architecture Overview

VoxSentinel uses a pluggable ASR engine architecture:

1. **`engine_base.py`** — Abstract base class all engines must implement
2. **`engine_registry.py`** — Registry that discovers and manages engine instances
3. **`router.py`** — Routes audio chunks to the appropriate engine
4. **`failover.py`** — Handles engine failures and automatic fallback

### Step 1: Create the Engine File

Create a new file in `services/asr/src/asr/engines/`:

```python
# services/asr/src/asr/engines/my_new_engine.py
"""My New ASR Engine integration."""

from asr.engine_base import ASREngineBase

class MyNewEngine(ASREngineBase):
    """ASR engine implementation for MyNewService."""

    engine_name = "my_new_engine"

    async def initialize(self) -> None:
        """Load model or establish API connection."""
        ...

    async def transcribe(self, audio_chunk: bytes, sample_rate: int) -> str:
        """Transcribe an audio chunk to text."""
        ...

    async def health_check(self) -> bool:
        """Check if the engine is operational."""
        ...
```

### Step 2: Register the Engine

Add the engine to `services/asr/src/asr/engines/__init__.py`.

### Step 3: Configure Priority

Update the engine priority list in `.env` or the configuration to include the new engine in the failover chain.

### Step 4: Add Tests

Create `services/asr/tests/test_my_new_engine.py` with unit tests covering initialization, transcription, and error handling.

### Supported Engines (V1)

| Engine | Type | GPU Required | Notes |
|--------|------|-------------|-------|
| Deepgram Nova-2 | Cloud API | No | Primary, lowest latency |
| Whisper V3 Turbo | Local | Yes | Fallback, highest accuracy |
| Lightning ASR | Local | Yes | Ultra-low latency |
| AssemblyAI | Cloud API | No | Alternative cloud |
| Parakeet TDT | Local | Yes | NVIDIA NeMo |
| Canary + Qwen | Local | Yes | Multilingual |
| NVIDIA Riva | Local/Cloud | Yes | Enterprise gRPC |
