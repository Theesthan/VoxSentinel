"""End-to-end test: RTSP stream to dashboard display.

Verifies the complete user-facing flow: an RTSP stream is ingested,
processed through the full pipeline, and live results appear on the
Streamlit dashboard via WebSocket.
"""

import pytest


@pytest.mark.e2e
class TestRTSPToDashboard:
    """E2E: RTSP stream ingestion to dashboard live view."""

    async def test_live_transcript_appears_on_dashboard(self) -> None:
        """Verify live transcript text appears in the dashboard live view."""
        ...

    async def test_stream_status_shown_on_dashboard(self) -> None:
        """Verify stream connection status is displayed on dashboard."""
        ...

    async def test_multiple_streams_displayed(self) -> None:
        """Verify multiple simultaneous streams are shown on dashboard."""
        ...
