"""CLI entrypoint for the Incident Zero agent."""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="incident-zero", description="AI On-Call Engineer")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("ping-llm", help="Smoke-test LLM connectivity (implemented in D1-04)")
    sub.add_parser("run", help="Run an investigation (stub; later issues)")
    sub.add_parser("dry-run", help="Preview actions without writing (stub; later issues)")
    sub.add_parser("kill", help="Engage kill switch (stub; later issues)")
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
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
