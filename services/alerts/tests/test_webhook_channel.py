"""
Tests for the webhook alert channel.

Validates HTTP POST delivery, retry logic with exponential backoff,
and error handling for failed deliveries.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx

from alerts.channels.webhook_channel import WebhookChannel


_TEST_URL = "https://example.com/webhook"


# ── successful delivery ──


class TestWebhookDelivery:
    """Tests for happy-path HTTP POST delivery."""

    async def test_send_posts_json_payload(self, sample_alert) -> None:
        ch = WebhookChannel(url=_TEST_URL, max_attempts=1, timeout=5.0)
        mock_response = httpx.Response(200, request=httpx.Request("POST", _TEST_URL))

        with patch.object(ch, "_get_client") as mock_gc:
            client = AsyncMock()
            client.post = AsyncMock(return_value=mock_response)
            mock_gc.return_value = client

            result = await ch.send(sample_alert)

        assert result is True
        client.post.assert_awaited_once()
        call_kwargs = client.post.call_args
        assert call_kwargs.kwargs["json"]["matched_rule"] == "gun"

    async def test_send_includes_custom_headers(self, sample_alert) -> None:
        ch = WebhookChannel(
            url=_TEST_URL, max_attempts=1, headers={"X-Secret": "abc123"}
        )
        mock_response = httpx.Response(200, request=httpx.Request("POST", _TEST_URL))

        with patch.object(ch, "_get_client") as mock_gc:
            client = AsyncMock()
            client.post = AsyncMock(return_value=mock_response)
            mock_gc.return_value = client

            await ch.send(sample_alert)

        headers = client.post.call_args.kwargs["headers"]
        assert headers["X-Secret"] == "abc123"

    async def test_send_returns_true_on_2xx(self, sample_alert) -> None:
        ch = WebhookChannel(url=_TEST_URL, max_attempts=1)
        mock_response = httpx.Response(201, request=httpx.Request("POST", _TEST_URL))

        with patch.object(ch, "_get_client") as mock_gc:
            client = AsyncMock()
            client.post = AsyncMock(return_value=mock_response)
            mock_gc.return_value = client

            assert await ch.send(sample_alert) is True


# ── failure / retry ──


class TestWebhookRetry:
    """Tests for retry behaviour and error handling."""

    async def test_send_returns_false_on_persistent_5xx(self, sample_alert) -> None:
        ch = WebhookChannel(url=_TEST_URL, max_attempts=1)
        mock_response = httpx.Response(500, request=httpx.Request("POST", _TEST_URL))

        with patch.object(ch, "_get_client") as mock_gc:
            client = AsyncMock()
            client.post = AsyncMock(return_value=mock_response)
            mock_gc.return_value = client

            result = await ch.send(sample_alert)

        assert result is False

    async def test_send_returns_false_on_transport_error(self, sample_alert) -> None:
        ch = WebhookChannel(url=_TEST_URL, max_attempts=1)

        with patch.object(ch, "_get_client") as mock_gc:
            client = AsyncMock()
            client.post = AsyncMock(side_effect=httpx.TransportError("connect failed"))
            mock_gc.return_value = client

            result = await ch.send(sample_alert)

        assert result is False

    async def test_send_retries_on_5xx_then_succeeds(self, sample_alert) -> None:
        ch = WebhookChannel(url=_TEST_URL, max_attempts=3)
        fail_resp = httpx.Response(500, request=httpx.Request("POST", _TEST_URL))
        ok_resp = httpx.Response(200, request=httpx.Request("POST", _TEST_URL))

        with patch.object(ch, "_get_client") as mock_gc:
            client = AsyncMock()
            client.post = AsyncMock(side_effect=[fail_resp, ok_resp])
            mock_gc.return_value = client

            result = await ch.send(sample_alert)

        assert result is True
        assert client.post.await_count == 2


# ── close ──


class TestWebhookClose:
    """Tests for resource cleanup."""

    async def test_close_closes_client(self) -> None:
        ch = WebhookChannel(url=_TEST_URL)
        mock_client = AsyncMock()
        mock_client.is_closed = False
        ch._client = mock_client
        await ch.close()
        mock_client.aclose.assert_awaited_once()
        assert ch._client is None

    async def test_close_noop_when_no_client(self) -> None:
        ch = WebhookChannel(url=_TEST_URL)
        await ch.close()  # should not raise


# ── constructor defaults ──


class TestWebhookDefaults:
    """Tests for construction parameters."""

    def test_default_max_attempts(self) -> None:
        ch = WebhookChannel(url=_TEST_URL)
        assert ch.max_attempts == 3

    def test_default_timeout(self) -> None:
        ch = WebhookChannel(url=_TEST_URL)
        assert ch.timeout == 10.0

    def test_channel_name(self) -> None:
        ch = WebhookChannel(url=_TEST_URL)
        assert ch.name == "webhook"

