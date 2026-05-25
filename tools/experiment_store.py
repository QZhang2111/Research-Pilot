#!/usr/bin/env python3
"""Read-only project experiment read model loader."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


SCHEMA_VERSION = "experiments-v1"
SOURCE_BOUNDARY = "project_experiments_read_model_not_graph_truth"
VALID_EXPERIMENT_STATUSES = {"planned", "ready", "running", "blocked", "completed", "superseded"}
VALID_RUN_STATUSES = {"not_started", "running", "completed", "failed", "inconclusive"}
VALID_EVIDENCE_TYPES = {
    "imported_paper_evidence",
    "local_experiment_result",
    "external_result",
    "replication_result",
}
SUMMARY_TEXT_FIELDS = {"strongest_current_evidence", "highest_priority_unresolved"}


def valid_project_id(project_id: str) -> bool:
    parts = Path(project_id).parts
    return bool(project_id) and len(parts) == 1 and not any(part in {"", ".", ".."} for part in parts)


def _list(value: Any) -> List[Dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item.copy() for item in value if isinstance(item, dict)]


def _normalize_status(record: Dict[str, Any], valid: set[str], default: str) -> Dict[str, Any]:
    status = str(record.get("status") or "").strip()
    record["status"] = status if status in valid else default
    return record


def _normalize_experiments(value: Any) -> List[Dict[str, Any]]:
    return [_normalize_status(item, VALID_EXPERIMENT_STATUSES, "planned") for item in _list(value)]


def _normalize_runs(value: Any) -> List[Dict[str, Any]]:
    runs = []
    for item in _list(value):
        _normalize_status(item, VALID_RUN_STATUSES, "not_started")
        evidence_type = str(item.get("evidence_type") or "").strip()
        item["evidence_type"] = evidence_type if evidence_type in VALID_EVIDENCE_TYPES else "local_experiment_result"
        runs.append(item)
    return runs


def _legacy_proposals(root: Path, project_id: str) -> Dict[str, Any]:
    proposal_dir = root / "wiki" / "projects" / project_id / "experiment-proposals"
    count = len(sorted(proposal_dir.glob("*.md"))) if proposal_dir.exists() else 0
    return {
        "count": count,
        "path": f"wiki/projects/{project_id}/experiment-proposals",
        "note": "Legacy markdown proposals are counted for migration context only.",
    }


def _summary(experiments: List[Dict[str, Any]], runs: List[Dict[str, Any]]) -> Dict[str, Any]:
    summary: Dict[str, Any] = {
        "total_experiments": len(experiments),
        "total_runs": len(runs),
        "completed_runs": sum(1 for run in runs if run.get("status") == "completed"),
    }
    for status in sorted(VALID_EXPERIMENT_STATUSES):
        summary[status] = sum(1 for experiment in experiments if experiment.get("status") == status)
    for status in sorted(VALID_RUN_STATUSES):
        summary[f"{status}_runs"] = sum(1 for run in runs if run.get("status") == status)
    for evidence_type in sorted(VALID_EVIDENCE_TYPES):
        summary[f"{evidence_type}_runs"] = sum(1 for run in runs if run.get("evidence_type") == evidence_type)
    summary["imported_evidence_runs"] = summary["imported_paper_evidence_runs"]
    summary["local_result_runs"] = summary["local_experiment_result_runs"]
    return summary


def _populate_summary(
    payload_summary: Any,
    experiments: List[Dict[str, Any]],
    runs: List[Dict[str, Any]],
) -> Dict[str, Any]:
    summary = _summary(experiments, runs)
    if isinstance(payload_summary, dict):
        for key in SUMMARY_TEXT_FIELDS:
            value = payload_summary.get(key)
            if isinstance(value, str) and value.strip():
                summary[key] = value
    return summary


def empty_project_experiments(project_id: str) -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "project_id": project_id,
        "source_boundary": SOURCE_BOUNDARY,
        "mutating": False,
        "summary": _summary([], []),
        "experiments": [],
        "runs": [],
        "next_moves": [],
        "legacy_proposals": {
            "count": 0,
            "path": f"wiki/projects/{project_id}/experiment-proposals",
            "note": "Legacy markdown proposals are counted for migration context only.",
        },
    }


def experiment_record_path(root: Path, project_id: str) -> Path:
    if not valid_project_id(project_id):
        raise ValueError(f"invalid project id: {project_id}")
    return root / "wiki" / "projects" / project_id / "experiments" / "experiments.json"


def build_project_experiments(root: Path, project_id: str) -> Dict[str, Any]:
    if not valid_project_id(project_id):
        raise ValueError(f"invalid project id: {project_id}")
    path = experiment_record_path(root, project_id)
    if not path.exists():
        model = empty_project_experiments(project_id)
        model["legacy_proposals"] = _legacy_proposals(root, project_id)
        return model
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("expected object")
    schema_version = str(payload.get("schema_version") or SCHEMA_VERSION)
    if schema_version != SCHEMA_VERSION:
        raise ValueError(f"unsupported schema_version: {schema_version}")
    experiments = _normalize_experiments(payload.get("experiments"))
    runs = _normalize_runs(payload.get("runs"))
    return {
        "schema_version": SCHEMA_VERSION,
        "project_id": project_id,
        "source_boundary": SOURCE_BOUNDARY,
        "mutating": False,
        "summary": _populate_summary(payload.get("summary"), experiments, runs),
        "experiments": experiments,
        "runs": runs,
        "next_moves": _list(payload.get("next_moves")),
        "legacy_proposals": _legacy_proposals(root, project_id),
    }
