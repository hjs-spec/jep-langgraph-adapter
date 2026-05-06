"""Command line interface for the JEP LangGraph adapter."""

from __future__ import annotations

import argparse
import sys

from .exporter import JEPReplayExporter


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="jep-langgraph")
    subparsers = parser.add_subparsers(dest="command", required=True)
    replay = subparsers.add_parser("replay", help="verify and replay a JSONL JEP event chain")
    replay.add_argument("session", help="path to session.jsonl")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "replay":
        result = JEPReplayExporter.replay_file(args.session)
        if result.valid:
            print(f"Replay valid: {len(result.events)} events")
            return 0
        print("Replay invalid:", file=sys.stderr)
        for error in result.errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
