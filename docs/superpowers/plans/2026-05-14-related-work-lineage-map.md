# Related Work Lineage Map Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a project-scoped, paper-only related work lineage map workflow and read-only dashboard view.

**Architecture:** Store lineage source artifacts as project-local literature-round artifacts, validate them with a focused CLI, expose them through the existing `.dashboard/index.json` read model, and render them in a new read-only dashboard page. Add a `related-work-lineage` skill and workspace workflow so the agent can narrow broad directions, collect baseline papers, and maintain lineage artifacts without writing Project Understanding Graph events.

**Tech Stack:** Python 3 standard library, Markdown skills/workflows, JSON source artifacts, existing Research Browser dashboard (`dashboard/app.js`, `dashboard/styles.css`), unittest.

---

## Storage-Path Alignment

The PRD requires storage-path alignment before implementation.

Existing conventions:

- Project-local source artifacts live under `wiki/projects/<ProjectId>/...`; project shell currently creates `overview.md`, `project-query-pack.md`, `decisions.md`, `papers/.gitkeep`, and `experiment-proposals/.gitkeep` (`templates/workspace/wiki/_system/workflows/first-run.md:68`).
- Paper dossiers already live under `wiki/projects/<Project>/papers/<paper-id>/index.md` (`tools/paper_dossier_cli.py:26`).
- Search/discovery artifacts already use `wiki/projects/<Project>/literature-rounds/<round>/...` (`tools/gap_search_cli.py:726`, `tools/gap_search_cli.py:735`).
- Dashboard read models are rebuildable and served through `.dashboard/index.json` (`tools/README.md:9`, `docs/guides/dashboard.md:5`).
- `tools/build_dashboard_index.py` already scans literature rounds and project-local paper artifacts (`tools/build_dashboard_index.py:858`, `tools/build_dashboard_index.py:899`, `tools/build_dashboard_index.py:945`).

Decision:

```text
Source JSON:
wiki/projects/<ProjectId>/literature-rounds/<RoundId>/related-work-lineage.json

Source Markdown summary:
wiki/projects/<ProjectId>/literature-rounds/<RoundId>/related-work-lineage.md

Dashboard read model:
.dashboard/index.json -> top-level "lineage_maps" array
```

Reason:

- A lineage map is a related-work search/organization artifact, so it fits the existing `literature-rounds` family better than a new project-level directory.
- The JSON artifact is the source artifact for local review state.
- The Markdown artifact gives the agent and user a durable plain-text summary.
- The dashboard remains a derived read model and does not write lineage data.

## Scope Boundary

Implement MVP only:

- paper-only nodes;
- max 20 papers per map;
- no citation graph;
- no D* events;
- no dashboard editing;
- no provider-specific search integration;
- no full literature review generation.

Agent search remains skill-guided. Deterministic code validates, summarizes, indexes, and renders lineage artifacts.

## File Structure

Create:

```text
tools/related_work_lineage_cli.py
tests/test_related_work_lineage_cli.py
skills/related-work-lineage/SKILL.md
templates/workspace/wiki/_system/workflows/related-work-lineage.md
dashboard/lineage.html
tests/test_related_work_lineage_dashboard.py
```

Modify:

```text
tools/build_dashboard_index.py
dashboard/app.js
dashboard/styles.css
skills/research-pilot/SKILL.md
docs/guides/dashboard.md
docs/guides/core-workflows.md
README.md
tools/README.md
tests/test_dashboard_public.py
```

Responsibilities:

- `tools/related_work_lineage_cli.py`: deterministic artifact path resolution, template creation, validation, and Markdown rendering.
- `tools/build_dashboard_index.py`: scan lineage JSON artifacts and expose dashboard-ready `lineage_maps`.
- `skills/related-work-lineage/SKILL.md`: agent-facing workflow trigger and boundaries.
- `templates/workspace/wiki/_system/workflows/related-work-lineage.md`: workspace-local protocol copied at init.
- `dashboard/lineage.html` and `dashboard/app.js`: read-only lineage map page.

## Data Contract

Use this source JSON shape:

```json
{
  "schema_version": "related-work-lineage-v1",
  "project": "DemoProject",
  "round": "vision-world-model-baselines",
  "title": "Vision World Model Related Work Lineage",
  "status": "candidate",
  "source_boundary": "related_work_lineage_only_not_graph_truth",
  "max_papers": 20,
  "route_narrowing": {
    "input_mode": "baseline_papers",
    "user_direction": "vision world models",
    "selected_anchor_papers": ["paper:dreamerv3"],
    "candidate_routes": []
  },
  "routes": [
    {
      "id": "object-centric-modeling",
      "label": "Object-centric Modeling",
      "description": "Papers that model world state through objects, slots, or entities.",
      "review_status": "candidate"
    }
  ],
  "papers": [
    {
      "id": "paper:dreamerv3",
      "kind": "paper",
      "title": "DreamerV3",
      "year": 2023,
      "month": "01",
      "route": "object-centric-modeling",
      "roles": ["method", "milestone", "baseline"],
      "venue": "arXiv",
      "source_url": "https://arxiv.org/abs/2301.04104",
      "identity": {"arxiv": "2301.04104"},
      "summary": "Scales latent world model reinforcement learning across domains.",
      "source_evidence": "arXiv page and abstract.",
      "review_status": "candidate"
    }
  ],
  "explicit_edges": [
    {
      "source": "paper:dreamerv3",
      "target": "paper:focus",
      "relation": "influences",
      "rationale": "FOCUS follows the object-centric world model route.",
      "confidence": "medium",
      "source_evidence": "FOCUS introduction positions itself against prior world model work.",
      "review_status": "candidate"
    }
  ],
  "positioning_note": "The project appears closest to object-centric modeling and embodied world model routes."
}
```

Valid review statuses:

```text
candidate
approved
rejected
```

Valid edge relations:

```text
branches-from
extends-method
adapts-to-domain
influences
competes-with
unifies
contrasts-with
```

## Task 1: Related Work Lineage CLI And Validation

**Files:**

- Create: `tools/related_work_lineage_cli.py`
- Create: `tests/test_related_work_lineage_cli.py`

- [ ] **Step 1: Write failing CLI tests**

Create `tests/test_related_work_lineage_cli.py`:

```python
import json
import tempfile
import unittest
from pathlib import Path

from tools.related_work_lineage_cli import (
    artifact_paths,
    create_template,
    render_markdown_summary,
    validate_lineage_map,
)


VALID_MAP = {
    "schema_version": "related-work-lineage-v1",
    "project": "DemoProject",
    "round": "vision-world-model-baselines",
    "title": "Vision World Model Related Work Lineage",
    "status": "candidate",
    "source_boundary": "related_work_lineage_only_not_graph_truth",
    "max_papers": 20,
    "route_narrowing": {
        "input_mode": "baseline_papers",
        "user_direction": "vision world models",
        "selected_anchor_papers": ["paper:dreamerv3"],
        "candidate_routes": [],
    },
    "routes": [
        {
            "id": "object-centric-modeling",
            "label": "Object-centric Modeling",
            "description": "Papers that model world state through objects, slots, or entities.",
            "review_status": "candidate",
        }
    ],
    "papers": [
        {
            "id": "paper:dreamerv3",
            "kind": "paper",
            "title": "DreamerV3",
            "year": 2023,
            "month": "01",
            "route": "object-centric-modeling",
            "roles": ["method", "milestone", "baseline"],
            "venue": "arXiv",
            "source_url": "https://arxiv.org/abs/2301.04104",
            "identity": {"arxiv": "2301.04104"},
            "summary": "Scales latent world model reinforcement learning across domains.",
            "source_evidence": "arXiv page and abstract.",
            "review_status": "candidate",
        },
        {
            "id": "paper:focus",
            "kind": "paper",
            "title": "FOCUS",
            "year": 2023,
            "month": "07",
            "route": "object-centric-modeling",
            "roles": ["method"],
            "venue": "arXiv",
            "source_url": "https://example.org/focus",
            "identity": {"official": "https://example.org/focus"},
            "summary": "Object-centric world modeling paper.",
            "source_evidence": "Official project page.",
            "review_status": "candidate",
        },
    ],
    "explicit_edges": [
        {
            "source": "paper:dreamerv3",
            "target": "paper:focus",
            "relation": "influences",
            "rationale": "FOCUS follows the object-centric world model route.",
            "confidence": "medium",
            "source_evidence": "FOCUS introduction positions itself against prior world model work.",
            "review_status": "candidate",
        }
    ],
    "positioning_note": "The project appears closest to object-centric modeling.",
}


class RelatedWorkLineageCliTest(unittest.TestCase):
    def test_artifact_paths_follow_literature_round_convention(self):
        root = Path("/tmp/workspace")
        paths = artifact_paths(root, "DemoProject", "vision-world-model-baselines")

        self.assertEqual(
            paths["json"],
            root / "wiki" / "projects" / "DemoProject" / "literature-rounds" / "vision-world-model-baselines" / "related-work-lineage.json",
        )
        self.assertEqual(paths["markdown"].name, "related-work-lineage.md")

    def test_validates_paper_only_map(self):
        result = validate_lineage_map(VALID_MAP)

        self.assertTrue(result["valid"], result)
        self.assertEqual(result["paper_count"], 2)

    def test_rejects_non_paper_nodes(self):
        payload = json.loads(json.dumps(VALID_MAP))
        payload["papers"][0]["kind"] = "dataset"

        result = validate_lineage_map(payload)

        self.assertFalse(result["valid"])
        self.assertIn("papers[0].kind must be paper", result["errors"])

    def test_rejects_more_than_twenty_papers(self):
        payload = json.loads(json.dumps(VALID_MAP))
        payload["papers"] = [
            {
                **payload["papers"][0],
                "id": f"paper:item-{index}",
                "title": f"Paper {index}",
                "source_url": f"https://example.org/{index}",
            }
            for index in range(21)
        ]

        result = validate_lineage_map(payload)

        self.assertFalse(result["valid"])
        self.assertIn("paper count must be <= 20", result["errors"])

    def test_rejects_edges_to_unknown_papers(self):
        payload = json.loads(json.dumps(VALID_MAP))
        payload["explicit_edges"][0]["target"] = "paper:missing"

        result = validate_lineage_map(payload)

        self.assertFalse(result["valid"])
        self.assertIn("explicit_edges[0].target unknown paper: paper:missing", result["errors"])

    def test_template_and_markdown_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            created = create_template(
                root=root,
                project="DemoProject",
                round_id="vision-world-model-baselines",
                title="Vision World Model Related Work Lineage",
                user_direction="vision world models",
                baseline_papers=["DreamerV3"],
                overwrite=False,
            )
            payload = json.loads(Path(created["json_path"]).read_text(encoding="utf-8"))
            summary = render_markdown_summary(VALID_MAP)

        self.assertTrue(created["created"], created)
        self.assertEqual(payload["project"], "DemoProject")
        self.assertEqual(payload["route_narrowing"]["selected_anchor_papers"], ["DreamerV3"])
        self.assertIn("# Vision World Model Related Work Lineage", summary)
        self.assertIn("## Technical Routes", summary)
        self.assertIn("DreamerV3", summary)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run CLI tests and verify failure**

Run:

```bash
python3 -m unittest tests.test_related_work_lineage_cli -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'tools.related_work_lineage_cli'`.

- [ ] **Step 3: Implement CLI module**

Create `tools/related_work_lineage_cli.py`:

```python
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


def empty_payload(project: str, round_id: str, title: str, user_direction: str, baseline_papers: List[str]) -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "project": project,
        "round": round_id,
        "title": title,
        "status": "candidate",
        "source_boundary": SOURCE_BOUNDARY,
        "max_papers": 20,
        "created": date.today().isoformat(),
        "updated": date.today().isoformat(),
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
    edges = payload.get("explicit_edges", [])
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
        lines.extend([
            f"### {route.get('label', route_id)}",
            "",
            str(route.get("description") or "No route description yet."),
            "",
        ])
        for paper in sorted(papers_by_route.get(route_id, []), key=lambda item: (str(item.get("year") or ""), str(item.get("month") or ""), str(item.get("title") or ""))):
            roles = ", ".join(str(role) for role in paper.get("roles", []) if role)
            lines.append(f"- {paper.get('year', '')}.{paper.get('month', '')} **{paper.get('title', '')}** [{roles}] — {paper.get('summary', '')}")
        lines.append("")
    lines.extend(["## Explicit Lineage Edges", ""])
    for edge in payload.get("explicit_edges", []):
        lines.append(f"- `{edge.get('source')}` {edge.get('relation')} `{edge.get('target')}`: {edge.get('rationale')}")
    if not payload.get("explicit_edges"):
        lines.append("- None.")
    lines.append("")
    return "\n".join(lines)


def create_template(root: Path, project: str, round_id: str, title: str, user_direction: str, baseline_papers: List[str], overwrite: bool) -> Dict[str, Any]:
    paths = artifact_paths(root, project, round_id)
    if paths["json"].exists() and not overwrite:
        return {"created": False, "error": "lineage artifact already exists", "json_path": str(paths["json"])}
    paths["dir"].mkdir(parents=True, exist_ok=True)
    payload = empty_payload(project, round_id, title, user_direction, baseline_papers)
    paths["json"].write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    paths["markdown"].write_text(render_markdown_summary(payload), encoding="utf-8")
    return {"created": True, "json_path": str(paths["json"]), "markdown_path": str(paths["markdown"])}


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Create and validate related work lineage artifacts.")
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
        result = create_template(Path(args.repo).expanduser().resolve(), args.project, args.round, args.title, args.direction, args.baseline_paper, args.overwrite)
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
            output = Path(args.output).expanduser().resolve() if args.output else source_path.with_suffix(".md")
            output.write_text(text, encoding="utf-8")
            result = {"valid": True, "output": str(output)}
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) if getattr(args, "json", False) else json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("valid", result.get("created", False)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run CLI tests and verify pass**

Run:

```bash
python3 -m unittest tests.test_related_work_lineage_cli -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/related_work_lineage_cli.py tests/test_related_work_lineage_cli.py
git commit -m "Add related work lineage artifact validation"
```

## Task 2: Dashboard Index Read Model

**Files:**

- Modify: `tools/build_dashboard_index.py`
- Modify: `tests/test_dashboard_public.py`

- [ ] **Step 1: Write failing dashboard index test**

Append to `DashboardPublicTest` in `tests/test_dashboard_public.py`:

```python
    def test_build_index_exposes_related_work_lineage_maps(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lineage_dir = root / "wiki" / "projects" / "DemoProject" / "literature-rounds" / "vision-world-model-baselines"
            lineage_dir.mkdir(parents=True)
            (lineage_dir / "related-work-lineage.json").write_text(
                json.dumps(
                    {
                        "schema_version": "related-work-lineage-v1",
                        "project": "DemoProject",
                        "round": "vision-world-model-baselines",
                        "title": "Vision World Model Related Work Lineage",
                        "status": "candidate",
                        "source_boundary": "related_work_lineage_only_not_graph_truth",
                        "max_papers": 20,
                        "route_narrowing": {
                            "input_mode": "baseline_papers",
                            "user_direction": "vision world models",
                            "selected_anchor_papers": ["paper:dreamerv3"],
                            "candidate_routes": [],
                        },
                        "routes": [
                            {
                                "id": "object-centric-modeling",
                                "label": "Object-centric Modeling",
                                "description": "Object-centric world model route.",
                                "review_status": "candidate",
                            }
                        ],
                        "papers": [
                            {
                                "id": "paper:dreamerv3",
                                "kind": "paper",
                                "title": "DreamerV3",
                                "year": 2023,
                                "month": "01",
                                "route": "object-centric-modeling",
                                "roles": ["method", "baseline"],
                                "venue": "arXiv",
                                "source_url": "https://arxiv.org/abs/2301.04104",
                                "identity": {"arxiv": "2301.04104"},
                                "summary": "Scales latent world model reinforcement learning across domains.",
                                "source_evidence": "arXiv page and abstract.",
                                "review_status": "candidate",
                            }
                        ],
                        "explicit_edges": [],
                        "positioning_note": "Closest to object-centric modeling.",
                    }
                ),
                encoding="utf-8",
            )

            index = build_index(root)

        self.assertEqual(len(index["lineage_maps"]), 1)
        lineage = index["lineage_maps"][0]
        self.assertEqual(lineage["id"], "DemoProject/vision-world-model-baselines")
        self.assertEqual(lineage["project"], "DemoProject")
        self.assertEqual(lineage["paper_count"], 1)
        self.assertEqual(lineage["route_count"], 1)
        self.assertEqual(lineage["path"], "wiki/projects/DemoProject/literature-rounds/vision-world-model-baselines/related-work-lineage.json")
        self.assertEqual(lineage["source_boundary"], "related_work_lineage_only_not_graph_truth")
```

- [ ] **Step 2: Run dashboard test and verify failure**

Run:

```bash
python3 -m unittest tests.test_dashboard_public.DashboardPublicTest.test_build_index_exposes_related_work_lineage_maps -v
```

Expected: FAIL with `KeyError: 'lineage_maps'`.

- [ ] **Step 3: Add lineage map collector**

Modify `tools/build_dashboard_index.py`:

1. Add import near the top:

```python
from tools.related_work_lineage_cli import validate_lineage_map
```

2. Add collector before `build_index`:

```python
def collect_lineage_maps(root: Path) -> List[Dict[str, Any]]:
    maps: List[Dict[str, Any]] = []
    projects_root = root / "wiki" / "projects"
    if not projects_root.exists():
        return maps
    for lineage_path in sorted(projects_root.glob("*/literature-rounds/*/related-work-lineage.json")):
        try:
            payload = json.loads(lineage_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        validation = validate_lineage_map(payload)
        project = str(payload.get("project") or lineage_path.relative_to(projects_root).parts[0])
        round_name = str(payload.get("round") or lineage_path.parent.name)
        maps.append(
            {
                "id": f"{project}/{round_name}",
                "project": project,
                "round": round_name,
                "title": str(payload.get("title") or "Related Work Lineage"),
                "status": str(payload.get("status") or "candidate"),
                "source_boundary": str(payload.get("source_boundary") or ""),
                "path": relpath(lineage_path, root),
                "markdown_path": relpath(lineage_path.with_suffix(".md"), root) if lineage_path.with_suffix(".md").exists() else "",
                "valid": validation["valid"],
                "errors": validation["errors"],
                "paper_count": len(payload.get("papers", [])) if isinstance(payload.get("papers"), list) else 0,
                "route_count": len(payload.get("routes", [])) if isinstance(payload.get("routes"), list) else 0,
                "edge_count": len(payload.get("explicit_edges", [])) if isinstance(payload.get("explicit_edges"), list) else 0,
                "route_narrowing": payload.get("route_narrowing", {}),
                "routes": payload.get("routes", []) if isinstance(payload.get("routes"), list) else [],
                "papers": payload.get("papers", []) if isinstance(payload.get("papers"), list) else [],
                "explicit_edges": payload.get("explicit_edges", []) if isinstance(payload.get("explicit_edges"), list) else [],
                "positioning_note": str(payload.get("positioning_note") or ""),
            }
        )
    return maps
```

3. In `build_index`, collect and return:

```python
    lineage_maps = collect_lineage_maps(root)
```

Add this before `jobs = list_job_records(root)`.

4. Add to returned dict:

```python
        "lineage_maps": lineage_maps,
```

5. Update CLI print line:

```python
        f"Rounds: {len(data['rounds'])} Claims: {len(data['claims'])} "
        f"Lineage maps: {len(data['lineage_maps'])}"
```

- [ ] **Step 4: Run dashboard tests**

Run:

```bash
python3 -m unittest tests.test_dashboard_public -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/build_dashboard_index.py tests/test_dashboard_public.py
git commit -m "Expose related work lineage maps in dashboard index"
```

## Task 3: Skill, Workflow, And Router Documentation

**Files:**

- Create: `skills/related-work-lineage/SKILL.md`
- Create: `templates/workspace/wiki/_system/workflows/related-work-lineage.md`
- Modify: `skills/research-pilot/SKILL.md`
- Modify: `tests/test_plugin_health.py`
- Modify: `tests/test_plugin_commands.py`

- [ ] **Step 1: Write failing skill/workflow tests**

Append to `tests/test_plugin_commands.py`:

```python
    def test_related_work_lineage_skill_and_workflow_exist(self) -> None:
        skill = REPO / "skills" / "related-work-lineage" / "SKILL.md"
        workflow = REPO / "templates" / "workspace" / "wiki" / "_system" / "workflows" / "related-work-lineage.md"

        self.assertTrue(skill.exists())
        self.assertTrue(workflow.exists())
        self.assertIn("paper-only", skill.read_text(encoding="utf-8"))
        self.assertIn("must not append graph events", workflow.read_text(encoding="utf-8"))
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
python3 -m unittest tests.test_plugin_commands.PluginCommandsTest.test_related_work_lineage_skill_and_workflow_exist -v
```

Expected: FAIL because skill/workflow files do not exist.

- [ ] **Step 3: Add skill**

Create `skills/related-work-lineage/SKILL.md`:

```markdown
---
name: related-work-lineage
description: Use when the user wants to understand a project's related-work technical routes, build a paper-only lineage map, narrow a broad research direction into baseline paper candidates, or inspect where a project contribution fits relative to prior work.
argument-hint: "[workspace path] [project id] [baseline papers or direction]"
---

# Related Work Lineage

Use this for human-facing related-work route understanding. Do not use it for Project Understanding Graph updates.

## Boundary

- Nodes are papers only.
- Dataset, benchmark, method, theory, survey, and system are paper roles, not node types.
- Do not build citation graphs.
- Do not append graph events.
- Do not register D* deltas.
- Do not require an existing Project Understanding Graph.
- Dashboard output is read-only.

## Required Context

Read:

```text
$WORKSPACE/wiki/projects/$PROJECT/overview.md if present
$WORKSPACE/wiki/projects/$PROJECT/project-query-pack.md if present
$WORKSPACE/wiki/projects/$PROJECT/literature-rounds/ if present
$WORKSPACE/wiki/projects/$PROJECT/papers/ if present
$WORKSPACE/wiki/_system/workflows/related-work-lineage.md
```

## Input Routing

If the user gives 1-2 baseline papers, use baseline paper mode.

If the user gives only a broad topic or direction, do not generate a map directly. First produce 3-5 candidate technical routes. Each route must include 1-2 candidate baseline papers, why that route fits, and what it excludes. Ask the user to choose route/anchor before generating the map.

## Artifact Path

Use one literature round:

```text
wiki/projects/$PROJECT/literature-rounds/$ROUND/related-work-lineage.json
wiki/projects/$PROJECT/literature-rounds/$ROUND/related-work-lineage.md
```

Create a skeleton when useful:

```bash
python3 "$PLUGIN_ROOT/tools/related_work_lineage_cli.py" create --repo "$WORKSPACE" --project "$PROJECT" --round "$ROUND" --title "$TITLE" --direction "$DIRECTION" --baseline-paper "$BASELINE" --json
```

Validate before presenting as complete:

```bash
python3 "$PLUGIN_ROOT/tools/related_work_lineage_cli.py" validate --path "$WORKSPACE/wiki/projects/$PROJECT/literature-rounds/$ROUND/related-work-lineage.json" --json
python3 "$PLUGIN_ROOT/tools/related_work_lineage_cli.py" render-summary --path "$WORKSPACE/wiki/projects/$PROJECT/literature-rounds/$ROUND/related-work-lineage.json" --json
```

## Output Requirements

- Max 20 papers.
- Every node has `kind: "paper"`.
- Every paper has title, year, route, roles, source URL, source evidence, and review status.
- Track-internal sequence is inferred by date.
- Store explicit edges only for cross-route influence, branching, convergence, or contrast.
- Include a short project positioning note.

## Stop Point

Stop after lineage artifact creation or update. If the user wants a claim/evidence update in project graph truth, route to the graph delta workflow separately.
```

- [ ] **Step 4: Add workspace workflow**

Create `templates/workspace/wiki/_system/workflows/related-work-lineage.md`:

```markdown
---
title: "Related Work Lineage Protocol v1"
type: workflow
status: active
human_review: approved
---

# Related Work Lineage Protocol v1

Use this protocol when a project needs a paper-only technical route map for related work.

## Boundary

This workflow must not append graph events, register D* deltas, approve papers as project-core, or mutate Zotero.

Lineage artifacts are related-work understanding aids. They are not Project Understanding Graph truth.

## Required Context

Read available project shell files:

```text
wiki/projects/<Project>/overview.md
wiki/projects/<Project>/project-query-pack.md
wiki/projects/<Project>/papers/
wiki/projects/<Project>/literature-rounds/
```

An existing Project Understanding Graph is optional context, not a prerequisite.

## Input Modes

### Baseline Paper Mode

Use when the user gives 1-2 baseline papers. Verify stable identity when possible, then build a route map around those anchors.

### Coarse Direction Mode

Use when the user gives only a broad direction. Do not build a map immediately. First produce 3-5 candidate technical routes, each with 1-2 candidate baseline papers, route fit, exclusions, and risk of over-broad scope. Ask the human to choose route and anchor.

## Artifact Location

Use:

```text
wiki/projects/<Project>/literature-rounds/<Round>/related-work-lineage.json
wiki/projects/<Project>/literature-rounds/<Round>/related-work-lineage.md
```

## Quality Bar

- Maximum 20 papers.
- Every node is a paper.
- Dataset, benchmark, method, survey, theory, and system are paper roles.
- Routes are technical development lanes.
- Paper order inside a lane follows publication or submission date.
- Explicit edges are only for cross-route influence, branching, convergence, or contrast.
- Each paper and edge has source evidence.
- Dashboard remains read-only.
```

- [ ] **Step 5: Update router skill**

Modify `skills/research-pilot/SKILL.md`:

1. Add to Current Capabilities:

```markdown
- Build paper-only related-work lineage maps for project-scoped technical route understanding.
```

2. Add intent routing after project gap discovery:

```markdown
### Related Work Lineage

When the user asks for a related-work route map, technology development map, lineage map, baseline route map, or wants to understand where a project fits in prior work:

1. Use the `related-work-lineage` skill.
2. Do not use `project-evidence-synthesis` for this intent.
3. Do not append graph events or register D* deltas.
4. If the input is broad direction only, require route/anchor narrowing before map generation.
```

- [ ] **Step 6: Run skill tests**

Run:

```bash
python3 -m unittest tests.test_plugin_commands -v
python3 -m unittest tests.test_plugin_health -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add skills/related-work-lineage/SKILL.md templates/workspace/wiki/_system/workflows/related-work-lineage.md skills/research-pilot/SKILL.md tests/test_plugin_commands.py
git commit -m "Add related work lineage skill workflow"
```

## Task 4: Read-Only Dashboard Lineage Page

**Files:**

- Create: `dashboard/lineage.html`
- Modify: `dashboard/app.js`
- Modify: `dashboard/styles.css`
- Create: `tests/test_related_work_lineage_dashboard.py`

- [ ] **Step 1: Write failing dashboard static tests**

Create `tests/test_related_work_lineage_dashboard.py`:

```python
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]


class RelatedWorkLineageDashboardTest(unittest.TestCase):
    def test_lineage_page_and_renderer_are_registered(self):
        lineage_html = REPO / "dashboard" / "lineage.html"
        app_js = (REPO / "dashboard" / "app.js").read_text(encoding="utf-8")

        self.assertTrue(lineage_html.exists())
        self.assertIn('data-page="lineage"', lineage_html.read_text(encoding="utf-8"))
        self.assertIn("function lineageUrl(projectId, roundName)", app_js)
        self.assertIn("function renderLineagePage()", app_js)
        self.assertIn('state.page === "lineage"', app_js)

    def test_lineage_styles_exist(self):
        styles = (REPO / "dashboard" / "styles.css").read_text(encoding="utf-8")

        self.assertIn(".lineage-map-shell", styles)
        self.assertIn(".lineage-lane", styles)
        self.assertIn(".lineage-paper-node", styles)
```

- [ ] **Step 2: Run static tests and verify failure**

Run:

```bash
python3 -m unittest tests.test_related_work_lineage_dashboard -v
```

Expected: FAIL because `dashboard/lineage.html` does not exist.

- [ ] **Step 3: Add dashboard HTML page**

Create `dashboard/lineage.html`:

```html
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>研究浏览器 · Related Work Lineage</title>
    <link rel="icon" href="data:," />
    <link rel="stylesheet" href="./styles.css" />
  </head>
  <body data-page="lineage">
    <main class="page-shell">
      <header class="topbar">
        <a class="brand-link" href="./index.html" aria-label="研究浏览器项目">
          <span class="brand-mark">RB</span>
          <span>
            <strong>研究浏览器</strong>
            <small>技术路线图</small>
          </span>
        </a>
        <nav id="project-nav" class="topnav" aria-label="项目导航"></nav>
      </header>
      <section class="page-head">
        <p id="page-kicker" class="page-kicker">Related Work</p>
        <h1 id="page-title">Lineage Map</h1>
        <p id="page-subtitle"></p>
      </section>
      <section id="page-content" class="page-content" aria-live="polite"></section>
    </main>
    <script src="./app.js" defer></script>
  </body>
</html>
```

- [ ] **Step 4: Add app.js lineage helpers**

Modify `dashboard/app.js`:

1. Add URL helper near `experimentProposalsUrl`:

```javascript
function lineageUrl(projectId, roundName = "") {
  const params = new URLSearchParams({ project: projectId });
  if (roundName) params.set("round", roundName);
  return `./lineage.html?${params.toString()}`;
}
```

2. Add data helper near `latestRound` helpers:

```javascript
function lineageMapsForProject(projectId) {
  return (state.data?.lineage_maps || []).filter((map) => map.project === projectId);
}
```

3. Update `renderProjectNav`:

```javascript
  const lineageCurrent = current === "lineage" ? ' aria-current="page"' : "";
```

Add link:

```javascript
    <a href="${escapeAttr(lineageUrl(project.id))}"${lineageCurrent}>技术路线</a>
```

4. Add lineage renderer before `renderEmpty`:

```javascript
function renderLineagePage() {
  const project = projectById();
  if (!project) {
    renderEmpty("未找到项目。");
    return;
  }
  renderProjectNav(project);
  const maps = lineageMapsForProject(project.id);
  const roundParam = params().get("round") || "";
  const lineage = maps.find((item) => item.round === roundParam) || maps[0] || null;
  setHeader(
    "技术路线",
    lineage?.title || "Related Work Lineage",
    lineage ? `${displayProjectTitle(project)} · ${lineage.paper_count || 0} papers · read-only` : `${displayProjectTitle(project)} · no lineage map yet`
  );
  if (!lineage) {
    el.content.innerHTML = `
      <section class="section-block lineage-map-shell">
        <div class="empty-state">No related-work lineage map yet. Ask agent to run related-work-lineage for this project.</div>
      </section>
    `;
    return;
  }
  const routes = Array.isArray(lineage.routes) ? lineage.routes : [];
  const papers = Array.isArray(lineage.papers) ? lineage.papers : [];
  const edges = Array.isArray(lineage.explicit_edges) ? lineage.explicit_edges : [];
  el.content.innerHTML = `
    <section class="section-block lineage-map-shell">
      <div class="section-head">
        <div>
          <p class="eyebrow">Paper-only technical lineage</p>
          <h2>${escapeHtml(lineage.title || "Related Work Lineage")}</h2>
          <p class="section-note">${escapeHtml(lineage.positioning_note || "No positioning note yet.")}</p>
        </div>
        <dl class="lineage-summary-facts">
          <div><dt>routes</dt><dd>${routes.length}</dd></div>
          <div><dt>papers</dt><dd>${papers.length}</dd></div>
          <div><dt>edges</dt><dd>${edges.length}</dd></div>
          <div><dt>status</dt><dd>${escapeHtml(lineage.status || "candidate")}</dd></div>
        </dl>
      </div>
      ${renderLineageLanes(routes, papers)}
      ${renderLineageEdges(edges)}
      ${renderLineagePaperTable(papers)}
      <footer class="lineage-boundary-note">
        Dashboard is read-only. This map is not Project Understanding Graph truth and does not create D* events.
      </footer>
    </section>
  `;
}

function renderLineageLanes(routes, papers) {
  if (!routes.length) return `<div class="empty-state">No routes yet.</div>`;
  return `
    <div class="lineage-lanes" aria-label="Related work technical lanes">
      ${routes.map((route) => {
        const routePapers = papers
          .filter((paper) => paper.route === route.id)
          .sort((a, b) => String(a.year || "").localeCompare(String(b.year || "")) || String(a.month || "").localeCompare(String(b.month || "")) || String(a.title || "").localeCompare(String(b.title || "")));
        return `
          <section class="lineage-lane">
            <header>
              <span>${escapeHtml(route.review_status || "candidate")}</span>
              <h3>${escapeHtml(route.label || route.id)}</h3>
              <p>${escapeHtml(route.description || "No route description yet.")}</p>
            </header>
            <div class="lineage-paper-track">
              ${routePapers.map((paper) => renderLineagePaperNode(paper)).join("") || `<div class="empty-state">No papers in this route.</div>`}
            </div>
          </section>
        `;
      }).join("")}
    </div>
  `;
}

function renderLineagePaperNode(paper) {
  const roles = Array.isArray(paper.roles) ? paper.roles : [];
  return `
    <article class="lineage-paper-node">
      <span>${escapeHtml([paper.year, paper.month].filter(Boolean).join("."))}</span>
      <h4>${escapeHtml(paper.title || paper.id)}</h4>
      <p>${escapeHtml(paper.summary || "No summary.")}</p>
      <div>${roles.map((role) => `<em>${escapeHtml(role)}</em>`).join("")}</div>
    </article>
  `;
}

function renderLineageEdges(edges) {
  return `
    <section class="lineage-edge-list">
      <h3>Explicit cross-route relationships</h3>
      ${edges.length ? `<ul>${edges.map((edge) => `
        <li><code>${escapeHtml(edge.source || "")}</code> ${escapeHtml(edge.relation || "")} <code>${escapeHtml(edge.target || "")}</code> · ${escapeHtml(edge.rationale || "")}</li>
      `).join("")}</ul>` : "<p>No explicit cross-route edges.</p>"}
    </section>
  `;
}

function renderLineagePaperTable(papers) {
  return `
    <div class="table-scroll">
      <table class="paper-library-table lineage-paper-table">
        <thead><tr><th>Paper</th><th>Year</th><th>Route</th><th>Roles</th><th>Status</th><th>Source</th></tr></thead>
        <tbody>
          ${papers.map((paper) => `
            <tr>
              <td>${escapeHtml(paper.title || paper.id)}</td>
              <td>${escapeHtml([paper.year, paper.month].filter(Boolean).join("."))}</td>
              <td>${escapeHtml(paper.route || "")}</td>
              <td>${escapeHtml(Array.isArray(paper.roles) ? paper.roles.join(", ") : "")}</td>
              <td>${escapeHtml(paper.review_status || "candidate")}</td>
              <td>${paper.source_url ? `<a href="${escapeAttr(paper.source_url)}" target="_blank" rel="noreferrer">source</a>` : ""}</td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  `;
}
```

5. Update `renderPage`:

```javascript
  else if (state.page === "lineage") renderLineagePage();
```

- [ ] **Step 5: Add CSS**

Append to `dashboard/styles.css`:

```css
.lineage-map-shell {
  display: grid;
  gap: 18px;
}

.lineage-summary-facts {
  display: grid;
  grid-template-columns: repeat(4, minmax(80px, 1fr));
  gap: 8px;
}

.lineage-summary-facts div {
  border: 1px solid var(--color-border-secondary);
  border-radius: 6px;
  padding: 8px;
}

.lineage-lanes {
  display: grid;
  gap: 12px;
}

.lineage-lane {
  display: grid;
  grid-template-columns: minmax(180px, 260px) 1fr;
  gap: 14px;
  border-top: 1px solid var(--color-border-secondary);
  padding-top: 14px;
}

.lineage-lane header span {
  display: inline-block;
  font-size: 11px;
  color: var(--color-text-tertiary);
  margin-bottom: 4px;
}

.lineage-lane header h3 {
  margin: 0 0 6px;
}

.lineage-lane header p {
  margin: 0;
  color: var(--color-text-secondary);
}

.lineage-paper-track {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 10px;
}

.lineage-paper-node {
  min-height: 132px;
  border: 1px solid var(--color-border-secondary);
  border-radius: 6px;
  padding: 10px;
  background: var(--color-background-primary);
}

.lineage-paper-node span {
  display: block;
  font-size: 11px;
  color: var(--color-text-tertiary);
  margin-bottom: 4px;
}

.lineage-paper-node h4 {
  margin: 0 0 6px;
  font-size: 15px;
}

.lineage-paper-node p {
  margin: 0 0 8px;
  color: var(--color-text-secondary);
}

.lineage-paper-node em {
  display: inline-block;
  margin: 0 4px 4px 0;
  font-size: 11px;
  font-style: normal;
  color: var(--color-text-secondary);
}

.lineage-edge-list {
  border-top: 1px solid var(--color-border-secondary);
  padding-top: 14px;
}

.lineage-boundary-note {
  color: var(--color-text-tertiary);
  font-size: 12px;
}

@media (max-width: 760px) {
  .lineage-lane {
    grid-template-columns: 1fr;
  }

  .lineage-summary-facts {
    grid-template-columns: repeat(2, minmax(80px, 1fr));
  }
}
```

- [ ] **Step 6: Run dashboard static tests**

Run:

```bash
python3 -m unittest tests.test_related_work_lineage_dashboard -v
```

Expected: PASS.

- [ ] **Step 7: Run browser smoke check**

Create a temporary workspace with a lineage map, build dashboard index, start the dashboard server, and inspect `dashboard/lineage.html` with a browser.

Minimum manual command sequence:

```bash
tmpdir="$(mktemp -d)"
python3 tools/research_pilot_init.py "$tmpdir" --no-git
python3 tools/project_shell_cli.py create --repo "$tmpdir" --project DemoProject --title "Demo Project" --direction "vision world models" --json
python3 tools/related_work_lineage_cli.py create --repo "$tmpdir" --project DemoProject --round vision-world-model-baselines --title "Vision World Model Related Work Lineage" --direction "vision world models" --baseline-paper "DreamerV3" --json
python3 tools/build_dashboard_index.py --repo "$tmpdir"
```

Expected:

- `.dashboard/index.json` includes `lineage_maps`.
- `dashboard/lineage.html?project=DemoProject` renders empty lanes without JavaScript errors.

- [ ] **Step 8: Commit**

```bash
git add dashboard/lineage.html dashboard/app.js dashboard/styles.css tests/test_related_work_lineage_dashboard.py
git commit -m "Add related work lineage dashboard page"
```

## Task 5: Docs And End-To-End Verification

**Files:**

- Modify: `README.md`
- Modify: `docs/guides/dashboard.md`
- Modify: `docs/guides/core-workflows.md`
- Modify: `tools/README.md`

- [ ] **Step 1: Update tools README**

Modify the table in `tools/README.md` to add:

```markdown
| lineage | `related_work_lineage_cli.py` | Create, validate, and summarize paper-only related-work lineage artifacts. |
```

- [ ] **Step 2: Update core workflows guide**

Add a section to `docs/guides/core-workflows.md` after Project Status:

```markdown
## Related Work Lineage

Use when a project needs a paper-only technical route map before or alongside Project Understanding Graph work.

Create a lineage skeleton:

```bash
python3 tools/related_work_lineage_cli.py create --repo "$WORKSPACE" --project "$PROJECT" --round "$ROUND" --title "$TITLE" --direction "$DIRECTION" --baseline-paper "$BASELINE" --json
```

Validate and render:

```bash
python3 tools/related_work_lineage_cli.py validate --path "$WORKSPACE/wiki/projects/$PROJECT/literature-rounds/$ROUND/related-work-lineage.json" --json
python3 tools/related_work_lineage_cli.py render-summary --path "$WORKSPACE/wiki/projects/$PROJECT/literature-rounds/$ROUND/related-work-lineage.json" --json
```

The artifact is not graph truth and does not create D* events.
```

- [ ] **Step 3: Update dashboard guide**

Add to `docs/guides/dashboard.md` under read sources:

```markdown
- related-work lineage artifacts under `wiki/projects/<Project>/literature-rounds/<Round>/related-work-lineage.json`.
```

Add page note:

```markdown
The `lineage.html` page shows paper-only related-work technical lanes. It is read-only and does not write Project Understanding Graph truth.
```

- [ ] **Step 4: Update README included capabilities**

Add bullets under "What Is Included":

```markdown
- Paper-only related-work lineage workflow for project-scoped technical route maps.
- Related-work lineage dashboard view over generated read models.
```

- [ ] **Step 5: Run full targeted test suite**

Run:

```bash
python3 -m unittest tests.test_related_work_lineage_cli tests.test_dashboard_public tests.test_related_work_lineage_dashboard tests.test_plugin_commands tests.test_plugin_health -v
```

Expected: PASS.

- [ ] **Step 6: Run release check if fast enough**

Run:

```bash
scripts/release_check.sh
```

Expected: PASS. If it fails from unrelated existing failures, capture exact failing command and output in the final implementation report.

- [ ] **Step 7: Commit docs**

```bash
git add README.md docs/guides/dashboard.md docs/guides/core-workflows.md tools/README.md
git commit -m "Document related work lineage workflow"
```

## Final Verification

Run:

```bash
git status --short
python3 -m unittest tests.test_related_work_lineage_cli tests.test_dashboard_public tests.test_related_work_lineage_dashboard tests.test_plugin_commands tests.test_plugin_health -v
```

Expected:

- working tree clean except intentional uncommitted user changes;
- targeted tests pass.

If frontend files changed, also run the temporary workspace dashboard smoke from Task 4 and inspect `dashboard/lineage.html?project=DemoProject`.

## Self-Review Checklist

- PRD requirement "nodes only paper" maps to Task 1 validation and Task 4 renderer.
- PRD requirement "coarse direction first narrows route/anchor" maps to Task 3 skill and workflow.
- PRD requirement "no Project Understanding Graph dependency" maps to Task 3 workflow and Task 1 template.
- PRD requirement "no D*" maps to Task 3 workflow, Task 4 boundary note, and docs.
- PRD requirement "dashboard read-only" maps to Task 4 renderer and no POST/API changes.
- PRD requirement "max 20 papers" maps to Task 1 validation.
- PRD storage-path alignment maps to this plan's Storage-Path Alignment section.

## Execution Handoff

Plan complete. Use either:

1. Subagent-Driven: dispatch a fresh worker per task and review between tasks.
2. Inline Execution: execute tasks in this session using checkpoints.
