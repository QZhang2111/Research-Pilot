# Research Pilot Tools

Tools execute local Research Pilot workflows. They are not research truth.

Truth boundaries:

- `wiki/understanding/events/**/*.jsonl` is normal product truth for ambient agent understanding updates.
- `wiki/graphs/events/**/*.jsonl` is advanced graph truth.
- `research-pilot.db` is the workspace-local dataset: one DB per workspace, many projects partitioned by `project_id`.
- `examples/workspaces` is the public example workspace. Its root `research-pilot.db` contains `DemoVisualAffordance`.
- `examples/archive/seed-workspaces/demo-visual-affordance` is the reusable legacy seed copied by workspace init.
- `wiki/program/` is context-only taste and north-star memory, not evidence or graph truth.
- `wiki/graphs/graph.db`, snapshots, reports, and `.dashboard/index.json` are rebuildable read models.
- Zotero remains the normal paper metadata/PDF source of truth.

The dashboard remains read-only and consumes API read models. Agent tools are the intended write layer. Legacy Markdown/JSONL/JSON artifacts remain import/export/report inputs during migration.

## Public Surface Policy

Treat `tools/` as implementation API, not product navigation. The normal user
path is:

```text
agent chat -> workspace research-pilot.db -> read-only dashboard
```

Tool groups below are intentionally split by product status:

- **Core**: first-run and dashboard-visible runtime path.
- **Supported adapters**: useful source/literature bridges that feed project
  understanding.
- **Advanced compatibility**: graph/delta machinery kept for rigor, migration,
  and advanced review mode. Do not present these as first-run concepts.
- **Transition**: still tested and supported, but product framing is being
  demoted or renamed. Do not build new first-run UX around these names.

Do not delete a transition or advanced tool only because it is not first-run.
Delete only after its tests, skill routes, docs, and migration path are removed
or replaced.

## Core Runtime

| Area | Files | Responsibility |
| --- | --- | --- |
| workspace | `research_pilot_init.py` | Create user workspaces and default demo dataset. |
| status | `research_pilot_status.py`, `plugin_health.py` | Inspect workspace/plugin health for chat-first routing. |
| dataset schema | `research_dataset.py` | Define and initialize the root `research-pilot.db` workspace dataset. |
| dataset writes | `research_dataset_writer.py` | Validate typed update packets and write project dataset rows. |
| dataset import | `research_dataset_import.py` | Import legacy workspace project artifacts into `research-pilot.db`. |
| dataset read models | `research_dataset_read_models.py` | Build API-facing read models from `research-pilot.db` with legacy fallback where supported. |
| dataset CLI | `research_dataset_cli.py` | Initialize datasets, import legacy projects, and print dataset-backed summaries. |
| understanding | `understanding_store.py`, `understanding_cli.py` | Record ambient UnderstandingUpdates and build ProjectUnderstanding read models. |
| dashboard | `build_dashboard_index.py`, `research_browser_server.py` | Build/serve read-only dashboard views and DB-backed APIs. |

## Supported Adapters

| Area | Files | Responsibility |
| --- | --- | --- |
| source intake | `source_intake_cli.py` | Capture source identity and create project-local source notes. |
| paper deep read | `paper_dossier_cli.py` | Create/validate deep-read paper notes and export proposed graph deltas. |
| literature structure | `related_work_lineage_cli.py` | Create, validate, and summarize paper-only related-work lineage artifacts. |
| Zotero | `zotero_setup.py`, `zotero_bridge.py` | Configure Zotero metadata/PDF bridge and optional sync helpers. |
| jobs | `job_records.py` | Track long-running agent work as execution state, not project truth. |

## Advanced Compatibility

These tools are intentionally retained, but they are not first-run product
concepts. They support graph rigor, legacy imports, reports, and optional review
mode.

| Area | Files | Responsibility |
| --- | --- | --- |
| graph events | `graph_store.py`, `graph_validate.py` | Validate/replay append-only graph events. |
| graph read models | `build_graph_snapshot.py`, `build_graph_db.py`, `build_project_graph_report.py`, `graph_query_cli.py` | Build/query legacy graph read models and reports. |
| graph deltas | `graph_delta_api.py`, `graph_delta_cli.py` | Dry-run, register, and decide human-gated graph deltas. |

## Transition Surface

These tools remain tested because current workflows and demos still depend on
them. Product naming should move away from these as top-level concepts.

| Area | Files | Current status |
| --- | --- | --- |
| next action | `project_next_action_cli.py` | Keep as advanced router. Do not expose as core `Next Moves` product surface. |
| gap search | `project_gap_cli.py`, `gap_search_cli.py`, `research_gap_discovery_cli.py` | Keep as graph-derived evidence discovery. Do not present as core workflow system. |
| experiment proposal | `project_experiment_cli.py`, `experiment_store.py` | Keep compatibility. New work should move toward project experiment design/result records, not proposal-only framing. |

Do not store private PDFs, Zotero credentials, private workspace datasets, generated graph SQLite files, or dashboard indexes in this public repo.
