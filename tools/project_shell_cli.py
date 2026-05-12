#!/usr/bin/env python3
"""Create early Research Pilot project shells without graph truth."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

THIS_DIR = Path(__file__).resolve().parent
ROOT_DIR = THIS_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from tools.research_browser_server import valid_project_id


VALID_MATURITY_STAGES = {
    "project_shell",
    "baseline_collection",
    "question_forming",
    "graph_started",
    "active_research",
    "archived",
}


def resolve_repo(value: str) -> Path:
    return Path(value).expanduser().resolve()


def yaml_string(value: str) -> str:
    return json.dumps(str(value), ensure_ascii=False)


def markdown_list(values: Iterable[str], empty_text: str = "_None yet._") -> str:
    items = [str(value).strip() for value in values if str(value).strip()]
    if not items:
        return f"{empty_text}\n"
    return "".join(f"- {item}\n" for item in items)


def build_overview(
    *,
    project_id: str,
    display_title: str,
    target_venue: str,
    maturity_stage: str,
    research_direction: str,
    baseline_anchors: Sequence[str],
    seed_questions: Sequence[str],
) -> str:
    return f"""---
project_id: {yaml_string(project_id)}
display_title: {yaml_string(display_title)}
target_venue: {yaml_string(target_venue)}
maturity_stage: {maturity_stage}
human_review: pending
---

# {display_title}

## Research Direction

{research_direction or "_Not specified yet._"}

## Baseline Anchors

{markdown_list(baseline_anchors)}
## Seed Questions

{markdown_list(seed_questions)}
## Graph Truth

Project shell only. No graph events created.
"""


def build_query_pack(
    *,
    project_id: str,
    display_title: str,
    target_venue: str,
    research_direction: str,
    baseline_anchors: Sequence[str],
    seed_questions: Sequence[str],
    search_questions: Sequence[str],
) -> str:
    return f"""---
project_id: {yaml_string(project_id)}
display_title: {yaml_string(display_title)}
target_venue: {yaml_string(target_venue)}
human_review: pending
---

# Project Query Pack

## Direction

{research_direction or "_Not specified yet._"}

## Baseline Anchors

{markdown_list(baseline_anchors)}
## Seed Questions

{markdown_list(seed_questions)}
## Search Questions

{markdown_list(search_questions)}
"""


def build_decisions(project_id: str, display_title: str) -> str:
    return f"""---
project_id: {yaml_string(project_id)}
display_title: {yaml_string(display_title)}
human_review: pending
---

# Decisions

_No decisions recorded yet._
"""


def create_project_shell(
    root: Path,
    project_id: str,
    display_title: str,
    target_venue: str,
    maturity_stage: str,
    research_direction: str,
    baseline_anchors: Sequence[str],
    seed_questions: Sequence[str],
    search_questions: Sequence[str],
    overwrite: bool,
) -> Dict[str, Any]:
    if not valid_project_id(project_id):
        raise ValueError(f"invalid project id: {project_id}")
    if maturity_stage not in VALID_MATURITY_STAGES:
        raise ValueError(f"invalid maturity stage: {maturity_stage}")

    workspace_root = Path(root).expanduser().resolve()
    project_dir = workspace_root / "wiki" / "projects" / project_id
    overview = project_dir / "overview.md"
    query_pack = project_dir / "project-query-pack.md"
    decisions = project_dir / "decisions.md"
    papers_gitkeep = project_dir / "papers" / ".gitkeep"
    experiment_gitkeep = project_dir / "experiment-proposals" / ".gitkeep"

    if overview.exists() and not overwrite:
        return {
            "created": False,
            "project_id": project_id,
            "project_dir": str(project_dir),
            "overview": str(overview),
            "graph_events_created": False,
            "writes": [],
        }

    project_dir.mkdir(parents=True, exist_ok=True)
    papers_gitkeep.parent.mkdir(parents=True, exist_ok=True)
    experiment_gitkeep.parent.mkdir(parents=True, exist_ok=True)

    writes: List[str] = []
    files = {
        overview: build_overview(
            project_id=project_id,
            display_title=display_title,
            target_venue=target_venue,
            maturity_stage=maturity_stage,
            research_direction=research_direction,
            baseline_anchors=baseline_anchors,
            seed_questions=seed_questions,
        ),
        query_pack: build_query_pack(
            project_id=project_id,
            display_title=display_title,
            target_venue=target_venue,
            research_direction=research_direction,
            baseline_anchors=baseline_anchors,
            seed_questions=seed_questions,
            search_questions=search_questions,
        ),
        decisions: build_decisions(project_id, display_title),
    }
    for path, content in files.items():
        if overwrite or not path.exists():
            path.write_text(content, encoding="utf-8")
            writes.append(str(path))

    for path in (papers_gitkeep, experiment_gitkeep):
        if overwrite or not path.exists():
            path.write_text("", encoding="utf-8")
            writes.append(str(path))

    return {
        "created": True,
        "project_id": project_id,
        "project_dir": str(project_dir),
        "overview": str(overview),
        "query_pack": str(query_pack),
        "decisions": str(decisions),
        "graph_events_created": False,
        "writes": writes,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create a Research Pilot project shell without graph truth.")
    parser.add_argument("--repo", default=".", help="Research Pilot workspace path.")
    parser.add_argument("--project", required=True, help="Project id.")
    parser.add_argument("--title", required=True, help="Project display title.")
    parser.add_argument("--target-venue", default="", help="Target venue or deadline frame.")
    parser.add_argument("--maturity-stage", default="project_shell", choices=sorted(VALID_MATURITY_STAGES))
    parser.add_argument("--direction", default="", help="One-sentence research direction.")
    parser.add_argument("--baseline-anchor", action="append", default=[], help="Baseline anchor. Repeatable.")
    parser.add_argument("--seed-question", action="append", default=[], help="Seed question. Repeatable.")
    parser.add_argument("--search-question", action="append", default=[], help="Search question. Repeatable.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing shell files.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    return parser


def print_result(result: Dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        result = create_project_shell(
            resolve_repo(args.repo),
            project_id=args.project,
            display_title=args.title,
            target_venue=args.target_venue,
            maturity_stage=args.maturity_stage,
            research_direction=args.direction,
            baseline_anchors=args.baseline_anchor,
            seed_questions=args.seed_question,
            search_questions=args.search_question,
            overwrite=args.overwrite,
        )
    except ValueError as exc:
        print_result({"created": False, "valid": False, "error": str(exc)}, bool(args.json))
        return 2
    print_result(result, bool(args.json))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
