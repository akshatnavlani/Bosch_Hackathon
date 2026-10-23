"""Acceptance tests for D1-10 alert listener and session bootstrap."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from agent.adapters.alert_source import (
    AlertSource,
    bootstrap_session,
    load_alert_json,
    new_incident_id,
)
from agent.main import main
from agent.state import IncidentState

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "alerts" / "mock_p1.json"


def test_incident_state_defaults() -> None:
    state = IncidentState(incident_id="inc-test", alert={"status": "firing"})
    assert state.incident_id == "inc-test"
    assert state.alert == {"status": "firing"}
    assert state.scratchpad == []
    assert state.diagnosis is None
    assert state.proposal is None
    assert state.kill_switch is False
    assert state.session_dir is None


def test_new_incident_id_format() -> None:
    iid = new_incident_id()
    assert iid.startswith("inc-")
    assert len(iid) == 4 + 12


def test_bootstrap_session_creates_dir_and_files(tmp_path: Path) -> None:
    alert = load_alert_json(FIXTURE)
    state = bootstrap_session(alert, reports_root=tmp_path, incident_id="inc-fixed01")

    session_dir = tmp_path / "sessions" / "inc-fixed01"
    assert session_dir.is_dir()
    assert state.session_dir == str(session_dir.resolve())
    assert state.scratchpad == []
    assert state.alert == alert

    alert_path = session_dir / "alert.json"
    state_path = session_dir / "state.json"
    assert alert_path.is_file()
    assert state_path.is_file()
    assert json.loads(alert_path.read_text(encoding="utf-8")) == alert
    dumped = json.loads(state_path.read_text(encoding="utf-8"))
    assert dumped["incident_id"] == "inc-fixed01"
    assert dumped["scratchpad"] == []


def test_alert_source_from_file(tmp_path: Path) -> None:
    source = AlertSource(reports_root=tmp_path)
    state = source.from_file(FIXTURE)
    assert state.incident_id.startswith("inc-")
    assert (tmp_path / "sessions" / state.incident_id).is_dir()
    assert state.alert["labels"]["alertname"] == "HighErrorRate"


def test_alert_source_poll_stubbed() -> None:
    assert AlertSource().poll() == []


def test_cli_open_session(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("REPORTS_DIR", str(tmp_path))
    code = main(["open-session", "--alert", str(FIXTURE)])
    captured = capsys.readouterr()
    assert code == 0
    assert "incident_id=" in captured.out
    assert "session_dir=" in captured.out
    sessions = list((tmp_path / "sessions").iterdir())
    assert len(sessions) == 1
    assert (sessions[0] / "alert.json").is_file()
    assert (sessions[0] / "state.json").is_file()


def test_cli_open_session_missing_file(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = main(["open-session", "--alert", "/nonexistent/alert.json"])
    captured = capsys.readouterr()
    assert code == 2
    assert "not found" in captured.err
