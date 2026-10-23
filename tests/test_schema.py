"""Placeholder tests for report schema validation (filled in D1-16)."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_draft_schema_file_exists() -> None:
    assert (ROOT / "schemas" / "incident_report.schema.json").is_file()
