"""CI-safe checks for D1-02 fault inject/reset runbook (no live demo calls)."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNBOOK = ROOT / "docs" / "faultctl-runbook.md"


def _text() -> str:
    assert RUNBOOK.is_file(), "docs/faultctl-runbook.md missing"
    return RUNBOOK.read_text(encoding="utf-8")


def test_runbook_covers_inject_and_reset() -> None:
    text = _text().lower()
    for needle in ("inject", "reset", "faultctl", "smoke_demo.sh"):
        assert needle in text, f"runbook must mention {needle!r}"


def test_runbook_warns_telemetry_only() -> None:
    text = _text()
    assert "WARNING" in text
    assert "telemetry only" in text.lower()


def test_runbook_lists_expected_symptoms() -> None:
    text = _text().lower()
    assert "expected symptoms" in text
    for needle in ("prometheus", "jaeger"):
        assert needle in text, f"runbook must mention {needle!r}"
