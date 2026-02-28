"""
Sentiment classification engine for VoxSentinel.

Runs DistilBERT-based sentiment model on 3-5 second transcript spans
to classify sentiment as positive/neutral/negative with confidence
scores. Emits escalation alerts on persistent negative sentiment.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from dataclasses import dataclass
from uuid import UUID

import structlog

from transformers import pipeline as hf_pipeline

from tg_common.models import SentimentEvent

logger = structlog.get_logger()

# HuggingFace model for sentiment
MODEL_NAME = "distilbert-base-uncased-finetuned-sst-2-english"

# Escalation: 3 consecutive negative spans with score > 0.8
DEFAULT_ESCALATION_CONSECUTIVE = 3
DEFAULT_ESCALATION_SCORE_THRESHOLD = 0.8
DEFAULT_ROLLING_WINDOW_S = 30.0


@dataclass
class SentimentResult:
    """Raw output from the sentiment model.

    Attributes:
        label: ``POSITIVE`` or ``NEGATIVE`` (from the model).
        score: Confidence score (0.0–1.0).
    """

    label: str
    score: float


@dataclass
class _SpanRecord:
    """Internal record for rolling sentiment tracking."""

    label: str
    score: float
    end_s: float


class SentimentEngine:
    """DistilBERT-based sentiment classification with escalation tracking.

    The HF pipeline is loaded once at :meth:`load_model` time.  Inference
    is run via :func:`asyncio.to_thread` to avoid blocking the event loop.

    Args:
        consecutive_threshold: Number of consecutive negative spans to trigger escalation.
        score_threshold: Minimum negative score for escalation counting.
        rolling_window_s: Duration of the rolling sentiment window.
    """

    def __init__(
        self,
        consecutive_threshold: int = DEFAULT_ESCALATION_CONSECUTIVE,
        score_threshold: float = DEFAULT_ESCALATION_SCORE_THRESHOLD,
        rolling_window_s: float = DEFAULT_ROLLING_WINDOW_S,
    ) -> None:
        self._pipeline: object | None = None
        self._consecutive_threshold = consecutive_threshold
        self._score_threshold = score_threshold
        self._rolling_window_s = rolling_window_s
        # Per-stream rolling history
        self._history: dict[str, deque[_SpanRecord]] = defaultdict(deque)

    # ── lifecycle ──

    def load_model(self) -> None:
        """Load the HuggingFace sentiment-analysis pipeline."""
        self._pipeline = hf_pipeline(
            "sentiment-analysis",
            model=MODEL_NAME,
            truncation=True,
        )
        logger.info("sentiment_model_loaded", model=MODEL_NAME)

    @property
    def is_ready(self) -> bool:
        """Whether the model pipeline has been loaded."""
        return self._pipeline is not None

    # ── inference ──

    async def classify(
        self,
        text: str,
        end_s: float,
        stream_id: UUID,
        session_id: UUID,
        speaker_id: str | None = None,
    ) -> tuple[SentimentResult, SentimentEvent | None]:
        """Classify sentiment of *text* and check for escalation.

        Args:
            text: Transcript span text.
            end_s: End time of the span in seconds (stream-relative).
            stream_id: UUID of the source stream.
            session_id: UUID of the active session.
            speaker_id: Speaker label if available.

        Returns:
            A tuple of ``(SentimentResult, optional SentimentEvent)``.
            The event is non-None only when an escalation is triggered.
        """
        if not self._pipeline or not text.strip():
            return SentimentResult(label="NEUTRAL", score=0.0), None

        # Run inference off the event loop
        raw: list[dict[str, object]] = await asyncio.to_thread(self._pipeline, text)  # type: ignore[arg-type]
        result = self._parse_result(raw)

        # Normalise label to lowercase
        sentiment_label = self._normalise_label(result.label)

        # Update rolling history
        sid = str(stream_id)
        self._history[sid].append(
            _SpanRecord(label=sentiment_label, score=result.score, end_s=end_s)
        )
        self._evict(sid, end_s)

        # Check escalation
        escalation_event: SentimentEvent | None = None
        if self._should_escalate(sid):
            escalation_event = SentimentEvent(
                stream_id=stream_id,
                session_id=session_id,
                speaker_id=speaker_id,
                sentiment_label=sentiment_label,
                sentiment_score=result.score,
            )
            logger.warning(
                "sentiment_escalation_triggered",
                stream_id=sid,
                consecutive=self._consecutive_threshold,
                score=result.score,
            )

        return result, escalation_event

    # ── internal helpers ──

    def _parse_result(self, raw: list[dict[str, object]]) -> SentimentResult:
        """Extract label and score from raw HF pipeline output."""
        if raw and isinstance(raw, list):
            entry = raw[0]
            return SentimentResult(
                label=str(entry.get("label", "NEUTRAL")),
                score=float(entry.get("score", 0.0)),  # type: ignore[arg-type]
            )
        return SentimentResult(label="NEUTRAL", score=0.0)

    @staticmethod
    def _normalise_label(label: str) -> str:
        """Map HF output labels to positive/negative/neutral."""
        upper = label.upper()
        if upper == "POSITIVE":
            return "positive"
        if upper == "NEGATIVE":
            return "negative"
        return "neutral"

    def _evict(self, stream_id: str, latest_end_s: float) -> None:
        """Drop records older than the rolling window."""
        cutoff = latest_end_s - self._rolling_window_s
        history = self._history[stream_id]
        while history and history[0].end_s < cutoff:
            history.popleft()

    def _should_escalate(self, stream_id: str) -> bool:
        """Check if the last N consecutive spans are negative above threshold."""
        history = self._history[stream_id]
        if len(history) < self._consecutive_threshold:
            return False
        recent = list(history)[-self._consecutive_threshold:]
        return all(
            r.label == "negative" and r.score > self._score_threshold
            for r in recent
        )

    def remove_stream(self, stream_id: str) -> None:
        """Clean up history for a stopped stream."""
        self._history.pop(stream_id, None)
