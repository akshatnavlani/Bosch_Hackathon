"""Incident session state and evidence models.

IncidentState is the Day-1 session bootstrap model. Full Evidence / Diagnosis /
ProposedAction schemas land in later issues (D1-14 / D1-16).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class IncidentState(BaseModel):
    """Minimal LangGraph-ready incident session state."""

    incident_id: str
    alert: dict[str, Any]
    scratchpad: list[dict[str, Any]] = Field(default_factory=list)
    diagnosis: dict[str, Any] | None = None
    proposal: dict[str, Any] | None = None
    kill_switch: bool = False
    session_dir: str | None = None
