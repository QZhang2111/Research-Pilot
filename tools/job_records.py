#!/usr/bin/env python3
"""Durable execution-state records for long-running Research Pilot jobs."""

from __future__ import annotations

import argparse
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

VALID_TYPES = {"paper_search", "deep_read", "evidence_synthesis", "experiment_proposal"}
VALID_STATUSES = {"queued", "running", "needs_review", "done", "failed"}
HUMAN_GATE = "required_before_graph_update"
TRUTH_BOUNDARY = "execution_state_only"


def now_string() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _id_timestamp(value: str) -> str:
    return value.replace("-", "").replace(":", "")


def _new_job_id(timestamp: str) -> str:
    return f"job-{_id_timestamp(timestamp)}-{uuid.uuid4().hex[:12]}"


def jobs_dir(root: Path) -> Path:
    return Path(root).expanduser().resolve() / ".research-pilot" / "jobs"


def validate_job_record(record: Dict[str, Any]) -> Dict[str, Any]:
    errors: List[str] = []
    if not isinstance(record.get("id"), str) or not record.get("id", "").strip():
        errors.append("id must be a non-empty string")
    if record.get("type") not in VALID_TYPES:
        errors.append(f"type must be one of {sorted(VALID_TYPES)}")
    if not isinstance(record.get("project"), str) or not record.get("project", "").strip():
        errors.append("project must be a non-empty string")
    if record.get("status") not in VALID_STATUSES:
        errors.append(f"status must be one of {sorted(VALID_STATUSES)}")
    if not isinstance(record.get("created_at"), str) or not record.get("created_at", "").strip():
        errors.append("created_at must be a non-empty string")
    if not isinstance(record.get("updated_at"), str) or not record.get("updated_at", "").strip():
        errors.append("updated_at must be a non-empty string")
    if record.get("owner") != "agent":
        errors.append("owner must be agent")
    if record.get("human_gate") != HUMAN_GATE:
        errors.append(f"human_gate must be {HUMAN_GATE}")
    if record.get("truth_boundary") != TRUTH_BOUNDARY:
        errors.append(f"truth_boundary must be {TRUTH_BOUNDARY}")
    if not isinstance(record.get("inputs"), dict):
        errors.append("inputs must be a dict")
    if not isinstance(record.get("artifacts"), list):
        errors.append("artifacts must be a list")
    if not isinstance(record.get("result_summary"), str):
        errors.append("result_summary must be a string")
    return {"valid": not errors, "errors": errors}


def create_job_record(
    root: Path,
    job_type: str,
    project: str,
    status: str,
    inputs: Optional[Dict[str, Any]] = None,
    artifacts: Optional[List[Any]] = None,
    result_summary: str = "",
) -> Dict[str, Any]:
    timestamp = now_string()
    directory = jobs_dir(root)
    directory.mkdir(parents=True, exist_ok=True)
    for _ in range(10):
        record = {
            "id": _new_job_id(timestamp),
            "type": job_type,
            "project": project,
            "status": status,
            "created_at": timestamp,
            "updated_at": timestamp,
            "owner": "agent",
            "human_gate": HUMAN_GATE,
            "truth_boundary": TRUTH_BOUNDARY,
            "inputs": {} if inputs is None else inputs,
            "artifacts": [] if artifacts is None else artifacts,
            "result_summary": result_summary,
        }
        validation = validate_job_record(record)
        if not validation["valid"]:
            raise ValueError("; ".join(validation["errors"]))
        path = directory / f"{record['id']}.json"
        try:
            with path.open("x", encoding="utf-8") as handle:
                json.dump(record, handle, ensure_ascii=False, indent=2, sort_keys=True)
                handle.write("\n")
            return record
        except FileExistsError:
            continue
    raise FileExistsError("could not create unique job record after 10 attempts")


def _relpath(path: Path, root: Path) -> str:
    resolved_root = Path(root).expanduser().resolve()
    try:
        return path.resolve().relative_to(resolved_root).as_posix()
    except ValueError:
        return str(path.resolve())


def list_job_records(root: Path) -> List[Dict[str, Any]]:
    directory = jobs_dir(root)
    if not directory.exists():
        return []
    records: List[Dict[str, Any]] = []
    for path in sorted(directory.glob("*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError, OSError):
            continue
        if not isinstance(record, dict):
            continue
        if not validate_job_record(record)["valid"]:
            continue
        if record["id"] != path.stem:
            continue
        record["path"] = _relpath(path, root)
        records.append(record)
    return records


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Manage durable Research Pilot job records.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List durable job records.")
    list_parser.add_argument("--repo", default=".", help="Repository root. Default: current directory.")
    list_parser.add_argument("--json", action="store_true", help="Print JSON output.")

    create_parser = subparsers.add_parser("create", help="Create durable job record.")
    create_parser.add_argument("--repo", default=".", help="Repository root. Default: current directory.")
    create_parser.add_argument("--json", action="store_true", help="Print JSON output.")
    create_parser.add_argument("--type", required=True, choices=sorted(VALID_TYPES), help="Job type.")
    create_parser.add_argument("--project", required=True, help="Project id.")
    create_parser.add_argument("--status", required=True, choices=sorted(VALID_STATUSES), help="Job status.")
    create_parser.add_argument("--summary", default="", help="Result summary.")

    args = parser.parse_args(argv)
    root = Path(args.repo)

    if args.command == "list":
        print(json.dumps(list_job_records(root), ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    record = create_job_record(
        root,
        job_type=args.type,
        project=args.project,
        status=args.status,
        result_summary=args.summary,
    )
    print(json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
