#!/usr/bin/env python3
"""Semantic understanding-event helpers for Research Pilot workspaces."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


SCHEMA_VERSION = "understanding-update-v1"
PROJECTION_SCHEMA_VERSION = "project-understanding-v1"
ACTORS = {"agent", "human", "system"}
TASK_KINDS = {
    "read_source",
    "skim_source",
    "summarize_source",
    "compare_sources",
    "find_related_work",
    "check_claim",
    "review_experiment",
    "discuss_direction",
    "identify_gap",
    "plan_next_work",
    "draft_research_text",
    "manual_note",
}
SOURCE_TYPES = {"pdf", "url", "arxiv", "doi", "markdown_note", "experiment_result", "zotero_item", "manual"}
SOURCE_STATUSES = {"seen", "skimmed", "read", "used"}
CONFIDENCE_STATUSES = {"agent-inferred", "source-backed", "user-confirmed", "contested", "weak", "stale"}
NEXT_MOVE_TYPES = {"read", "search", "compare", "test", "revise", "write", "clarify"}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def relpath(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def understanding_event_path(root: Path, project_id: str) -> Path:
    return Path(root) / "wiki" / "understanding" / "events" / f"{project_id}.jsonl"


def project_understanding_path(root: Path, project_id: str) -> Path:
    return Path(root) / "wiki" / "understanding" / "project-understanding" / f"{project_id}.json"


def _require_string(update: Dict[str, Any], field: str, errors: List[str]) -> None:
    if not isinstance(update.get(field), str) or not update.get(field):
        errors.append(f"missing {field}")


def _require_list(update: Dict[str, Any], field: str, errors: List[str]) -> None:
    if not isinstance(update.get(field), list):
        errors.append(f"{field} must be an array")


def validate_understanding_update(update: Dict[str, Any]) -> Dict[str, Any]:
    errors: List[str] = []
    for field in ["schema_version", "update_id", "project_id", "created_at", "actor", "recent_change_summary", "confidence"]:
        _require_string(update, field, errors)
    for field in ["source_refs"]:
        _require_list(update, field, errors)
    if not isinstance(update.get("task"), dict):
        errors.append("missing task")
    if errors:
        return {"valid": False, "errors": errors}

    if update["schema_version"] != SCHEMA_VERSION:
        errors.append("schema_version must be understanding-update-v1")
    if update["actor"] not in ACTORS:
        errors.append(f"unsupported actor: {update['actor']}")
    if update["confidence"] not in CONFIDENCE_STATUSES:
        errors.append(f"unsupported confidence: {update['confidence']}")

    task = update["task"]
    if not isinstance(task.get("kind"), str) or not task.get("kind"):
        errors.append("task.kind must be a non-empty string")
    elif task["kind"] not in TASK_KINDS:
        errors.append(f"unsupported task.kind: {task['kind']}")
    if not isinstance(task.get("summary"), str) or not task.get("summary"):
        errors.append("task.summary must be a non-empty string")

    for source in update.get("new_sources") or []:
        if not isinstance(source, dict):
            errors.append("new_sources items must be objects")
            continue
        if not source.get("source_id"):
            errors.append("source.source_id must be non-empty")
        if source.get("type") not in SOURCE_TYPES:
            errors.append(f"unsupported source.type: {source.get('type')}")
        if source.get("status") not in SOURCE_STATUSES:
            errors.append(f"unsupported source.status: {source.get('status')}")
        if not source.get("title"):
            errors.append("source.title must be non-empty")

    for move in update.get("next_moves") or []:
        if not isinstance(move, dict):
            errors.append("next_moves items must be objects")
            continue
        if not move.get("move_id"):
            errors.append("next_move.move_id must be non-empty")
        if move.get("type") not in NEXT_MOVE_TYPES:
            errors.append(f"unsupported next_move.type: {move.get('type')}")
        if not move.get("text"):
            errors.append("next_move.text must be non-empty")

    return {"valid": not errors, "errors": errors}


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    records: List[Dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_number}: expected JSON object")
        records.append(value)
    return records


def read_understanding_updates(root: Path, project_id: str) -> List[Dict[str, Any]]:
    return read_jsonl(understanding_event_path(root, project_id))


def append_understanding_update(root: Path, project_id: str, update: Dict[str, Any]) -> Dict[str, Any]:
    root = Path(root).resolve()
    validation = validate_understanding_update(update)
    if not validation["valid"]:
        return {"valid": False, "appended": False, "errors": validation["errors"], "warnings": []}
    if update["project_id"] != project_id:
        return {"valid": False, "appended": False, "errors": ["project_id mismatch"], "warnings": []}

    path = understanding_event_path(root, project_id)
    existing = read_jsonl(path)
    update_id = str(update["update_id"])
    if update_id in {str(item.get("update_id") or "") for item in existing}:
        return {"valid": False, "appended": False, "errors": [f"duplicate update_id: {update_id}"], "warnings": []}

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(stable_json(update) + "\n")
    return {"valid": True, "appended": True, "update_id": update_id, "event_path": relpath(path, root), "errors": [], "warnings": []}


def _upsert_by_id(items: Dict[str, Dict[str, Any]], item: Dict[str, Any], key: str, update_id: str) -> None:
    value = str(item.get(key) or "")
    if not value:
        return
    merged = dict(items.get(value) or {})
    merged.update(item)
    merged["last_update_id"] = update_id
    items[value] = merged


def build_project_understanding(root: Path, project_id: str, generated_at: str | None = None) -> Dict[str, Any]:
    root = Path(root).resolve()
    updates = read_understanding_updates(root, project_id)
    sources: Dict[str, Dict[str, Any]] = {}
    claims: Dict[str, Dict[str, Any]] = {}
    evidence: Dict[str, Dict[str, Any]] = {}
    gaps: Dict[str, Dict[str, Any]] = {}
    next_moves: Dict[str, Dict[str, Any]] = {}
    recent_changes: List[Dict[str, Any]] = []

    for update in updates:
        update_id = str(update.get("update_id") or "")
        for source in update.get("new_sources") or []:
            _upsert_by_id(sources, dict(source), "source_id", update_id)
        for claim in update.get("changed_claims") or []:
            _upsert_by_id(claims, dict(claim), "claim_id", update_id)
        for item in update.get("new_evidence") or []:
            _upsert_by_id(evidence, dict(item), "evidence_id", update_id)
        for gap in update.get("new_gaps") or []:
            _upsert_by_id(gaps, dict(gap), "gap_id", update_id)
        for move in update.get("next_moves") or []:
            _upsert_by_id(next_moves, dict(move), "move_id", update_id)
        recent_changes.append(
            {
                "update_id": update_id,
                "created_at": str(update.get("created_at") or ""),
                "task": update.get("task") or {},
                "summary": str(update.get("recent_change_summary") or ""),
                "source_refs": list(update.get("source_refs") or []),
                "confidence": str(update.get("confidence") or ""),
            }
        )

    event_path = understanding_event_path(root, project_id)
    return {
        "schema_version": PROJECTION_SCHEMA_VERSION,
        "project_id": project_id,
        "generated_at": generated_at or utc_now(),
        "project_brief": {},
        "sources": list(sources.values()),
        "claims": list(claims.values()),
        "evidence": list(evidence.values()),
        "gaps": list(gaps.values()),
        "recent_changes": recent_changes,
        "next_moves": list(next_moves.values()),
        "inputs": [relpath(event_path, root)] if event_path.exists() else [],
    }


def write_project_understanding(root: Path, project_id: str, generated_at: str | None = None) -> Dict[str, Any]:
    root = Path(root).resolve()
    projection = build_project_understanding(root, project_id, generated_at=generated_at)
    output = project_understanding_path(root, project_id)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(projection, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"valid": True, "written": True, "path": relpath(output, root), "project_understanding": projection}
