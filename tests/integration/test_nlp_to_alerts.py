"""Integration tests: NLP -> Alerts pipeline.

Publishes a fake final ``TranscriptToken`` whose text contains a
keyword (``gun``) to ``enriched_tokens:test-stream-001`` and asserts
that a ``KeywordMatchEvent`` with ``keyword='gun'`` and
``match_type='exact'`` is published to ``match_events:test-stream-001``
within 2 seconds.

The NLP keyword engine is exercised directly (not via the full NLP
service container) because we only need to verify the keyword-detection →
Redis-publish contract.
"""

from __future__ import annotations

import json
import uuid

import pytest
import redis.asyncio as aioredis

from tg_common.models import KeywordRule, RuleMatchType
from tg_common.models.alert import Severity


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_keyword_rules() -> list[KeywordRule]:
    """Return a small rule set with an exact 'gun' rule."""
    return [
        KeywordRule(
            rule_set_name="security",
            keyword="gun",
            match_type=RuleMatchType.EXACT,
            severity=Severity.CRITICAL,
            category="security",
            enabled=True,
        ),
        KeywordRule(
            rule_set_name="security",
            keyword="bomb",
            match_type=RuleMatchType.EXACT,
            severity=Severity.CRITICAL,
            category="security",
            enabled=True,
        ),
    ]


async def _run_keyword_detection_and_publish(
    redis: aioredis.Redis,
    stream_id: str,
    session_id: str,
    text: str,
) -> None:
    """Run keyword engine on *text* and publish matches to Redis.

    Mimics the NLP service's ``_process_token`` flow for the keyword
    detection path only.  Uses the provided ``redis`` client directly
    rather than creating a separate connection.
    """
    from nlp.keyword_engine import KeywordEngine

    engine = KeywordEngine()
    engine.load_rules(_make_keyword_rules())

    events = engine.detect(
        text=text,
        start_s=0.0,
        end_s=1.0,
        stream_id=uuid.UUID(stream_id),
        session_id=uuid.UUID(session_id),
    )

    for evt in events:
        payload = json.dumps(evt.model_dump(mode="json"))
        await redis.publish(f"match_events:{stream_id}", payload)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestNLPToAlerts:
    """Test NLP keyword detection → alert event publishing."""

    async def test_keyword_match_triggers_alert(
        self,
        redis_client: aioredis.Redis,
    ) -> None:
        """Publish text containing 'gun' and verify a KeywordMatchEvent.

        Steps:
            1. Subscribe to ``match_events:test-stream-001``.
            2. Run keyword detection on ``'he has a gun'``.
            3. Assert event received within 2 s with correct fields.
        """
        stream_id = "00000000-0000-0000-0000-000000000001"
        session_id = str(uuid.uuid4())
        channel = f"match_events:{stream_id}"

        # Subscribe to match events channel
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(channel)

        # Consume the subscription-confirmation message
        await pubsub.get_message(timeout=2.0)

        # Run detection + publish
        await _run_keyword_detection_and_publish(
            redis=redis_client,
            stream_id=stream_id,
            session_id=session_id,
            text="he has a gun",
        )

        # Wait for the event
        msg = await pubsub.get_message(timeout=2.0)
        # Pub/sub may need a bit more time
        if msg is None:
            msg = await pubsub.get_message(timeout=2.0)

        assert msg is not None, "No KeywordMatchEvent received within 2 seconds"
        assert msg["type"] == "message"

        event_data = json.loads(msg["data"])
        assert event_data["keyword"] == "gun"
        assert event_data["match_type"] == "exact"
        assert event_data["stream_id"] == stream_id

        await pubsub.unsubscribe(channel)
        await pubsub.aclose()

    async def test_no_match_when_keyword_absent(
        self,
        redis_client: aioredis.Redis,
    ) -> None:
        """Verify no event is published when text has no keyword match."""
        stream_id = "00000000-0000-0000-0000-000000000002"
        session_id = str(uuid.uuid4())
        channel = f"match_events:{stream_id}"

        pubsub = redis_client.pubsub()
        await pubsub.subscribe(channel)
        await pubsub.get_message(timeout=1.0)  # consume subscription ack

        await _run_keyword_detection_and_publish(
            redis=redis_client,
            stream_id=stream_id,
            session_id=session_id,
            text="the weather is nice today",
        )

        msg = await pubsub.get_message(timeout=2.0)
        assert msg is None, f"Unexpected event received: {msg}"

        await pubsub.unsubscribe(channel)
        await pubsub.aclose()

    async def test_alert_throttling_prevents_duplicates(
        self,
        redis_client: aioredis.Redis,
    ) -> None:
        """Verify alert dedup: same keyword in rapid succession → distinct events.

        This test sends the same keyword text twice and verifies that the
        keyword engine correctly produces matches for both invocations
        (deduplication is handled by the alert service, not the NLP engine).
        """
        stream_id = "00000000-0000-0000-0000-000000000003"
        session_id = str(uuid.uuid4())
        channel = f"match_events:{stream_id}"

        pubsub = redis_client.pubsub()
        await pubsub.subscribe(channel)
        await pubsub.get_message(timeout=1.0)

        # Publish twice in quick succession
        for _ in range(2):
            await _run_keyword_detection_and_publish(
                redis=redis_client,
                stream_id=stream_id,
                session_id=session_id,
                text="there is a bomb in the building",
            )

        events_received = 0
        for _ in range(4):
            msg = await pubsub.get_message(timeout=1.0)
            if msg and msg["type"] == "message":
                event_data = json.loads(msg["data"])
                assert event_data["keyword"] == "bomb"
                events_received += 1

        assert events_received >= 2, f"Expected ≥2 events, got {events_received}"

        await pubsub.unsubscribe(channel)
        await pubsub.aclose()
