#!/usr/bin/env python3
"""Single user-facing command for project-gap paper discovery."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

THIS_DIR = Path(__file__).resolve().parent
ROOT_DIR = THIS_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from tools.gap_search_cli import (
    build_discovery_handoff,
    build_search_contract,
    save_discovery_handoff_artifact,
    search_from_contract,
)


def resolve_repo(value: str) -> Path:
    return Path(value).resolve()


def compact_record(record: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "title": record.get("title", ""),
        "year": record.get("year", ""),
        "venue": record.get("venue", ""),
        "url": record.get("url", ""),
        "source": record.get("source", ""),
        "project_fit": record.get("project_fit", ""),
        "fit_score": record.get("fit_score", 0),
        "recommendation": record.get("recommendation", ""),
        "triage_status": record.get("triage_status", ""),
        "why_deep_read": record.get("why_deep_read", ""),
        "why_not_deep_read": record.get("why_not_deep_read", ""),
        "risk": record.get("risk", ""),
        "matched_terms": record.get("suggested_topics", []),
    }


def compact_noise(lead: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "title": lead.get("title", ""),
        "url": lead.get("url", ""),
        "source": lead.get("source", ""),
        "fit_score": lead.get("fit_score", 0),
        "reject_reason": lead.get("reject_reason", ""),
        "matched_terms": lead.get("matched_terms", []),
    }


def surface_discovery_result(handoff: Dict[str, Any], *, include_internal: bool = False) -> Dict[str, Any]:
    if not handoff.get("valid"):
        return handoff
    contract = handoff.get("search_contract") or {}
    gap = contract.get("source_gap") or {}
    target = gap.get("target") or {}
    records = list(handoff.get("candidate_records") or [])
    recommended = [compact_record(record) for record in records if record.get("recommendation") == "deep-read"]
    keep = [compact_record(record) for record in records if record.get("recommendation") == "keep-candidate"]
    later = [compact_record(record) for record in records if record.get("recommendation") == "later"]
    rejected = [compact_noise(lead) for lead in handoff.get("discarded_leads", [])]
    result: Dict[str, Any] = {
        "valid": True,
        "project": handoff.get("project", ""),
        "gap": {
            "target_id": target.get("id", ""),
            "target_kind": target.get("kind", ""),
            "text": target.get("text", ""),
            "gap_type": gap.get("gap_type", ""),
            "evidence_need": gap.get("evidence_need", ""),
        },
        "counts": {
            "recommended_for_deep_read": len(recommended),
            "keep_candidate": len(keep),
            "later": len(later),
            "rejected_or_noise": len(rejected),
        },
        "recommended_for_deep_read": recommended,
        "keep_candidate": keep,
        "later": later,
        "rejected_or_noise": rejected,
        "human_next": "Human should choose one recommended paper for deep-read, ask for more search, or stop.",
        "effects": handoff.get("effects", {"writes": [], "zotero_writes": [], "graph_events": []}),
    }
    if include_internal:
        result["internal"] = {
            "search_contract": contract,
            "candidate_records": records,
            "discarded_leads": handoff.get("discarded_leads", []),
        }
    return result


def run_gap_discovery(
    root: Path,
    project: str,
    gap_target: str,
    *,
    gap_type: str = "",
    source: str = "all",
    max_results: int = 5,
    include_noise: bool = False,
    include_internal: bool = False,
    save_artifact: bool = False,
) -> Dict[str, Any]:
    contract = build_search_contract(root, project, gap_target, gap_type=gap_type, target_count=max_results)
    search_result = search_from_contract(contract, source=source, max_results=max_results, include_noise=include_noise, root=root)
    handoff = build_discovery_handoff(search_result)
    if handoff.get("valid") and save_artifact:
        artifact_path = save_discovery_handoff_artifact(root, project, handoff)
        handoff.setdefault("effects", {}).setdefault("writes", []).append(artifact_path)
    return surface_discovery_result(handoff, include_internal=include_internal)


def print_result(result: Dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))


def command_run(args: argparse.Namespace) -> Tuple[int, Dict[str, Any]]:
    result = run_gap_discovery(
        resolve_repo(args.repo),
        args.project,
        args.gap,
        gap_type=args.gap_type,
        source=args.source,
        max_results=args.max_results,
        include_noise=args.include_noise,
        include_internal=args.include_internal,
        save_artifact=args.save_artifact,
    )
    return (0 if result.get("valid") else 1), result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run project-gap discovery as one user-facing command.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser("run", help="Find candidate papers for one project graph gap.")
    run.add_argument("--repo", default=".")
    run.add_argument("--project", required=True)
    run.add_argument("--gap", required=True, help="Gap target local id, e.g. Q7 or C2.")
    run.add_argument("--gap-type", default="")
    run.add_argument("--source", choices=["arxiv", "openreview", "memory", "all", "none"], default="all")
    run.add_argument("--max-results", type=int, default=5)
    run.add_argument("--include-noise", action="store_true")
    run.add_argument("--include-internal", action="store_true")
    run.add_argument("--save-artifact", action="store_true")
    run.add_argument("--json", action="store_true")
    return parser


def dispatch(args: argparse.Namespace) -> Tuple[int, Dict[str, Any]]:
    if args.command == "run":
        return command_run(args)
    return 2, {"valid": False, "error": f"unsupported command: {args.command}"}


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    code, result = dispatch(args)
    print_result(result, bool(getattr(args, "json", False)))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
