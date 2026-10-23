"""Tests for draft incident report schema validation (D1-16)."""

from __future__ import annotations

from pathlib import Path

import pytest
from agent.reporting.schema_validate import is_valid_report, load_schema, validate_report
from jsonschema.exceptions import ValidationError

ROOT = Path(__file__).resolve().parents[1]


def _minimal_report(**overrides: object) -> dict:
    report: dict = {
        "incident_id": "inc-p1-demo",
        "status": "diagnosed",
        "timeline": [
            {
                "ts": "2026-10-23T10:00:00Z",
                "event": "alert_received",
                "detail": "checkout error rate spike",
            }
        ],
        "root_cause": {
            "component": "payment",
            "summary": "payment service returning elevated 5xx on checkout",
        },
        "confidence": 0.85,
        "evidence": [
            {
                "kind": "metric",
                "pointer": 'promql:rate(http_requests_total{service="payment"}[5m])',
                "snippet": "payment 5xx rate ~0.92",
                "service": "payment",
            }
        ],
    }
    report.update(overrides)
    return report


def test_draft_schema_file_exists() -> None:
    assert (ROOT / "schemas" / "incident_report.schema.json").is_file()


def test_schema_readme_mentions_organiser_replacement() -> None:
    readme = ROOT / "schemas" / "README.md"
    assert readme.is_file()
    text = readme.read_text(encoding="utf-8").lower()
    assert "organiser" in text
    assert "replace" in text


def test_load_schema_has_required_keys() -> None:
    schema = load_schema()
    assert schema.get("title") == "IncidentReport"
    required = set(schema.get("required", []))
    assert {
        "incident_id",
        "status",
        "timeline",
        "root_cause",
        "confidence",
        "evidence",
    } <= required


def test_valid_minimal_report_passes() -> None:
    payload = _minimal_report()
    assert validate_report(payload) == payload
    assert is_valid_report(payload) is True


def test_valid_report_with_optional_action() -> None:
    payload = _minimal_report(
        status="proposed",
        action={
            "action_type": "restart",
            "target": "payment",
            "params": {},
        },
    )
    assert is_valid_report(payload) is True
    validate_report(payload)


def test_missing_evidence_fails() -> None:
    payload = _minimal_report()
    del payload["evidence"]
    assert is_valid_report(payload) is False
    with pytest.raises(ValidationError):
        validate_report(payload)


def test_out_of_range_confidence_fails() -> None:
    payload = _minimal_report(confidence=1.5)
    assert is_valid_report(payload) is False
    with pytest.raises(ValidationError):
        validate_report(payload)


def test_invalid_action_type_fails() -> None:
    payload = _minimal_report(
        action={
            "action_type": "delete_everything",
            "target": "payment",
            "params": {},
        }
    )
    assert is_valid_report(payload) is False
    with pytest.raises(ValidationError):
        validate_report(payload)
