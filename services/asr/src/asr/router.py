"""
ASR stream router for VoxSentinel.

Routes audio streams to the appropriate ASR engine based on
per-stream configuration, handling engine selection and
connection management.
"""

from __future__ import annotations

import asyncio
import base64
from typing import Any

import structlog

from tg_common.messaging.redis_client import RedisClient

from asr.failover import ASRFailoverManager

logger = structlog.get_logger()


class ASRRouter:
    """Consume ``speech_chunks:{stream_id}`` and produce ``transcript_tokens:{stream_id}``.

    For each stream the router:

    1. Reads base-64-encoded PCM chunks from the Redis stream
       ``speech_chunks:{stream_id}``.
    2. Forwards them through an :class:`ASRFailoverManager` to the
       configured ASR engine.
    3. Publishes each resulting :class:`TranscriptToken` (JSON) to the
       Redis stream ``transcript_tokens:{stream_id}``.

    Args:
        redis_client: A connected :class:`RedisClient` instance.
        failover_manager: The failover manager wrapping primary/fallback engines.
    """

    def __init__(
        self,
        redis_client: RedisClient,
        failover_manager: ASRFailoverManager,
    ) -> None:
        self._redis = redis_client
        self._failover = failover_manager

    async def process_stream(
        self,
        stream_id: str,
        *,
        stop_event: asyncio.Event | None = None,
    ) -> None:
        """Blocking loop: read speech chunks, transcribe, publish tokens.

        Args:
            stream_id: The stream UUID whose speech chunks to consume.
            stop_event: Set this event to break the loop gracefully.
        """
        in_key = f"speech_chunks:{stream_id}"
        out_key = f"transcript_tokens:{stream_id}"
        last_id = "0"
        log = logger.bind(stream_id=stream_id)
        log.info("asr_router_started", in_key=in_key, out_key=out_key)

        while stop_event is None or not stop_event.is_set():
            try:
                entries: list[Any] = await self._redis.xread(
                    {in_key: last_id},
                    count=10,
                    block=1000,
                )
            except asyncio.CancelledError:
                break
            except Exception:
                log.exception("asr_router_xread_error")
                await asyncio.sleep(1.0)
                continue

            if not entries:
                continue

            for _stream_name, messages in entries:
                for entry_id, fields in messages:
                    last_id = entry_id
                    await self._handle_entry(fields, out_key, log)

        log.info("asr_router_stopped")

    # ── internal ─────────────────────────────────────────────

    async def _handle_entry(
        self,
        fields: dict[str, str],
        out_key: str,
        log: Any,
    ) -> None:
        """Decode one speech-chunk entry and route through ASR."""
        pcm_b64 = fields.get("pcm_b64", "")
        if not pcm_b64:
            log.warning("asr_router_missing_pcm_b64")
            return

        try:
            chunk = base64.b64decode(pcm_b64)
        except Exception:
            log.error("asr_router_b64_decode_error", exc_info=True)
            return

        try:
            async for token in self._failover.stream_audio(chunk):
                token_json = token.model_dump_json()
                await self._redis.xadd(
                    out_key,
                    {"token": token_json},
                    maxlen=10_000,
                )
                log.debug(
                    "asr_token_published",
                    text=token.text[:50],
                    is_final=token.is_final,
                )
        except Exception:
            log.error("asr_router_stream_error", exc_info=True)
