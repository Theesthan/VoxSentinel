"""
Keyword rule hot-reload loader for VoxSentinel.

Loads keyword rule configurations from the database or REST API and
watches for changes to trigger automaton rebuilds and pattern
recompilation without service restarts.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from typing import Any

import httpx
import structlog

from tg_common.config import get_settings
from tg_common.models import KeywordRule

from nlp.keyword_engine import KeywordEngine

logger = structlog.get_logger()

DEFAULT_POLL_INTERVAL_S: float = 5.0


class RuleLoader:
    """Periodically fetches keyword rules from the API and hot-reloads the engine.

    Args:
        keyword_engine: The :class:`KeywordEngine` to reload when rules change.
        api_base_url: Base URL of the rules API (e.g. ``http://api:8000``).
        poll_interval_s: Seconds between polling cycles.
    """

    def __init__(
        self,
        keyword_engine: KeywordEngine,
        api_base_url: str | None = None,
        poll_interval_s: float = DEFAULT_POLL_INTERVAL_S,
    ) -> None:
        self._engine = keyword_engine
        settings = get_settings()
        self._api_base = api_base_url or f"http://{settings.api_host}:{settings.api_port}"
        self._poll_interval = poll_interval_s
        self._rules_hash: str = ""
        self._running = False
        self._task: asyncio.Task[None] | None = None

    # ── lifecycle ──

    async def start(self) -> None:
        """Begin the background polling loop."""
        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info("rule_loader_started", poll_interval_s=self._poll_interval)

    async def stop(self) -> None:
        """Stop the background polling loop."""
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("rule_loader_stopped")

    # ── polling ──

    async def _poll_loop(self) -> None:
        """Poll GET /api/v1/rules at the configured interval."""
        while self._running:
            try:
                await self._fetch_and_reload()
            except Exception:
                logger.exception("rule_loader_poll_error")
            await asyncio.sleep(self._poll_interval)

    async def _fetch_and_reload(self) -> None:
        """Fetch rules from the API and reload if changed."""
        settings = get_settings()
        url = f"{self._api_base}/api/v1/rules"
        headers = {"Authorization": f"Bearer {settings.api_key}"}

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        # Expect {"rules": [...]} or just a list
        raw_rules: list[dict[str, Any]] = data if isinstance(data, list) else data.get("rules", [])

        # Hash to detect changes
        rules_json = json.dumps(raw_rules, sort_keys=True, default=str)
        new_hash = hashlib.sha256(rules_json.encode()).hexdigest()

        if new_hash == self._rules_hash:
            return  # no change

        # Parse into KeywordRule models and reload
        rules = [KeywordRule.model_validate(r) for r in raw_rules]
        errors: list[str] = self._engine.load_rules(rules)
        self._rules_hash = new_hash

        logger.info(
            "rules_hot_reloaded",
            rule_count=len(rules),
            regex_errors=len(errors),
        )

    def load_rules_directly(self, rules: list[KeywordRule]) -> list[str]:
        """Load rules programmatically without polling (for tests).

        Args:
            rules: List of :class:`KeywordRule` instances.

        Returns:
            List of regex compilation error messages (if any).
        """
        errors: list[str] = self._engine.load_rules(rules)
        rules_json = json.dumps([r.model_dump(mode="json") for r in rules], sort_keys=True, default=str)
        self._rules_hash = hashlib.sha256(rules_json.encode()).hexdigest()
        return errors
