"""CLI entrypoint for the Incident Zero agent."""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="incident-zero", description="AI On-Call Engineer")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("ping-llm", help="Smoke-test LLM connectivity (implemented in a later issue)")
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    if args.command == "ping-llm":
        print("ping-llm is not implemented yet; see issue D1-04.", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
