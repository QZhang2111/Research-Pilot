#!/usr/bin/env python3
"""CLI for Research Pilot understanding updates."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

THIS_DIR = Path(__file__).resolve().parent
ROOT_DIR = THIS_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from tools.understanding_store import (
    append_understanding_update,
    read_understanding_updates,
    validate_understanding_update,
    write_project_understanding,
)


def load_json(path: Path) -> Dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON file must contain an object")
    return value


def print_result(result: Dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage Research Pilot understanding updates.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    append = subparsers.add_parser("append", help="Append an UnderstandingUpdate JSON file.")
    append.add_argument("--repo", default=".")
    append.add_argument("--project", required=True)
    append.add_argument("--update", required=True)
    append.add_argument("--json", action="store_true")

    validate = subparsers.add_parser("validate", help="Validate understanding updates for a project.")
    validate.add_argument("--repo", default=".")
    validate.add_argument("--project", required=True)
    validate.add_argument("--json", action="store_true")

    build = subparsers.add_parser("build-project-understanding", help="Build ProjectUnderstanding JSON.")
    build.add_argument("--repo", default=".")
    build.add_argument("--project", required=True)
    build.add_argument("--json", action="store_true")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    root = Path(args.repo).expanduser().resolve()

    if args.command == "append":
        try:
            update = load_json(Path(args.update).expanduser().resolve())
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            result = {"valid": False, "appended": False, "errors": [str(exc)], "warnings": []}
            print_result(result, bool(args.json))
            return 1
        result = append_understanding_update(root, args.project, update)
        print_result(result, bool(args.json))
        return 0 if result.get("valid") else 1

    if args.command == "validate":
        errors = []
        updates = read_understanding_updates(root, args.project)
        for index, update in enumerate(updates, start=1):
            validation = validate_understanding_update(update)
            for error in validation["errors"]:
                errors.append({"line": index, "update_id": update.get("update_id", ""), "error": error})
        result = {"valid": not errors, "update_count": len(updates), "errors": errors}
        print_result(result, bool(args.json))
        return 0 if result["valid"] else 1

    result = write_project_understanding(root, args.project)
    output = dict(result)
    output.pop("project_understanding", None)
    print_result(output, bool(args.json))
    return 0 if result.get("valid") else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
