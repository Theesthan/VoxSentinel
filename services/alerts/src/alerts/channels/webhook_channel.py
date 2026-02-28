"""
Webhook alert channel for VoxSentinel.

Sends HTTP POST requests with JSON alert payloads to configured
webhook URLs with retry logic (3 attempts, exponential backoff).
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from tg_common.models.alert import Alert

from .base import AlertChannel

logger = structlog.get_logger()

# Default values — overridable via constructor.
_DEFAULT_MAX_ATTEMPTS = 3
_DEFAULT_TIMEOUT_S = 10.0


class WebhookChannel(AlertChannel):
    """Deliver alerts as HTTP POST JSON payloads to a webhook URL.

    Uses :mod:`httpx` for async HTTP and :mod:`tenacity` for transparent
    retry with exponential back-off.

    Args:
        url: Destination webhook URL.
        max_attempts: Number of delivery attempts (default 3).
        timeout: Per-request timeout in seconds (default 10).
        headers: Optional extra headers to include on every request.
    """

    name: str = "webhook"

    def __init__(
        self,
        url: str,
        *,
        max_attempts: int = _DEFAULT_MAX_ATTEMPTS,
        timeout: float = _DEFAULT_TIMEOUT_S,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.url = url
        self.max_attempts = max_attempts
        self.timeout = timeout
        self.headers = headers or {}
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Return (and lazily create) the shared ``httpx.AsyncClient``."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    # ── delivery ──

    async def _post_with_retry(self, payload: dict[str, Any]) -> httpx.Response:
        """POST *payload* to the configured URL with retry.

        The retry decorator is built dynamically so ``max_attempts`` can be
        set at construction time rather than module-import time.
        """

        @retry(
            stop=stop_after_attempt(self.max_attempts),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TransportError)),
            reraise=True,
        )
        async def _inner() -> httpx.Response:
            client = await self._get_client()
            resp = await client.post(
                self.url,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    **self.headers,
                },
            )
            resp.raise_for_status()
            return resp

        return await _inner()

    async def send(self, alert: Alert) -> bool:
        """Deliver *alert* via HTTP POST.

        Returns:
            ``True`` on a 2xx response, ``False`` if all retries are
            exhausted or an unexpected error occurs.
        """
        payload = alert.model_dump(mode="json")
        log = logger.bind(webhook_url=self.url, alert_id=str(alert.alert_id))
        try:
            resp = await self._post_with_retry(payload)
            log.info("webhook_delivered", status=resp.status_code)
            return True
        except (httpx.HTTPStatusError, httpx.TransportError) as exc:
            log.error("webhook_delivery_failed", error=str(exc))
            return False
        except Exception as exc:  # noqa: BLE001
            log.error("webhook_unexpected_error", error=str(exc))
            return False

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
