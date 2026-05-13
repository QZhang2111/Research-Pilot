# Research Pilot Tools

Tools execute local Research Pilot workflows. They are not research truth.

Truth boundaries:

- `wiki/graphs/events/**/*.jsonl` is append-only graph truth.
- `wiki/program/` is context-only taste and north-star memory, not evidence or graph truth.
- `wiki/graphs/graph.db`, snapshots, reports, and `.dashboard/index.json` are rebuildable read models.
- Zotero remains the normal paper metadata/PDF source of truth.

## Current Areas

| Area | Files | Responsibility |
| --- | --- | --- |
| workspace | `research_pilot_init.py` | Create private user workspace from templates. |
| graph | `graph_store.py`, `graph_validate.py`, `build_graph_snapshot.py`, `build_graph_db.py`, `build_project_graph_report.py`, `graph_query_cli.py` | Validate/replay graph events and query read models. |
| delta | `graph_delta_api.py`, `graph_delta_cli.py` | Dry-run, register, and decide human-gated graph deltas. |
| dossier | `paper_dossier_cli.py`, `source_intake_cli.py` | Create project-local paper/source dossiers and export proposed deltas. |
| gap | `project_gap_cli.py`, `project_next_action_cli.py`, `gap_search_cli.py`, `research_gap_discovery_cli.py` | Detect graph gaps, recommend next workflow moves, and derive paper-search leads. |
| experiment | `project_experiment_cli.py` | Generate read-only experiment proposals from graph claims. |
| zotero | `zotero_bridge.py` | Dry-run/apply Zotero metadata/card sync and status tag mirror when configured. |
| dashboard | `build_dashboard_index.py`, `research_browser_server.py` | Build and serve dashboard read models. |

Do not store private PDFs, Zotero credentials, generated SQLite files, or dashboard indexes in this public repo.
