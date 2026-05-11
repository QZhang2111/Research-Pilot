#!/usr/bin/env python3
"""Human-gated graph delta operations for Research Pilot workspaces."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from tools.build_graph_db import main as build_db_main
from tools.build_graph_snapshot import main as build_snapshot_main
from tools.graph_store import (
    graph_event_paths,
    graph_id_for_project,
    project_ref,
    read_jsonl,
    relpath,
    stable_json,
    utc_now,
)


SUPPORTED_PATCH_OPS = {"add_node", "update_node", "add_link", "update_link"}
SUPPORTED_NODE_UPDATE_FIELDS = {
    "text",
    "status",
    "lifecycle_status",
    "confidence",
    "human_review",
    "metadata",
    "supersedes",
    "superseded_by",
    "derived_from",
}
DECISION_TO_EVENT = {
    "accept": "delta.accepted",
    "accepted": "delta.accepted",
    "reject": "delta.rejected",
    "rejected": "delta.rejected",
    "park": "delta.parked",
    "parked": "delta.parked",
    "revise": "delta.revised",
    "revised": "delta.revised",
}
DECISION_TO_LIFECYCLE = {
    "accept": "accepted",
    "accepted": "accepted",
    "reject": "rejected",
    "rejected": "rejected",
    "park": "parked",
    "parked": "parked",
    "revise": "revised",
    "revised": "revised",
}


def default_graph_db_path(root: Path) -> Path:
    return root / "wiki" / "graphs" / "graph.db"


def project_event_path(root: Path, project_id: str) -> Path:
    return root / "wiki" / "graphs" / "events" / "projects" / f"{project_id}.jsonl"


def project_snapshot_path(root: Path, project_id: str) -> Path:
    return root / "wiki" / "graphs" / "snapshots" / "projects" / f"{project_id}.graph.json"


def local_id_from_graph_ref(ref: str) -> str:
    return str(ref or "").rsplit(":", 1)[-1]


def normalize_project_ref(project_id: str, ref: str) -> str:
    value = str(ref or "")
    if value.startswith(("project:", "paper:", "program:")):
        return value
    return project_ref(project_id, value)


def load_delta_file(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("delta file must contain a JSON object")
    return payload.get("delta") if isinstance(payload.get("delta"), dict) else payload


def source_refs_for_node(conn: sqlite3.Connection, node_id: str) -> List[str]:
    rows = conn.execute("select source_ref from node_sources where node_id = ? order by position", (node_id,)).fetchall()
    return [str(row[0]) for row in rows]


def node_payload_from_row(conn: sqlite3.Connection, row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "node_id": row["node_id"],
        "local_id": row["local_id"],
        "node_type": row["node_type"],
        "text": row["text"],
        "scope": row["scope"],
        "project_id": row["project_id"],
        "paper_id": row["paper_id"],
        "status": row["status"],
        "lifecycle_status": row["lifecycle_status"],
        "confidence": row["confidence"],
        "human_review": row["human_review"],
        "source_refs": source_refs_for_node(conn, row["node_id"]),
        "supersedes": json.loads(row["supersedes_json"] or "[]"),
        "superseded_by": json.loads(row["superseded_by_json"] or "[]"),
        "derived_from": json.loads(row["derived_from_json"] or "[]"),
        "metadata": json.loads(row["metadata_json"] or "{}"),
    }


def fetch_node(conn: sqlite3.Connection, node_id: str) -> Optional[Dict[str, Any]]:
    row = conn.execute("select * from nodes where node_id = ?", (node_id,)).fetchone()
    return node_payload_from_row(conn, row) if row else None


def fetch_link(conn: sqlite3.Connection, link_id: str) -> Optional[Dict[str, Any]]:
    row = conn.execute("select payload_json from links where link_id = ?", (link_id,)).fetchone()
    return json.loads(row["payload_json"] or "{}") if row else None


def validate_delta_shape(project_id: str, delta: Dict[str, Any], errors: List[str]) -> None:
    if not project_id:
        errors.append("missing project")
    if not delta:
        errors.append("missing delta")
        return
    for field in ["local_id", "operation_type", "evolution_type", "epistemic_effect", "summary", "patch_ops"]:
        value = delta.get(field)
        if field not in delta or value is None or value == "" or value == []:
            errors.append(f"missing delta.{field}")
    if "patch_ops" in delta and not isinstance(delta["patch_ops"], list):
        errors.append("delta.patch_ops must be a list")


def empty_preview() -> Dict[str, List[Dict[str, Any]]]:
    return {
        "added_nodes": [],
        "updated_nodes": [],
        "retired_nodes": [],
        "added_links": [],
        "updated_links": [],
        "retired_links": [],
    }


def values_match(left: Any, right: Any) -> bool:
    if isinstance(left, list) or isinstance(right, list):
        return list(left or []) == list(right or [])
    if isinstance(left, dict) or isinstance(right, dict):
        return dict(left or {}) == dict(right or {})
    return str(left or "") == str(right or "")


def dry_run_graph_delta(root: Path, project_id: str, delta: Dict[str, Any]) -> Dict[str, Any]:
    root = root.resolve()
    errors: List[str] = []
    warnings: List[str] = []
    preview = empty_preview()
    validate_delta_shape(project_id, delta, errors)
    if errors:
        return {"valid": False, "summary": "Delta payload is invalid.", "preview": preview, "warnings": warnings, "errors": errors}

    db = default_graph_db_path(root)
    if not db.exists():
        errors.append(f"graph database not found: {relpath(db, root)}")
        return {"valid": False, "summary": "Graph database is missing.", "preview": preview, "warnings": warnings, "errors": errors}

    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    try:
        graph_row = conn.execute("select graph_id from graphs where graph_id = ?", (graph_id_for_project(project_id),)).fetchone()
        if not graph_row:
            errors.append(f"project graph not found: {graph_id_for_project(project_id)}")
            return {"valid": False, "summary": "Project graph is missing.", "preview": preview, "warnings": warnings, "errors": errors}
        for index, patch_op in enumerate(delta.get("patch_ops") or []):
            if not isinstance(patch_op, dict):
                errors.append(f"patch_ops[{index}] must be an object")
                continue
            op = str(patch_op.get("op") or "")
            if op not in SUPPORTED_PATCH_OPS:
                errors.append(f"unsupported patch op: {op}")
                continue
            if op == "update_node":
                preview_update_node(conn, project_id, patch_op, preview, errors)
            elif op == "add_node":
                preview_add_node(conn, project_id, patch_op, preview, errors)
            elif op == "update_link":
                preview_update_link(conn, project_id, patch_op, preview, errors)
            elif op == "add_link":
                preview_add_link(conn, project_id, patch_op, preview, errors, warnings)
    finally:
        conn.close()

    valid = not errors
    count = sum(len(items) for items in preview.values())
    return {
        "valid": valid,
        "summary": f"{count} patch op{'s' if count != 1 else ''} previewed." if valid else "Delta dry-run failed.",
        "preview": preview,
        "warnings": warnings,
        "errors": errors,
    }


def preview_update_node(conn: sqlite3.Connection, project_id: str, patch_op: Dict[str, Any], preview: Dict[str, List[Dict[str, Any]]], errors: List[str]) -> None:
    node_id = normalize_project_ref(project_id, str(patch_op.get("node_id") or ""))
    node = fetch_node(conn, node_id)
    if not node:
        errors.append(f"node not found: {node_id}")
        return
    field = str(patch_op.get("field") or "")
    if field not in SUPPORTED_NODE_UPDATE_FIELDS:
        errors.append(f"unsupported node field: {field}")
        return
    before = patch_op.get("before")
    if not values_match(node.get(field), before):
        errors.append(f"before value mismatch for {node_id}")
        return
    after = patch_op.get("after")
    if values_match(after, before):
        errors.append(f"no-op update for {node_id}")
        return
    preview["updated_nodes"].append({"id": node["local_id"], "node_id": node_id, "field": field, "before": before, "after": after})


def preview_add_node(conn: sqlite3.Connection, project_id: str, patch_op: Dict[str, Any], preview: Dict[str, List[Dict[str, Any]]], errors: List[str]) -> None:
    node = patch_op.get("node") if isinstance(patch_op.get("node"), dict) else {}
    node_id = normalize_project_ref(project_id, str(node.get("node_id") or node.get("local_id") or ""))
    if fetch_node(conn, node_id):
        errors.append(f"node id collision: {node_id}")
        return
    for field in ["local_id", "node_type", "text"]:
        if not node.get(field):
            errors.append(f"missing node.{field}")
    if errors:
        return
    preview["added_nodes"].append({"id": node["local_id"], "node_id": node_id, "kind": node["node_type"], "text": node["text"]})


def preview_update_link(conn: sqlite3.Connection, project_id: str, patch_op: Dict[str, Any], preview: Dict[str, List[Dict[str, Any]]], errors: List[str]) -> None:
    link_id = normalize_project_ref(project_id, str(patch_op.get("link_id") or ""))
    link = fetch_link(conn, link_id)
    if not link:
        errors.append(f"link not found: {link_id}")
        return
    if str(patch_op.get("field") or "") != "relation":
        errors.append(f"unsupported link field: {patch_op.get('field')}")
        return
    before = str(patch_op.get("before") or "")
    if str(link.get("relation") or "") != before:
        errors.append(f"before value mismatch for {link_id}")
        return
    after = str(patch_op.get("after") or "")
    if after == before:
        errors.append(f"no-op update for {link_id}")
        return
    preview["updated_links"].append({"id": link.get("local_id") or local_id_from_graph_ref(link_id), "link_id": link_id, "field": "relation", "before": before, "after": after})


def preview_add_link(conn: sqlite3.Connection, project_id: str, patch_op: Dict[str, Any], preview: Dict[str, List[Dict[str, Any]]], errors: List[str], warnings: List[str]) -> None:
    link = patch_op.get("link") if isinstance(patch_op.get("link"), dict) else {}
    link_id = normalize_project_ref(project_id, str(link.get("link_id") or link.get("local_id") or ""))
    if fetch_link(conn, link_id):
        errors.append(f"link id collision: {link_id}")
        return
    from_nodes = [normalize_project_ref(project_id, ref) for ref in link.get("from_nodes", [])]
    to_nodes = [normalize_project_ref(project_id, ref) for ref in link.get("to_nodes", [])]
    if not to_nodes:
        errors.append(f"link has no target: {link_id}")
    for ref in from_nodes + to_nodes:
        if not fetch_node(conn, ref):
            errors.append(f"link endpoint not found: {ref}")
    if link.get("relation") in {"supports", "challenges"} and not link.get("warrant_nodes") and not link.get("inline_warrant"):
        warnings.append(f"{link_id} {link.get('relation')} link has no warrant")
    if errors:
        return
    preview["added_links"].append({"id": link.get("local_id"), "link_id": link_id, "relation": link.get("relation"), "from_nodes": from_nodes, "to_nodes": to_nodes})


def before_after_from_patch_ops(patch_ops: Sequence[Dict[str, Any]]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    before: Dict[str, Any] = {}
    after: Dict[str, Any] = {}
    for patch_op in patch_ops:
        op = str(patch_op.get("op") or "")
        if op == "update_node":
            local_id = local_id_from_graph_ref(str(patch_op.get("node_id") or ""))
            field = str(patch_op.get("field") or "")
            before[local_id] = {field: patch_op.get("before")}
            after[local_id] = {field: patch_op.get("after")}
        elif op == "add_node":
            node = patch_op.get("node") if isinstance(patch_op.get("node"), dict) else {}
            local_id = str(node.get("local_id") or local_id_from_graph_ref(str(node.get("node_id") or "")))
            before[local_id] = None
            after[local_id] = node
        elif op == "update_link":
            local_id = local_id_from_graph_ref(str(patch_op.get("link_id") or ""))
            field = str(patch_op.get("field") or "")
            before[local_id] = {field: patch_op.get("before")}
            after[local_id] = {field: patch_op.get("after")}
        elif op == "add_link":
            link = patch_op.get("link") if isinstance(patch_op.get("link"), dict) else {}
            local_id = str(link.get("local_id") or local_id_from_graph_ref(str(link.get("link_id") or "")))
            before[local_id] = None
            after[local_id] = link
    return before, after


def normalized_delta_payload(project_id: str, delta: Dict[str, Any], lifecycle: str, created_at: str, decision_note: str = "") -> Dict[str, Any]:
    local_id = local_id_from_graph_ref(str(delta.get("delta_id") or delta.get("local_id") or ""))
    before, after = before_after_from_patch_ops(delta.get("patch_ops") or [])
    return {
        "delta_id": normalize_project_ref(project_id, local_id),
        "local_id": local_id,
        "source_type": str(delta.get("source_type") or ""),
        "source_graph_id": str(delta.get("source_graph_id") or ""),
        "source_dossier": str(delta.get("source_dossier") or ""),
        "source_refs": list(delta.get("source_refs") or []),
        "operation": list(delta.get("operation") or [str(delta.get("operation_type") or "")]),
        "operation_type": str(delta.get("operation_type") or ""),
        "evolution_type": str(delta.get("evolution_type") or ""),
        "epistemic_effect": str(delta.get("epistemic_effect") or ""),
        "summary": str(delta.get("summary") or ""),
        "source_paper_nodes": list(delta.get("source_paper_nodes") or []),
        "affected_nodes": [normalize_project_ref(project_id, ref) for ref in delta.get("affected_nodes", [])],
        "affected_links": [normalize_project_ref(project_id, ref) for ref in delta.get("affected_links", [])],
        "patch_ops": list(delta.get("patch_ops") or []),
        "before": dict(delta.get("before") or before),
        "after": dict(delta.get("after") or after),
        "rationale": str(delta.get("rationale") or delta.get("summary") or ""),
        "caused_by": list(delta.get("caused_by") or []),
        "supersedes": list(delta.get("supersedes") or []),
        "confidence": str(delta.get("confidence") or "medium"),
        "status": lifecycle,
        "lifecycle_status": lifecycle,
        "decision": "pending" if lifecycle == "proposed" else lifecycle,
        "decision_note": decision_note,
        "created_at": created_at,
        "decided_at": created_at if lifecycle != "proposed" else "",
        "human_review": str(delta.get("human_review") or "pending"),
    }


def next_event_id(project_id: str, created_at: str, index: int) -> str:
    return f"{created_at}-{project_id}-delta-{index:06d}"


def make_graph_event(project_id: str, event_type: str, payload: Dict[str, Any], created_at: str, actor: str, provenance: Sequence[str], index: int, human_review: str = "pending") -> Dict[str, Any]:
    return {
        "schema_version": "graph-event-v1",
        "event_id": next_event_id(project_id, created_at, index),
        "event_type": event_type,
        "created_at": created_at,
        "actor": actor,
        "graph_id": graph_id_for_project(project_id),
        "scope": "project",
        "payload": payload,
        "provenance": list(provenance),
        "human_review": human_review,
    }


def append_events(path: Path, events: Sequence[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for event in events:
            handle.write(stable_json(event) + "\n")


def existing_event_local_ids(root: Path, project_id: str) -> set[str]:
    path = project_event_path(root, project_id)
    ids: set[str] = set()
    for event in read_jsonl(path):
        payload = event.get("payload") or {}
        local_id = str(payload.get("local_id") or "")
        if local_id:
            ids.add(local_id)
    return ids


def rebuild_generated_graph_indexes(root: Path, project_id: str) -> Dict[str, Any]:
    build_db_main(["--repo", str(root), "--project", project_id])
    build_snapshot_main(["--repo", str(root), "--project", project_id])
    return {
        "graph_db": relpath(default_graph_db_path(root), root),
        "graph_snapshot": relpath(project_snapshot_path(root, project_id), root),
    }


def register_graph_delta(root: Path, project_id: str, delta: Dict[str, Any], actor: str = "agent", decision_note: str = "") -> Dict[str, Any]:
    root = root.resolve()
    dry_run = dry_run_graph_delta(root, project_id, delta)
    if not dry_run.get("valid"):
        return {"valid": False, "registered": False, "dry_run": dry_run, "errors": dry_run["errors"], "warnings": dry_run["warnings"]}
    local_id = local_id_from_graph_ref(str(delta.get("delta_id") or delta.get("local_id") or ""))
    if local_id in existing_event_local_ids(root, project_id):
        return {"valid": False, "registered": False, "errors": ["delta already registered"], "warnings": [], "delta_id": local_id}
    created_at = utc_now()
    event_path = project_event_path(root, project_id)
    existing_count = len(read_jsonl(event_path)) if event_path.exists() else 0
    payload = normalized_delta_payload(project_id, delta, "proposed", created_at, decision_note=decision_note)
    event = make_graph_event(project_id, "delta.proposed", payload, created_at, actor, payload.get("source_refs", []), existing_count + 1, payload["human_review"])
    append_events(event_path, [event])
    rebuild = rebuild_generated_graph_indexes(root, project_id)
    return {"valid": True, "registered": True, "delta_id": local_id, "event_path": relpath(event_path, root), "dry_run": dry_run, "rebuild": rebuild}


def load_delta_payload_from_db(root: Path, project_id: str, local_id: str) -> Optional[Dict[str, Any]]:
    db = default_graph_db_path(root)
    if not db.exists():
        return None
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute("select payload_json from deltas where graph_id = ? and delta_id = ?", (graph_id_for_project(project_id), normalize_project_ref(project_id, local_id))).fetchone()
        return json.loads(row["payload_json"] or "{}") if row else None
    finally:
        conn.close()


def content_event_payloads_from_patch_ops(root: Path, project_id: str, patch_ops: Sequence[Dict[str, Any]]) -> List[Tuple[str, Dict[str, Any]]]:
    conn = sqlite3.connect(default_graph_db_path(root))
    conn.row_factory = sqlite3.Row
    payloads: List[Tuple[str, Dict[str, Any]]] = []
    try:
        for patch_op in patch_ops:
            op = str(patch_op.get("op") or "")
            if op == "update_node":
                node_id = normalize_project_ref(project_id, str(patch_op.get("node_id") or ""))
                node = fetch_node(conn, node_id)
                if node:
                    node[str(patch_op.get("field"))] = patch_op.get("after")
                    payloads.append(("node.updated", node))
            elif op == "add_node":
                node = dict(patch_op.get("node") or {})
                node["node_id"] = normalize_project_ref(project_id, str(node.get("node_id") or node.get("local_id") or ""))
                node.setdefault("scope", "project")
                node.setdefault("project_id", project_id)
                node.setdefault("paper_id", None)
                node.setdefault("status", "active")
                node.setdefault("lifecycle_status", "active")
                node.setdefault("confidence", "unknown")
                node.setdefault("human_review", "pending")
                node.setdefault("source_refs", [])
                node.setdefault("supersedes", [])
                node.setdefault("superseded_by", [])
                node.setdefault("derived_from", [])
                node.setdefault("metadata", {})
                payloads.append(("node.created", node))
            elif op == "update_link":
                link_id = normalize_project_ref(project_id, str(patch_op.get("link_id") or ""))
                link = fetch_link(conn, link_id)
                if link:
                    link[str(patch_op.get("field"))] = str(patch_op.get("after") or "")
                    payloads.append(("link.updated", link))
            elif op == "add_link":
                link = dict(patch_op.get("link") or {})
                link["link_id"] = normalize_project_ref(project_id, str(link.get("link_id") or link.get("local_id") or ""))
                link.setdefault("confidence", "unknown")
                link.setdefault("human_review", "pending")
                link.setdefault("source_refs", [])
                payloads.append(("link.created", link))
    finally:
        conn.close()
    return payloads


def decide_graph_delta(root: Path, project_id: str, local_id: str, decision: str, actor: str = "human", decision_note: str = "") -> Dict[str, Any]:
    root = root.resolve()
    decision_key = decision.strip().lower()
    if decision_key not in DECISION_TO_EVENT:
        return {"valid": False, "applied": False, "errors": [f"unsupported decision: {decision}"], "warnings": []}
    delta = load_delta_payload_from_db(root, project_id, local_id)
    if not delta:
        return {"valid": False, "applied": False, "errors": [f"delta not found: {local_id}"], "warnings": []}
    if decision_key in {"accept", "accepted"}:
        delta["human_review"] = "approved"
    elif decision_key in {"reject", "rejected"}:
        delta["human_review"] = "rejected"
    dry_run = dry_run_graph_delta(root, project_id, delta)
    if decision_key in {"accept", "accepted"} and not dry_run.get("valid"):
        return {"valid": False, "applied": False, "dry_run": dry_run, "errors": dry_run["errors"], "warnings": dry_run["warnings"]}

    lifecycle = DECISION_TO_LIFECYCLE[decision_key]
    created_at = utc_now()
    payload = normalized_delta_payload(project_id, delta, lifecycle, created_at, decision_note=decision_note)
    event_path = project_event_path(root, project_id)
    existing_count = len(read_jsonl(event_path)) if event_path.exists() else 0
    events = [
        make_graph_event(project_id, DECISION_TO_EVENT[decision_key], payload, created_at, actor, payload.get("source_refs", []), existing_count + 1, payload["human_review"])
    ]
    if lifecycle == "accepted":
        provenance = [f"delta:{payload['delta_id']}"]
        for offset, (event_type, content_payload) in enumerate(content_event_payloads_from_patch_ops(root, project_id, payload.get("patch_ops") or []), start=existing_count + 2):
            events.append(make_graph_event(project_id, event_type, content_payload, created_at, actor, provenance, offset, str(content_payload.get("human_review") or "pending")))
    append_events(event_path, events)
    rebuild = rebuild_generated_graph_indexes(root, project_id)
    return {
        "valid": True,
        "applied": True,
        "decision": lifecycle,
        "delta_id": payload["delta_id"],
        "events_appended": len(events),
        "event_path": relpath(event_path, root),
        "dry_run": dry_run,
        "rebuild": rebuild,
    }
