"""Validate diagnosis/report payloads against organiser JSON schema (D1-16)."""

from __future__ import annotations

import json
from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "incident_report.schema.json"

__all__ = [
    "SCHEMA_PATH",
    "ValidationError",
    "is_valid_report",
    "load_schema",
    "validate_report",
]


@lru_cache(maxsize=1)
def load_schema() -> dict[str, Any]:
    """Load the incident report JSON Schema from disk."""
    with SCHEMA_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def validate_report(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate *payload* against the draft (or organiser) report schema.

    Returns the payload as a plain dict on success.
    Raises ``jsonschema.ValidationError`` when invalid.
    """
    data = dict(payload)
    Draft202012Validator(load_schema()).validate(data)
    return data


def is_valid_report(payload: Mapping[str, Any]) -> bool:
    """Return True when *payload* validates against the report schema."""
    try:
        validate_report(payload)
    except ValidationError:
        return False
    return True
