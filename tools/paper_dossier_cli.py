#!/usr/bin/env python3
"""Create and validate project paper dossiers with delta JSON proposals."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional


DELTA_BLOCK_PATTERN = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)


def relpath(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def dossier_path(root: Path, project: str, paper: str) -> Path:
    return root / "wiki" / "projects" / project / "papers" / paper / "index.md"


def default_dossier_text(project: str, paper: str, title: str, source_ref: str) -> str:
    today = date.today().isoformat()
    return f"""---
title: "{title}"
type: paper
created: {today}
updated: {today}
project: {project}
paper_id: {paper}
source_refs: [{json.dumps(source_ref) if source_ref else ""}]
status: candidate
human_review: pending
---

# {title}

## Source Identity

- Paper id: `{paper}`
- Source refs: {source_ref or "not provided"}

## Deep Read Notes

Write claim, evidence, method, assumptions, limitations, and project relevance here.

## Project Relevance

Explain how this paper changes, supports, bounds, or challenges the project graph.

## Project Graph Delta Proposals

Add proposed graph deltas as fenced JSON objects. Each object should be compatible with `tools/graph_delta_cli.py`.

```json
{{
  "local_id": "D1",
  "operation": ["refine_node"],
  "operation_type": "update_node",
  "evolution_type": "refine",
  "epistemic_effect": "clarifies",
  "summary": "Replace this with the proposed project graph change.",
  "affected_nodes": [],
  "affected_links": [],
  "patch_ops": [],
  "source_type": "paper_dossier",
  "source_dossier": "wiki/projects/{project}/papers/{paper}/index.md",
  "source_refs": ["wiki/projects/{project}/papers/{paper}/index.md"],
  "source_paper_nodes": [],
  "human_review": "pending"
}}
```
"""


def create_dossier(root: Path, project: str, paper: str, title: str, source_ref: str, overwrite: bool) -> Dict[str, Any]:
    path = dossier_path(root, project, paper)
    if path.exists() and not overwrite:
        return {"valid": False, "created": False, "error": "dossier already exists", "path": relpath(path, root)}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(default_dossier_text(project, paper, title, source_ref), encoding="utf-8")
    return {"valid": True, "created": True, "path": relpath(path, root)}


def extract_delta_blocks(text: str) -> List[Dict[str, Any]]:
    deltas: List[Dict[str, Any]] = []
    for match in DELTA_BLOCK_PATTERN.finditer(text):
        try:
            payload = json.loads(match.group(1))
        except json.JSONDecodeError as exc:
            deltas.append({"valid": False, "error": f"invalid delta JSON: {exc}"})
            continue
        if not isinstance(payload, dict):
            deltas.append({"valid": False, "error": "delta block must be a JSON object"})
            continue
        missing = [field for field in ["local_id", "operation_type", "summary", "patch_ops"] if field not in payload]
        if missing:
            deltas.append({"valid": False, "error": f"delta block missing fields: {', '.join(missing)}", "delta": payload})
            continue
        deltas.append({"valid": True, "delta": payload})
    return deltas


def validate_dossier(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"valid": False, "error": "dossier not found", "path": str(path)}
    text = path.read_text(encoding="utf-8")
    errors: List[str] = []
    for section in ["## Source Identity", "## Deep Read Notes", "## Project Relevance", "## Project Graph Delta Proposals"]:
        if section not in text:
            errors.append(f"missing section: {section}")
    deltas = extract_delta_blocks(text)
    invalid = [item for item in deltas if not item.get("valid")]
    errors.extend(str(item.get("error")) for item in invalid)
    return {
        "valid": not errors,
        "path": str(path),
        "delta_count": len([item for item in deltas if item.get("valid")]),
        "errors": errors,
    }


def export_deltas(path: Path, output_dir: Path) -> Dict[str, Any]:
    validation = validate_dossier(path)
    if not validation["valid"]:
        return {"valid": False, "exported": [], "errors": validation["errors"]}
    output_dir.mkdir(parents=True, exist_ok=True)
    exported: List[str] = []
    for item in extract_delta_blocks(path.read_text(encoding="utf-8")):
        delta = item["delta"]
        local_id = str(delta["local_id"])
        output = output_dir / f"{local_id}.json"
        output.write_text(json.dumps(delta, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        exported.append(str(output))
    return {"valid": True, "exported": exported}


def print_result(result: Dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Create and validate paper dossiers.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create")
    create.add_argument("--repo", default=".")
    create.add_argument("--project", required=True)
    create.add_argument("--paper", required=True)
    create.add_argument("--title", required=True)
    create.add_argument("--source-ref", default="")
    create.add_argument("--overwrite", action="store_true")
    create.add_argument("--json", action="store_true")

    validate = subparsers.add_parser("validate")
    validate.add_argument("--dossier", required=True)
    validate.add_argument("--json", action="store_true")

    export = subparsers.add_parser("export-deltas")
    export.add_argument("--dossier", required=True)
    export.add_argument("--output-dir", required=True)
    export.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    if args.command == "create":
        result = create_dossier(Path(args.repo).resolve(), args.project, args.paper, args.title, args.source_ref, args.overwrite)
    elif args.command == "validate":
        result = validate_dossier(Path(args.dossier).resolve())
    else:
        result = export_deltas(Path(args.dossier).resolve(), Path(args.output_dir).resolve())
    print_result(result, bool(getattr(args, "json", False)))
    return 0 if result.get("valid") else 1


if __name__ == "__main__":
    raise SystemExit(main())
