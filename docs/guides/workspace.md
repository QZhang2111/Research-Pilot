# Workspace Guide

Research Pilot public repo is plugin source. User workspace is private research memory.

Initialized workspace:

```text
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

Do not publish a workspace unless it is explicitly sanitized.

Do not commit PDFs, Zotero credentials, local Zotero databases, generated SQLite files, or dashboard read models.

## Demo Project

New workspaces include `DemoVisualAffordance` by default. It is sanitized example data for learning the workflow and inspecting dashboard changes.

Delete it from a workspace:

```bash
rm -rf wiki/projects/DemoVisualAffordance
rm -f wiki/graphs/events/projects/DemoVisualAffordance.jsonl
python3 "$PLUGIN_ROOT/tools/build_dashboard_index.py" --repo "$PWD" --output .dashboard/index.json
```

The dashboard is read-only and does not delete projects.

## Program Context

`wiki/program/` is context-only memory for long-term research taste, north-star framing, and background preferences.

It is not graph truth, not evidence, and not a project decision source. Agents may read it to understand the user's research style, but must not use it to decide project direction or copy it into project graph truth.

## Workspace Stages

Research Pilot workspaces are stage-aware:
- empty workspace;
- project shell;
- graph started;
- papers present;
- open deltas;
- stale read models;
- Zotero setup needed.

The agent should inspect stage before suggesting next actions.
