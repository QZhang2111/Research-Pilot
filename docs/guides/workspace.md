# Workspace Guide

Research Pilot public repo is plugin source. User workspace is private research memory.

Initialized workspace:

```text
research-pilot.db
AGENTS.md
wiki/
  index.md
  log.md
  program/
  projects/
  graphs/events/
  graphs/schema/
  _system/workflows/
  _system/templates/
.research-pilot/
  config.example.toml
```

## Primary Dataset

`research-pilot.db` is the primary local workspace dataset. It stores project-scoped research memory by `project_id`.

Normal users interact through chat. Agents write through Research Pilot tools. The dashboard reads generated API/read models.

Do not publish a workspace unless it is explicitly sanitized.

Research-Pilot workspaces have one `research-pilot.db` at the workspace root. It is the local dataset for that workspace, not a repo-global database and not a dashboard cache. Projects are rows in the `projects` table; project-owned records in sources, understanding, experiments, literature, updates, and audit tables are connected by `project_id`.

Do not publish PDFs, Zotero credentials, local Zotero databases, private workspace datasets, or dashboard read models unless explicitly sanitized.
Generated dashboard/read-model artifacts include `.dashboard/`, `wiki/graphs/graph.db`, and `wiki/graphs/snapshots/`.
Legacy Markdown, JSONL, and JSON workspace artifacts can still be used for imports, exports, reports, and fallback workflows while migration continues.

## Demo Project

New workspaces include `DemoVisualAffordance` by default. Initialization copies the sanitized demo source files into the workspace and imports the demo project into the workspace `research-pilot.db`.

The public repo also includes an example workspace at `examples/workspaces`. Treat that directory as a normal initialized workspace for demos: it has one root `research-pilot.db`, and `DemoVisualAffordance` is one project in that DB.

The reusable demo seed lives under `examples/archive/seed-workspaces/demo-visual-affordance` and keeps durable seed inputs only:

- project markdown under `wiki/projects/DemoVisualAffordance/`;
- graph events under `wiki/graphs/events/projects/DemoVisualAffordance.jsonl`;
- understanding events under `wiki/understanding/events/DemoVisualAffordance.jsonl`.

The user workspace DB created by `research_pilot_init.py` is the default runtime dataset. Generated dashboard/index, graph database, and graph snapshots are intentionally rebuildable and should not be treated as demo source.

The dashboard is read-only and does not create or delete projects.

## Agent/Internal Fallback

Start without the demo:

```bash
python3 "$PLUGIN_ROOT/tools/research_pilot_init.py" "$WORKSPACE_PATH" --no-demo
```

## Program Context

`wiki/program/` is context-only memory for long-term research taste, north-star framing, and background preferences.

It is not graph truth, not evidence, and not a project decision source. Agents may read it to understand the user's research style, but must not use it to decide project direction or copy it into project graph truth.

## Workspace Stages

Research Pilot workspaces are stage-aware:
- no workspace yet;
- workspace initialized;
- project exists;
- project has sources;
- project has understanding updates;
- project has literature structure;
- project has experiment design/results;
- strict-review graph data exists;
- dashboard read models need refresh.

The agent should inspect stage before suggesting next actions.
