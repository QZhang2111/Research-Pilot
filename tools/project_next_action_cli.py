#!/usr/bin/env python3
"""Read-only next-action router for Research Pilot projects."""

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

from tools.graph_query_cli import query_open
from tools.graph_store import graph_id_for_project, relpath
from tools.project_gap_cli import detect_gaps


PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}
MOVE_TYPE_ORDER = {
    "human_gate_review": 0,
    "design_experiment": 2,
    "human_discussion_or_gap_search": 3,
    "find_paper_or_demote_claim": 4,
    "add_warrant_or_test_warrant": 5,
    "add_translation_link": 6,
    "inspect_gap": 9,
}


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


def graph_counts(root: Path, project_id: str) -> Dict[str, Any]:
    graph_id = graph_id_for_project(project_id)
    conn = connect(root)
    try:
        node_rows = conn.execute(
            "select node_type, count(*) as count from nodes where graph_id = ? group by node_type order by node_type",
            (graph_id,),
        ).fetchall()
        link_rows = conn.execute(
            "select link_type, count(*) as count from links where graph_id = ? group by link_type order by link_type",
            (graph_id,),
        ).fetchall()
    finally:
        conn.close()
    return {
        "nodes": {row["node_type"]: row["count"] for row in node_rows},
        "links": {row["link_type"]: row["count"] for row in link_rows},
    }


def target_from_gap(gap: Dict[str, Any]) -> Dict[str, str]:
    target = gap.get("target") or {}
    return {
        "id": str(target.get("id") or ""),
        "kind": str(target.get("kind") or ""),
        "text": str(target.get("text") or ""),
        "gap_type": str(gap.get("gap_type") or ""),
    }


def move(
    *,
    move_id: str,
    move_type: str,
    priority: str,
    target: Dict[str, str],
    why: str,
    suggested_command: str,
    expected_artifact: str,
    human_decision: str,
) -> Dict[str, Any]:
    return {
        "id": move_id,
        "type": move_type,
        "priority": priority,
        "target": target,
        "why": why,
        "suggested_command": suggested_command,
        "expected_artifact": expected_artifact,
        "human_decision": human_decision,
    }


def priority_for_gap(gap: Dict[str, Any]) -> str:
    severity = str(gap.get("severity") or "medium")
    return severity if severity in PRIORITY_ORDER else "medium"


def move_for_gap(project_id: str, gap: Dict[str, Any], move_id: str) -> Dict[str, Any]:
    target = target_from_gap(gap)
    gap_type = str(gap.get("gap_type") or "")
    if gap_type == "overbounded_claim" and target["kind"] == "Claim":
        return move(
            move_id=move_id,
            move_type="design_experiment",
            priority=priority_for_gap(gap),
            target=target,
            why=gap.get("evidence_need") or "Produce project-owned evidence for this bounded claim.",
            suggested_command=f"python3 tools/project_experiment_cli.py suggest --repo <WorkspacePath> --project {project_id} --target {target['id']} --json",
            expected_artifact="experiment_proposal",
            human_decision="Decide whether to design, park, revise, reject, or search papers first.",
        )
    if gap_type == "unsupported_claim":
        return move(
            move_id=move_id,
            move_type="find_paper_or_demote_claim",
            priority=priority_for_gap(gap),
            target=target,
            why=gap.get("evidence_need") or "Claim has no direct support.",
            suggested_command=f"python3 tools/project_gap_cli.py detect --repo <WorkspacePath> --project {project_id} --json",
            expected_artifact="paper-search decision, claim demotion, or D* revision",
            human_decision="Decide whether to search papers, demote the claim, or revise it through D*.",
        )
    if gap_type == "unanswered_question":
        return move(
            move_id=move_id,
            move_type="human_discussion_or_gap_search",
            priority=priority_for_gap(gap),
            target=target,
            why=gap.get("evidence_need") or "Question has no answer link.",
            suggested_command=f"python3 tools/project_gap_cli.py detect --repo <WorkspacePath> --project {project_id} --json",
            expected_artifact="paper-search decision or human-discussion delta",
            human_decision="Decide whether this question needs paper search, human discussion, or decomposition.",
        )
    if gap_type == "weak_warrant":
        return move(
            move_id=move_id,
            move_type="add_warrant_or_test_warrant",
            priority=priority_for_gap(gap),
            target=target,
            why=gap.get("evidence_need") or "Reasoning link lacks explicit warrant.",
            suggested_command=f"python3 tools/graph_query_cli.py link --repo <WorkspacePath> --project {project_id} --id {target['id']} --json",
            expected_artifact="warrant addition, warrant test, or reasoning-link revision",
            human_decision="Decide whether to add W*, test the warrant, or revise the reasoning link.",
        )
    if gap_type == "missing_translation":
        return move(
            move_id=move_id,
            move_type="add_translation_link",
            priority=priority_for_gap(gap),
            target=target,
            why=gap.get("evidence_need") or "Paper-derived node lacks a project translation link.",
            suggested_command=f"python3 tools/graph_query_cli.py node --repo <WorkspacePath> --project {project_id} --id {target['id']} --json",
            expected_artifact="TranslationLink D* proposal",
            human_decision="Decide whether the source-side knowledge should enter project understanding.",
        )
    return move(
        move_id=move_id,
        move_type="inspect_gap",
        priority=priority_for_gap(gap),
        target=target,
        why=gap.get("evidence_need") or gap.get("why") or "Inspect graph gap.",
        suggested_command=f"python3 tools/project_gap_cli.py detect --repo <WorkspacePath> --project {project_id} --json",
        expected_artifact="gap inspection",
        human_decision="Decide next action manually.",
    )


def open_delta_moves(root: Path, project_id: str) -> Tuple[List[str], List[Dict[str, Any]]]:
    result = query_open(root, project_id)
    open_ids = list(result.get("open_deltas") or [])
    moves: List[Dict[str, Any]] = []
    for index, delta in enumerate(result.get("deltas") or [], start=1):
        delta_id = str(delta.get("local_id") or "")
        moves.append(
            move(
                move_id=f"NM{index}",
                move_type="human_gate_review",
                priority="high",
                target={
                    "id": delta_id,
                    "kind": "Delta",
                    "text": str(delta.get("summary") or ""),
                    "gap_type": "open_delta",
                },
                why="Open D* exists; human gate should be resolved before adding more graph changes.",
                suggested_command=f"python3 tools/graph_query_cli.py open --repo <WorkspacePath> --project {project_id} --json",
                expected_artifact="accept/reject/park/revise decision",
                human_decision="Review D* and choose accept, reject, park, or revise.",
            )
        )
    return open_ids, moves


def count_move_types(moves: Sequence[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for item in moves:
        move_type = str(item.get("type") or "")
        counts[move_type] = counts.get(move_type, 0) + 1
    return counts


def project_readout(project_id: str, project_state: Dict[str, Any], moves: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    counts = count_move_types(moves)
    open_count = len(project_state.get("open_deltas") or [])
    if open_count:
        main_blocker = "Human gate has open D* deltas that should be reviewed before more graph changes."
        strategy = "Resolve human_gate_review first, then rerun next-action routing."
    elif counts.get("design_experiment"):
        main_blocker = "Project has bounded claims that need project-owned evidence."
        strategy = "Use experiment proposal workflow on the highest-priority bounded claim."
    elif counts.get("human_discussion_or_gap_search"):
        main_blocker = "Project has unanswered questions that need discussion, decomposition, or paper search."
        strategy = "Choose one question and route it to human discussion or gap-driven search."
    elif counts.get("find_paper_or_demote_claim"):
        main_blocker = "Project has unsupported claims that need evidence or demotion."
        strategy = "Search for support or demote/refine unsupported claims through D*."
    else:
        main_blocker = "No dominant blocker detected by structural graph checks."
        strategy = "Inspect top gaps manually."
    top_types = ", ".join(f"{name}:{count}" for name, count in sorted(counts.items()))
    next_actions = [
        {
            "type": item["type"],
            "target": item["target"]["id"],
            "why": item["why"],
            "suggested_command": item["suggested_command"],
        }
        for item in list(moves)[:3]
    ]
    if moves:
        first = moves[0]
        state = f"{project_id} has {project_state.get('top_gap_count', 0)} graph gaps; top move is {first['type']} on {first['target']['id']}."
    else:
        state = f"{project_id} has no recommended moves from the current structural checks."
    return {
        "one_sentence_state": state,
        "main_blocker": main_blocker,
        "recommended_strategy": strategy,
        "why_this_order": f"Order prioritizes open human gates, direct evidence needs, then search/cleanup. Move mix: {top_types}.",
        "next_3_actions": next_actions,
    }


def suggest_next_actions(root: Path, project_id: str, limit: int = 8) -> Dict[str, Any]:
    gap_result = detect_gaps(root, project_id)
    if not gap_result.get("valid"):
        return gap_result
    open_ids, moves = open_delta_moves(root, project_id)
    gaps = gap_result.get("gaps") or []
    next_index = len(moves) + 1
    for gap in gaps:
        moves.append(move_for_gap(project_id, gap, f"NM{next_index}"))
        next_index += 1
    moves.sort(key=lambda item: (PRIORITY_ORDER.get(item["priority"], 9), MOVE_TYPE_ORDER.get(item["type"], 9), item["id"]))
    moves = moves[:limit]
    state = {
        "open_deltas": open_ids,
        "graph_counts": graph_counts(root, project_id),
        "top_gap_count": len(gaps),
    }
    return {
        "valid": True,
        "project": project_id,
        "project_state": state,
        "project_readout": project_readout(project_id, state, moves),
        "top_gaps": gaps[:limit],
        "recommended_next_moves": moves,
        "human_choices": [item["type"] for item in moves],
        "stop_rule": "No mutation performed. This router only suggests the next workflow.",
        "effects": {"writes": [], "graph_events": [], "zotero_writes": [], "experiment_runs": []},
    }


def print_result(result: Dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))


def command_suggest(args: argparse.Namespace) -> Tuple[int, Dict[str, Any]]:
    try:
        result = suggest_next_actions(resolve_repo(args.repo), args.project, limit=args.limit)
    except FileNotFoundError as exc:
        result = {"valid": False, "project": args.project, "error": str(exc)}
    return (0 if result.get("valid") else 1), result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Suggest next agent workflow action for a Project Understanding Graph.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    suggest = subparsers.add_parser("suggest", help="Suggest next project workflow actions.")
    suggest.add_argument("--repo", default=".")
    suggest.add_argument("--project", required=True)
    suggest.add_argument("--limit", type=int, default=8)
    suggest.add_argument("--json", action="store_true")
    return parser


def dispatch(args: argparse.Namespace) -> Tuple[int, Dict[str, Any]]:
    if args.command == "suggest":
        return command_suggest(args)
    return 2, {"valid": False, "error": f"unsupported command: {args.command}"}


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    code, result = dispatch(args)
    print_result(result, bool(getattr(args, "json", False)))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
