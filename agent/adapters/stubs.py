"""Pre-kickoff mocks for Action API, alerts, and fault injection."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class StubTransport:
    """Pretend transport: logs the payload and returns ok/stub. Sends nothing."""

    def __init__(self) -> None:
        # Keep every payload so tests can check what would have been sent.
        self.calls: list[dict[str, Any]] = []

    def send(self, base_url: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(payload)
        logger.info("[stub] Action API payload (not sent): %s", payload)
        return {"ok": True, "stub": True, "base_url": base_url, "payload": payload}
