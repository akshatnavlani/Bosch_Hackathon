"""Smoke checks for D1-03 package skeleton and CLI entrypoint."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_python_m_agent_main_help() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "agent.main", "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "incident-zero" in result.stdout or "AI On-Call" in result.stdout


def test_core_stub_modules_importable() -> None:
    import agent.adapters  # noqa: F401
    import agent.config  # noqa: F401
    import agent.graph  # noqa: F401
    import agent.reporting  # noqa: F401
    import agent.safety  # noqa: F401
    import agent.state  # noqa: F401
    import agent.tools  # noqa: F401
