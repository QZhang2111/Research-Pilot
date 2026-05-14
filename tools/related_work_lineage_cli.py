#!/usr/bin/env python3
"""Create and validate paper-only related work lineage artifacts."""

from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional


VALID_REVIEW_STATUSES = {"candidate", "approved", "rejected"}
VALID_RELATIONS = {
    "branches-from",
    "extends-method",
    "adapts-to-domain",
    "influences",
    "competes-with",
    "unifies",
    "contrasts-with",
}
SCHEMA_VERSION = "related-work-lineage-v1"
SOURCE_BOUNDARY = "related_work_lineage_only_not_graph_truth"


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug[:96] or "lineage-map"


def relpath(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path)


def artifact_paths(root: Path, project: str, round_id: str) -> Dict[str, Path]:
    base = root / "wiki" / "projects" / project / "literature-rounds" / round_id
    return {
        "dir": base,
        "json": base / "related-work-lineage.json",
        "markdown": base / "related-work-lineage.md",
    }


def empty_payload(
    project: str,
    round_id: str,
    title: str,
    user_direction: str,
    baseline_papers: List[str],
) -> Dict[str, Any]:
    today = date.today().isoformat()
    return {
        "schema_version": SCHEMA_VERSION,
        "project": project,
        "round": round_id,
        "title": title,
        "status": "candidate",
        "source_boundary": SOURCE_BOUNDARY,
        "max_papers": 20,
        "created": today,
        "updated": today,
        "route_narrowing": {
            "input_mode": "baseline_papers" if baseline_papers else "coarse_direction",
            "user_direction": user_direction,
            "selected_anchor_papers": baseline_papers,
            "candidate_routes": [],
        },
        "routes": [],
        "papers": [],
        "explicit_edges": [],
        "positioning_note": "",
    }


def require_string(item: Dict[str, Any], key: str, label: str, errors: List[str]) -> str:
    value = str(item.get(key) or "").strip()
    if not value:
        errors.append(f"{label}.{key} is required")
    return value


def validate_lineage_map(payload: Dict[str, Any]) -> Dict[str, Any]:
    errors: List[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    if payload.get("source_boundary") != SOURCE_BOUNDARY:
        errors.append(f"source_boundary must be {SOURCE_BOUNDARY}")
    require_string(payload, "project", "root", errors)
    require_string(payload, "round", "root", errors)
    require_string(payload, "title", "root", errors)

    routes = payload.get("routes")
    papers = payload.get("papers")
    edges = payload.get("explicit_edges")
    if not isinstance(routes, list):
        errors.append("routes must be a list")
        routes = []
    if not isinstance(papers, list):
        errors.append("papers must be a list")
        papers = []
    if not isinstance(edges, list):
        errors.append("explicit_edges must be a list")
        edges = []
    if len(papers) > 20:
        errors.append("paper count must be <= 20")

    route_ids = set()
    for index, route in enumerate(routes):
        if not isinstance(route, dict):
            errors.append(f"routes[{index}] must be an object")
            continue
        route_id = require_string(route, "id", f"routes[{index}]", errors)
        if route_id in route_ids:
            errors.append(f"routes[{index}].id duplicate: {route_id}")
        route_ids.add(route_id)
        require_string(route, "label", f"routes[{index}]", errors)
        status = str(route.get("review_status") or "candidate")
        if status not in VALID_REVIEW_STATUSES:
            errors.append(f"routes[{index}].review_status invalid: {status}")

    paper_ids = set()
    for index, paper in enumerate(papers):
        if not isinstance(paper, dict):
            errors.append(f"papers[{index}] must be an object")
            continue
        paper_id = require_string(paper, "id", f"papers[{index}]", errors)
        if paper_id in paper_ids:
            errors.append(f"papers[{index}].id duplicate: {paper_id}")
        paper_ids.add(paper_id)
        if paper.get("kind") != "paper":
            errors.append(f"papers[{index}].kind must be paper")
        require_string(paper, "title", f"papers[{index}]", errors)
        require_string(paper, "source_url", f"papers[{index}]", errors)
        require_string(paper, "source_evidence", f"papers[{index}]", errors)
        route = str(paper.get("route") or "").strip()
        if route not in route_ids:
            errors.append(f"papers[{index}].route unknown route: {route}")
        status = str(paper.get("review_status") or "candidate")
        if status not in VALID_REVIEW_STATUSES:
            errors.append(f"papers[{index}].review_status invalid: {status}")

    for index, edge in enumerate(edges):
        if not isinstance(edge, dict):
            errors.append(f"explicit_edges[{index}] must be an object")
            continue
        source = require_string(edge, "source", f"explicit_edges[{index}]", errors)
        target = require_string(edge, "target", f"explicit_edges[{index}]", errors)
        if source and source not in paper_ids:
            errors.append(f"explicit_edges[{index}].source unknown paper: {source}")
        if target and target not in paper_ids:
            errors.append(f"explicit_edges[{index}].target unknown paper: {target}")
        relation = str(edge.get("relation") or "").strip()
        if relation not in VALID_RELATIONS:
            errors.append(f"explicit_edges[{index}].relation invalid: {relation}")
        require_string(edge, "rationale", f"explicit_edges[{index}]", errors)
        require_string(edge, "confidence", f"explicit_edges[{index}]", errors)
        require_string(edge, "source_evidence", f"explicit_edges[{index}]", errors)
        status = str(edge.get("review_status") or "candidate")
        if status not in VALID_REVIEW_STATUSES:
            errors.append(f"explicit_edges[{index}].review_status invalid: {status}")

    return {
        "valid": not errors,
        "errors": errors,
        "paper_count": len(papers),
        "route_count": len(routes),
        "edge_count": len(edges),
    }


def render_markdown_summary(payload: Dict[str, Any]) -> str:
    lines = [
        "---",
        f"title: \"{payload.get('title', 'Related Work Lineage')}\"",
        "type: related-work-lineage",
        f"project: {payload.get('project', '')}",
        f"round: {payload.get('round', '')}",
        f"status: {payload.get('status', 'candidate')}",
        "human_review: pending",
        "---",
        "",
        f"# {payload.get('title', 'Related Work Lineage')}",
        "",
        "## Boundary",
        "",
        "This related-work lineage artifact is not Project Understanding Graph truth and does not create D* events.",
        "",
        "## Positioning Note",
        "",
        str(payload.get("positioning_note") or "No positioning note yet."),
        "",
        "## Technical Routes",
        "",
    ]
    papers_by_route: Dict[str, List[Dict[str, Any]]] = {}
    for paper in payload.get("papers", []):
        papers_by_route.setdefault(str(paper.get("route") or ""), []).append(paper)
    for route in payload.get("routes", []):
        route_id = str(route.get("id") or "")
        lines.extend(
            [
                f"### {route.get('label', route_id)}",
                "",
                str(route.get("description") or "No route description yet."),
                "",
            ]
        )
        route_papers = sorted(
            papers_by_route.get(route_id, []),
            key=lambda item: (
                str(item.get("year") or ""),
                str(item.get("month") or ""),
                str(item.get("title") or ""),
            ),
        )
        for paper in route_papers:
            roles = ", ".join(str(role) for role in paper.get("roles", []) if role)
            lines.append(
                f"- {paper.get('year', '')}.{paper.get('month', '')} "
                f"**{paper.get('title', '')}** [{roles}] - {paper.get('summary', '')}"
            )
        lines.append("")
    lines.extend(["## Explicit Lineage Edges", ""])
    for edge in payload.get("explicit_edges", []):
        lines.append(
            f"- `{edge.get('source')}` {edge.get('relation')} "
            f"`{edge.get('target')}`: {edge.get('rationale')}"
        )
    if not payload.get("explicit_edges"):
        lines.append("- None.")
    lines.append("")
    return "\n".join(lines)


def create_template(
    root: Path,
    project: str,
    round_id: str,
    title: str,
    user_direction: str,
    baseline_papers: List[str],
    overwrite: bool,
) -> Dict[str, Any]:
    paths = artifact_paths(root, project, round_id)
    if paths["json"].exists() and not overwrite:
        return {
            "created": False,
            "error": "lineage artifact already exists",
            "json_path": str(paths["json"]),
        }
    paths["dir"].mkdir(parents=True, exist_ok=True)
    payload = empty_payload(project, round_id, title, user_direction, baseline_papers)
    paths["json"].write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    paths["markdown"].write_text(render_markdown_summary(payload), encoding="utf-8")
    return {
        "created": True,
        "json_path": str(paths["json"]),
        "markdown_path": str(paths["markdown"]),
    }


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Create and validate related work lineage artifacts."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create")
    create.add_argument("--repo", default=".")
    create.add_argument("--project", required=True)
    create.add_argument("--round", required=True)
    create.add_argument("--title", required=True)
    create.add_argument("--direction", default="")
    create.add_argument("--baseline-paper", action="append", default=[])
    create.add_argument("--overwrite", action="store_true")
    create.add_argument("--json", action="store_true")

    validate = subparsers.add_parser("validate")
    validate.add_argument("--path", required=True)
    validate.add_argument("--json", action="store_true")

    render = subparsers.add_parser("render-summary")
    render.add_argument("--path", required=True)
    render.add_argument("--output", default="")
    render.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    if args.command == "create":
        result = create_template(
            Path(args.repo).expanduser().resolve(),
            args.project,
            args.round,
            args.title,
            args.direction,
            args.baseline_paper,
            args.overwrite,
        )
    elif args.command == "validate":
        result = validate_lineage_map(load_json(Path(args.path).expanduser().resolve()))
    else:
        source_path = Path(args.path).expanduser().resolve()
        payload = load_json(source_path)
        validation = validate_lineage_map(payload)
        if not validation["valid"]:
            result = validation
        else:
            text = render_markdown_summary(payload)
            output = (
                Path(args.output).expanduser().resolve()
                if args.output
                else source_path.with_suffix(".md")
            )
            output.write_text(text, encoding="utf-8")
            result = {"valid": True, "output": str(output)}
    print(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
        if getattr(args, "json", False)
        else json.dumps(result, ensure_ascii=False, sort_keys=True)
    )
    return 0 if result.get("valid", result.get("created", False)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
