#!/usr/bin/env python3
"""Read-only graph query CLI for nodes, links, and deltas."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

THIS_DIR = Path(__file__).resolve().parent
ROOT_DIR = THIS_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from tools.graph_store import OPEN_DELTA_LIFECYCLES, graph_id_for_project, project_ref, relpath


def db_path(root: Path) -> Path:
    return root / "wiki" / "graphs" / "graph.db"


def connect(root: Path) -> sqlite3.Connection:
    db = db_path(root)
    if not db.exists():
        raise FileNotFoundError(f"graph database not found: {relpath(db, root)}")
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    return conn


def parse_json(value: str, fallback: Any) -> Any:
    try:
        return json.loads(value or "")
    except json.JSONDecodeError:
        return fallback


def local_id_from_ref(value: str) -> str:
    return str(value or "").split(":")[-1]


def normalize_ref(project_id: str, value: str) -> str:
    text = str(value or "").strip()
    if text.startswith(("project:", "paper:", "program:")):
        return text
    return project_ref(project_id, text)


def positioned_values(conn: sqlite3.Connection, table: str, owner_column: str, owner_id: str, value_column: str) -> List[str]:
    rows = conn.execute(f"select {value_column} from {table} where {owner_column} = ? order by position", (owner_id,)).fetchall()
    return [str(row[0]) for row in rows]


def localize_refs(values: Sequence[str]) -> List[str]:
    return [local_id_from_ref(value) for value in values]


def query_node(root: Path, project_id: str, record_id: str) -> Dict[str, Any]:
    node_id = normalize_ref(project_id, record_id)
    conn = connect(root)
    try:
        row = conn.execute("select * from nodes where node_id = ?", (node_id,)).fetchone()
        if not row:
            return {"valid": False, "error": f"node not found: {node_id}"}
        node = {
            "node_id": row["node_id"],
            "local_id": row["local_id"],
            "node_type": row["node_type"],
            "text": row["text"],
            "scope": row["scope"],
            "project_id": row["project_id"],
            "paper_id": row["paper_id"],
            "status": row["status"],
            "lifecycle_status": row["lifecycle_status"],
            "confidence": row["confidence"],
            "human_review": row["human_review"],
            "source_refs": positioned_values(conn, "node_sources", "node_id", row["node_id"], "source_ref"),
            "supersedes": parse_json(row["supersedes_json"], []),
            "superseded_by": parse_json(row["superseded_by_json"], []),
            "derived_from": parse_json(row["derived_from_json"], []),
            "metadata": parse_json(row["metadata_json"], {}),
        }
    finally:
        conn.close()
    return {"valid": True, "project": project_id, "node": node}


def query_link(root: Path, project_id: str, record_id: str) -> Dict[str, Any]:
    link_id = normalize_ref(project_id, record_id)
    conn = connect(root)
    try:
        row = conn.execute("select * from links where link_id = ?", (link_id,)).fetchone()
        if not row:
            return {"valid": False, "error": f"link not found: {link_id}"}
        payload = parse_json(row["payload_json"], {})
        link = {
            "link_id": row["link_id"],
            "local_id": row["local_id"],
            "link_type": row["link_type"],
            "relation": row["relation"],
            "confidence": row["confidence"],
            "human_review": row["human_review"],
            "from_nodes": localize_refs(positioned_values(conn, "link_from_nodes", "link_id", row["link_id"], "node_id")),
            "to_nodes": localize_refs(positioned_values(conn, "link_to_nodes", "link_id", row["link_id"], "node_id")),
            "warrant_nodes": localize_refs(positioned_values(conn, "link_warrants", "link_id", row["link_id"], "node_id")),
            "limitation_nodes": localize_refs(positioned_values(conn, "link_limitations", "link_id", row["link_id"], "node_id")),
            "project_warrant_nodes": localize_refs(positioned_values(conn, "link_project_warrants", "link_id", row["link_id"], "node_id")),
            "project_limitation_nodes": localize_refs(positioned_values(conn, "link_project_limitations", "link_id", row["link_id"], "node_id")),
            "source_refs": positioned_values(conn, "link_sources", "link_id", row["link_id"], "source_ref"),
            "payload": payload,
        }
    finally:
        conn.close()
    return {"valid": True, "project": project_id, "link": link}


def row_to_delta(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "delta_id": row["delta_id"],
        "local_id": row["local_id"],
        "source_graph_id": row["source_graph_id"],
        "source_dossier": row["source_dossier"],
        "event_type": row["event_type"],
        "created_at": row["created_at"],
        "status": row["status"],
        "lifecycle_status": row["lifecycle_status"],
        "decision": row["decision"],
        "decision_note": row["decision_note"],
        "decided_at": row["decided_at"],
        "human_review": row["human_review"],
        "summary": row["summary"],
        "evolution_type": row["evolution_type"],
        "rationale": row["rationale"],
        "before": parse_json(row["before_json"], {}),
        "after": parse_json(row["after_json"], {}),
        "caused_by": parse_json(row["caused_by_json"], []),
        "supersedes": parse_json(row["supersedes_json"], []),
        "payload": parse_json(row["payload_json"], {}),
        "operation": parse_json(row["operation_json"], []),
        "source_paper_nodes": parse_json(row["source_paper_nodes_json"], []),
    }


def query_delta(root: Path, project_id: str, record_id: str) -> Dict[str, Any]:
    delta_id = normalize_ref(project_id, record_id)
    conn = connect(root)
    try:
        row = conn.execute("select * from deltas where graph_id = ? and delta_id = ?", (graph_id_for_project(project_id), delta_id)).fetchone()
        if not row:
            return {"valid": False, "error": f"delta not found: {delta_id}"}
        delta = row_to_delta(row)
    finally:
        conn.close()
    return {"valid": True, "project": project_id, "delta": delta}


def query_open(root: Path, project_id: str) -> Dict[str, Any]:
    conn = connect(root)
    try:
        placeholders = ",".join("?" for _ in OPEN_DELTA_LIFECYCLES)
        rows = conn.execute(
            f"select * from deltas where graph_id = ? and lifecycle_status in ({placeholders}) order by local_id",
            (graph_id_for_project(project_id), *sorted(OPEN_DELTA_LIFECYCLES)),
        ).fetchall()
        deltas = [row_to_delta(row) for row in rows]
    finally:
        conn.close()
    return {"valid": True, "project": project_id, "open_deltas": [delta["local_id"] for delta in deltas], "deltas": deltas, "counts": {"open_deltas": len(deltas)}}


def query_summary(root: Path, project_id: str) -> Dict[str, Any]:
    graph_id = graph_id_for_project(project_id)
    conn = connect(root)
    try:
        node_counts = dict(conn.execute("select node_type, count(*) from nodes where graph_id = ? group by node_type", (graph_id,)).fetchall())
        link_count = conn.execute("select count(*) from links where graph_id = ?", (graph_id,)).fetchone()[0]
        delta_count = conn.execute("select count(*) from deltas where graph_id = ?", (graph_id,)).fetchone()[0]
        open_count = conn.execute(
            f"select count(*) from deltas where graph_id = ? and lifecycle_status in ({','.join('?' for _ in OPEN_DELTA_LIFECYCLES)})",
            (graph_id, *sorted(OPEN_DELTA_LIFECYCLES)),
        ).fetchone()[0]
    finally:
        conn.close()
    return {"valid": True, "project": project_id, "node_counts": node_counts, "link_count": link_count, "delta_count": delta_count, "open_delta_count": open_count}


def print_result(result: Dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only graph query CLI for nodes, links, and deltas.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ["node", "link", "delta"]:
        sub = subparsers.add_parser(command)
        sub.add_argument("--repo", default=".")
        sub.add_argument("--project", required=True)
        sub.add_argument("--id", required=True)
        sub.add_argument("--json", action="store_true")
    for command in ["open", "summary"]:
        sub = subparsers.add_parser(command)
        sub.add_argument("--repo", default=".")
        sub.add_argument("--project", required=True)
        sub.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    root = Path(args.repo).resolve()
    try:
        if args.command == "node":
            result = query_node(root, args.project, args.id)
        elif args.command == "link":
            result = query_link(root, args.project, args.id)
        elif args.command == "delta":
            result = query_delta(root, args.project, args.id)
        elif args.command == "open":
            result = query_open(root, args.project)
        else:
            result = query_summary(root, args.project)
    except FileNotFoundError as exc:
        result = {"valid": False, "error": str(exc)}
    print_result(result, args.json)
    return 0 if result.get("valid") else 1


if __name__ == "__main__":
    raise SystemExit(main())
