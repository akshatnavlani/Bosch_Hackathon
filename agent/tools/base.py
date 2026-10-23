"""Shared compact result helpers for read-only investigation tools."""

from __future__ import annotations

from typing import Any

MAX_ITEMS = 20
MAX_SNIPPET_LENGTH = 240


def tool_result(
    *, kind: str, service: str | None, summary: str,
    items: list[dict[str, str]] | None = None, ok: bool = True,
) -> dict[str, Any]:
    """Build the compact, shared response shape and cap evidence size."""
    capped = [
        {"pointer": str(item.get("pointer", ""))[:MAX_SNIPPET_LENGTH],
         "snippet": str(item.get("snippet", ""))[:MAX_SNIPPET_LENGTH]}
        for item in (items or [])[:MAX_ITEMS]
    ]
    return {
        "ok": ok, "kind": kind, "service": service,
        "summary": summary[:MAX_SNIPPET_LENGTH], "items": capped,
    }
