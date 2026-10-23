"""Diagnose node: scratchpad -> evidence-backed Diagnosis."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

from pydantic import ValidationError

from agent.reporting.evidence import check_evidence
from agent.state import Diagnosis, IncidentState

PROMPT_PATH = Path(__file__).parent / "prompts" / "diagnose.md"


def _escalate(reason: str) -> Diagnosis:
    return Diagnosis(
        component="unknown",
        cause=f"Escalated: {reason}",
        confidence=0.0,
        uncertain=True,
    )


def diagnose_node(state: IncidentState, llm: Callable[[str, str], str]) -> IncidentState:
    """llm(system_prompt, user_content) must return a JSON string."""
    system = PROMPT_PATH.read_text(encoding="utf-8")
    user = json.dumps({"alert": state.alert, "scratchpad": state.scratchpad})

    try:
        diagnosis = Diagnosis.model_validate_json(llm(system, user))
        problems = check_evidence(diagnosis, state.scratchpad)
        if problems:
            diagnosis = _escalate("; ".join(problems))
    except (ValidationError, ValueError) as exc:
        diagnosis = _escalate(f"invalid diagnosis output ({type(exc).__name__})")

    state.diagnosis = diagnosis
    out_dir = Path(state.session_dir or f"reports/sessions/{state.incident_id}")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "diagnosis.json").write_text(diagnosis.model_dump_json(indent=2), encoding="utf-8")
    return state
