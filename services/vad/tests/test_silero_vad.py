"""Unit tests for ``vad.silero_vad.SileroVADModel``."""

from __future__ import annotations

import asyncio
import struct
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from vad.silero_vad import SAMPLE_RATE, SileroVADModel


class TestSileroVADModelInit:
    """Constructor / default state."""

    def test_defaults(self) -> None:
        model = SileroVADModel()
        assert model._repo == "snakers4/silero-vad"
        assert model._model_name == "silero_vad"
        assert model.is_loaded is False

    def test_custom_repo(self) -> None:
        model = SileroVADModel(repo_or_dir="custom/repo", model_name="custom")
        assert model._repo == "custom/repo"
        assert model._model_name == "custom"


class TestLoad:
    """Model loading via ``torch.hub.load``."""

    def test_load_calls_torch_hub(self) -> None:
        import torch

        mock_model = MagicMock()
        torch.hub.load = MagicMock(return_value=(mock_model, ["utils"]))

        vad = SileroVADModel()
        vad.load()

        torch.hub.load.assert_called_once_with(
            "snakers4/silero-vad", "silero_vad", trust_repo=True,
        )
        assert vad.is_loaded is True

    def test_is_loaded_false_before_load(self) -> None:
        vad = SileroVADModel()
        assert vad.is_loaded is False


class TestClassifySync:
    """Synchronous inference."""

    @staticmethod
    def _make_pcm(n_samples: int = 160, amplitude: int = 1000) -> bytes:
        """Build fake 16-bit LE PCM bytes."""
        return struct.pack(f"<{n_samples}h", *([amplitude] * n_samples))

    def test_raises_when_not_loaded(self) -> None:
        vad = SileroVADModel()
        with pytest.raises(RuntimeError, match="not loaded"):
            vad.classify_sync(self._make_pcm())

    def test_returns_float_score(self) -> None:
        import torch

        mock_inner = MagicMock(return_value=0.92)
        torch.from_numpy = MagicMock(return_value=MagicMock())

        vad = SileroVADModel()
        vad._model = mock_inner

        score = vad.classify_sync(self._make_pcm())
        assert isinstance(score, float)
        mock_inner.assert_called_once()

    def test_pcm_conversion_uses_numpy(self) -> None:
        """Ensure bytes are converted via np.frombuffer → float32 / 32768."""
        import torch

        pcm = self._make_pcm(4, amplitude=16384)
        captured_tensor = None

        def _fake_from_numpy(arr: np.ndarray) -> MagicMock:
            nonlocal captured_tensor
            captured_tensor = arr
            return MagicMock()

        torch.from_numpy = _fake_from_numpy

        mock_inner = MagicMock(return_value=0.5)
        vad = SileroVADModel()
        vad._model = mock_inner
        vad.classify_sync(pcm)

        assert captured_tensor is not None
        np.testing.assert_allclose(captured_tensor, [0.5, 0.5, 0.5, 0.5], atol=1e-4)

    def test_sample_rate_constant(self) -> None:
        assert SAMPLE_RATE == 16_000


class TestClassifyAsync:
    """Async ``classify`` delegates to ``classify_sync`` via to_thread."""

    @pytest.mark.asyncio
    async def test_classify_delegates_to_sync(self) -> None:
        import torch

        mock_inner = MagicMock(return_value=0.77)
        torch.from_numpy = MagicMock(return_value=MagicMock())

        vad = SileroVADModel()
        vad._model = mock_inner

        pcm = struct.pack("<4h", 100, 200, 300, 400)
        score = await vad.classify(pcm)

        assert isinstance(score, float)
        mock_inner.assert_called_once()


class TestResetStates:
    """State reset between streams."""

    def test_reset_states_calls_model(self) -> None:
        mock_inner = MagicMock()
        vad = SileroVADModel()
        vad._model = mock_inner
        vad.reset_states()
        mock_inner.reset_states.assert_called_once()

    def test_reset_states_noop_when_not_loaded(self) -> None:
        vad = SileroVADModel()
        # Should not raise, just silently return.
        vad.reset_states()
