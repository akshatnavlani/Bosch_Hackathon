"""CLI entrypoint for the Incident Zero agent."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from agent.adapters.alert_source import AlertSource


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="incident-zero", description="AI On-Call Engineer")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("ping-llm", help="Smoke-test LLM connectivity (implemented in D1-04)")
    open_session = sub.add_parser(
        "open-session",
        help="Open an investigation session from a mock alert JSON file",
    )
    open_session.add_argument(
        "--alert",
        required=True,
        metavar="PATH",
        help="Path to mock alert JSON",
    )
    sub.add_parser("run", help="Run an investigation (stub; later issues)")
    sub.add_parser("dry-run", help="Preview actions without writing (stub; later issues)")
    sub.add_parser("kill", help="Engage kill switch (stub; later issues)")
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    if args.command == "open-session":
        alert_path = Path(args.alert)
        if not alert_path.is_file():
            print(f"alert file not found: {alert_path}", file=sys.stderr)
            return 2
        try:
            state = AlertSource().from_file(alert_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"failed to open session: {exc}", file=sys.stderr)
            return 2
        print(f"incident_id={state.incident_id}")
        print(f"session_dir={state.session_dir}")
        return 0

    stubs = {
        "ping-llm": "ping-llm is not implemented yet; see issue D1-04.",
        "run": "run is not implemented yet.",
        "dry-run": "dry-run is not implemented yet.",
        "kill": "kill is not implemented yet.",
    }
    if args.command in stubs:
        print(stubs[args.command], file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
