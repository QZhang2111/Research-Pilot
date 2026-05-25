#!/usr/bin/env python3
"""CLI for Research Pilot local dataset commands."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

THIS_DIR = Path(__file__).resolve().parent
ROOT_DIR = THIS_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from tools.research_dataset import DB_FILENAME, SCHEMA_VERSION, initialize_dataset
from tools.research_dataset_import import import_legacy_project
from tools.research_dataset_read_models import build_project_summary_model


def print_json(value: dict[str, Any], *, stderr: bool = False) -> None:
    print(json.dumps(value, sort_keys=True), file=sys.stderr if stderr else sys.stdout)


def cmd_init(args: argparse.Namespace) -> dict[str, Any]:
    initialize_dataset(Path(args.repo))
    return {"valid": True, "db": DB_FILENAME, "schema_version": SCHEMA_VERSION}


def cmd_import_legacy(args: argparse.Namespace) -> dict[str, Any]:
    return import_legacy_project(Path(args.repo), args.project, reset=args.reset)


def cmd_summary(args: argparse.Namespace) -> dict[str, Any]:
    result = build_project_summary_model(Path(args.repo), args.project)
    result["valid"] = True
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage Research Pilot local dataset.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init", help="Initialize local dataset.")
    init.add_argument("--repo", required=True)
    init.set_defaults(handler=cmd_init)

    import_legacy = subparsers.add_parser("import-legacy", help="Import legacy project data.")
    import_legacy.add_argument("--repo", required=True)
    import_legacy.add_argument("--project", required=True)
    import_legacy.add_argument("--reset", action="store_true")
    import_legacy.set_defaults(handler=cmd_import_legacy)

    summary = subparsers.add_parser("summary", help="Print project summary model.")
    summary.add_argument("--repo", required=True)
    summary.add_argument("--project", required=True)
    summary.set_defaults(handler=cmd_summary)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = args.handler(args)
    except Exception as exc:
        print_json({"valid": False, "error": str(exc)}, stderr=True)
        return 1
    print_json(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
