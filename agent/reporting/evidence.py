"""Check that diagnosis evidence was really returned by tools."""

from __future__ import annotations

from typing import Any

from agent.state import Diagnosis


def collect_items(scratchpad: list[dict[str, Any]]) -> dict[str, str]:
    """Map pointer -> snippet for every item any tool returned."""
    found: dict[str, str] = {}
    for entry in scratchpad:
        result = entry.get("result", entry)
        if not isinstance(result, dict):
            continue
        for item in result.get("items", []):
            if item.get("pointer") and item.get("snippet"):
                found[item["pointer"]] = item["snippet"]
    return found


def check_evidence(diagnosis: Diagnosis, scratchpad: list[dict[str, Any]]) -> list[str]:
    """Return a list of problems. An empty list means the evidence is valid."""
    known = collect_items(scratchpad)
    problems = []
    for ev in diagnosis.evidence:
        if ev.pointer not in known:
            problems.append(f"pointer not in scratchpad: {ev.pointer}")
        elif ev.snippet not in known[ev.pointer]:
            problems.append(f"snippet does not match tool output for {ev.pointer}")
    return problems
