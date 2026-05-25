#!/usr/bin/env python3
"""Typed write service for Research Pilot local datasets."""

from __future__ import annotations

import uuid
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.research_dataset import connect_dataset, dataset_db_path, initialize_dataset, json_dumps, valid_project_id


class DatasetValidationError(ValueError):
    """Raised when a dataset update packet is invalid."""


NODE_TYPES = {"question", "claim", "evidence", "warrant", "limitation"}
SCOPES = {"paper", "project", "program"}
LINK_TYPES = {"reasoning", "translation"}
ENDPOINT_ROLES = {"from", "to", "warrant", "limitation", "project_warrant", "project_limitation"}
REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    "sources": ("source_id",),
    "understanding_nodes": ("node_id", "scope", "node_type", "text"),
    "understanding_links": ("link_id", "link_type", "relation"),
    "experiments": ("experiment_id", "title"),
    "experiment_runs": ("run_id", "experiment_id", "origin_type"),
    "experiment_metrics": ("metric_id", "run_id", "name", "value_text"),
    "experiment_artifacts": ("artifact_id", "run_id", "artifact_type", "locator"),
    "literature_lanes": ("lane_id", "title"),
    "literature_items": ("item_id",),
    "literature_relations": ("relation_id", "from_item_id", "to_item_id", "relation_type"),
    "project_positionings": ("positioning_id", "text"),
    "entity_links": ("from_entity_type", "from_entity_id", "to_entity_type", "to_entity_id", "relation_type"),
}


@dataclass(frozen=True)
class TableSpec:
    table: str
    pk: str
    columns: tuple[str, ...]
    mutable_columns: tuple[str, ...]
    defaults: dict[str, Any]
    json_columns: frozenset[str] = frozenset()


SPECS: dict[str, TableSpec] = {
    "project": TableSpec(
        table="projects",
        pk="project_id",
        columns=(
            "project_id",
            "slug",
            "title",
            "summary",
            "main_question",
            "working_hypothesis",
            "target_contribution",
            "stage",
            "status",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "confirmation",
            "metadata_json",
        ),
        mutable_columns=(
            "slug",
            "title",
            "summary",
            "main_question",
            "working_hypothesis",
            "target_contribution",
            "stage",
            "status",
            "updated_at",
            "updated_by",
            "confirmation",
            "metadata_json",
        ),
        defaults={
            "summary": "",
            "main_question": "",
            "working_hypothesis": "",
            "target_contribution": "",
            "stage": "idea",
            "status": "active",
            "confirmation": "unconfirmed",
            "metadata_json": {},
        },
        json_columns=frozenset({"metadata_json"}),
    ),
    "sources": TableSpec(
        table="sources",
        pk="source_id",
        columns=(
            "source_id",
            "project_id",
            "source_type",
            "title",
            "authors",
            "year",
            "locator",
            "doi",
            "arxiv_id",
            "url",
            "zotero_key",
            "attachment_locator_type",
            "attachment_locator",
            "reading_status",
            "reading_depth",
            "short_summary",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "confirmation",
            "metadata_json",
        ),
        mutable_columns=(
            "source_type",
            "title",
            "authors",
            "year",
            "locator",
            "doi",
            "arxiv_id",
            "url",
            "zotero_key",
            "attachment_locator_type",
            "attachment_locator",
            "reading_status",
            "reading_depth",
            "short_summary",
            "updated_at",
            "updated_by",
            "confirmation",
            "metadata_json",
        ),
        defaults={
            "source_type": "paper",
            "title": "",
            "authors": "",
            "year": "",
            "locator": "",
            "doi": "",
            "arxiv_id": "",
            "url": "",
            "zotero_key": "",
            "attachment_locator_type": "",
            "attachment_locator": "",
            "reading_status": "seen",
            "reading_depth": "metadata_only",
            "short_summary": "",
            "confirmation": "unconfirmed",
            "metadata_json": {},
        },
        json_columns=frozenset({"metadata_json"}),
    ),
    "understanding_nodes": TableSpec(
        table="understanding_nodes",
        pk="node_id",
        columns=(
            "node_id",
            "project_id",
            "scope",
            "source_id",
            "node_type",
            "text",
            "status",
            "confidence",
            "confirmation",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "source_refs_json",
            "metadata_json",
        ),
        mutable_columns=(
            "scope",
            "source_id",
            "node_type",
            "text",
            "status",
            "confidence",
            "confirmation",
            "updated_at",
            "updated_by",
            "source_refs_json",
            "metadata_json",
        ),
        defaults={
            "source_id": None,
            "text": "",
            "status": "active",
            "confidence": "unknown",
            "confirmation": "unconfirmed",
            "source_refs_json": [],
            "metadata_json": {},
        },
        json_columns=frozenset({"source_refs_json", "metadata_json"}),
    ),
    "understanding_links": TableSpec(
        table="understanding_links",
        pk="link_id",
        columns=(
            "link_id",
            "project_id",
            "scope",
            "link_type",
            "relation",
            "confidence",
            "confirmation",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "source_refs_json",
            "metadata_json",
        ),
        mutable_columns=(
            "scope",
            "link_type",
            "relation",
            "confidence",
            "confirmation",
            "updated_at",
            "updated_by",
            "source_refs_json",
            "metadata_json",
        ),
        defaults={
            "scope": "project",
            "relation": "",
            "confidence": "unknown",
            "confirmation": "unconfirmed",
            "source_refs_json": [],
            "metadata_json": {},
        },
        json_columns=frozenset({"source_refs_json", "metadata_json"}),
    ),
    "experiments": TableSpec(
        table="experiments",
        pk="experiment_id",
        columns=(
            "experiment_id",
            "project_id",
            "title",
            "question",
            "hypothesis",
            "experiment_type",
            "status",
            "protocol_summary",
            "benchmark_name",
            "dataset_name",
            "planned_at",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "confirmation",
            "metadata_json",
        ),
        mutable_columns=(
            "title",
            "question",
            "hypothesis",
            "experiment_type",
            "status",
            "protocol_summary",
            "benchmark_name",
            "dataset_name",
            "planned_at",
            "updated_at",
            "updated_by",
            "confirmation",
            "metadata_json",
        ),
        defaults={
            "title": "",
            "question": "",
            "hypothesis": "",
            "experiment_type": "benchmark_eval",
            "status": "planned",
            "protocol_summary": "",
            "benchmark_name": "",
            "dataset_name": "",
            "planned_at": "",
            "confirmation": "unconfirmed",
            "metadata_json": {},
        },
        json_columns=frozenset({"metadata_json"}),
    ),
    "experiment_runs": TableSpec(
        table="experiment_runs",
        pk="run_id",
        columns=(
            "run_id",
            "project_id",
            "experiment_id",
            "origin_type",
            "status",
            "method_name",
            "run_label",
            "source_id",
            "completed_at",
            "summary",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "confirmation",
            "metadata_json",
        ),
        mutable_columns=(
            "experiment_id",
            "origin_type",
            "status",
            "method_name",
            "run_label",
            "source_id",
            "completed_at",
            "summary",
            "updated_at",
            "updated_by",
            "confirmation",
            "metadata_json",
        ),
        defaults={
            "origin_type": "manual",
            "status": "not_started",
            "method_name": "",
            "run_label": "",
            "source_id": None,
            "completed_at": "",
            "summary": "",
            "confirmation": "unconfirmed",
            "metadata_json": {},
        },
        json_columns=frozenset({"metadata_json"}),
    ),
    "experiment_metrics": TableSpec(
        table="experiment_metrics",
        pk="metric_id",
        columns=(
            "metric_id",
            "project_id",
            "run_id",
            "name",
            "value_text",
            "value_numeric",
            "unit",
            "direction",
            "benchmark_name",
            "dataset_name",
            "split_name",
            "created_at",
            "metadata_json",
        ),
        mutable_columns=(
            "run_id",
            "name",
            "value_text",
            "value_numeric",
            "unit",
            "direction",
            "benchmark_name",
            "dataset_name",
            "split_name",
            "metadata_json",
        ),
        defaults={
            "name": "",
            "value_text": "",
            "value_numeric": None,
            "unit": "",
            "direction": "neutral",
            "benchmark_name": "",
            "dataset_name": "",
            "split_name": "",
            "metadata_json": {},
        },
        json_columns=frozenset({"metadata_json"}),
    ),
    "experiment_artifacts": TableSpec(
        table="experiment_artifacts",
        pk="artifact_id",
        columns=(
            "artifact_id",
            "project_id",
            "run_id",
            "artifact_type",
            "locator_type",
            "locator",
            "label",
            "description",
            "created_at",
            "metadata_json",
        ),
        mutable_columns=("run_id", "artifact_type", "locator_type", "locator", "label", "description", "metadata_json"),
        defaults={
            "artifact_type": "",
            "locator_type": "local_path",
            "locator": "",
            "label": "",
            "description": "",
            "metadata_json": {},
        },
        json_columns=frozenset({"metadata_json"}),
    ),
    "literature_lanes": TableSpec(
        table="literature_lanes",
        pk="lane_id",
        columns=("lane_id", "project_id", "title", "description", "status", "created_at", "updated_at", "metadata_json"),
        mutable_columns=("title", "description", "status", "updated_at", "metadata_json"),
        defaults={"title": "", "description": "", "status": "active", "metadata_json": {}},
        json_columns=frozenset({"metadata_json"}),
    ),
    "literature_items": TableSpec(
        table="literature_items",
        pk="item_id",
        columns=(
            "item_id",
            "project_id",
            "source_id",
            "lane_id",
            "role",
            "importance",
            "summary",
            "created_at",
            "updated_at",
            "metadata_json",
        ),
        mutable_columns=("source_id", "lane_id", "role", "importance", "summary", "updated_at", "metadata_json"),
        defaults={"source_id": None, "lane_id": None, "role": "background", "importance": "medium", "summary": "", "metadata_json": {}},
        json_columns=frozenset({"metadata_json"}),
    ),
    "literature_relations": TableSpec(
        table="literature_relations",
        pk="relation_id",
        columns=("relation_id", "project_id", "from_item_id", "to_item_id", "relation_type", "rationale", "created_at", "updated_at", "metadata_json"),
        mutable_columns=("from_item_id", "to_item_id", "relation_type", "rationale", "updated_at", "metadata_json"),
        defaults={"rationale": "", "metadata_json": {}},
        json_columns=frozenset({"metadata_json"}),
    ),
    "project_positionings": TableSpec(
        table="project_positionings",
        pk="positioning_id",
        columns=("positioning_id", "project_id", "text", "confidence", "created_at", "updated_at", "metadata_json"),
        mutable_columns=("text", "confidence", "updated_at", "metadata_json"),
        defaults={"text": "", "confidence": "unknown", "metadata_json": {}},
        json_columns=frozenset({"metadata_json"}),
    ),
    "entity_links": TableSpec(
        table="entity_links",
        pk="entity_link_id",
        columns=(
            "entity_link_id",
            "project_id",
            "from_entity_type",
            "from_entity_id",
            "to_entity_type",
            "to_entity_id",
            "relation_type",
            "created_at",
            "metadata_json",
        ),
        mutable_columns=("from_entity_type", "from_entity_id", "to_entity_type", "to_entity_id", "relation_type", "metadata_json"),
        defaults={"metadata_json": {}},
        json_columns=frozenset({"metadata_json"}),
    ),
    "activity_sessions": TableSpec(
        table="activity_sessions",
        pk="session_id",
        columns=("session_id", "project_id", "actor", "activity_type", "started_at", "ended_at", "summary", "metadata_json"),
        mutable_columns=("actor", "activity_type", "ended_at", "summary", "metadata_json"),
        defaults={"ended_at": "", "summary": "", "metadata_json": {}},
        json_columns=frozenset({"metadata_json"}),
    ),
    "updates": TableSpec(
        table="updates",
        pk="update_id",
        columns=("update_id", "project_id", "session_id", "summary", "confidence", "created_at", "metadata_json"),
        mutable_columns=("session_id", "summary", "confidence", "metadata_json"),
        defaults={"confidence": "unknown", "metadata_json": {}},
        json_columns=frozenset({"metadata_json"}),
    ),
}


class ProjectDatasetWriter:
    def __init__(self, root: Path, actor: str = "agent") -> None:
        self.root = Path(root)
        self.actor = actor

    def write_project_update(self, packet: dict[str, Any]) -> dict[str, Any]:
        validation = self._validate(packet)
        project_id = validation["project_id"]
        timestamp = _utc_timestamp()
        compact_timestamp = _compact_timestamp(timestamp)
        session_id = f"session:{project_id}:{compact_timestamp}:{uuid.uuid4().hex[:8]}"
        update_id = f"update:{project_id}:{compact_timestamp}:{uuid.uuid4().hex[:8]}"

        initialize_dataset(self.root)
        audit_count = 0
        with closing(connect_dataset(self.root)) as connection:
            with connection:
                session = {
                    "session_id": session_id,
                    "project_id": project_id,
                    "actor": self.actor,
                    "activity_type": packet["activity_type"].strip(),
                    "started_at": timestamp,
                    "ended_at": timestamp,
                    "summary": packet["summary"].strip(),
                }
                update = {
                    "update_id": update_id,
                    "project_id": project_id,
                    "session_id": session_id,
                    "summary": packet["summary"].strip(),
                }

                project_entity, other_entities = self._entities(packet, project_id, timestamp)
                bootstrap_entities = [project_entity, ("activity_sessions", session), ("updates", update)]
                pending_audits = []
                for section, entity in bootstrap_entities:
                    spec = SPECS[section]
                    before, after, operation = _upsert(connection, spec, entity, self.actor, timestamp)
                    pending_audits.append((spec, entity, before, after, operation))

                for spec, entity, before, after, operation in pending_audits:
                    event_id = f"audit:{project_id}:{compact_timestamp}:{uuid.uuid4().hex[:8]}:{audit_count}"
                    _insert_audit_event(
                        connection,
                        event_id,
                        project_id,
                        update_id,
                        spec.table,
                        str(entity[spec.pk]),
                        operation,
                        before,
                        after,
                        packet["summary"].strip(),
                        timestamp,
                    )
                    audit_count += 1

                for section, entity in other_entities:
                    spec = SPECS[section]
                    before, after, operation = _upsert(connection, spec, entity, self.actor, timestamp)
                    event_id = f"audit:{project_id}:{compact_timestamp}:{uuid.uuid4().hex[:8]}:{audit_count}"
                    _insert_audit_event(
                        connection,
                        event_id,
                        project_id,
                        update_id,
                        spec.table,
                        str(entity[spec.pk]),
                        operation,
                        before,
                        after,
                        packet["summary"].strip(),
                        timestamp,
                    )
                    audit_count += 1

                for link in packet.get("understanding_links", []):
                    self._write_link_endpoints(connection, project_id, link)

        return {
            "valid": True,
            "project_id": project_id,
            "session_id": session_id,
            "update_id": update_id,
            "audit_event_count": audit_count,
        }

    def _validate(self, packet: dict[str, Any]) -> dict[str, str]:
        project_id = packet.get("project_id")
        if not valid_project_id(project_id):
            raise DatasetValidationError("project_id must be non-empty valid project id")
        if not _non_empty_string(packet.get("activity_type")):
            raise DatasetValidationError("activity_type must be non-empty string")
        if not _non_empty_string(packet.get("summary")):
            raise DatasetValidationError("summary must be non-empty string")

        for section, required_fields in REQUIRED_FIELDS.items():
            for index, item in enumerate(packet.get(section, [])):
                if not isinstance(item, dict):
                    raise DatasetValidationError(f"{section}[] must be object")
                for field in required_fields:
                    if not _non_empty_string(item.get(field)):
                        raise DatasetValidationError(f"{section}[{index}].{field} must be non-empty string")

        packet_nodes: dict[str, str] = {}
        for node in packet.get("understanding_nodes", []):
            node_type = node.get("node_type")
            scope = node.get("scope")
            if node_type not in NODE_TYPES:
                raise DatasetValidationError("understanding_nodes[].node_type invalid")
            if scope not in SCOPES:
                raise DatasetValidationError("understanding_nodes[].scope invalid")
            if _non_empty_string(node.get("node_id")):
                packet_nodes[node["node_id"]] = node_type

        for link in packet.get("understanding_links", []):
            if link.get("link_type") not in LINK_TYPES:
                raise DatasetValidationError("understanding_links[].link_type invalid")
            if link.get("scope", "project") not in SCOPES:
                raise DatasetValidationError("understanding_links[].scope invalid")
            endpoints = link.get("endpoints")
            if not isinstance(endpoints, list):
                raise DatasetValidationError("understanding_links[].endpoints must be list")
            for endpoint in endpoints:
                role = endpoint.get("role")
                node_id = endpoint.get("node_id")
                if role not in ENDPOINT_ROLES:
                    raise DatasetValidationError("understanding_link endpoint role invalid")
                self._require_endpoint_node(project_id, packet_nodes, node_id)
                if role in {"warrant", "project_warrant"}:
                    self._require_endpoint_node_type(project_id, packet_nodes, node_id, "warrant")
                if role in {"limitation", "project_limitation"}:
                    self._require_endpoint_node_type(project_id, packet_nodes, node_id, "limitation")

        for run in packet.get("experiment_runs", []):
            if run.get("origin_type") == "imported_paper" and not _non_empty_string(run.get("source_id")):
                raise DatasetValidationError("imported_paper experiment run requires source_id")

        packet_run_ids = {run.get("run_id") for run in packet.get("experiment_runs", []) if _non_empty_string(run.get("run_id"))}
        metric_run_ids = [metric.get("run_id") for metric in packet.get("experiment_metrics", [])]
        missing_run_ids = [run_id for run_id in metric_run_ids if run_id not in packet_run_ids]
        if missing_run_ids:
            if not dataset_db_path(self.root).exists():
                raise DatasetValidationError("experiment_metrics[].run_id must refer to existing or same-packet run")
            with closing(connect_dataset(self.root)) as connection:
                for run_id in missing_run_ids:
                    row = connection.execute(
                        "SELECT 1 FROM experiment_runs WHERE project_id = ? AND run_id = ?",
                        (project_id, run_id),
                    ).fetchone()
                    if row is None:
                        raise DatasetValidationError("experiment_metrics[].run_id must refer to existing or same-packet run")

        for link in packet.get("entity_links", []):
            if link.get("relation_type") == "supports":
                raise DatasetValidationError("entity_links must not use relation_type supports")

        return {"project_id": project_id}

    def _require_endpoint_node(self, project_id: str, packet_nodes: dict[str, str], node_id: Any) -> None:
        if node_id in packet_nodes:
            return
        if not dataset_db_path(self.root).exists():
            raise DatasetValidationError("understanding_link endpoint node_id must refer to existing or same-packet node")
        with closing(connect_dataset(self.root)) as connection:
            row = connection.execute(
                "SELECT 1 FROM understanding_nodes WHERE project_id = ? AND node_id = ?",
                (project_id, node_id),
            ).fetchone()
        if row is None:
            raise DatasetValidationError("understanding_link endpoint node_id must refer to existing or same-packet node")

    def _require_endpoint_node_type(
        self,
        project_id: str,
        packet_nodes: dict[str, str],
        node_id: Any,
        expected_type: str,
    ) -> None:
        actual = packet_nodes.get(node_id)
        if actual is None:
            if not dataset_db_path(self.root).exists():
                raise DatasetValidationError(f"endpoint role requires node_type={expected_type!r}")
            with closing(connect_dataset(self.root)) as connection:
                row = connection.execute(
                    "SELECT node_type FROM understanding_nodes WHERE project_id = ? AND node_id = ?",
                    (project_id, node_id),
                ).fetchone()
            actual = None if row is None else row["node_type"]
        if actual != expected_type:
            raise DatasetValidationError(f"endpoint role requires node_type={expected_type!r}")

    def _entities(
        self, packet: dict[str, Any], project_id: str, timestamp: str
    ) -> tuple[tuple[str, dict[str, Any]], list[tuple[str, dict[str, Any]]]]:
        entities: list[tuple[str, dict[str, Any]]] = []
        project = dict(packet.get("project") or {})
        project["project_id"] = project_id
        project_entity = ("project", project)

        for section in (
            "sources",
            "understanding_nodes",
            "understanding_links",
            "experiments",
            "experiment_runs",
            "experiment_metrics",
            "experiment_artifacts",
            "literature_lanes",
            "literature_items",
            "literature_relations",
            "project_positionings",
        ):
            for item in packet.get(section, []):
                entity = dict(item)
                entity["project_id"] = project_id
                entity.pop("endpoints", None)
                entities.append((section, entity))

        for link in packet.get("entity_links", []):
            entity = dict(link)
            entity["project_id"] = project_id
            entity.setdefault(
                "entity_link_id",
                "entity_link:{from_entity_type}:{from_entity_id}:{relation_type}:{to_entity_type}:{to_entity_id}".format(
                    **entity
                ),
            )
            entities.append(("entity_links", entity))

        for _, entity in [project_entity, *entities]:
            entity.setdefault("created_at", timestamp)
            entity.setdefault("updated_at", timestamp)
            entity.setdefault("created_by", self.actor)
            entity.setdefault("updated_by", self.actor)
        return project_entity, entities

    def _write_link_endpoints(self, connection: Any, project_id: str, link: dict[str, Any]) -> None:
        link_id = link["link_id"]
        for position, endpoint in enumerate(link.get("endpoints", [])):
            role = endpoint["role"]
            node_id = endpoint["node_id"]
            endpoint_id = f"endpoint:{link_id}:{role}:{position}:{node_id}"
            metadata_json = _json_value(endpoint.get("metadata_json", endpoint.get("metadata", {})))
            connection.execute(
                """
                INSERT INTO understanding_link_endpoints (
                    endpoint_id, project_id, link_id, node_id, role, position, metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(endpoint_id) DO UPDATE SET
                    project_id = excluded.project_id,
                    link_id = excluded.link_id,
                    node_id = excluded.node_id,
                    role = excluded.role,
                    position = excluded.position,
                    metadata_json = excluded.metadata_json
                """,
                (endpoint_id, project_id, link_id, node_id, role, position, metadata_json),
            )


def _upsert(connection: Any, spec: TableSpec, entity: dict[str, Any], actor: str, timestamp: str) -> tuple[str, str, str]:
    pk_value = entity.get(spec.pk)
    if not _non_empty_string(pk_value):
        raise DatasetValidationError(f"{spec.pk} must be non-empty string")

    before_row = connection.execute(f"SELECT * FROM {spec.table} WHERE {spec.pk} = ?", (pk_value,)).fetchone()
    before_json = "{}" if before_row is None else json_dumps(dict(before_row))
    operation = "create" if before_row is None else "update"

    values = _coerce_values(spec, entity, actor, timestamp)
    if before_row is None:
        columns = list(spec.columns)
        placeholders = ", ".join("?" for _ in columns)
        connection.execute(
            f"INSERT INTO {spec.table} ({', '.join(columns)}) VALUES ({placeholders})",
            [values[column] for column in columns],
        )
    else:
        update_columns = [
            column
            for column in spec.mutable_columns
            if column in entity or column in {"updated_at", "updated_by"}
        ]
        assignments = ", ".join(f"{column} = ?" for column in update_columns)
        connection.execute(
            f"UPDATE {spec.table} SET {assignments} WHERE {spec.pk} = ?",
            [values[column] for column in update_columns] + [pk_value],
        )

    after_row = connection.execute(f"SELECT * FROM {spec.table} WHERE {spec.pk} = ?", (pk_value,)).fetchone()
    return before_json, json_dumps(dict(after_row)), operation


def _coerce_values(spec: TableSpec, entity: dict[str, Any], actor: str, timestamp: str) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for column in spec.columns:
        if column in entity:
            value = entity[column]
        elif column in spec.defaults:
            value = spec.defaults[column]
        elif spec.table == "projects" and column in {"slug", "title"}:
            value = entity[spec.pk]
        elif column == "created_at":
            value = timestamp
        elif column == "updated_at":
            value = timestamp
        elif column == "created_by":
            value = actor
        elif column == "updated_by":
            value = actor
        else:
            raise DatasetValidationError(f"{spec.table}.{column} is required")
        if column in spec.json_columns:
            value = _json_value(value)
        values[column] = value
    return values


def _insert_audit_event(
    connection: Any,
    audit_event_id: str,
    project_id: str,
    update_id: str,
    entity_type: str,
    entity_id: str,
    operation: str,
    before_json: str,
    after_json: str,
    reason: str,
    timestamp: str,
) -> None:
    connection.execute(
        """
        INSERT INTO audit_events (
            audit_event_id, project_id, update_id, entity_type, entity_id,
            operation, before_json, after_json, reason, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (audit_event_id, project_id, update_id, entity_type, entity_id, operation, before_json, after_json, reason, timestamp),
    )


def _non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and value.strip() != ""


def _json_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json_dumps(value)


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _compact_timestamp(timestamp: str) -> str:
    return timestamp.replace("-", "").replace(":", "").replace("T", "").removesuffix("Z")
