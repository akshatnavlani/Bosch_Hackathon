"""Alert / incident session bootstrap source (D1-10).

Opens a session from mock alert JSON and persists under reports/sessions/.
Prometheus alert polling is stubbed until a live listener is ready.
"""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any

from agent.state import IncidentState

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_REPORTS_ROOT = _REPO_ROOT / "reports"


def new_incident_id() -> str:
    """Return a short unique incident id (e.g. inc-a1b2c3d4e5f6)."""
    return f"inc-{uuid.uuid4().hex[:12]}"


def default_reports_root() -> Path:
    """Resolve reports root: REPORTS_DIR env, else repo reports/."""
    env = os.environ.get("REPORTS_DIR")
    if env:
        return Path(env).expanduser().resolve()
    return _DEFAULT_REPORTS_ROOT


def load_alert_json(path: Path | str) -> dict[str, Any]:
    """Load and parse a mock alert JSON file."""
    alert_path = Path(path)
    with alert_path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"alert JSON must be an object, got {type(data).__name__}")
    return data


def bootstrap_session(
    alert: dict[str, Any],
    *,
    reports_root: Path | None = None,
    incident_id: str | None = None,
) -> IncidentState:
    """Create IncidentState and persist session folder for later report writing."""
    root = Path(reports_root) if reports_root is not None else default_reports_root()
    iid = incident_id or new_incident_id()
    session_dir = (root / "sessions" / iid).resolve()
    session_dir.mkdir(parents=True, exist_ok=True)

    state = IncidentState(
        incident_id=iid,
        alert=alert,
        scratchpad=[],
        session_dir=str(session_dir),
    )

    alert_path = session_dir / "alert.json"
    state_path = session_dir / "state.json"
    alert_path.write_text(json.dumps(alert, indent=2) + "\n", encoding="utf-8")
    state_path.write_text(state.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return state


class AlertSource:
    """Alert ingest adapter: mock file bootstrap + stubbed Prometheus poll."""

    def __init__(self, *, reports_root: Path | None = None) -> None:
        self.reports_root = reports_root

    def from_file(self, path: Path | str) -> IncidentState:
        """Open a new investigation session from a mock alert JSON file."""
        alert = load_alert_json(path)
        return bootstrap_session(alert, reports_root=self.reports_root)

    def poll(self) -> list[dict[str, Any]]:
        """Stub: Prometheus alert polling is not wired yet."""
        return []
