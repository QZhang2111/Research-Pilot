#!/usr/bin/env python3
"""Build generated SQLite graph read index from graph-event JSONL."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

THIS_DIR = Path(__file__).resolve().parent
ROOT_DIR = THIS_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from tools.graph_store import build_graph_db_from_event_files, graph_event_paths, relpath


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Build generated SQLite graph read index from graph-event JSONL.")
    parser.add_argument("--repo", default=".", help="Workspace root.")
    parser.add_argument("--project", help="Project id for wiki/graphs/events/projects/<project>.jsonl.")
    parser.add_argument("--events", nargs="+", help="One or more graph-event JSONL files. Defaults to wiki/graphs/events/**/*.jsonl.")
    parser.add_argument("--output", default="wiki/graphs/graph.db", help="Output SQLite path relative to workspace root.")
    args = parser.parse_args(argv)

    root = Path(args.repo).resolve()
    event_paths = [Path(value) if Path(value).is_absolute() else root / value for value in args.events] if args.events else graph_event_paths(root, args.project)
    if not event_paths:
        parser.error("no graph event files found")
    output = Path(args.output) if Path(args.output).is_absolute() else root / args.output
    stats = build_graph_db_from_event_files(event_paths, output)
    print(f"Wrote {relpath(output, root)}")
    print(f"Graphs: {stats['graphs']} Events: {stats['events']} Nodes: {stats['nodes']} Links: {stats['links']} Deltas: {stats['deltas']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
