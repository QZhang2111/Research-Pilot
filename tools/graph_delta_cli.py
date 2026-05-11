#!/usr/bin/env python3
"""CLI for human-gated Research Pilot graph deltas."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

THIS_DIR = Path(__file__).resolve().parent
ROOT_DIR = THIS_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from tools.graph_delta_api import decide_graph_delta, dry_run_graph_delta, load_delta_file, register_graph_delta


def print_result(result: Dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Human-gated graph delta operations.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_common(subparser: argparse.ArgumentParser) -> None:
        subparser.add_argument("--repo", default=".", help="Workspace root.")
        subparser.add_argument("--project", required=True, help="Project id.")
        subparser.add_argument("--json", action="store_true", help="Print formatted JSON.")

    dry_run = subparsers.add_parser("dry-run", help="Preview a delta JSON file without writing events.")
    add_common(dry_run)
    dry_run.add_argument("--delta", required=True, help="Delta JSON file.")

    register = subparsers.add_parser("register", help="Append delta.proposed after a valid dry-run.")
    add_common(register)
    register.add_argument("--delta", required=True, help="Delta JSON file.")
    register.add_argument("--actor", default="agent", help="Event actor.")
    register.add_argument("--decision-note", default="", help="Optional registration note.")

    decide = subparsers.add_parser("decide", help="Apply a human decision to a registered delta.")
    add_common(decide)
    decide.add_argument("--id", required=True, help="Delta local id, e.g. D1.")
    decide.add_argument("--decision", required=True, choices=["accept", "accepted", "reject", "rejected", "park", "parked", "revise", "revised"])
    decide.add_argument("--actor", default="human", help="Event actor.")
    decide.add_argument("--decision-note", default="", help="Human decision note.")

    args = parser.parse_args(argv)
    root = Path(args.repo).resolve()
    try:
        if args.command == "dry-run":
            result = dry_run_graph_delta(root, args.project, load_delta_file(Path(args.delta)))
        elif args.command == "register":
            result = register_graph_delta(root, args.project, load_delta_file(Path(args.delta)), actor=args.actor, decision_note=args.decision_note)
        else:
            result = decide_graph_delta(root, args.project, args.id, args.decision, actor=args.actor, decision_note=args.decision_note)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        result = {"valid": False, "error": str(exc)}
    print_result(result, args.json)
    return 0 if result.get("valid") else 1


if __name__ == "__main__":
    raise SystemExit(main())
