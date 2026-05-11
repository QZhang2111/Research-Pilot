#!/usr/bin/env python3
"""Self-contained graph-event store helpers for Research Pilot workspaces."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


EVENT_TYPES = {
    "node.created",
    "node.updated",
    "node.retired",
    "node.superseded",
    "link.created",
    "link.updated",
    "link.retired",
    "link.superseded",
    "delta.proposed",
    "delta.registered",
    "delta.accepted",
    "delta.integrated",
    "delta.partially_integrated",
    "delta.rejected",
    "delta.parked",
    "delta.revised",
    "delta.superseded",
    "human.reviewed",
    "source.attached",
    "graph.imported_from_markdown",
}
SCOPES = {"paper", "project", "program"}
ACTORS = {"agent", "human", "system"}
HUMAN_REVIEW_VALUES = {"pending", "approved", "rejected"}
NODE_TYPES = {"Question", "Claim", "Evidence", "Warrant", "Limitation"}
LINK_TYPES = {"ReasoningLink", "TranslationLink"}
DELTA_STATUS_TO_LIFECYCLE = {
    "proposed": "proposed",
    "registered": "proposed",
    "accepted": "accepted",
    "integrated": "accepted",
    "partially_integrated": "accepted",
    "rejected": "rejected",
    "parked": "parked",
    "revised": "revised",
    "superseded": "revised",
}
OPEN_DELTA_LIFECYCLES = {"proposed", "parked", "revised"}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def graph_id_for_project(project_id: str) -> str:
    return f"project:{project_id}"


def project_ref(project_id: str, local_id: str) -> str:
    value = str(local_id or "")
    if value.startswith(("project:", "paper:", "program:")):
        return value
    return f"{graph_id_for_project(project_id)}:{value}"


def relpath(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, events: Sequence[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(stable_json(event) + "\n" for event in events), encoding="utf-8")


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    if not path.exists():
        return events
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_number}: expected JSON object")
        events.append(value)
    return events


def canonical_delta_lifecycle(value: str) -> str:
    return DELTA_STATUS_TO_LIFECYCLE.get(str(value or "").strip().lower(), "proposed")


def delta_decision_from_lifecycle(lifecycle_status: str) -> str:
    if lifecycle_status == "proposed":
        return "pending"
    return lifecycle_status


def infer_delta_evolution_type(delta: Dict[str, Any]) -> str:
    text = " ".join(str(item).lower() for item in (delta.get("operation") or []))
    text = f"{text} {str(delta.get('operation_type') or '').lower()} {str(delta.get('epistemic_effect') or '').lower()} {str(delta.get('summary') or '').lower()}"
    if "split" in text or "decompose" in text:
        return "split" if "split" in text else "decompose"
    if "merge" in text or "consolidate" in text:
        return "merge"
    if "promote" in text or "add_claim" in text or "add_question" in text:
        return "promote"
    if "demote" in text or "weaken" in text or "change_confidence" in text:
        return "demote"
    if "reframe" in text:
        return "reframe"
    if "retire" in text:
        return "retire"
    if "qualify_translation" in text or "update_link" in text or "refine_link" in text:
        return "clarify_translation"
    if "add_link" in text:
        return "connect"
    if "bound" in text or "limit" in text or "add_boundary" in text or "add_limitation" in text:
        return "bound"
    if "support" in text or "strengthen" in text:
        return "strengthen"
    if "refine" in text or "update_node" in text:
        return "refine"
    if "add_node" in text or "add_evidence" in text or "add_warrant" in text:
        return "add"
    return "clarify"


def validate_event(event: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    required = ["schema_version", "event_id", "event_type", "created_at", "actor", "graph_id", "scope", "payload", "provenance", "human_review"]
    for field in required:
        if field not in event:
            errors.append(f"missing {field}")
    if errors:
        return errors
    if event["schema_version"] != "graph-event-v1":
        errors.append("schema_version must be graph-event-v1")
    if not str(event["event_id"]):
        errors.append("event_id must be non-empty")
    if event["event_type"] not in EVENT_TYPES:
        errors.append(f"unsupported event_type: {event['event_type']}")
    if event["actor"] not in ACTORS:
        errors.append(f"unsupported actor: {event['actor']}")
    if event["scope"] not in SCOPES:
        errors.append(f"unsupported scope: {event['scope']}")
    if not isinstance(event["payload"], dict):
        errors.append("payload must be an object")
    if not isinstance(event["provenance"], list) or not all(isinstance(item, str) for item in event["provenance"]):
        errors.append("provenance must be a string array")
    if event["human_review"] not in HUMAN_REVIEW_VALUES:
        errors.append(f"unsupported human_review: {event['human_review']}")

    event_type = str(event["event_type"])
    payload = event["payload"] if isinstance(event["payload"], dict) else {}
    if event_type.startswith("node."):
        errors.extend(validate_node_payload(payload))
    elif event_type.startswith("link."):
        errors.extend(validate_link_payload(payload))
    elif event_type.startswith("delta."):
        errors.extend(validate_delta_payload(payload))
    elif event_type == "human.reviewed":
        for field in ["target_type", "target_id", "review"]:
            if not payload.get(field):
                errors.append(f"payload missing {field}")
    return errors


def _require_string(payload: Dict[str, Any], field: str, errors: List[str]) -> None:
    if not isinstance(payload.get(field), str) or not payload.get(field):
        errors.append(f"payload.{field} must be a non-empty string")


def _require_list(payload: Dict[str, Any], field: str, errors: List[str]) -> None:
    if not isinstance(payload.get(field), list):
        errors.append(f"payload.{field} must be an array")


def validate_node_payload(payload: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    for field in ["node_id", "local_id", "node_type", "text", "scope", "status", "confidence", "human_review"]:
        _require_string(payload, field, errors)
    _require_list(payload, "source_refs", errors)
    if payload.get("node_type") and payload.get("node_type") not in NODE_TYPES:
        errors.append(f"unsupported node_type: {payload.get('node_type')}")
    if payload.get("human_review") and payload.get("human_review") not in HUMAN_REVIEW_VALUES:
        errors.append(f"unsupported payload.human_review: {payload.get('human_review')}")
    return errors


def validate_link_payload(payload: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    for field in ["link_id", "local_id", "link_type", "relation", "confidence", "human_review"]:
        _require_string(payload, field, errors)
    for field in ["from_nodes", "to_nodes", "source_refs"]:
        _require_list(payload, field, errors)
    if payload.get("link_type") and payload.get("link_type") not in LINK_TYPES:
        errors.append(f"unsupported link_type: {payload.get('link_type')}")
    if payload.get("human_review") and payload.get("human_review") not in HUMAN_REVIEW_VALUES:
        errors.append(f"unsupported payload.human_review: {payload.get('human_review')}")
    return errors


def validate_delta_payload(payload: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    for field in ["delta_id", "local_id", "operation_type", "evolution_type", "epistemic_effect", "status", "human_review", "summary"]:
        _require_string(payload, field, errors)
    for field in ["operation", "source_paper_nodes", "affected_nodes", "affected_links", "patch_ops"]:
        _require_list(payload, field, errors)
    if payload.get("human_review") and payload.get("human_review") not in HUMAN_REVIEW_VALUES:
        errors.append(f"unsupported payload.human_review: {payload.get('human_review')}")
    return errors


def validate_event_files(paths: Sequence[Path]) -> Dict[str, Any]:
    errors: List[Dict[str, Any]] = []
    event_ids: set[str] = set()
    event_count = 0
    for path in paths:
        for index, event in enumerate(read_jsonl(path), start=1):
            event_count += 1
            for error in validate_event(event):
                errors.append({"path": str(path), "line": index, "event_id": event.get("event_id", ""), "error": error})
            event_id = str(event.get("event_id") or "")
            if event_id in event_ids:
                errors.append({"path": str(path), "line": index, "event_id": event_id, "error": "duplicate event_id"})
            if event_id:
                event_ids.add(event_id)
    return {"valid": not errors, "event_count": event_count, "errors": errors}


def build_snapshot_from_events(events: Sequence[Dict[str, Any]], generated_at: Optional[str] = None) -> Dict[str, Any]:
    graph_id = ""
    nodes: Dict[str, Dict[str, Any]] = {}
    links: Dict[str, Dict[str, Any]] = {}
    deltas: Dict[str, Dict[str, Any]] = {}

    for event in events:
        graph_id = graph_id or str(event.get("graph_id") or "")
        event_type = str(event.get("event_type") or "")
        payload = event.get("payload") or {}
        if event_type in {"node.created", "node.updated"}:
            nodes[payload["node_id"]] = payload
        elif event_type in {"node.retired", "node.superseded"}:
            nodes.pop(payload.get("node_id", ""), None)
        elif event_type in {"link.created", "link.updated"}:
            links[payload["link_id"]] = payload
        elif event_type in {"link.retired", "link.superseded"}:
            links.pop(payload.get("link_id", ""), None)
        elif event_type.startswith("delta."):
            delta = dict(payload)
            lifecycle_status = canonical_delta_lifecycle(str(delta.get("lifecycle_status") or delta.get("status") or event_type.split(".", 1)[-1]))
            delta["lifecycle_status"] = lifecycle_status
            delta.setdefault("event_type", event_type)
            delta.setdefault("created_at", event.get("created_at") or "")
            delta.setdefault("evolution_type", infer_delta_evolution_type(delta))
            delta.setdefault("decision", delta_decision_from_lifecycle(lifecycle_status))
            if lifecycle_status != "proposed":
                delta.setdefault("decided_at", event.get("created_at") or "")
            deltas[delta["delta_id"]] = delta
        elif event_type == "human.reviewed":
            apply_human_review(nodes, links, deltas, payload)

    return {
        "schema_version": "graph-snapshot-v1",
        "graph_id": graph_id,
        "generated_at": generated_at or utc_now(),
        "nodes": list(nodes.values()),
        "links": list(links.values()),
        "deltas": list(deltas.values()),
        "event_count": len(events),
    }


def apply_human_review(
    nodes: Dict[str, Dict[str, Any]],
    links: Dict[str, Dict[str, Any]],
    deltas: Dict[str, Dict[str, Any]],
    payload: Dict[str, Any],
) -> None:
    target_type = payload.get("target_type")
    target_id = payload.get("target_id")
    review = payload.get("review")
    if target_type == "node" and target_id in nodes:
        nodes[target_id]["human_review"] = review
    elif target_type == "link" and target_id in links:
        links[target_id]["human_review"] = review
    elif target_type == "delta" and target_id in deltas:
        deltas[target_id]["human_review"] = review


def build_snapshot_from_event_files(paths: Sequence[Path], generated_at: Optional[str] = None) -> Dict[str, Any]:
    events: List[Dict[str, Any]] = []
    for path in paths:
        events.extend(read_jsonl(path))
    return build_snapshot_from_events(events, generated_at=generated_at)


def graph_scope_from_id(graph_id: str) -> str:
    return graph_id.split(":", 1)[0] if ":" in graph_id else ""


def graph_project_and_paper_ids(graph_id: str) -> Tuple[Optional[str], Optional[str]]:
    if graph_id.startswith("project:"):
        return graph_id.split("project:", 1)[1], None
    if graph_id.startswith("paper:"):
        suffix = graph_id.split("paper:", 1)[1]
        if "/" in suffix:
            project_id, paper_id = suffix.split("/", 1)
            return project_id or None, paper_id or None
        return None, suffix or None
    return None, None


def create_graph_db_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        drop table if exists delta_affected_links;
        drop table if exists delta_affected_nodes;
        drop table if exists deltas;
        drop table if exists link_sources;
        drop table if exists link_project_limitations;
        drop table if exists link_project_warrants;
        drop table if exists link_limitations;
        drop table if exists link_warrants;
        drop table if exists link_to_nodes;
        drop table if exists link_from_nodes;
        drop table if exists links;
        drop table if exists node_sources;
        drop table if exists nodes;
        drop table if exists events;
        drop table if exists graphs;

        create table graphs(
          graph_id text primary key,
          scope text not null,
          project_id text,
          paper_id text,
          title text,
          updated_at text
        );

        create table events(
          event_id text primary key,
          event_type text not null,
          graph_id text not null,
          created_at text not null,
          actor text not null,
          scope text not null,
          payload_json text not null,
          provenance_json text not null,
          human_review text not null
        );

        create table nodes(
          node_id text primary key,
          graph_id text not null,
          local_id text not null,
          node_type text not null,
          text text not null,
          scope text not null,
          project_id text,
          paper_id text,
          status text not null,
          lifecycle_status text not null,
          confidence text not null,
          human_review text not null,
          supersedes_json text not null,
          superseded_by_json text not null,
          derived_from_json text not null,
          metadata_json text not null
        );

        create table node_sources(node_id text not null, source_ref text not null, position integer not null, primary key(node_id, position));

        create table links(
          link_id text primary key,
          graph_id text not null,
          local_id text not null,
          link_type text not null,
          relation text not null,
          to_node text,
          confidence text not null,
          human_review text not null,
          payload_json text not null
        );

        create table link_from_nodes(link_id text not null, node_id text not null, position integer not null, primary key(link_id, position));
        create table link_to_nodes(link_id text not null, node_id text not null, position integer not null, primary key(link_id, position));
        create table link_warrants(link_id text not null, node_id text not null, position integer not null, primary key(link_id, position));
        create table link_limitations(link_id text not null, node_id text not null, position integer not null, primary key(link_id, position));
        create table link_project_warrants(link_id text not null, node_id text not null, position integer not null, primary key(link_id, position));
        create table link_project_limitations(link_id text not null, node_id text not null, position integer not null, primary key(link_id, position));
        create table link_sources(link_id text not null, source_ref text not null, position integer not null, primary key(link_id, position));

        create table deltas(
          delta_id text primary key,
          graph_id text not null,
          local_id text not null,
          source_graph_id text,
          source_dossier text,
          event_type text not null,
          created_at text not null,
          status text not null,
          lifecycle_status text not null,
          decision text not null,
          decision_note text,
          decided_at text,
          human_review text not null,
          summary text not null,
          evolution_type text not null,
          rationale text not null,
          before_json text not null,
          after_json text not null,
          caused_by_json text not null,
          supersedes_json text not null,
          payload_json text not null,
          operation_json text not null,
          source_paper_nodes_json text not null
        );

        create table delta_affected_nodes(delta_id text not null, node_id text not null, position integer not null, primary key(delta_id, position));
        create table delta_affected_links(delta_id text not null, link_id text not null, position integer not null, primary key(delta_id, position));

        create index idx_events_graph on events(graph_id);
        create index idx_nodes_graph_type on nodes(graph_id, node_type);
        create index idx_nodes_review on nodes(human_review);
        create index idx_links_target_relation on links(to_node, relation);
        create index idx_link_from_nodes_node on link_from_nodes(node_id);
        create index idx_deltas_status on deltas(status);
        create index idx_deltas_lifecycle on deltas(lifecycle_status);
        create index idx_deltas_source_dossier on deltas(source_dossier);
        """
    )


def insert_position_rows(conn: sqlite3.Connection, table: str, first_column: str, first_value: str, second_column: str, values: Sequence[str]) -> None:
    conn.executemany(
        f"insert into {table}({first_column}, {second_column}, position) values (?, ?, ?)",
        [(first_value, value, index) for index, value in enumerate(values)],
    )


def events_by_graph(events: Sequence[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for event in events:
        graph_id = str(event.get("graph_id") or "")
        if graph_id:
            grouped.setdefault(graph_id, []).append(event)
    return grouped


def insert_graph_rows(conn: sqlite3.Connection, grouped_events: Dict[str, List[Dict[str, Any]]]) -> None:
    rows: List[Tuple[str, str, Optional[str], Optional[str], str, str]] = []
    for graph_id, graph_events in grouped_events.items():
        scope = str(graph_events[0].get("scope") or graph_scope_from_id(graph_id))
        project_id, paper_id = graph_project_and_paper_ids(graph_id)
        updated_at = max(str(event.get("created_at") or "") for event in graph_events)
        rows.append((graph_id, scope, project_id, paper_id, "", updated_at))
    conn.executemany("insert into graphs(graph_id, scope, project_id, paper_id, title, updated_at) values (?, ?, ?, ?, ?, ?)", rows)


def insert_event_rows(conn: sqlite3.Connection, events: Sequence[Dict[str, Any]]) -> None:
    conn.executemany(
        """
        insert into events(event_id, event_type, graph_id, created_at, actor, scope, payload_json, provenance_json, human_review)
        values (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                event["event_id"],
                event["event_type"],
                event["graph_id"],
                event["created_at"],
                event["actor"],
                event["scope"],
                stable_json(event.get("payload") or {}),
                stable_json(event.get("provenance") or []),
                event.get("human_review") or "pending",
            )
            for event in events
        ],
    )


def insert_node_rows(conn: sqlite3.Connection, graph_id: str, nodes: Sequence[Dict[str, Any]]) -> None:
    for node in nodes:
        conn.execute(
            """
            insert into nodes(
              node_id, graph_id, local_id, node_type, text, scope, project_id, paper_id,
              status, lifecycle_status, confidence, human_review,
              supersedes_json, superseded_by_json, derived_from_json, metadata_json
            )
            values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                node["node_id"],
                graph_id,
                node.get("local_id") or "",
                node.get("node_type") or "",
                node.get("text") or "",
                node.get("scope") or "",
                node.get("project_id"),
                node.get("paper_id"),
                node.get("status") or "",
                node.get("lifecycle_status") or "active",
                node.get("confidence") or "unknown",
                node.get("human_review") or "pending",
                stable_json(node.get("supersedes") or []),
                stable_json(node.get("superseded_by") or []),
                stable_json(node.get("derived_from") or []),
                stable_json(node.get("metadata") or {}),
            ),
        )
        insert_position_rows(conn, "node_sources", "node_id", node["node_id"], "source_ref", node.get("source_refs", []))


def insert_link_rows(conn: sqlite3.Connection, graph_id: str, links: Sequence[Dict[str, Any]]) -> None:
    for link in links:
        to_nodes = list(link.get("to_nodes") or [])
        conn.execute(
            """
            insert into links(link_id, graph_id, local_id, link_type, relation, to_node, confidence, human_review, payload_json)
            values (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                link["link_id"],
                graph_id,
                link.get("local_id") or "",
                link.get("link_type") or "",
                link.get("relation") or "",
                to_nodes[0] if to_nodes else None,
                link.get("confidence") or "unknown",
                link.get("human_review") or "pending",
                stable_json(link),
            ),
        )
        insert_position_rows(conn, "link_from_nodes", "link_id", link["link_id"], "node_id", link.get("from_nodes", []))
        insert_position_rows(conn, "link_to_nodes", "link_id", link["link_id"], "node_id", to_nodes)
        insert_position_rows(conn, "link_warrants", "link_id", link["link_id"], "node_id", link.get("warrant_nodes", []))
        insert_position_rows(conn, "link_limitations", "link_id", link["link_id"], "node_id", link.get("limitation_nodes", []))
        insert_position_rows(conn, "link_project_warrants", "link_id", link["link_id"], "node_id", link.get("project_warrant_nodes", []))
        insert_position_rows(conn, "link_project_limitations", "link_id", link["link_id"], "node_id", link.get("project_limitation_nodes", []))
        insert_position_rows(conn, "link_sources", "link_id", link["link_id"], "source_ref", link.get("source_refs", []))


def insert_delta_rows(conn: sqlite3.Connection, graph_id: str, deltas: Sequence[Dict[str, Any]]) -> None:
    for delta in deltas:
        lifecycle_status = canonical_delta_lifecycle(str(delta.get("lifecycle_status") or delta.get("status") or "proposed"))
        conn.execute(
            """
            insert into deltas(
              delta_id, graph_id, local_id, source_graph_id, source_dossier, event_type, created_at,
              status, lifecycle_status, decision, decision_note, decided_at, human_review, summary,
              evolution_type, rationale, before_json, after_json, caused_by_json, supersedes_json,
              payload_json, operation_json, source_paper_nodes_json
            )
            values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                delta["delta_id"],
                graph_id,
                delta.get("local_id") or "",
                delta.get("source_graph_id") or "",
                delta.get("source_dossier") or "",
                delta.get("event_type") or "",
                delta.get("created_at") or "",
                delta.get("status") or "",
                lifecycle_status,
                delta.get("decision") or delta_decision_from_lifecycle(lifecycle_status),
                delta.get("decision_note") or "",
                delta.get("decided_at") or "",
                delta.get("human_review") or "pending",
                delta.get("summary") or "",
                delta.get("evolution_type") or infer_delta_evolution_type(delta),
                delta.get("rationale") or "",
                stable_json(delta.get("before") or {}),
                stable_json(delta.get("after") or {}),
                stable_json(delta.get("caused_by") or []),
                stable_json(delta.get("supersedes") or []),
                stable_json(delta),
                stable_json(delta.get("operation") or []),
                stable_json(delta.get("source_paper_nodes") or []),
            ),
        )
        insert_position_rows(conn, "delta_affected_nodes", "delta_id", delta["delta_id"], "node_id", delta.get("affected_nodes", []))
        insert_position_rows(conn, "delta_affected_links", "delta_id", delta["delta_id"], "link_id", delta.get("affected_links", []))


def build_graph_db_from_events(events: Sequence[Dict[str, Any]], db_path: Path) -> Dict[str, int]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    grouped = events_by_graph(events)
    conn = sqlite3.connect(db_path)
    try:
        create_graph_db_schema(conn)
        insert_graph_rows(conn, grouped)
        insert_event_rows(conn, events)
        for graph_id, graph_events in grouped.items():
            snapshot = build_snapshot_from_events(graph_events)
            insert_node_rows(conn, graph_id, snapshot["nodes"])
            insert_link_rows(conn, graph_id, snapshot["links"])
            insert_delta_rows(conn, graph_id, snapshot["deltas"])
        conn.commit()
        stats = {
            "graphs": conn.execute("select count(*) from graphs").fetchone()[0],
            "events": conn.execute("select count(*) from events").fetchone()[0],
            "nodes": conn.execute("select count(*) from nodes").fetchone()[0],
            "links": conn.execute("select count(*) from links").fetchone()[0],
            "deltas": conn.execute("select count(*) from deltas").fetchone()[0],
        }
    finally:
        conn.close()
    return stats


def build_graph_db_from_event_files(paths: Sequence[Path], db_path: Path) -> Dict[str, int]:
    events: List[Dict[str, Any]] = []
    for path in paths:
        events.extend(read_jsonl(path))
    return build_graph_db_from_events(events, db_path)


def graph_event_paths(root: Path, project_id: Optional[str] = None) -> List[Path]:
    if project_id:
        path = root / "wiki" / "graphs" / "events" / "projects" / f"{project_id}.jsonl"
        return [path] if path.exists() else []
    return sorted((root / "wiki" / "graphs" / "events").glob("**/*.jsonl"))
