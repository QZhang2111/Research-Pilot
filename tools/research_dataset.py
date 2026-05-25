#!/usr/bin/env python3
"""Local SQLite dataset foundation for Research Pilot workspaces."""

from __future__ import annotations

import json
import re
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION: int = 1
DB_FILENAME: str = "research-pilot.db"

_PROJECT_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


def dataset_db_path(root: Path) -> Path:
    return Path(root) / DB_FILENAME


def connect_dataset(root: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(dataset_db_path(root))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def initialize_dataset(root: Path, workspace_id: str = "local") -> Path:
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    db_path = dataset_db_path(root)
    timestamp = _utc_timestamp()
    with closing(connect_dataset(root)) as connection:
        with connection:
            connection.executescript(_SCHEMA_SQL)
            connection.execute(
                """
                INSERT INTO workspace (workspace_id, schema_version, created_at, updated_at)
                SELECT ?, ?, ?, ?
                WHERE NOT EXISTS (SELECT 1 FROM workspace)
                """,
                (workspace_id, SCHEMA_VERSION, timestamp, timestamp),
            )
            connection.execute(
                """
                INSERT OR IGNORE INTO schema_migrations (version, applied_at, description)
                VALUES (?, ?, ?)
                """,
                (SCHEMA_VERSION, timestamp, "initial local dataset schema"),
            )
    return db_path


def dataset_initialized(root: Path) -> bool:
    db_path = dataset_db_path(root)
    if not db_path.exists():
        return False
    try:
        with closing(connect_dataset(root)) as connection:
            row = connection.execute("SELECT schema_version FROM workspace LIMIT 1").fetchone()
    except sqlite3.Error:
        return False
    return row is not None and row["schema_version"] == SCHEMA_VERSION


def require_valid_project_id(project_id: str) -> None:
    if not valid_project_id(project_id):
        raise ValueError(f"invalid project_id: {project_id!r}")


def valid_project_id(project_id: str) -> bool:
    return isinstance(project_id, str) and bool(_PROJECT_ID_PATTERN.fullmatch(project_id))


def json_dumps(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def json_loads(value: str | None, default: Any = None) -> Any:
    if value is None or value == "":
        return default
    return json.loads(value)


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS workspace (
    workspace_id TEXT PRIMARY KEY,
    schema_version INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL,
    description TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS projects (
    project_id TEXT PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    summary TEXT NOT NULL DEFAULT '',
    main_question TEXT NOT NULL DEFAULT '',
    working_hypothesis TEXT NOT NULL DEFAULT '',
    target_contribution TEXT NOT NULL DEFAULT '',
    stage TEXT NOT NULL DEFAULT 'idea',
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    created_by TEXT NOT NULL DEFAULT 'system',
    updated_by TEXT NOT NULL DEFAULT 'system',
    confirmation TEXT NOT NULL DEFAULT 'unconfirmed',
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS sources (
    source_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    source_type TEXT NOT NULL,
    title TEXT NOT NULL,
    authors TEXT NOT NULL DEFAULT '',
    year TEXT NOT NULL DEFAULT '',
    locator TEXT NOT NULL DEFAULT '',
    doi TEXT NOT NULL DEFAULT '',
    arxiv_id TEXT NOT NULL DEFAULT '',
    url TEXT NOT NULL DEFAULT '',
    zotero_key TEXT NOT NULL DEFAULT '',
    attachment_locator_type TEXT NOT NULL DEFAULT '',
    attachment_locator TEXT NOT NULL DEFAULT '',
    reading_status TEXT NOT NULL DEFAULT 'seen',
    reading_depth TEXT NOT NULL DEFAULT 'metadata_only',
    short_summary TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    created_by TEXT NOT NULL DEFAULT 'system',
    updated_by TEXT NOT NULL DEFAULT 'system',
    confirmation TEXT NOT NULL DEFAULT 'unconfirmed',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY(project_id) REFERENCES projects(project_id)
);

CREATE TABLE IF NOT EXISTS understanding_nodes (
    node_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    scope TEXT NOT NULL,
    source_id TEXT,
    node_type TEXT NOT NULL,
    text TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    confidence TEXT NOT NULL DEFAULT 'unknown',
    confirmation TEXT NOT NULL DEFAULT 'unconfirmed',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    created_by TEXT NOT NULL DEFAULT 'system',
    updated_by TEXT NOT NULL DEFAULT 'system',
    source_refs_json TEXT NOT NULL DEFAULT '[]',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY(project_id) REFERENCES projects(project_id),
    FOREIGN KEY(source_id) REFERENCES sources(source_id)
);

CREATE TABLE IF NOT EXISTS understanding_links (
    link_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    scope TEXT NOT NULL,
    link_type TEXT NOT NULL,
    relation TEXT NOT NULL,
    confidence TEXT NOT NULL DEFAULT 'unknown',
    confirmation TEXT NOT NULL DEFAULT 'unconfirmed',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    created_by TEXT NOT NULL DEFAULT 'system',
    updated_by TEXT NOT NULL DEFAULT 'system',
    source_refs_json TEXT NOT NULL DEFAULT '[]',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY(project_id) REFERENCES projects(project_id)
);

CREATE TABLE IF NOT EXISTS understanding_link_endpoints (
    endpoint_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    link_id TEXT NOT NULL,
    node_id TEXT NOT NULL,
    role TEXT NOT NULL,
    position INTEGER NOT NULL DEFAULT 0,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY(project_id) REFERENCES projects(project_id),
    FOREIGN KEY(link_id) REFERENCES understanding_links(link_id),
    FOREIGN KEY(node_id) REFERENCES understanding_nodes(node_id)
);

CREATE TABLE IF NOT EXISTS experiments (
    experiment_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    title TEXT NOT NULL,
    question TEXT NOT NULL DEFAULT '',
    hypothesis TEXT NOT NULL DEFAULT '',
    experiment_type TEXT NOT NULL DEFAULT 'benchmark_eval',
    status TEXT NOT NULL DEFAULT 'planned',
    protocol_summary TEXT NOT NULL DEFAULT '',
    benchmark_name TEXT NOT NULL DEFAULT '',
    dataset_name TEXT NOT NULL DEFAULT '',
    planned_at TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    created_by TEXT NOT NULL DEFAULT 'system',
    updated_by TEXT NOT NULL DEFAULT 'system',
    confirmation TEXT NOT NULL DEFAULT 'unconfirmed',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY(project_id) REFERENCES projects(project_id)
);

CREATE TABLE IF NOT EXISTS experiment_runs (
    run_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    experiment_id TEXT NOT NULL,
    origin_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'not_started',
    method_name TEXT NOT NULL DEFAULT '',
    run_label TEXT NOT NULL DEFAULT '',
    source_id TEXT,
    completed_at TEXT NOT NULL DEFAULT '',
    summary TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    created_by TEXT NOT NULL DEFAULT 'system',
    updated_by TEXT NOT NULL DEFAULT 'system',
    confirmation TEXT NOT NULL DEFAULT 'unconfirmed',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY(project_id) REFERENCES projects(project_id),
    FOREIGN KEY(experiment_id) REFERENCES experiments(experiment_id),
    FOREIGN KEY(source_id) REFERENCES sources(source_id)
);

CREATE TABLE IF NOT EXISTS experiment_metrics (
    metric_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    name TEXT NOT NULL,
    value_text TEXT NOT NULL,
    value_numeric REAL,
    unit TEXT NOT NULL DEFAULT '',
    direction TEXT NOT NULL DEFAULT 'neutral',
    benchmark_name TEXT NOT NULL DEFAULT '',
    dataset_name TEXT NOT NULL DEFAULT '',
    split_name TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY(project_id) REFERENCES projects(project_id),
    FOREIGN KEY(run_id) REFERENCES experiment_runs(run_id)
);

CREATE TABLE IF NOT EXISTS experiment_artifacts (
    artifact_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    artifact_type TEXT NOT NULL,
    locator_type TEXT NOT NULL DEFAULT 'local_path',
    locator TEXT NOT NULL,
    label TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY(project_id) REFERENCES projects(project_id),
    FOREIGN KEY(run_id) REFERENCES experiment_runs(run_id)
);

CREATE TABLE IF NOT EXISTS literature_lanes (
    lane_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY(project_id) REFERENCES projects(project_id)
);

CREATE TABLE IF NOT EXISTS literature_items (
    item_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    source_id TEXT,
    lane_id TEXT,
    role TEXT NOT NULL DEFAULT 'background',
    importance TEXT NOT NULL DEFAULT 'medium',
    summary TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY(project_id) REFERENCES projects(project_id),
    FOREIGN KEY(source_id) REFERENCES sources(source_id),
    FOREIGN KEY(lane_id) REFERENCES literature_lanes(lane_id)
);

CREATE TABLE IF NOT EXISTS literature_relations (
    relation_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    from_item_id TEXT NOT NULL,
    to_item_id TEXT NOT NULL,
    relation_type TEXT NOT NULL,
    rationale TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY(project_id) REFERENCES projects(project_id),
    FOREIGN KEY(from_item_id) REFERENCES literature_items(item_id),
    FOREIGN KEY(to_item_id) REFERENCES literature_items(item_id)
);

CREATE TABLE IF NOT EXISTS project_positionings (
    positioning_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    text TEXT NOT NULL,
    confidence TEXT NOT NULL DEFAULT 'unknown',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY(project_id) REFERENCES projects(project_id)
);

CREATE TABLE IF NOT EXISTS activity_sessions (
    session_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    actor TEXT NOT NULL,
    activity_type TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT NOT NULL DEFAULT '',
    summary TEXT NOT NULL DEFAULT '',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY(project_id) REFERENCES projects(project_id)
);

CREATE TABLE IF NOT EXISTS updates (
    update_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    session_id TEXT,
    summary TEXT NOT NULL,
    confidence TEXT NOT NULL DEFAULT 'unknown',
    created_at TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY(project_id) REFERENCES projects(project_id),
    FOREIGN KEY(session_id) REFERENCES activity_sessions(session_id)
);

CREATE TABLE IF NOT EXISTS audit_events (
    audit_event_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    update_id TEXT,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    operation TEXT NOT NULL,
    before_json TEXT NOT NULL DEFAULT '{}',
    after_json TEXT NOT NULL DEFAULT '{}',
    reason TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    FOREIGN KEY(project_id) REFERENCES projects(project_id),
    FOREIGN KEY(update_id) REFERENCES updates(update_id)
);

CREATE TABLE IF NOT EXISTS entity_links (
    entity_link_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    from_entity_type TEXT NOT NULL,
    from_entity_id TEXT NOT NULL,
    to_entity_type TEXT NOT NULL,
    to_entity_id TEXT NOT NULL,
    relation_type TEXT NOT NULL,
    created_at TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY(project_id) REFERENCES projects(project_id)
);

CREATE INDEX IF NOT EXISTS idx_sources_project ON sources(project_id);
CREATE INDEX IF NOT EXISTS idx_nodes_project_scope_type ON understanding_nodes(project_id, scope, node_type);
CREATE INDEX IF NOT EXISTS idx_nodes_source ON understanding_nodes(source_id);
CREATE INDEX IF NOT EXISTS idx_links_project_type ON understanding_links(project_id, link_type);
CREATE INDEX IF NOT EXISTS idx_endpoints_link_role ON understanding_link_endpoints(link_id, role);
CREATE INDEX IF NOT EXISTS idx_experiments_project ON experiments(project_id);
CREATE INDEX IF NOT EXISTS idx_runs_experiment ON experiment_runs(experiment_id);
CREATE INDEX IF NOT EXISTS idx_metrics_run ON experiment_metrics(run_id);
CREATE INDEX IF NOT EXISTS idx_literature_items_project ON literature_items(project_id);
CREATE INDEX IF NOT EXISTS idx_literature_relations_project ON literature_relations(project_id);
CREATE INDEX IF NOT EXISTS idx_updates_project_created ON updates(project_id, created_at);
CREATE INDEX IF NOT EXISTS idx_audit_update ON audit_events(update_id);
CREATE INDEX IF NOT EXISTS idx_entity_links_from ON entity_links(project_id, from_entity_type, from_entity_id);
CREATE INDEX IF NOT EXISTS idx_entity_links_to ON entity_links(project_id, to_entity_type, to_entity_id);
"""
