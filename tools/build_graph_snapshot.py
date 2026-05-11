#!/usr/bin/env python3
"""Build graph snapshot JSON from graph-event JSONL."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

THIS_DIR = Path(__file__).resolve().parent
ROOT_DIR = THIS_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from tools.graph_store import build_snapshot_from_event_files, relpath, write_json


def default_events(project: str) -> str:
    return f"wiki/graphs/events/projects/{project}.jsonl"


def default_output(project: str) -> str:
    return f"wiki/graphs/snapshots/projects/{project}.graph.json"


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Build graph snapshot JSON from graph-event JSONL.")
    parser.add_argument("--repo", default=".", help="Workspace root.")
    parser.add_argument("--project", help="Project id for default paths.")
    parser.add_argument("--events", nargs="+", help="One or more graph-event JSONL files.")
    parser.add_argument("--output", help="Output snapshot JSON path.")
    parser.add_argument("--generated-at", help="Snapshot timestamp. Defaults to current UTC time.")
    args = parser.parse_args(argv)

    if not args.project and not args.events:
        parser.error("--project or --events is required")
    root = Path(args.repo).resolve()
    event_values = args.events or [default_events(args.project)]
    event_paths = [Path(value) if Path(value).is_absolute() else root / value for value in event_values]
    output_value = args.output or default_output(args.project)
    output = Path(output_value) if Path(output_value).is_absolute() else root / output_value
    snapshot = build_snapshot_from_event_files(event_paths, generated_at=args.generated_at)
    write_json(output, snapshot)
    print(f"Wrote {relpath(output, root)}")
    print(f"Nodes: {len(snapshot['nodes'])} Links: {len(snapshot['links'])} Deltas: {len(snapshot['deltas'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
