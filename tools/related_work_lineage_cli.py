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
METHOD_COMPONENT_ROUTE_HINTS = {
    "attention",
    "architecture",
    "feature",
    "internal",
    "internals",
    "model-internals",
    "module",
    "probing",
    "representation",
}
FIXED_DOMAIN_QUERY_TYPES = {
    "fully supervised",
    "weakly supervised",
    "open vocabulary",
    "zero shot",
    "zero-shot",
}
SCHEMA_VERSION = "related-work-lineage-v1"
SOURCE_BOUNDARY = "related_work_lineage_only_not_graph_truth"
SAFE_SEGMENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug[:96] or "lineage-map"


def relpath(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path)


def validate_path_segment(value: str, label: str) -> str:
    segment = str(value or "").strip()
    if (
        not segment
        or segment in {".", ".."}
        or "/" in segment
        or "\\" in segment
        or not SAFE_SEGMENT_RE.fullmatch(segment)
    ):
        raise ValueError(f"{label} must be a safe path segment")
    return segment


def artifact_paths(root: Path, project: str, round_id: str) -> Dict[str, Path]:
    project = validate_path_segment(project, "project")
    round_id = validate_path_segment(round_id, "round")
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
        "axis_candidates": [] if baseline_papers else [],
        "baseline_paper_field_scope": {
            "primary_problem": "",
            "input_output": "",
            "benchmarks_or_datasets": [],
            "evaluation_setting": "",
            "survey_boundary": "",
            "exclusion_rules": [],
            "field_structure": {
                "lane_axis": {
                    "name": "",
                    "why_this_axis_defines_field_structure": "",
                    "selected_lanes": [],
                },
                "non_lane_axes": [],
            },
            "derived_taxonomy": [],
        } if baseline_papers else {},
        "search_log": [],
        "routes": [],
        "papers": [],
        "explicit_edges": [],
        "survey_catalog": [],
        "timeline_tracks": [],
        "major_trends": [],
        "notable_forks": [],
        "positioning_note": "",
    }


def require_string(item: Dict[str, Any], key: str, label: str, errors: List[str]) -> str:
    value = str(item.get(key) or "").strip()
    if not value:
        errors.append(f"{label}.{key} is required")
    return value


def validate_lineage_map(payload: Any) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return {
            "valid": False,
            "errors": ["payload must be an object"],
            "paper_count": 0,
            "route_count": 0,
            "edge_count": 0,
        }

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

    route_narrowing = payload.get("route_narrowing")
    baseline_mode = (
        isinstance(route_narrowing, dict)
        and str(route_narrowing.get("input_mode") or "") == "baseline_papers"
    )
    selected_lanes = []
    lane_axis_name = ""
    if baseline_mode:
        field_scope = payload.get("baseline_paper_field_scope")
        if not isinstance(field_scope, dict) or not field_scope:
            errors.append("baseline_paper_field_scope is required for baseline_papers input_mode")
            field_scope = {}
        else:
            for key in ("primary_problem", "input_output", "survey_boundary"):
                require_string(field_scope, key, "baseline_paper_field_scope", errors)
            if not isinstance(field_scope.get("benchmarks_or_datasets"), list):
                errors.append("baseline_paper_field_scope.benchmarks_or_datasets must be a list")
            if not isinstance(field_scope.get("exclusion_rules"), list):
                errors.append("baseline_paper_field_scope.exclusion_rules must be a list")
            field_structure = field_scope.get("field_structure")
            selected_lanes = []
            if not isinstance(field_structure, dict) or not field_structure:
                errors.append("baseline_paper_field_scope.field_structure is required")
            else:
                lane_axis = field_structure.get("lane_axis")
                if not isinstance(lane_axis, dict) or not lane_axis:
                    errors.append("baseline_paper_field_scope.field_structure.lane_axis is required")
                else:
                    require_string(lane_axis, "name", "baseline_paper_field_scope.field_structure.lane_axis", errors)
                    lane_axis_name = str(lane_axis.get("name") or "").strip()
                    require_string(
                        lane_axis,
                        "why_this_axis_defines_field_structure",
                        "baseline_paper_field_scope.field_structure.lane_axis",
                        errors,
                    )
                    selected_lanes = lane_axis.get("selected_lanes")
                    if not isinstance(selected_lanes, list) or not selected_lanes:
                        errors.append(
                            "baseline_paper_field_scope.field_structure.lane_axis.selected_lanes must be a non-empty list"
                        )
                if not isinstance(field_structure.get("non_lane_axes", []), list):
                    errors.append("baseline_paper_field_scope.field_structure.non_lane_axes must be a list")
            taxonomy = field_scope.get("derived_taxonomy")
            if not isinstance(taxonomy, list) or not taxonomy:
                errors.append("baseline_paper_field_scope.derived_taxonomy must be a non-empty list")
            else:
                for index, item in enumerate(taxonomy):
                    if not isinstance(item, dict):
                        errors.append(f"baseline_paper_field_scope.derived_taxonomy[{index}] must be an object")
                        continue
                    require_string(item, "axis", f"baseline_paper_field_scope.derived_taxonomy[{index}]", errors)
                    values = item.get("values")
                    if not isinstance(values, list) or not values:
                        errors.append(f"baseline_paper_field_scope.derived_taxonomy[{index}].values must be a non-empty list")

        axis_candidates = payload.get("axis_candidates")
        if not isinstance(axis_candidates, list) or not axis_candidates:
            errors.append("axis_candidates must be a non-empty list for baseline_papers input_mode")
        else:
            selected_matches_lane_axis = False
            for index, candidate in enumerate(axis_candidates):
                if not isinstance(candidate, dict):
                    errors.append(f"axis_candidates[{index}] must be an object")
                    continue
                axis_name = require_string(candidate, "axis", f"axis_candidates[{index}]", errors)
                lanes = candidate.get("lanes")
                if not isinstance(lanes, list) or not lanes:
                    errors.append(f"axis_candidates[{index}].lanes must be a non-empty list")
                source = candidate.get("source")
                if not isinstance(source, list) or not source:
                    errors.append(f"axis_candidates[{index}].source must be a non-empty list")
                require_string(candidate, "why_field_native", f"axis_candidates[{index}]", errors)
                require_string(candidate, "risk", f"axis_candidates[{index}]", errors)
                tests = candidate.get("tests")
                if not isinstance(tests, dict):
                    errors.append(f"axis_candidates[{index}].tests must be an object")
                else:
                    for key in ("baseline_removal", "neighbor_paper", "project_intent", "non_component"):
                        require_string(tests, key, f"axis_candidates[{index}].tests", errors)
                decision = str(candidate.get("decision") or "").strip()
                if decision not in {"selected", "rejected"}:
                    errors.append(f"axis_candidates[{index}].decision must be selected or rejected")
                require_string(candidate, "reason", f"axis_candidates[{index}]", errors)
                if decision == "selected" and axis_name == lane_axis_name:
                    selected_matches_lane_axis = True
            if lane_axis_name and not selected_matches_lane_axis:
                errors.append(
                    "axis_candidates must include one selected candidate matching "
                    "baseline_paper_field_scope.field_structure.lane_axis.name"
                )

    search_log = payload.get("search_log", [])
    if search_log is not None and not isinstance(search_log, list):
        errors.append("search_log must be a list")
    elif baseline_mode:
        for index, item in enumerate(search_log):
            if not isinstance(item, dict):
                errors.append(f"search_log[{index}] must be an object")
                continue
            query_type = str(item.get("query_type") or "").lower()
            if any(term in query_type for term in FIXED_DOMAIN_QUERY_TYPES):
                errors.append(
                    f"search_log[{index}].query_type looks like a fixed domain template; "
                    "baseline searches must be derived from extracted taxonomy"
                )
            require_string(item, "query", f"search_log[{index}]", errors)
    survey_catalog = payload.get("survey_catalog", [])
    if survey_catalog is not None and not isinstance(survey_catalog, list):
        errors.append("survey_catalog must be a list")
    timeline_tracks = payload.get("timeline_tracks", [])
    if timeline_tracks is not None and not isinstance(timeline_tracks, list):
        errors.append("timeline_tracks must be a list")
    major_trends = payload.get("major_trends", [])
    if major_trends is not None and not isinstance(major_trends, list):
        errors.append("major_trends must be a list")
    notable_forks = payload.get("notable_forks", [])
    if notable_forks is not None and not isinstance(notable_forks, list):
        errors.append("notable_forks must be a list")

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
        if baseline_mode:
            route_text = f"{route_id} {route.get('label') or ''}".lower()
            if any(term in route_text for term in METHOD_COMPONENT_ROUTE_HINTS):
                errors.append(
                    f"routes[{index}].id looks like a method-component lane; "
                    "baseline_papers mode must use field-structure routes"
                )
            if selected_lanes and route_id not in selected_lanes:
                errors.append(
                    f"routes[{index}].id is not in "
                    "baseline_paper_field_scope.field_structure.lane_axis.selected_lanes"
                )
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
        identity = paper.get("identity")
        if not isinstance(identity, dict) or not identity:
            errors.append(f"papers[{index}].identity must be a non-empty object")
        route = str(paper.get("route") or "").strip()
        if route not in route_ids:
            errors.append(f"papers[{index}].route unknown route: {route}")
        if baseline_mode:
            require_string(paper, "field_position", f"papers[{index}]", errors)
            require_string(paper, "method_setting", f"papers[{index}]", errors)
            require_string(paper, "artifact_type", f"papers[{index}]", errors)
        status = str(paper.get("review_status") or "candidate")
        if status not in VALID_REVIEW_STATUSES:
            errors.append(f"papers[{index}].review_status invalid: {status}")

    if isinstance(survey_catalog, list):
        for index, item in enumerate(survey_catalog):
            if not isinstance(item, dict):
                errors.append(f"survey_catalog[{index}] must be an object")
                continue
            require_string(item, "period", f"survey_catalog[{index}]", errors)
            paper_id = require_string(item, "paper", f"survey_catalog[{index}]", errors)
            if paper_id and paper_id not in paper_ids:
                errors.append(f"survey_catalog[{index}].paper unknown paper: {paper_id}")
            require_string(item, "contribution", f"survey_catalog[{index}]", errors)

    if isinstance(timeline_tracks, list):
        for index, track in enumerate(timeline_tracks):
            if not isinstance(track, dict):
                errors.append(f"timeline_tracks[{index}] must be an object")
                continue
            track_id = require_string(track, "id", f"timeline_tracks[{index}]", errors)
            if track_id and track_id not in route_ids:
                errors.append(f"timeline_tracks[{index}].id unknown route: {track_id}")
            require_string(track, "label", f"timeline_tracks[{index}]", errors)

    if isinstance(major_trends, list):
        for index, trend in enumerate(major_trends):
            if not isinstance(trend, dict):
                errors.append(f"major_trends[{index}] must be an object")
                continue
            require_string(trend, "name", f"major_trends[{index}]", errors)
            evidence = trend.get("evidence_papers", [])
            if not isinstance(evidence, list):
                errors.append(f"major_trends[{index}].evidence_papers must be a list")
            else:
                for paper_id in evidence:
                    if paper_id not in paper_ids:
                        errors.append(f"major_trends[{index}].evidence_papers unknown paper: {paper_id}")

    if isinstance(notable_forks, list):
        for index, fork in enumerate(notable_forks):
            if not isinstance(fork, dict):
                errors.append(f"notable_forks[{index}] must be an object")
                continue
            require_string(fork, "name", f"notable_forks[{index}]", errors)
            if not isinstance(fork.get("sides", []), list):
                errors.append(f"notable_forks[{index}].sides must be a list")

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


def yaml_scalar(value: Any) -> str:
    return json.dumps(str(value), ensure_ascii=False)


def render_markdown_summary(payload: Dict[str, Any]) -> str:
    lines = [
        "---",
        f"title: {yaml_scalar(payload.get('title', 'Related Work Lineage'))}",
        "type: related-work-lineage",
        f"project: {yaml_scalar(payload.get('project', ''))}",
        f"round: {yaml_scalar(payload.get('round', ''))}",
        f"status: {yaml_scalar(payload.get('status', 'candidate'))}",
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
    ]
    field_scope = payload.get("baseline_paper_field_scope") or {}
    lines.extend(["## Baseline Paper Field Scope", ""])
    if isinstance(field_scope, dict) and field_scope:
        lines.extend(
            [
                f"- Primary problem: {field_scope.get('primary_problem', '')}",
                f"- Input/output: {field_scope.get('input_output', '')}",
                f"- Evaluation setting: {field_scope.get('evaluation_setting', '')}",
                f"- Survey boundary: {field_scope.get('survey_boundary', '')}",
            ]
        )
        field_structure = field_scope.get("field_structure") or {}
        lane_axis = field_structure.get("lane_axis") if isinstance(field_structure, dict) else {}
        if isinstance(lane_axis, dict) and lane_axis:
            lines.append(f"- Lane axis: {lane_axis.get('name', '')}")
            lanes = lane_axis.get("selected_lanes") or []
            if lanes:
                lines.append(f"- Selected lanes: {', '.join(str(item) for item in lanes)}")
        datasets = field_scope.get("benchmarks_or_datasets") or []
        if datasets:
            lines.append(f"- Benchmarks/datasets: {', '.join(str(item) for item in datasets)}")
        exclusions = field_scope.get("exclusion_rules") or []
        if exclusions:
            lines.append(f"- Exclusion rules: {'; '.join(str(item) for item in exclusions)}")
    else:
        lines.append("No baseline field scope recorded.")

    lines.extend(["", "## Search Log", ""])
    search_log = payload.get("search_log") or []
    if search_log:
        for item in search_log:
            if isinstance(item, dict):
                lines.append(f"- {item.get('query_type', 'query')}: {item.get('query', '')}")
    else:
        lines.append("- No search log recorded.")

    lines.extend(["", "## Axis Candidates", ""])
    axis_candidates = payload.get("axis_candidates") or []
    if axis_candidates:
        for candidate in axis_candidates:
            if not isinstance(candidate, dict):
                continue
            lanes = ", ".join(str(item) for item in candidate.get("lanes", []) if item)
            lines.append(
                f"- {candidate.get('decision', 'candidate')}: "
                f"{candidate.get('axis', '')} ({lanes}) - {candidate.get('reason', '')}"
            )
    else:
        lines.append("- No axis candidates recorded.")

    lines.extend(["", "## Technical Routes", ""])
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
    lines.extend(["", "## Chronological Catalog", ""])
    catalog = payload.get("survey_catalog") or []
    if catalog:
        for item in catalog:
            if not isinstance(item, dict):
                continue
            lines.append(
                f"- {item.get('period', '')} `{item.get('paper', '')}`: "
                f"{item.get('contribution', '')}"
            )
            relevance = item.get("field_relevance") or item.get("task_relevance")
            if relevance:
                lines.append(f"  Task relevance: {relevance}")
    else:
        lines.append("- No chronological catalog recorded.")

    lines.extend(["", "## Major Trends", ""])
    trends = payload.get("major_trends") or []
    if trends:
        for trend in trends:
            if not isinstance(trend, dict):
                continue
            evidence = ", ".join(str(item) for item in trend.get("evidence_papers", []))
            suffix = f" Evidence: {evidence}." if evidence else ""
            lines.append(f"- {trend.get('name', '')}: {trend.get('summary', '')}{suffix}")
    else:
        lines.append("- No major trends recorded.")

    lines.extend(["", "## Notable Forks", ""])
    forks = payload.get("notable_forks") or []
    if forks:
        for fork in forks:
            if not isinstance(fork, dict):
                continue
            sides = " vs ".join(str(item) for item in fork.get("sides", []))
            side_text = f" ({sides})" if sides else ""
            lines.append(f"- {fork.get('name', '')}{side_text}: {fork.get('summary', '')}")
    else:
        lines.append("- No notable forks recorded.")
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
    try:
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
    except (OSError, json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
        result = {"valid": False, "created": False, "errors": [str(exc)]}
    print(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
        if getattr(args, "json", False)
        else json.dumps(result, ensure_ascii=False, sort_keys=True)
    )
    return 0 if result.get("valid", result.get("created", False)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
