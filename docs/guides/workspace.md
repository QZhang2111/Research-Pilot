# Workspace Guide

Research Pilot public repo is plugin source. User workspace is private research memory.

Initialized workspace:

```text
AGENTS.md
wiki/
  index.md
  log.md
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
