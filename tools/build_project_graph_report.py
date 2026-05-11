#!/usr/bin/env python3
"""Build generated project-understanding graph markdown reports from graph.db."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

THIS_DIR = Path(__file__).resolve().parent
ROOT_DIR = THIS_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from tools.graph_store import OPEN_DELTA_LIFECYCLES, graph_id_for_project, relpath


GENERATED_MARKER = "<!-- GENERATED FROM graph.db; DO NOT EDIT Q/C/E/W/L/RL/TL/D TABLES BY HAND. -->"


def default_output_path(root: Path, project_id: str) -> Path:
    return root / "wiki" / "projects" / project_id / "project-understanding-graph.md"


def default_db_path(root: Path) -> Path:
    return root / "wiki" / "graphs" / "graph.db"


def read_json(value: str, fallback: Any) -> Any:
    try:
        return json.loads(value or "")
    except json.JSONDecodeError:
        return fallback


def markdown_cell(value: Any) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", "<br>")


def local_id_from_ref(value: str) -> str:
    return str(value or "").split(":")[-1]


def local_refs(values: Sequence[str]) -> List[str]:
    return [local_id_from_ref(value) for value in values]


def positioned_values(conn: sqlite3.Connection, table: str, owner_column: str, owner_id: str, value_column: str) -> List[str]:
    rows = conn.execute(f"select {value_column} from {table} where {owner_column} = ? order by position", (owner_id,)).fetchall()
    return [str(row[0]) for row in rows]


def frontmatter(project_id: str) -> str:
    return (
        "---\n"
        f'title: "{project_id} Project Understanding Graph"\n'
        "type: artifact\n"
        "status: active\n"
        "human_review: pending\n"
        "tags: [project-understanding-graph, generated, graph-store]\n"
        f'sources: ["wiki/graphs/events/projects/{project_id}.jsonl"]\n'
        "---\n"
    )


def connect(db_path: Path, root: Path) -> sqlite3.Connection:
    if not db_path.exists():
        raise FileNotFoundError(f"graph database not found: {relpath(db_path, root)}")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def build_project_graph_report(root: Path, project_id: str, db_path: Optional[Path] = None) -> str:
    root = root.resolve()
    db = (db_path or default_db_path(root)).resolve()
    graph_id = graph_id_for_project(project_id)
    conn = connect(db, root)
    try:
        graph = conn.execute("select * from graphs where graph_id = ?", (graph_id,)).fetchone()
        if not graph:
            raise ValueError(f"project graph not found: {graph_id}")
        nodes = load_nodes(conn, graph_id)
        links = load_links(conn, graph_id)
        deltas = load_deltas(conn, graph_id)
    finally:
        conn.close()

    reasoning_links = [link for link in links if link["link_type"] == "ReasoningLink"]
    translation_links = [link for link in links if link["link_type"] == "TranslationLink"]
    parts = [
        frontmatter(project_id),
        GENERATED_MARKER,
        "",
        f"# {project_id} Project Understanding Graph",
        "",
        "This report is generated from `wiki/graphs/graph.db`.",
        "Graph truth lives in `wiki/graphs/events/**/*.jsonl`; this markdown file is a rebuildable read model.",
        "",
        "## Current Graph Snapshot",
        "",
        snapshot_table(nodes, reasoning_links, translation_links, deltas),
        "",
        render_nodes_section("Project Questions", nodes.get("Question", []), ["ID", "Question", "Status", "Confidence", "Human review"], standard_node_row),
        "",
        render_nodes_section("Project Claims", nodes.get("Claim", []), ["ID", "Claim", "Status", "Confidence", "Human review"], standard_node_row),
        "",
        render_nodes_section("Evidence", nodes.get("Evidence", []), ["ID", "Evidence", "Kind", "Confidence", "Source refs"], evidence_row),
        "",
        render_nodes_section("Warrants", nodes.get("Warrant", []), ["ID", "Warrant", "Basis", "Confidence", "Source refs"], warrant_row),
        "",
        render_nodes_section("Limitations", nodes.get("Limitation", []), ["ID", "Limitation", "Severity", "Confidence", "Source refs"], limitation_row),
        "",
        render_reasoning_links(reasoning_links),
        "",
        render_translation_links(translation_links),
        "",
        render_delta_history(deltas),
        "",
        render_open_audit_questions(nodes, reasoning_links, deltas),
        "",
    ]
    return "\n".join(parts)


def load_nodes(conn: sqlite3.Connection, graph_id: str) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {"Question": [], "Claim": [], "Evidence": [], "Warrant": [], "Limitation": []}
    rows = conn.execute("select * from nodes where graph_id = ? order by local_id", (graph_id,)).fetchall()
    for row in rows:
        node = {
            "node_id": row["node_id"],
            "local_id": row["local_id"],
            "node_type": row["node_type"],
            "text": row["text"],
            "status": row["status"],
            "lifecycle_status": row["lifecycle_status"],
            "confidence": row["confidence"],
            "human_review": row["human_review"],
            "source_refs": positioned_values(conn, "node_sources", "node_id", row["node_id"], "source_ref"),
            "metadata": read_json(row["metadata_json"], {}),
        }
        grouped.setdefault(node["node_type"], []).append(node)
    return grouped


def load_links(conn: sqlite3.Connection, graph_id: str) -> List[Dict[str, Any]]:
    rows = conn.execute("select * from links where graph_id = ? order by local_id", (graph_id,)).fetchall()
    links: List[Dict[str, Any]] = []
    for row in rows:
        payload = read_json(row["payload_json"], {})
        links.append(
            {
                "link_id": row["link_id"],
                "local_id": row["local_id"],
                "link_type": row["link_type"],
                "relation": row["relation"],
                "confidence": row["confidence"],
                "human_review": row["human_review"],
                "from_nodes": local_refs(positioned_values(conn, "link_from_nodes", "link_id", row["link_id"], "node_id")),
                "to_nodes": local_refs(positioned_values(conn, "link_to_nodes", "link_id", row["link_id"], "node_id")),
                "warrant_nodes": local_refs(positioned_values(conn, "link_warrants", "link_id", row["link_id"], "node_id")),
                "limitation_nodes": local_refs(positioned_values(conn, "link_limitations", "link_id", row["link_id"], "node_id")),
                "project_warrant_nodes": local_refs(positioned_values(conn, "link_project_warrants", "link_id", row["link_id"], "node_id")),
                "project_limitation_nodes": local_refs(positioned_values(conn, "link_project_limitations", "link_id", row["link_id"], "node_id")),
                "source_refs": positioned_values(conn, "link_sources", "link_id", row["link_id"], "source_ref"),
                "source_input": payload.get("source_input") or "",
            }
        )
    return links


def load_deltas(conn: sqlite3.Connection, graph_id: str) -> List[Dict[str, Any]]:
    rows = conn.execute("select * from deltas where graph_id = ? order by created_at, local_id", (graph_id,)).fetchall()
    deltas: List[Dict[str, Any]] = []
    for row in rows:
        affected_nodes = positioned_values(conn, "delta_affected_nodes", "delta_id", row["delta_id"], "node_id")
        affected_links = positioned_values(conn, "delta_affected_links", "delta_id", row["delta_id"], "link_id")
        delta = {
            "local_id": row["local_id"],
            "summary": row["summary"],
            "lifecycle_status": row["lifecycle_status"],
            "human_review": row["human_review"],
            "evolution_type": row["evolution_type"],
            "operation": read_json(row["operation_json"], []),
            "affected": local_refs(affected_nodes + affected_links),
            "source_dossier": row["source_dossier"],
        }
        if is_reportable_delta(delta):
            deltas.append(delta)
    return deltas


def is_reportable_delta(delta: Dict[str, Any]) -> bool:
    local_id = str(delta.get("local_id") or "")
    summary = str(delta.get("summary") or "").lower()
    if local_id.startswith("NOOP"):
        return False
    if "smoke-test" in summary:
        return False
    return True


def snapshot_table(
    nodes: Dict[str, List[Dict[str, Any]]],
    reasoning_links: Sequence[Dict[str, Any]],
    translation_links: Sequence[Dict[str, Any]],
    deltas: Sequence[Dict[str, Any]],
) -> str:
    counts = {
        "Questions": len(nodes.get("Question", [])),
        "Claims": len(nodes.get("Claim", [])),
        "Evidence": len(nodes.get("Evidence", [])),
        "Warrants": len(nodes.get("Warrant", [])),
        "Limitations": len(nodes.get("Limitation", [])),
        "Reasoning links": len(reasoning_links),
        "Translation links": len(translation_links),
        "Accepted deltas": len([delta for delta in deltas if delta["lifecycle_status"] == "accepted"]),
        "Open deltas": len([delta for delta in deltas if delta["lifecycle_status"] in OPEN_DELTA_LIFECYCLES]),
    }
    lines = ["| Item | Count |", "| --- | --- |"]
    for key, value in counts.items():
        lines.append(f"| {key} | {value} |")
    return "\n".join(lines)


def render_nodes_section(title: str, rows: Sequence[Dict[str, Any]], headers: Sequence[str], row_fn) -> str:
    lines = [f"## {title}", "", "| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(markdown_cell(value) for value in row_fn(row)) + " |")
    return "\n".join(lines)


def standard_node_row(row: Dict[str, Any]) -> List[str]:
    return [row["local_id"], row["text"], row["status"], row["confidence"], row["human_review"]]


def evidence_row(row: Dict[str, Any]) -> List[str]:
    return [row["local_id"], row["text"], row["metadata"].get("evidence_kind") or "", row["confidence"], ", ".join(row["source_refs"])]


def warrant_row(row: Dict[str, Any]) -> List[str]:
    return [row["local_id"], row["text"], row["metadata"].get("basis") or "", row["confidence"], ", ".join(row["source_refs"])]


def limitation_row(row: Dict[str, Any]) -> List[str]:
    return [row["local_id"], row["text"], row["metadata"].get("severity") or "", row["confidence"], ", ".join(row["source_refs"])]


def render_reasoning_links(rows: Sequence[Dict[str, Any]]) -> str:
    lines = [
        "## Reasoning Links",
        "",
        "| ID | Premises | Relation | Target | Warrants | Limitations | Confidence | Human review |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        values = [
            row["local_id"],
            ", ".join(row["from_nodes"]),
            row["relation"],
            ", ".join(row["to_nodes"]),
            ", ".join(row["warrant_nodes"]),
            ", ".join(row["limitation_nodes"]),
            row["confidence"],
            row["human_review"],
        ]
        lines.append("| " + " | ".join(markdown_cell(value) for value in values) + " |")
    return "\n".join(lines)


def render_translation_links(rows: Sequence[Dict[str, Any]]) -> str:
    lines = [
        "## Translation Links",
        "",
        "| ID | Source input | Relation | Project target | Project warrants | Project limitations | Confidence |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        values = [
            row["local_id"],
            row["source_input"] or ", ".join(row["from_nodes"]),
            row["relation"],
            ", ".join(row["to_nodes"]),
            ", ".join(row["project_warrant_nodes"]),
            ", ".join(row["project_limitation_nodes"]),
            row["confidence"],
        ]
        lines.append("| " + " | ".join(markdown_cell(value) for value in values) + " |")
    return "\n".join(lines)


def render_delta_history(rows: Sequence[Dict[str, Any]]) -> str:
    lines = [
        "## Delta History",
        "",
        "| ID | Summary | Lifecycle | Human review | Evolution | Operation | Affected | Source dossier |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        values = [
            row["local_id"],
            row["summary"],
            row["lifecycle_status"],
            row["human_review"],
            row["evolution_type"],
            ", ".join(row["operation"]),
            ", ".join(row["affected"]),
            row["source_dossier"],
        ]
        lines.append("| " + " | ".join(markdown_cell(value) for value in values) + " |")
    return "\n".join(lines)


def render_open_audit_questions(
    nodes: Dict[str, List[Dict[str, Any]]],
    reasoning_links: Sequence[Dict[str, Any]],
    deltas: Sequence[Dict[str, Any]],
) -> str:
    questions: List[str] = []
    for claim in nodes.get("Claim", []):
        if claim["confidence"] in {"low", "unknown"}:
            questions.append(f"- Review `{claim['local_id']}` because confidence is `{claim['confidence']}`.")
    for link in reasoning_links:
        if link["relation"] == "supports" and not link["warrant_nodes"]:
            questions.append(f"- Add or justify missing warrant for support link `{link['local_id']}`.")
        if link["relation"] == "supports" and not link["limitation_nodes"]:
            questions.append(f"- Add or justify missing limitations for support link `{link['local_id']}`.")
    for delta in deltas:
        if delta["lifecycle_status"] in OPEN_DELTA_LIFECYCLES:
            questions.append(f"- Resolve open delta `{delta['local_id']}`: {delta['summary']}")
    if not questions:
        questions.append("- No generated audit questions.")
    return "## Open Audit Questions\n\n" + "\n".join(questions)


def write_project_graph_report(root: Path, project_id: str, output: Optional[Path] = None, db_path: Optional[Path] = None) -> Path:
    root = root.resolve()
    target = (output or default_output_path(root, project_id)).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(build_project_graph_report(root, project_id, db_path=db_path), encoding="utf-8")
    return target


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Build generated project-understanding graph markdown report from graph.db.")
    parser.add_argument("--repo", default=".", help="Workspace root.")
    parser.add_argument("--project", required=True, help="Project id.")
    parser.add_argument("--db", default="wiki/graphs/graph.db", help="SQLite graph DB path relative to workspace root.")
    parser.add_argument("--output", help="Output markdown path. Defaults to wiki/projects/<Project>/project-understanding-graph.md.")
    args = parser.parse_args(argv)

    root = Path(args.repo).resolve()
    db_path = Path(args.db) if Path(args.db).is_absolute() else root / args.db
    output = None if not args.output else (Path(args.output) if Path(args.output).is_absolute() else root / args.output)
    target = write_project_graph_report(root, args.project, output=output, db_path=db_path)
    print(f"Wrote {relpath(target, root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
