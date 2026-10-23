"""Action API client adapter (D1-13).

Sole write path to the organiser Action API. Day 1 is stub-only: the client builds a
payload and hands it to a transport. The only transport shipped is StubTransport, which
logs the payload and never makes an HTTP call. The real HTTP transport is swapped in on
the day (Day 2), after human approval + kill switch exist.
"""

from __future__ import annotations

import os
from typing import Any, Protocol

from agent.adapters.stubs import StubTransport


class Transport(Protocol):
    """Anything that can deliver an Action API payload."""

    def send(self, base_url: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Deliver the payload and return the response."""
        raise NotImplementedError


class ActionAPIClient:
    """Four allowlisted actions. Each one just builds a payload and passes it on."""

    def __init__(self, base_url: str | None = None, transport: Transport | None = None) -> None:
        # Base URL comes from ACTION_API_URL so it can be swapped on the day.
        if base_url is None:
            base_url = os.environ.get("ACTION_API_URL", "")
        self.base_url = base_url
        # Default is the stub, so nothing real is ever sent on Day 1.
        self.transport: Transport = transport if transport is not None else StubTransport()

    def _send(self, action_type: str, target: str, params: dict[str, Any]) -> dict[str, Any]:
        payload = {"action_type": action_type, "target": target, "params": params}
        return self.transport.send(self.base_url, payload)

    def restart(self, service: str) -> dict[str, Any]:
        return self._send("restart", service, {})

    def toggle_flag(self, flag: str, enabled: bool) -> dict[str, Any]:
        return self._send("toggle_flag", flag, {"enabled": enabled})

    def throttle_loadgen(self, users: int) -> dict[str, Any]:
        return self._send("throttle_loadgen", "load-generator", {"users": users})

    def scale(self, service: str, replicas: int) -> dict[str, Any]:
        return self._send("scale", service, {"replicas": replicas})