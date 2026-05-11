#!/usr/bin/env python3
"""Validate Research Pilot graph-event JSONL files."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

THIS_DIR = Path(__file__).resolve().parent
ROOT_DIR = THIS_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from tools.graph_store import graph_event_paths, validate_event_files


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Validate graph-event JSONL files.")
    parser.add_argument("--repo", default=".", help="Workspace root.")
    parser.add_argument("--project", help="Project id for wiki/graphs/events/projects/<project>.jsonl.")
    parser.add_argument("--events", nargs="+", help="Explicit event JSONL files.")
    parser.add_argument("--json", action="store_true", help="Print full JSON result.")
    args = parser.parse_args(argv)

    root = Path(args.repo).resolve()
    paths = [Path(value) if Path(value).is_absolute() else root / value for value in args.events] if args.events else graph_event_paths(root, args.project)
    if not paths:
        parser.error("no graph event files found")
    result = validate_event_files(paths)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    elif result["valid"]:
        print(f"Graph events valid. Events: {result['event_count']}")
    else:
        for error in result["errors"]:
            print(f"{error['path']}:{error['line']}: {error['error']}", file=sys.stderr)
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
