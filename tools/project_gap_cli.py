#!/usr/bin/env python3
"""Read-only Project Understanding Graph gap detector."""

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

from tools.graph_store import graph_id_for_project, relpath


SUPPORT_RELATIONS = {"supports", "answers", "strengthens"}
QUESTION_ANSWER_RELATIONS = {"answers"}
WARRANT_REQUIRED_RELATIONS = {"supports", "challenges", "answers"}
INACTIVE_LIFECYCLES = {"retired", "superseded", "merged"}
SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def resolve_repo(value: str) -> Path:
    return Path(value).resolve()


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


def local_id(value: str) -> str:
    return str(value or "").rsplit(":", 1)[-1]


def positioned_values(conn: sqlite3.Connection, table: str, owner_column: str, owner_id: str, value_column: str) -> List[str]:
    rows = conn.execute(
        f"select {value_column} from {table} where {owner_column} = ? order by position",
        (owner_id,),
    ).fetchall()
    return [str(row[0]) for row in rows]


def node_sources(conn: sqlite3.Connection, node_id: str) -> List[str]:
    return positioned_values(conn, "node_sources", "node_id", node_id, "source_ref")


def link_node_values(conn: sqlite3.Connection, table: str, link_id: str) -> List[str]:
    return positioned_values(conn, table, "link_id", link_id, "node_id")


def active_node(row: sqlite3.Row) -> bool:
    lifecycle = str(row["lifecycle_status"] or "").lower()
    status = str(row["status"] or "").lower()
    return lifecycle not in INACTIVE_LIFECYCLES and status not in {"archived", "rejected", "retired"}


def load_graph(conn: sqlite3.Connection, project_id: str) -> Dict[str, Any]:
    graph_id = graph_id_for_project(project_id)
    nodes = {
        row["node_id"]: row
        for row in conn.execute("select * from nodes where graph_id = ?", (graph_id,)).fetchall()
        if active_node(row)
    }
    links: Dict[str, Dict[str, Any]] = {}
    for row in conn.execute("select * from links where graph_id = ?", (graph_id,)).fetchall():
        link_id = row["link_id"]
        payload = parse_json(row["payload_json"], {})
        links[link_id] = {
            "row": row,
            "payload": payload,
            "from_nodes": link_node_values(conn, "link_from_nodes", link_id),
            "to_nodes": link_node_values(conn, "link_to_nodes", link_id),
            "warrant_nodes": link_node_values(conn, "link_warrants", link_id) + link_node_values(conn, "link_project_warrants", link_id),
            "limitation_nodes": link_node_values(conn, "link_limitations", link_id) + link_node_values(conn, "link_project_limitations", link_id),
            "source_refs": positioned_values(conn, "link_sources", "link_id", link_id, "source_ref"),
        }
    incoming: Dict[str, List[Dict[str, Any]]] = {node_id: [] for node_id in nodes}
    translation_touch: set[str] = set()
    for link in links.values():
        row = link["row"]
        if row["link_type"] == "TranslationLink":
            translation_touch.update(link["from_nodes"])
            translation_touch.update(link["to_nodes"])
            translation_touch.update(link["warrant_nodes"])
            translation_touch.update(link["limitation_nodes"])
        for target in link["to_nodes"]:
            incoming.setdefault(target, []).append(link)
    return {"graph_id": graph_id, "nodes": nodes, "links": links, "incoming": incoming, "translation_touch": translation_touch}


def target(node_or_link: sqlite3.Row, kind: str) -> Dict[str, str]:
    if kind == "link":
        return {"id": local_id(node_or_link["link_id"]), "kind": node_or_link["link_type"], "text": node_or_link["relation"]}
    return {"id": local_id(node_or_link["node_id"]), "kind": node_or_link["node_type"], "text": node_or_link["text"]}


def gap(
    *,
    gap_type: str,
    severity: str,
    target_record: Dict[str, str],
    why: str,
    evidence_need: str,
    current_support: Optional[Sequence[str]] = None,
    blocking_limitations: Optional[Sequence[str]] = None,
    suggested_action: str = "",
) -> Dict[str, Any]:
    return {
        "gap_type": gap_type,
        "severity": severity,
        "target": target_record,
        "why": why,
        "evidence_need": evidence_need,
        "current_support": list(current_support or []),
        "blocking_limitations": list(blocking_limitations or []),
        "suggested_action": suggested_action,
    }


def support_links_for_node(graph: Dict[str, Any], node_id: str) -> List[Dict[str, Any]]:
    return [link for link in graph["incoming"].get(node_id, []) if str(link["row"]["relation"]) in SUPPORT_RELATIONS]


def answer_links_for_question(graph: Dict[str, Any], node_id: str) -> List[Dict[str, Any]]:
    return [link for link in graph["incoming"].get(node_id, []) if str(link["row"]["relation"]) in QUESTION_ANSWER_RELATIONS]


def relation_requires_warrant(link: Dict[str, Any]) -> bool:
    relation = str(link["row"]["relation"] or "")
    payload = link["payload"]
    return relation in WARRANT_REQUIRED_RELATIONS and not link["warrant_nodes"] and not payload.get("inline_warrant")


def paper_source_refs(source_refs: Sequence[str]) -> List[str]:
    result: List[str] = []
    for source_ref in source_refs:
        value = str(source_ref or "")
        if "wiki/projects/" in value and "/papers/" in value:
            result.append(value)
        elif value.startswith("zotero:item:") or value.startswith("paper:"):
            result.append(value)
    return result


def detect_gaps(root: Path, project_id: str, limit: int = 0) -> Dict[str, Any]:
    conn = connect(root)
    try:
        graph_row = conn.execute("select graph_id from graphs where graph_id = ?", (graph_id_for_project(project_id),)).fetchone()
        if not graph_row:
            return {"valid": False, "project": project_id, "error": f"project graph not found: {graph_id_for_project(project_id)}"}
        graph = load_graph(conn, project_id)
        gaps: List[Dict[str, Any]] = []
        for node_id, node in graph["nodes"].items():
            node_type = str(node["node_type"] or "")
            if node_type == "Claim":
                support_links = support_links_for_node(graph, node_id)
                if not support_links:
                    gaps.append(
                        gap(
                            gap_type="unsupported_claim",
                            severity="high",
                            target_record=target(node, "node"),
                            why="Active claim has no incoming support link.",
                            evidence_need="Find or produce evidence plus warrant that directly supports this claim, or demote/refine the claim.",
                            suggested_action="Create an evidence need or revise the claim through D*.",
                        )
                    )
                else:
                    limitation_ids = sorted({local_id(item) for link in support_links for item in link["limitation_nodes"]})
                    if limitation_ids:
                        gaps.append(
                            gap(
                                gap_type="overbounded_claim",
                                severity="medium",
                                target_record=target(node, "node"),
                                why="Claim has support, but its support links carry explicit limitations.",
                                evidence_need="Find evidence that directly addresses the listed limitations, or narrow the claim scope.",
                                current_support=[local_id(link["row"]["link_id"]) for link in support_links],
                                blocking_limitations=limitation_ids,
                                suggested_action="Search for limitation-closing evidence or propose claim refinement.",
                            )
                        )
            elif node_type == "Question" and not answer_links_for_question(graph, node_id):
                gaps.append(
                    gap(
                        gap_type="unanswered_question",
                        severity="high",
                        target_record=target(node, "node"),
                        why="Active question has no incoming answer link.",
                        evidence_need="Add claim(s) and reasoning links that answer this question, or decompose it into answerable subquestions.",
                        suggested_action="Run human-discussion delta or evidence search focused on this question.",
                    )
                )
            elif node_type in {"Evidence", "Claim"}:
                sources = paper_source_refs(node_sources(conn, node_id))
                if sources and node_id not in graph["translation_touch"]:
                    gaps.append(
                        gap(
                            gap_type="missing_translation",
                            severity="medium",
                            target_record=target(node, "node"),
                            why="Paper-derived project node is not connected through a TranslationLink.",
                            evidence_need="Add a TranslationLink explaining how the source-side result maps into project understanding, or mark why no translation is needed.",
                            suggested_action="Create TL* or revise provenance.",
                        )
                    )
        for link in graph["links"].values():
            row = link["row"]
            if row["link_type"] == "ReasoningLink" and relation_requires_warrant(link):
                gaps.append(
                    gap(
                        gap_type="weak_warrant",
                        severity="medium",
                        target_record=target(row, "link"),
                        why="Reasoning link uses a warrant-requiring relation but has no warrant node or inline warrant.",
                        evidence_need="Add an explicit warrant explaining why the premise supports/challenges/answers the target.",
                        current_support=[local_id(item) for item in link["from_nodes"]],
                        suggested_action="Add W* and update the reasoning link.",
                    )
                )
        gaps.sort(key=lambda item: (SEVERITY_ORDER.get(item["severity"], 9), item["gap_type"], item["target"]["id"]))
        if limit > 0:
            gaps = gaps[:limit]
        return {"valid": True, "project": project_id, "counts": {"gaps": len(gaps)}, "gaps": gaps}
    finally:
        conn.close()


def print_result(result: Dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return
    if not result.get("valid"):
        print(result.get("error") or "invalid gap report")
        return
    print(f"Project: {result['project']}")
    print(f"Gaps: {result['counts']['gaps']}")
    for item in result["gaps"]:
        target_info = item["target"]
        print(f"- {item['gap_type']} [{item['severity']}] {target_info['id']}: {item['evidence_need']}")


def command_detect(args: argparse.Namespace) -> Tuple[int, Dict[str, Any]]:
    try:
        result = detect_gaps(resolve_repo(args.repo), args.project, limit=args.limit)
    except FileNotFoundError as exc:
        result = {"valid": False, "project": args.project, "error": str(exc)}
    return (0 if result.get("valid") else 1), result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Detect evidence and reasoning gaps in a Project Understanding Graph.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    detect = subparsers.add_parser("detect", help="Generate a read-only gap report.")
    detect.add_argument("--repo", default=".")
    detect.add_argument("--project", required=True)
    detect.add_argument("--limit", type=int, default=0)
    detect.add_argument("--json", action="store_true")
    return parser


def dispatch(args: argparse.Namespace) -> Tuple[int, Dict[str, Any]]:
    if args.command == "detect":
        return command_detect(args)
    return 2, {"valid": False, "error": f"unsupported command: {args.command}"}


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    code, result = dispatch(args)
    print_result(result, bool(getattr(args, "json", False)))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
