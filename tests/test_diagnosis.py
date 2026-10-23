import json

import pytest
from agent.diagnose import diagnose_node
from agent.state import Diagnosis, IncidentState
from pydantic import ValidationError

ITEM = {"pointer": "trace:abc123", "snippet": "payment charge (812 ms) ERROR"}

GOOD = {
    "component": "payment",
    "cause": "charge failing",
    "confidence": 0.85,
    "uncertain": False,
    "evidence": [{"kind": "trace", **ITEM, "service": "payment"}],
}


def make_state(tmp_path):
    return IncidentState(
        incident_id="t1",
        alert={"name": "high_error_rate"},
        scratchpad=[{"tool": "query_traces", "result": {"ok": True, "items": [ITEM]}}],
        session_dir=str(tmp_path),
    )


def fake_llm(payload):
    return lambda system, user: json.dumps(payload)


def test_valid_diagnosis_written(tmp_path):
    state = diagnose_node(make_state(tmp_path), fake_llm(GOOD))
    assert state.diagnosis.component == "payment"
    assert (tmp_path / "diagnosis.json").exists()


def test_invented_pointer_escalates(tmp_path):
    bad = {**GOOD, "evidence": [{"kind": "trace", "pointer": "trace:FAKE", "snippet": "x"}]}
    state = diagnose_node(make_state(tmp_path), fake_llm(bad))
    assert state.diagnosis.uncertain
    assert state.diagnosis.confidence == 0.0


def test_confident_without_evidence_rejected():
    with pytest.raises(ValidationError):
        Diagnosis(component="a", cause="b", confidence=0.9, evidence=[], uncertain=False)


def test_garbage_output_escalates(tmp_path):
    state = diagnose_node(make_state(tmp_path), lambda s, u: "not json")
    assert state.diagnosis.uncertain
