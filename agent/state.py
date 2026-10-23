"""Incident session state and evidence models.

IncidentState is the Day-1 session bootstrap model. Evidence and Diagnosis
(D1-14) live here; ProposedAction lands in a later issue.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class Evidence(BaseModel):
    kind: Literal["trace", "metric", "log", "health"]
    pointer: str
    snippet: str
    service: str | None = None


class Diagnosis(BaseModel):
    component: str
    cause: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[Evidence] = Field(default_factory=list)
    uncertain: bool = False

    @model_validator(mode="after")
    def _confident_needs_evidence(self) -> Diagnosis:
        if (not self.uncertain or self.confidence >= 0.5) and not self.evidence:
            raise ValueError("confident diagnosis must include evidence")
        return self


class IncidentState(BaseModel):
    """Minimal LangGraph-ready incident session state."""

    incident_id: str
    alert: dict[str, Any]
    scratchpad: list[dict[str, Any]] = Field(default_factory=list)
    diagnosis: Diagnosis | None = None
    proposal: dict[str, Any] | None = None
    kill_switch: bool = False
    session_dir: str | None = None
