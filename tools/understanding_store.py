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


def valid_project_id(project_id: str) -> bool:
    if not project_id or project_id in {".", ".."}:
        return False
    if "/" in project_id or "\\" in project_id:
        return False
    return project_id == Path(project_id).name


def require_valid_project_id(project_id: str) -> None:
    if not valid_project_id(project_id):
        raise ValueError("invalid project_id")


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
    require_valid_project_id(project_id)
    return Path(root) / "wiki" / "understanding" / "events" / f"{project_id}.jsonl"


def project_understanding_path(root: Path, project_id: str) -> Path:
    require_valid_project_id(project_id)
    return Path(root) / "wiki" / "understanding" / "project-understanding" / f"{project_id}.json"


def _require_string(update: Dict[str, Any], field: str, errors: List[str]) -> None:
    if not isinstance(update.get(field), str) or not update.get(field):
        errors.append(f"missing {field}")


def _require_list(update: Dict[str, Any], field: str, errors: List[str]) -> None:
    if not isinstance(update.get(field), list):
        errors.append(f"{field} must be an array")


def _optional_object_array(update: Dict[str, Any], field: str, errors: List[str]) -> List[Dict[str, Any]]:
    if field not in update:
        return []
    value = update.get(field)
    if not isinstance(value, list):
        errors.append(f"{field} must be an array")
        return []
    items: List[Dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            errors.append(f"{field} items must be objects")
            continue
        items.append(item)
    return items


def _require_item_string(item: Dict[str, Any], field: str, label: str, errors: List[str]) -> None:
    if not isinstance(item.get(field), str) or not item.get(field):
        errors.append(f"{label}.{field} must be non-empty")


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
    if not valid_project_id(update["project_id"]):
        errors.append("invalid project_id")
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

    for source in _optional_object_array(update, "new_sources", errors):
        _require_item_string(source, "source_id", "source", errors)
        if source.get("type") not in SOURCE_TYPES:
            errors.append(f"unsupported source.type: {source.get('type')}")
        if source.get("status") not in SOURCE_STATUSES:
            errors.append(f"unsupported source.status: {source.get('status')}")
        if not source.get("title"):
            errors.append("source.title must be non-empty")

    for claim in _optional_object_array(update, "changed_claims", errors):
        _require_item_string(claim, "claim_id", "changed_claim", errors)
        _require_item_string(claim, "text", "changed_claim", errors)

    for item in _optional_object_array(update, "new_evidence", errors):
        _require_item_string(item, "evidence_id", "evidence", errors)
        _require_item_string(item, "text", "evidence", errors)

    for gap in _optional_object_array(update, "new_gaps", errors):
        _require_item_string(gap, "gap_id", "gap", errors)
        _require_item_string(gap, "text", "gap", errors)

    for status_change in _optional_object_array(update, "status_changes", errors):
        _require_item_string(status_change, "target_id", "status_change", errors)
        _require_item_string(status_change, "status", "status_change", errors)
        if status_change.get("status") and status_change.get("status") not in CONFIDENCE_STATUSES:
            errors.append(f"unsupported status_change.status: {status_change.get('status')}")

    for move in _optional_object_array(update, "next_moves", errors):
        _require_item_string(move, "move_id", "next_move", errors)
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
    if not valid_project_id(project_id):
        return {"valid": False, "appended": False, "errors": ["invalid project_id"], "warnings": []}
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


def _dict_items(value: Any) -> List[Dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def build_project_understanding(root: Path, project_id: str, generated_at: str | None = None) -> Dict[str, Any]:
    root = Path(root).resolve()
    require_valid_project_id(project_id)
    updates = read_understanding_updates(root, project_id)
    sources: Dict[str, Dict[str, Any]] = {}
    claims: Dict[str, Dict[str, Any]] = {}
    evidence: Dict[str, Dict[str, Any]] = {}
    gaps: Dict[str, Dict[str, Any]] = {}
    next_moves: Dict[str, Dict[str, Any]] = {}
    recent_changes: List[Dict[str, Any]] = []

    for update in updates:
        update_id = str(update.get("update_id") or "")
        for source in _dict_items(update.get("new_sources")):
            _upsert_by_id(sources, dict(source), "source_id", update_id)
        for claim in _dict_items(update.get("changed_claims")):
            _upsert_by_id(claims, dict(claim), "claim_id", update_id)
        for item in _dict_items(update.get("new_evidence")):
            _upsert_by_id(evidence, dict(item), "evidence_id", update_id)
        for gap in _dict_items(update.get("new_gaps")):
            _upsert_by_id(gaps, dict(gap), "gap_id", update_id)
        for move in _dict_items(update.get("next_moves")):
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
