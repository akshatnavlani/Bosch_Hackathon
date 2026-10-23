"""CLI entrypoint for the Incident Zero agent."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from agent.adapters.alert_source import AlertSource
from agent.graph import investigate
from agent.state import IncidentState


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
    run = sub.add_parser("run", help="Run the read-only symptom investigation")
    run_source = run.add_mutually_exclusive_group(required=True)
    run_source.add_argument(
        "--alert", metavar="PATH", help="Mock alert JSON to open and investigate"
    )
    run_source.add_argument(
        "--session-dir", metavar="PATH", help="Existing session directory from open-session"
    )
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

    if args.command == "run":
        try:
            if args.alert:
                state = AlertSource().from_file(args.alert)
            else:
                state_path = Path(args.session_dir) / "state.json"
                if not state_path.is_file():
                    raise ValueError(f"session state not found: {state_path}")
                state = IncidentState.model_validate_json(state_path.read_text(encoding="utf-8"))
            report = investigate(state)
            print(f"Incident {report['incident_id']} — symptom summary")
            print(report["symptom_summary"])
            print("Evidence:")
            if report["evidence"]:
                for item in report["evidence"]:
                    print(
                        f"- [{item['kind']}/{item.get('service') or 'unknown'}] "
                        f"{item['snippet']} ({item['pointer']})"
                    )
            else:
                print("- No evidence items returned.")
            if state.session_dir:
                session_dir = Path(state.session_dir)
                (session_dir / "state.json").write_text(
                    state.model_dump_json(indent=2) + "\n", encoding="utf-8"
                )
                (session_dir / "symptoms.json").write_text(
                    json.dumps(report, indent=2) + "\n", encoding="utf-8"
                )
            return 0
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"investigation failed: {exc}", file=sys.stderr)
            return 2

    stubs = {
        "ping-llm": "ping-llm is not implemented yet; see issue D1-04.",
        "dry-run": "dry-run is not implemented yet.",
        "kill": "kill is not implemented yet.",
    }
    if args.command in stubs:
        print(stubs[args.command], file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
