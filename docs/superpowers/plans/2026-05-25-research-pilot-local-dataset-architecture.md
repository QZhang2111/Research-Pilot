# Research-Pilot Local Dataset Architecture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the DB-backed, project-centered local dataset architecture described in the PRD while preserving the existing dashboard and Demo Visual Affordance behavior.

**Architecture:** Add `research-pilot.db` as the primary local store, with typed storage modules, a legacy demo importer, DB-backed read model builders, API fallback integration, and a minimal typed write service that always writes audit/update history. The existing dashboard frontend must remain unchanged in this architecture phase; server/API read models translate DB state into dashboard-compatible JSON.

**Tech Stack:** Python standard library (`sqlite3`, `json`, `pathlib`, `unittest`, `http.server`), existing Research-Pilot file parsers/builders, existing vanilla JS dashboard as read-only consumer.

---

## Non-Negotiable Constraints For Workers

- Do not redesign dashboard pages.
- Do not modify dashboard CSS/JS unless a test proves a server/API compatibility bug that cannot be fixed in read models.
- Do not delete legacy files, graph events, paper dossiers, lineage JSON, experiments JSON, or understanding update JSONL.
- Do not commit `.dashboard/`, `wiki/graphs/graph.db`, graph snapshots, or private local artifacts. `research-pilot.db` belongs to the user-selected workspace as the local dataset; do not treat it as a dashboard cache.
- Do not make migration cost drive architecture decisions.
- Do not flatten Q/C/E/W/L into generic notes.
- Preserve `Question`, `Claim`, `Evidence`, `Warrant`, `Limitation`, `ReasoningLink`, and `TranslationLink` semantics.
- Do not mark imported paper evidence as local experiment result.
- Do not let agent-facing write paths bypass audit/update history.
- Do not let dashboard read raw DB tables directly.
- Do not introduce cloud auth, cloud sync, permissions, hosted dashboard, or conflict UI.

## Required Reference Docs

- PRD: `docs/superpowers/specs/2026-05-25-research-pilot-local-dataset-architecture-prd.md`
- Design note: `docs/superpowers/specs/2026-05-25-research-pilot-local-dataset-architecture-design.md`
- Existing graph schema: `templates/workspace/wiki/graphs/schema/graph-event.schema.json`
- Existing demo graph events: `examples/workspaces/demo-visual-affordance/wiki/graphs/events/projects/DemoVisualAffordance.jsonl`
- Existing demo experiments: `examples/workspaces/demo-visual-affordance/wiki/projects/DemoVisualAffordance/experiments/experiments.json`
- Existing demo lineage: `examples/workspaces/demo-visual-affordance/wiki/projects/DemoVisualAffordance/literature-rounds/demo-affordance-lineage/related-work-lineage.json`

## Implementation Contract

Workers must implement the architecture below, not a smaller substitute.

Storage contract:

```text
workspace root
└── research-pilot.db              primary durable dataset
```

Legacy files remain import sources and fallback sources. They are not deleted, rewritten, or treated as the new storage model.

Domain contract:

```text
Project
├─ Brief
├─ Sources / Papers
├─ Project Understanding
├─ Experiments
├─ Literature Structure
└─ Activity / Updates
```

Understanding contract:

```text
Question / Claim / Evidence / Warrant / Limitation stay first-class nodes.
ReasoningLink / TranslationLink stay first-class links.
ReasoningLink endpoints must preserve from, to, warrant, limitation, project_warrant, project_limitation roles.
Gap is not a first-class DB table or node type in this plan.
```

Source contract:

```text
Source stores identity and reading state.
Paper deep-read content becomes UnderstandingNode(scope='paper', source_id='<source>').
Project argument content becomes UnderstandingNode(scope='project').
TranslationLink maps paper/program understanding into project understanding.
```

Experiment contract:

```text
Experiment.status = design lifecycle.
ExperimentRun.origin_type = evidence origin.
origin_type imported_paper never counts as local completed work.
ExperimentMetric belongs to ExperimentRun, not directly to Claim.
Important ExperimentRun produces project-scope Evidence node through EntityLink relation_type='produces'.
```

Dashboard contract:

```text
Dashboard frontend is unchanged.
Server/API/read-model code adapts DB state into existing dashboard-shaped JSON.
Dashboard never reads SQL tables directly.
```

Cloud contract:

```text
Build stable IDs, timestamps, actor/provenance fields, migrations, audit events, and portable artifact locators.
Do not build auth, sync, permissions, hosted dashboard, or conflict UI.
```

Generated artifact contract:

```text
Do not commit research-pilot.db.
Do not commit .dashboard/.
Do not commit wiki/graphs/graph.db.
Do not commit generated snapshots.
```

## File Structure

Create:

- `tools/research_dataset.py`: SQLite path, connection, schema migration, table initialization, validation constants, JSON helpers.
- `tools/research_dataset_writer.py`: typed write service and `ProjectUpdatePacket` transaction/audit behavior.
- `tools/research_dataset_import.py`: legacy/demo import into `research-pilot.db`.
- `tools/research_dataset_read_models.py`: DB-backed dashboard-compatible read model builders.
- `tools/research_dataset_cli.py`: minimal CLI for `init`, `import-legacy`, and `summary`.
- `tests/test_research_dataset_schema.py`: DB schema/migration tests.
- `tests/test_research_dataset_writer.py`: typed writer/audit tests.
- `tests/test_research_dataset_import.py`: Demo Visual Affordance import tests.
- `tests/test_research_dataset_read_models.py`: DB-backed read model tests.
- `tests/test_research_browser_db_fallback.py`: API DB-first/legacy-fallback tests.

Modify:

- `tools/research_browser_server.py`: prefer DB-backed read models when `research-pilot.db` exists and contains requested project; otherwise use existing legacy readers.
- `tools/README.md`: add DB-backed architecture module summary.
- `docs/guides/workspace.md`: explain `research-pilot.db` as the workspace-local dataset: one DB per workspace, many projects by `project_id`.
- `README.md`: update architecture framing only after tests pass.

Do not modify:

- `dashboard/app.js`
- `dashboard/styles.css`
- `dashboard/*.html`
- `dashboard/project-graph/*`

If a worker thinks a dashboard file must change, stop and report the exact failing API contract and screenshot/test evidence before editing.

## Target Schema Summary

The physical SQLite schema must include these durable tables:

```text
workspace
schema_migrations
projects
sources
understanding_nodes
understanding_links
understanding_link_endpoints
experiments
experiment_runs
experiment_metrics
experiment_artifacts
literature_lanes
literature_items
literature_relations
project_positionings
activity_sessions
updates
audit_events
entity_links
```

The DB file path must be:

```text
<workspace>/research-pilot.db
```

## Task 1: SQLite Dataset Foundation

**Files:**

- Create: `tools/research_dataset.py`
- Create: `tests/test_research_dataset_schema.py`

### Required Public API

`tools/research_dataset.py` must expose:

```text
SCHEMA_VERSION: int = 1
DB_FILENAME: str = "research-pilot.db"
dataset_db_path(root: Path) -> Path
connect_dataset(root: Path) -> sqlite3.Connection
initialize_dataset(root: Path, workspace_id: str = "local") -> Path
dataset_initialized(root: Path) -> bool
require_valid_project_id(project_id: str) -> None
valid_project_id(project_id: str) -> bool
json_dumps(value: Any) -> str
json_loads(value: str | None, default: Any = None) -> Any
```

Implementation rules:

```text
dataset_db_path(root) returns root / DB_FILENAME.
connect_dataset(root) opens dataset_db_path(root), sets row_factory=sqlite3.Row, and executes PRAGMA foreign_keys=ON.
initialize_dataset(root) creates parent directories only for root itself, creates schema, inserts one workspace row, inserts one schema_migrations row.
dataset_initialized(root) returns True only when research-pilot.db exists and contains workspace.schema_version = SCHEMA_VERSION.
valid_project_id accepts ASCII letters, digits, underscore, hyphen only.
require_valid_project_id raises ValueError with message containing "invalid project_id" when invalid.
json_dumps uses sort_keys=True and separators=(",", ":").
json_loads returns default when value is None or empty string.
```

### Required SQL

Use `TEXT` stable IDs. Use `metadata_json`, `before_json`, and `after_json` as JSON text. Use timestamps as UTC ISO-8601 strings ending in `Z`.

`initialize_dataset()` must create all tables below. Add only the indexes listed in this task. Do not remove, rename, or change any listed column.

```sql
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
```

### Required Indexes

Create these indexes:

```sql
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
```

### Tests

- [ ] Write `tests/test_research_dataset_schema.py`.

Test file must include:

```python
import sqlite3
import tempfile
import unittest
from pathlib import Path

from tools.research_dataset import (
    SCHEMA_VERSION,
    connect_dataset,
    dataset_db_path,
    dataset_initialized,
    initialize_dataset,
    valid_project_id,
)


class ResearchDatasetSchemaTest(unittest.TestCase):
    def test_initialize_creates_expected_tables_and_workspace_row(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db_path = initialize_dataset(root, workspace_id="test-workspace")

            self.assertEqual(db_path, root / "research-pilot.db")
            self.assertTrue(db_path.exists())
            self.assertTrue(dataset_initialized(root))

            with sqlite3.connect(db_path) as conn:
                tables = {
                    row[0]
                    for row in conn.execute(
                        "select name from sqlite_master where type='table'"
                    ).fetchall()
                }
                self.assertTrue(
                    {
                        "workspace",
                        "schema_migrations",
                        "projects",
                        "sources",
                        "understanding_nodes",
                        "understanding_links",
                        "understanding_link_endpoints",
                        "experiments",
                        "experiment_runs",
                        "experiment_metrics",
                        "experiment_artifacts",
                        "literature_lanes",
                        "literature_items",
                        "literature_relations",
                        "project_positionings",
                        "activity_sessions",
                        "updates",
                        "audit_events",
                        "entity_links",
                    }.issubset(tables)
                )
                workspace = conn.execute("select workspace_id, schema_version from workspace").fetchone()
                self.assertEqual(workspace, ("test-workspace", SCHEMA_VERSION))
                migration = conn.execute("select version from schema_migrations").fetchone()
                self.assertEqual(migration, (SCHEMA_VERSION,))

    def test_initialize_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = initialize_dataset(root, workspace_id="test-workspace")
            second = initialize_dataset(root, workspace_id="test-workspace")
            self.assertEqual(first, second)
            with sqlite3.connect(first) as conn:
                rows = conn.execute("select count(*) from schema_migrations").fetchone()[0]
            self.assertEqual(rows, 1)

    def test_valid_project_id_rejects_path_parts(self) -> None:
        self.assertTrue(valid_project_id("DemoVisualAffordance"))
        self.assertFalse(valid_project_id("../DemoVisualAffordance"))
        self.assertFalse(valid_project_id("nested/project"))
        self.assertFalse(valid_project_id(""))

    def test_connect_dataset_enables_foreign_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            initialize_dataset(root)
            with connect_dataset(root) as conn:
                enabled = conn.execute("pragma foreign_keys").fetchone()[0]
            self.assertEqual(enabled, 1)


if __name__ == "__main__":
    unittest.main()
```

- [ ] Run:

```bash
python3 -m unittest tests.test_research_dataset_schema -v
```

Expected after implementation:

```text
Ran 4 tests
OK
```

### Commit

After tests pass:

```bash
git add tools/research_dataset.py tests/test_research_dataset_schema.py
git commit -m "feat: add research dataset sqlite foundation"
```

## Task 2: Typed Write Service With Audit History

**Files:**

- Create: `tools/research_dataset_writer.py`
- Create: `tests/test_research_dataset_writer.py`

### Required Behavior

Implement a write service that writes current state and audit/update history in one transaction.

Do not expose raw SQL to agents. The writer accepts a typed packet shape.

### Required Public API

```text
DatasetValidationError: subclass of ValueError
ProjectDatasetWriter.__init__(root: Path, actor: str = "agent") -> None
ProjectDatasetWriter.write_project_update(packet: dict[str, Any]) -> dict[str, Any]
```

`write_project_update()` packet shape:

```python
{
    "project_id": "DemoProject",
    "activity_type": "deep_read_source",
    "summary": "Human-readable update summary.",
    "confidence": "medium",
    "project": {
        "project_id": "DemoProject",
        "slug": "demo-project",
        "title": "Demo Project"
    },
    "sources": [],
    "understanding_nodes": [],
    "understanding_links": [],
    "experiments": [],
    "experiment_runs": [],
    "experiment_metrics": [],
    "experiment_artifacts": [],
    "literature_lanes": [],
    "literature_items": [],
    "literature_relations": [],
    "project_positionings": [],
    "entity_links": [],
}
```

Each section is optional except `project_id`, `activity_type`, and `summary`.

### Validation Rules

Implement these rules exactly:

- `project_id` must pass `valid_project_id`.
- `activity_type` must be non-empty string.
- `summary` must be non-empty string.
- `understanding_nodes[].node_type` must be one of `question`, `claim`, `evidence`, `warrant`, `limitation`.
- `understanding_nodes[].scope` must be one of `paper`, `project`, `program`.
- `understanding_links[].link_type` must be one of `reasoning`, `translation`.
- `understanding_link_endpoints[].role` must be one of `from`, `to`, `warrant`, `limitation`, `project_warrant`, `project_limitation`.
- Endpoint role `warrant` or `project_warrant` must point to a node with `node_type='warrant'`.
- Endpoint role `limitation` or `project_limitation` must point to a node with `node_type='limitation'`.
- `experiment_runs[].origin_type='imported_paper'` must include `source_id`.
- `experiment_metrics[].run_id` must refer to an existing or same-packet run.
- `entity_links` must not use relation type `supports` for Q/C/E/W/L argument support; workers must use `understanding_links` for argument relations.

### Audit Requirements

For each inserted or updated entity, create one `audit_events` row.

Operations:

```text
create
update
```

Use `before_json='{}'` for create. Use row JSON before update for update.

Create exactly one `activity_sessions` row and one `updates` row per call to `write_project_update()`.

Generated ID rules:

```text
session_id = session:<project_id>:<UTC timestamp compact>:<8 hex chars>
update_id = update:<project_id>:<UTC timestamp compact>:<8 hex chars>
audit_event_id = audit:<project_id>:<UTC timestamp compact>:<8 hex chars>:<zero-based sequence>
endpoint_id = endpoint:<link_id>:<role>:<position>:<node_id>
entity_link_id = entity_link:<from_entity_type>:<from_entity_id>:<relation_type>:<to_entity_type>:<to_entity_id>
```

Use `uuid.uuid4().hex[:8]` for the 8 hex suffix. Use the same timestamp compact string for all IDs generated inside one `write_project_update()` call.

Upsert rules:

```text
If primary key exists, update mutable columns and create operation='update' audit row.
If primary key does not exist, insert row and create operation='create' audit row.
Do not delete rows in writer.
Do not create audit rows for understanding_link_endpoints generated as part of the same understanding_link audit event.
```

Return:

```python
{
    "valid": True,
    "project_id": "DemoProject",
    "session_id": "generated session id",
    "update_id": "generated update id",
    "audit_event_count": 7,
}
```

On validation error, raise `DatasetValidationError` and write no rows.

### Tests

- [ ] Write `tests/test_research_dataset_writer.py`.

Tests must include:

```python
import sqlite3
import tempfile
import unittest
from pathlib import Path

from tools.research_dataset import connect_dataset, initialize_dataset
from tools.research_dataset_writer import DatasetValidationError, ProjectDatasetWriter


class ResearchDatasetWriterTest(unittest.TestCase):
    def test_write_project_source_node_link_and_audit_in_one_update(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            initialize_dataset(root)
            writer = ProjectDatasetWriter(root, actor="agent")
            result = writer.write_project_update(
                {
                    "project_id": "DemoProject",
                    "activity_type": "deep_read_source",
                    "summary": "Created project, source, paper evidence, project claim, and reasoning link.",
                    "confidence": "medium",
                    "project": {
                        "project_id": "DemoProject",
                        "slug": "demo-project",
                        "title": "Demo Project",
                        "summary": "Demo summary.",
                        "main_question": "What is being tested?",
                    },
                    "sources": [
                        {
                            "source_id": "S1",
                            "source_type": "paper",
                            "title": "Source Paper",
                            "reading_status": "deep_read",
                            "reading_depth": "deep_structured",
                        }
                    ],
                    "understanding_nodes": [
                        {
                            "node_id": "P-E1",
                            "scope": "paper",
                            "source_id": "S1",
                            "node_type": "evidence",
                            "text": "Paper table reports a useful result.",
                            "confidence": "medium",
                        },
                        {
                            "node_id": "C1",
                            "scope": "project",
                            "node_type": "claim",
                            "text": "The method works on this benchmark.",
                            "confidence": "medium",
                        },
                        {
                            "node_id": "W1",
                            "scope": "project",
                            "node_type": "warrant",
                            "text": "The benchmark matches the project claim scope.",
                            "confidence": "medium",
                        },
                        {
                            "node_id": "L1",
                            "scope": "project",
                            "node_type": "limitation",
                            "text": "The result is imported, not local.",
                            "confidence": "medium",
                        },
                    ],
                    "understanding_links": [
                        {
                            "link_id": "RL1",
                            "scope": "project",
                            "link_type": "reasoning",
                            "relation": "supports",
                            "endpoints": [
                                {"node_id": "P-E1", "role": "from", "position": 0},
                                {"node_id": "C1", "role": "to", "position": 0},
                                {"node_id": "W1", "role": "warrant", "position": 0},
                                {"node_id": "L1", "role": "limitation", "position": 0},
                            ],
                        }
                    ],
                }
            )

            self.assertTrue(result["valid"])
            self.assertGreaterEqual(result["audit_event_count"], 7)
            with connect_dataset(root) as conn:
                self.assertEqual(conn.execute("select count(*) from projects").fetchone()[0], 1)
                self.assertEqual(conn.execute("select count(*) from sources").fetchone()[0], 1)
                self.assertEqual(conn.execute("select count(*) from understanding_nodes").fetchone()[0], 4)
                self.assertEqual(conn.execute("select count(*) from understanding_links").fetchone()[0], 1)
                self.assertEqual(conn.execute("select count(*) from understanding_link_endpoints").fetchone()[0], 4)
                self.assertEqual(conn.execute("select count(*) from activity_sessions").fetchone()[0], 1)
                self.assertEqual(conn.execute("select count(*) from updates").fetchone()[0], 1)
                self.assertEqual(
                    conn.execute("select count(*) from audit_events where update_id=?", (result["update_id"],)).fetchone()[0],
                    result["audit_event_count"],
                )

    def test_invalid_warrant_endpoint_rolls_back_transaction(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            initialize_dataset(root)
            writer = ProjectDatasetWriter(root, actor="agent")
            with self.assertRaises(DatasetValidationError):
                writer.write_project_update(
                    {
                        "project_id": "DemoProject",
                        "activity_type": "revise_understanding",
                        "summary": "Invalid warrant endpoint.",
                        "project": {"project_id": "DemoProject", "slug": "demo-project", "title": "Demo Project"},
                        "understanding_nodes": [
                            {"node_id": "C1", "scope": "project", "node_type": "claim", "text": "Claim."},
                            {"node_id": "E1", "scope": "project", "node_type": "evidence", "text": "Evidence."},
                        ],
                        "understanding_links": [
                            {
                                "link_id": "RL1",
                                "scope": "project",
                                "link_type": "reasoning",
                                "relation": "supports",
                                "endpoints": [
                                    {"node_id": "E1", "role": "from"},
                                    {"node_id": "C1", "role": "to"},
                                    {"node_id": "C1", "role": "warrant"},
                                ],
                            }
                        ],
                    }
                )
            with connect_dataset(root) as conn:
                self.assertEqual(conn.execute("select count(*) from projects").fetchone()[0], 0)
                self.assertEqual(conn.execute("select count(*) from audit_events").fetchone()[0], 0)

    def test_imported_paper_run_requires_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            initialize_dataset(root)
            writer = ProjectDatasetWriter(root, actor="agent")
            with self.assertRaises(DatasetValidationError):
                writer.write_project_update(
                    {
                        "project_id": "DemoProject",
                        "activity_type": "import_experiment_evidence",
                        "summary": "Invalid imported run.",
                        "project": {"project_id": "DemoProject", "slug": "demo-project", "title": "Demo Project"},
                        "experiments": [{"experiment_id": "EXP1", "title": "Experiment"}],
                        "experiment_runs": [
                            {
                                "run_id": "RUN1",
                                "experiment_id": "EXP1",
                                "origin_type": "imported_paper",
                                "status": "completed",
                            }
                        ],
                    }
                )


if __name__ == "__main__":
    unittest.main()
```

- [ ] Run:

```bash
python3 -m unittest tests.test_research_dataset_writer -v
```

Expected:

```text
Ran 3 tests
OK
```

### Commit

```bash
git add tools/research_dataset_writer.py tests/test_research_dataset_writer.py
git commit -m "feat: add audited project dataset writer"
```

## Task 3: Demo Visual Affordance Legacy Importer

**Files:**

- Create: `tools/research_dataset_import.py`
- Create: `tests/test_research_dataset_import.py`

### Required Public API

```text
import_legacy_project(root: Path, project_id: str, *, reset: bool = False) -> dict[str, Any]
import_demo_visual_affordance(root: Path, *, reset: bool = False) -> dict[str, Any]
```

`import_demo_visual_affordance(root, reset)` calls `import_legacy_project(root, "DemoVisualAffordance", reset=reset)`.

Reset behavior:

```text
reset=False and project exists in DB: raise ValueError with message containing "already imported".
reset=True: delete only rows for project_id from DB tables, then re-import inside one transaction.
reset=True must not delete or edit legacy Markdown, JSONL, JSON, dashboard, graph, or paper files.
```

Delete order for reset:

```text
audit_events
updates
activity_sessions
entity_links
experiment_artifacts
experiment_metrics
experiment_runs
experiments
literature_relations
literature_items
literature_lanes
project_positionings
understanding_link_endpoints
understanding_links
understanding_nodes
sources
projects
```

### Required Import Sources

Importer must read:

```text
wiki/projects/<ProjectId>/overview.md
wiki/projects/<ProjectId>/project-query-pack.md
wiki/projects/<ProjectId>/papers/*/index.md
wiki/graphs/events/projects/<ProjectId>.jsonl
wiki/projects/<ProjectId>/experiments/experiments.json
wiki/projects/<ProjectId>/literature-rounds/*/related-work-lineage.json
wiki/understanding/events/<ProjectId>.jsonl
```

When one import source file is missing, importer appends a warning string to `result["warnings"]` and continues. Missing graph events produce zero graph nodes. Missing experiments produce zero experiments. Missing lineage produces zero literature lanes/items. Missing overview still creates project from `project_id`.

### Required Mapping

Project:

- project_id from path/project argument.
- title from overview frontmatter `title`, fallback project_id.
- summary from overview body first paragraph or project-query-pack summary.
- main_question from project-query-pack current question or first project graph question.
- stage from overview frontmatter `stage`, fallback `literature_mapping`.

Sources:

- one Source per `papers/*/index.md`.
- `source_id` must be `paper:<slug>`.
- `source_type='paper'`.
- `title`, `authors`, `year`, `url`, `doi`, `arxiv_id` from frontmatter. Use empty string for missing fields.
- `locator` must be workspace-relative path to the dossier.
- `reading_status='deep_read'`.
- `reading_depth='deep_structured'`.
- `short_summary` from dossier summary/abstract section, trimmed to first sentence.

Understanding:

- build snapshot from existing graph event JSONL using `tools.graph_store.build_snapshot_from_event_files`.
- insert active project graph nodes into `understanding_nodes`.
- map graph node type names:

```text
Question -> question
Claim -> claim
Evidence -> evidence
Warrant -> warrant
Limitation -> limitation
```

- preserve `node_id`, `local_id`, `scope`, `text`, `status`, `confidence`, `human_review` as `confirmation`.
- insert `source_refs` into `source_refs_json`.
- insert reasoning links and endpoints from snapshot links.
- endpoint roles:

```text
from_nodes -> from
to_nodes -> to
warrant_nodes -> warrant
limitation_nodes -> limitation
project_warrant_nodes -> project_warrant
project_limitation_nodes -> project_limitation
```

Experiments:

- read via `tools.experiment_store.build_project_experiments`.
- insert experiments, runs, metrics, artifacts.
- map evidence type:

```text
imported_paper_evidence -> origin_type imported_paper
local_experiment_result -> origin_type local
replication_result -> origin_type replication
external_result -> origin_type external
```

- each imported run must link to source `paper:zhang2026-geometry-interaction-vfm` when no better source can be resolved from artifact URL/path.
- create an `UnderstandingNode(node_type='evidence', scope='project')` for each run with ID `run:<run_id>:evidence`.
- create `EntityLink(experiment_run -> understanding_node, relation_type='produces')`.
- for each `claim_impacts[]`, create `EntityLink(experiment_run -> understanding_node(claim), relation_type=<impact>)` if claim node exists.
- do not create a local run from imported evidence.

Literature:

- read each `related-work-lineage.json`.
- insert routes as `literature_lanes`.
- insert papers as `literature_items`.
- Normalize lineage paper IDs, source IDs, source titles, and source locators by lowercasing and replacing every non-alphanumeric run with `-`.
- Link a lineage item to a source when normalized lineage paper ID equals normalized source ID suffix after `paper:`, or normalized lineage title equals normalized source title.
- When no match exists, set `source_id=NULL` and preserve lineage paper metadata in `metadata_json`.
- insert explicit edges as `literature_relations`.
- insert project positioning from `title`, `topic_name`, `baseline_paper_field_scope.primary_problem`, and `survey_boundary` into one `project_positionings` row per lineage map.

Activity:

- create one ActivitySession/Update for the import:

```text
activity_type = legacy_import
summary = Imported legacy project files into research-pilot.db.
```

Return shape:

```python
{
    "valid": True,
    "project_id": "DemoVisualAffordance",
    "sources": 9,
    "understanding_nodes": 24,
    "understanding_links": 7,
    "experiments": 4,
    "experiment_runs": 5,
    "experiment_metrics": 15,
    "literature_lanes": 4,
    "literature_items": 9,
    "warnings": [],
}
```

Exact counts may be higher only when legacy project contains more files than the current demo fixture. Demo fixture tests below pin the minimums and key exact experiment counts.

### Tests

- [ ] Write `tests/test_research_dataset_import.py`.

Test file must include:

```python
import shutil
import tempfile
import unittest
from pathlib import Path

from tools.research_dataset import connect_dataset, initialize_dataset
from tools.research_dataset_import import import_demo_visual_affordance


REPO_ROOT = Path(__file__).resolve().parents[1]
DEMO_ROOT = REPO_ROOT / "examples" / "workspaces" / "demo-visual-affordance"


class ResearchDatasetImportTest(unittest.TestCase):
    def test_import_demo_visual_affordance_preserves_core_counts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "demo"
            shutil.copytree(DEMO_ROOT, root)
            initialize_dataset(root)
            result = import_demo_visual_affordance(root, reset=True)

            self.assertTrue(result["valid"])
            self.assertEqual(result["project_id"], "DemoVisualAffordance")
            self.assertGreaterEqual(result["sources"], 9)
            self.assertGreaterEqual(result["understanding_nodes"], 20)
            self.assertGreaterEqual(result["understanding_links"], 6)
            self.assertEqual(result["experiments"], 4)
            self.assertEqual(result["experiment_runs"], 5)
            self.assertGreaterEqual(result["literature_lanes"], 4)
            self.assertGreaterEqual(result["literature_items"], 9)

            with connect_dataset(root) as conn:
                project = conn.execute(
                    "select title from projects where project_id='DemoVisualAffordance'"
                ).fetchone()
                self.assertEqual(project[0], "Demo Visual Affordance")

                q_count = conn.execute(
                    "select count(*) from understanding_nodes where project_id='DemoVisualAffordance' and scope='project' and node_type='question'"
                ).fetchone()[0]
                c_count = conn.execute(
                    "select count(*) from understanding_nodes where project_id='DemoVisualAffordance' and scope='project' and node_type='claim'"
                ).fetchone()[0]
                e_count = conn.execute(
                    "select count(*) from understanding_nodes where project_id='DemoVisualAffordance' and scope='project' and node_type='evidence'"
                ).fetchone()[0]
                w_count = conn.execute(
                    "select count(*) from understanding_nodes where project_id='DemoVisualAffordance' and scope='project' and node_type='warrant'"
                ).fetchone()[0]
                l_count = conn.execute(
                    "select count(*) from understanding_nodes where project_id='DemoVisualAffordance' and scope='project' and node_type='limitation'"
                ).fetchone()[0]
                self.assertGreaterEqual(q_count, 3)
                self.assertGreaterEqual(c_count, 4)
                self.assertGreaterEqual(e_count, 8)
                self.assertGreaterEqual(w_count, 4)
                self.assertGreaterEqual(l_count, 5)

    def test_import_demo_preserves_experiment_origin_and_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "demo"
            shutil.copytree(DEMO_ROOT, root)
            initialize_dataset(root)
            import_demo_visual_affordance(root, reset=True)

            with connect_dataset(root) as conn:
                origins = dict(
                    conn.execute(
                        "select origin_type, count(*) from experiment_runs group by origin_type"
                    ).fetchall()
                )
                self.assertEqual(origins.get("imported_paper"), 5)
                self.assertNotIn("local", origins)

                metrics = {
                    (row[0], row[1]): row[2]
                    for row in conn.execute(
                        "select run_id, name, value_text from experiment_metrics"
                    ).fetchall()
                }
                self.assertIn(("RUN2", "KLD"), metrics)
                self.assertEqual(metrics[("RUN2", "KLD")], "1.825")
                self.assertEqual(metrics[("RUN3", "KLD")], "1.493")
                self.assertEqual(metrics[("RUN3", "SIM")], "0.326")
                self.assertEqual(metrics[("RUN3", "NSS")], "1.090")

                produced = conn.execute(
                    "select count(*) from entity_links where from_entity_type='experiment_run' and to_entity_type='understanding_node' and relation_type='produces'"
                ).fetchone()[0]
                self.assertEqual(produced, 5)

    def test_import_is_idempotent_with_reset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "demo"
            shutil.copytree(DEMO_ROOT, root)
            initialize_dataset(root)
            first = import_demo_visual_affordance(root, reset=True)
            second = import_demo_visual_affordance(root, reset=True)
            self.assertEqual(first["experiments"], second["experiments"])
            with connect_dataset(root) as conn:
                self.assertEqual(
                    conn.execute("select count(*) from projects where project_id='DemoVisualAffordance'").fetchone()[0],
                    1,
                )


if __name__ == "__main__":
    unittest.main()
```

- [ ] Run:

```bash
python3 -m unittest tests.test_research_dataset_import -v
```

Expected:

```text
Ran 3 tests
OK
```

### Commit

```bash
git add tools/research_dataset_import.py tests/test_research_dataset_import.py
git commit -m "feat: import legacy demo into research dataset"
```

## Task 4: DB-Backed Read Model Builders

**Files:**

- Create: `tools/research_dataset_read_models.py`
- Create: `tests/test_research_dataset_read_models.py`

### Required Public API

```text
project_exists_in_dataset(root: Path, project_id: str) -> bool
build_project_summary_model(root: Path, project_id: str) -> dict[str, Any]
build_sources_model(root: Path, project_id: str) -> dict[str, Any]
build_source_detail_model(root: Path, project_id: str, source_id: str) -> dict[str, Any]
build_project_graph_model(root: Path, project_id: str) -> dict[str, Any]
build_experiments_model(root: Path, project_id: str) -> dict[str, Any]
build_literature_model(root: Path, project_id: str) -> dict[str, Any]
build_recent_updates_model(root: Path, project_id: str, limit: int = 10) -> dict[str, Any]
```

### Required Output Compatibility

`build_project_graph_model()` must output the same high-level shape consumed by current `/api/project-graph`:

```python
{
    "project": "DemoVisualAffordance",
    "source": "research-pilot.db",
    "nodes": [
        {
            "id": "C1",
            "kind": "claim",
            "label": "Claim text",
            "subtitle": "active",
            "status": "active",
            "confidence": "medium",
            "source_refs": [],
            "metadata": {}
        }
    ],
    "links": [
        {
            "id": "RL1",
            "relation": "supports",
            "premises": ["E1"],
            "target": ["C1"],
            "warrant": ["W1"],
            "limitations": ["L1"],
            "confidence": "medium",
            "source_refs": []
        }
    ],
    "counts": {
        "question": 3,
        "claim": 4,
        "evidence": 8,
        "warrant": 4,
        "limitation": 5,
        "reasoning": 7,
        "translation": 0
    },
}
```

Node fields:

```text
id
kind
label
subtitle
status
confidence
source_refs
metadata
```

Kind mapping:

```text
question -> question
claim -> claim
evidence -> evidence
warrant -> warrant
limitation -> limitation
```

Link fields:

```text
id
relation
premises
target
warrant
limitations
confidence
source_refs
```

`build_experiments_model()` must keep current `/api/experiments` top-level shape:

```text
schema_version
project_id
source_boundary
mutating
summary
experiments
runs
next_moves
legacy_proposals
```

but values must come from DB.

For DB-backed output:

```text
source_boundary = project_experiments_from_research_dataset
mutating = False
legacy_proposals.count = legacy markdown count if directory exists
```

`build_recent_updates_model()` output:

```python
{
    "project_id": "DemoVisualAffordance",
    "source": "research-pilot.db",
    "updates": [
        {
            "id": "update:DemoVisualAffordance:20260525T000000Z:1234abcd",
            "activity_type": "legacy_import",
            "summary": "Imported legacy project files into research-pilot.db.",
            "confidence": "unknown",
            "created_at": "2026-05-25T00:00:00Z",
            "audit_event_count": 42
        }
    ]
}
```

### Tests

- [ ] Write `tests/test_research_dataset_read_models.py`.

Tests must import demo into DB, then assert read models:

```python
import shutil
import tempfile
import unittest
from pathlib import Path

from tools.research_dataset import initialize_dataset
from tools.research_dataset_import import import_demo_visual_affordance
from tools.research_dataset_read_models import (
    build_experiments_model,
    build_literature_model,
    build_project_graph_model,
    build_project_summary_model,
    build_sources_model,
    project_exists_in_dataset,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DEMO_ROOT = REPO_ROOT / "examples" / "workspaces" / "demo-visual-affordance"


class ResearchDatasetReadModelsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "demo"
        shutil.copytree(DEMO_ROOT, self.root)
        initialize_dataset(self.root)
        import_demo_visual_affordance(self.root, reset=True)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_project_summary_model_uses_db(self) -> None:
        self.assertTrue(project_exists_in_dataset(self.root, "DemoVisualAffordance"))
        model = build_project_summary_model(self.root, "DemoVisualAffordance")
        self.assertEqual(model["project_id"], "DemoVisualAffordance")
        self.assertEqual(model["title"], "Demo Visual Affordance")
        self.assertGreaterEqual(model["source_count"], 9)
        self.assertGreaterEqual(model["claim_count"], 4)
        self.assertGreaterEqual(model["evidence_count"], 8)
        self.assertEqual(model["source"], "research-pilot.db")

    def test_sources_model_includes_paper_understanding_counts(self) -> None:
        model = build_sources_model(self.root, "DemoVisualAffordance")
        self.assertEqual(model["project_id"], "DemoVisualAffordance")
        self.assertGreaterEqual(len(model["sources"]), 9)
        zhang = next(item for item in model["sources"] if "2602.20501" in item.get("url", "") or "zhang2026" in item["source_id"])
        self.assertEqual(zhang["reading_depth"], "deep_structured")
        self.assertIn("paper_understanding_count", zhang)

    def test_project_graph_model_preserves_qcewl_and_links(self) -> None:
        model = build_project_graph_model(self.root, "DemoVisualAffordance")
        kinds = {node["kind"] for node in model["nodes"]}
        self.assertTrue({"question", "claim", "evidence", "warrant", "limitation"}.issubset(kinds))
        self.assertGreaterEqual(len(model["links"]), 6)
        link = next(item for item in model["links"] if item.get("warrant"))
        self.assertTrue(link["limitations"])
        self.assertEqual(model["source"], "research-pilot.db")

    def test_experiments_model_preserves_imported_origin_and_metrics(self) -> None:
        model = build_experiments_model(self.root, "DemoVisualAffordance")
        self.assertEqual(model["schema_version"], "experiments-v1")
        self.assertEqual(model["summary"]["total_experiments"], 4)
        self.assertEqual(model["summary"]["total_runs"], 5)
        self.assertEqual(model["summary"]["imported_evidence_runs"], 5)
        self.assertEqual(model["summary"]["local_result_runs"], 0)
        run3 = next(run for run in model["runs"] if run["id"] == "RUN3")
        metric_values = {metric["name"]: metric["value"] for metric in run3["metrics"]}
        self.assertEqual(metric_values["KLD"], "1.493")
        self.assertEqual(metric_values["SIM"], "0.326")
        self.assertEqual(metric_values["NSS"], "1.090")

    def test_literature_model_has_lanes_items_and_relations(self) -> None:
        model = build_literature_model(self.root, "DemoVisualAffordance")
        self.assertEqual(model["project"], "DemoVisualAffordance")
        self.assertGreaterEqual(len(model["routes"]), 4)
        self.assertGreaterEqual(len(model["papers"]), 9)
        self.assertIn("source", model)
        self.assertEqual(model["source"], "research-pilot.db")


if __name__ == "__main__":
    unittest.main()
```

- [ ] Run:

```bash
python3 -m unittest tests.test_research_dataset_read_models -v
```

Expected:

```text
Ran 5 tests
OK
```

### Commit

```bash
git add tools/research_dataset_read_models.py tests/test_research_dataset_read_models.py
git commit -m "feat: add db backed dashboard read models"
```

## Task 5: Research Browser API DB-First Fallback

**Files:**

- Modify: `tools/research_browser_server.py`
- Create: `tests/test_research_browser_db_fallback.py`

### Required Behavior

Do not change dashboard frontend.

Server endpoints must prefer DB-backed read models only when:

```text
research-pilot.db exists
requested project exists in DB
DB-backed builder returns valid model
```

Otherwise existing legacy path must run.

Endpoints to integrate:

```text
/api/project-graph
/api/experiments
/api/experiment-proposals
```

For `/api/experiment-proposals`, keep legacy wrapper shape. Set `experiments_model` to DB-backed experiments model only when `project_exists_in_dataset(root, project_id)` returns `True` and `build_experiments_model(root, project_id)` returns a dict with `schema_version == "experiments-v1"`.

Do not add source or literature server endpoints in this plan. Existing lineage dashboard reads `.dashboard/index.json`; this plan provides `build_literature_model()` for architecture coverage, not a dashboard route.

### Tests

- [ ] Write `tests/test_research_browser_db_fallback.py`.

```python
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tools.research_browser_server import handle_experiments_request, handle_project_graph_request
from tools.research_dataset import initialize_dataset
from tools.research_dataset_import import import_demo_visual_affordance


REPO_ROOT = Path(__file__).resolve().parents[1]
DEMO_ROOT = REPO_ROOT / "examples" / "workspaces" / "demo-visual-affordance"


class ResearchBrowserDbFallbackTest(unittest.TestCase):
    def test_experiments_endpoint_prefers_db_when_project_imported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "demo"
            shutil.copytree(DEMO_ROOT, root)
            initialize_dataset(root)
            import_demo_visual_affordance(root, reset=True)

            status, payload = handle_experiments_request(root, "/api/experiments?project=DemoVisualAffordance")
            model = json.loads(payload.decode("utf-8"))

        self.assertEqual(status, 200)
        self.assertEqual(model["source_boundary"], "project_experiments_from_research_dataset")
        self.assertEqual(model["summary"]["total_experiments"], 4)
        self.assertEqual(model["summary"]["imported_evidence_runs"], 5)

    def test_experiments_endpoint_falls_back_to_legacy_without_db(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "demo"
            shutil.copytree(DEMO_ROOT, root)
            status, payload = handle_experiments_request(root, "/api/experiments?project=DemoVisualAffordance")
            model = json.loads(payload.decode("utf-8"))

        self.assertEqual(status, 200)
        self.assertEqual(model["source_boundary"], "project_experiments_read_model_not_graph_truth")
        self.assertEqual(model["summary"]["total_experiments"], 4)

    def test_project_graph_endpoint_prefers_db_when_project_imported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "demo"
            shutil.copytree(DEMO_ROOT, root)
            initialize_dataset(root)
            import_demo_visual_affordance(root, reset=True)

            status, payload = handle_project_graph_request(root, "/api/project-graph?project=DemoVisualAffordance")
            model = json.loads(payload.decode("utf-8"))

        self.assertEqual(status, 200)
        self.assertEqual(model["source"], "research-pilot.db")
        kinds = {node["kind"] for node in model["nodes"]}
        self.assertTrue({"question", "claim", "evidence", "warrant", "limitation"}.issubset(kinds))


if __name__ == "__main__":
    unittest.main()
```

- [ ] Run:

```bash
python3 -m unittest tests.test_research_browser_db_fallback -v
```

Expected:

```text
Ran 3 tests
OK
```

- [ ] Run legacy dashboard tests:

```bash
python3 -m unittest tests.test_dashboard_public tests.test_demo_project tests.test_related_work_lineage_dashboard -v
```

Expected:

```text
OK
```

### Commit

```bash
git add tools/research_browser_server.py tests/test_research_browser_db_fallback.py
git commit -m "feat: prefer db backed dashboard read models"
```

## Task 6: Research Dataset CLI

**Files:**

- Create: `tools/research_dataset_cli.py`
- Add tests to: `tests/test_research_dataset_import.py`

### Required CLI

Commands:

```bash
python3 tools/research_dataset_cli.py init --repo <workspace>
python3 tools/research_dataset_cli.py import-legacy --repo <workspace> --project <ProjectId> --reset
python3 tools/research_dataset_cli.py summary --repo <workspace> --project <ProjectId>
```

Outputs must be JSON to stdout.

`init` output:

```json
{"valid": true, "db": "research-pilot.db", "schema_version": 1}
```

`import-legacy` output:

```json
{"valid": true, "project_id": "DemoVisualAffordance", "sources": 9, "understanding_nodes": 24, "understanding_links": 7, "experiments": 4, "experiment_runs": 5, "experiment_metrics": 15, "literature_lanes": 4, "literature_items": 9, "warnings": []}
```

`summary` output:

```json
{"valid": true, "project_id": "DemoVisualAffordance", "source": "research-pilot.db", "title": "Demo Visual Affordance", "source_count": 9, "claim_count": 4, "evidence_count": 8, "experiment_count": 4}
```

### Tests

Add to `tests/test_research_dataset_import.py`:

```python
    def test_cli_init_import_and_summary_return_json(self) -> None:
        import json
        import subprocess
        import sys

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "demo"
            shutil.copytree(DEMO_ROOT, root)
            init = subprocess.run(
                [sys.executable, "tools/research_dataset_cli.py", "init", "--repo", str(root)],
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                check=True,
            )
            self.assertTrue(json.loads(init.stdout)["valid"])
            imported = subprocess.run(
                [
                    sys.executable,
                    "tools/research_dataset_cli.py",
                    "import-legacy",
                    "--repo",
                    str(root),
                    "--project",
                    "DemoVisualAffordance",
                    "--reset",
                ],
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                check=True,
            )
            self.assertEqual(json.loads(imported.stdout)["project_id"], "DemoVisualAffordance")
            summary = subprocess.run(
                [
                    sys.executable,
                    "tools/research_dataset_cli.py",
                    "summary",
                    "--repo",
                    str(root),
                    "--project",
                    "DemoVisualAffordance",
                ],
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                check=True,
            )
            payload = json.loads(summary.stdout)
            self.assertTrue(payload["valid"])
            self.assertEqual(payload["project_id"], "DemoVisualAffordance")
            self.assertEqual(payload["source"], "research-pilot.db")
```

- [ ] Run:

```bash
python3 -m unittest tests.test_research_dataset_import -v
```

Expected:

```text
Ran 4 tests
OK
```

### Commit

```bash
git add tools/research_dataset_cli.py tests/test_research_dataset_import.py
git commit -m "feat: add research dataset cli"
```

## Task 7: Documentation Polish

**Files:**

- Modify: `tools/README.md`
- Modify: `docs/guides/workspace.md`
- Modify: `README.md`

### Required Copy

Add or update wording:

```text
Research-Pilot workspaces have one research-pilot.db at the workspace root.
That DB is the workspace-local dataset: many projects, partitioned by project_id.
The dashboard remains read-only and consumes API read models.
Agent tools are the intended write layer.
Legacy Markdown/JSONL/JSON artifacts remain import/export/report inputs during migration.
```

Do not claim every old CLI is migrated.

Do not claim cloud sync exists.

Do not claim dashboard redesign is complete.

### Tests

- [ ] Run docs/copy grep:

```bash
rg -n "cloud sync exists|dashboard redesign complete|all CLIs migrated" README.md docs/guides/workspace.md tools/README.md
```

Expected:

```text
no matches
```

- [ ] Run core tests:

```bash
python3 -m unittest tests.test_research_dataset_schema tests.test_research_dataset_writer tests.test_research_dataset_import tests.test_research_dataset_read_models tests.test_research_browser_db_fallback -v
```

Expected:

```text
OK
```

### Commit

```bash
git add README.md docs/guides/workspace.md tools/README.md
git commit -m "docs: explain local dataset architecture"
```

## Task 8: Full Verification

**Files:**

- No new files unless a test exposes a defect.

### Required Commands

- [ ] Run architecture test suite:

```bash
python3 -m unittest tests.test_research_dataset_schema tests.test_research_dataset_writer tests.test_research_dataset_import tests.test_research_dataset_read_models tests.test_research_browser_db_fallback -v
```

Expected:

```text
OK
```

- [ ] Run existing dashboard/demo suite:

```bash
python3 -m unittest tests.test_dashboard_public tests.test_demo_project tests.test_related_work_lineage_dashboard tests.test_understanding_schema_contracts tests.test_understanding_store tests.test_understanding_cli -v
```

Expected:

```text
OK
```

- [ ] Run generated artifact leak check:

```bash
find examples/workspaces/demo-visual-affordance -name research-pilot.db -o -name graph.db -o -name .dashboard
```

Expected:

```text
no committed generated artifact paths
```

If `.dashboard` appears because local server generated it, do not commit it. Remove generated files only if they are created by this task and are untracked.

- [ ] Run dashboard server smoke manually:

```bash
python3 tools/research_browser_server.py --repo examples/workspaces/demo-visual-affordance --host 127.0.0.1 --port 8899
```

In another shell:

```bash
curl -s 'http://127.0.0.1:8899/api/experiments?project=DemoVisualAffordance' | python3 -m json.tool | sed -n '1,80p'
curl -s 'http://127.0.0.1:8899/api/project-graph?project=DemoVisualAffordance' | python3 -m json.tool | sed -n '1,80p'
```

Expected:

```text
experiments endpoint returns total_experiments 4 and imported_evidence_runs 5
project graph endpoint returns question/claim/evidence/warrant/limitation nodes
```

Stop the server after smoke test.

### Final Commit

If previous tasks were committed individually, no extra commit is required. If work was batched, commit:

```bash
git add tools tests README.md docs/guides/workspace.md tools/README.md
git commit -m "feat: add project centered local dataset architecture"
```

## Self-Review Checklist For Implementer

Before final handoff, verify:

- [ ] `research-pilot.db` is primary local store for new path.
- [ ] Legacy files are not deleted.
- [ ] Dashboard frontend files are unchanged unless user approved a separate frontend fix.
- [ ] DB read models preserve existing API shapes for `/api/experiments` and `/api/project-graph`.
- [ ] Q/C/E/W/L nodes are present after demo import.
- [ ] Reasoning links preserve warrants and limitations.
- [ ] Experiments preserve `origin_type=imported_paper` for all five demo runs.
- [ ] Demo metrics preserve KLD/SIM/NSS exact values.
- [ ] Write service records ActivitySession, Update, and AuditEvent rows.
- [ ] No cloud sync/auth/permissions code is introduced.
- [ ] No generated DB files are committed.

## Execution Notes For Subagents

Use one fresh worker per task. Each worker must:

- Read the PRD and this plan before editing.
- Touch only files listed in the task.
- Run the task-specific tests before reporting completion.
- Report exact commands and pass/fail output.
- Stop if they believe dashboard frontend changes are required.
- Stop if they need to weaken Q/C/E/W/L semantics.
- Stop if they cannot preserve imported/local experiment distinction.

Recommended worker model when dispatching:

```text
gpt-5.5 medium
```
