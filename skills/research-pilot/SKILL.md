---
name: research-pilot
description: Use when the user wants to initialize, inspect, or operate a Research Pilot workspace for agent-operated research memory.
argument-hint: "[init <path>|inspect]"
---

# Research Pilot

Research Pilot is the primary router skill for agent-operated research memory.

## Current MVP-A Capabilities

- Explain plugin vs workspace boundary.
- Initialize a private research workspace.
- Inspect whether the current directory looks like a Research Pilot workspace.

Graph querying, Zotero paper workflows, dashboard launching, and paper-to-delta automation are extracted in later MVP slices.

## Workspace Detection

A directory is a Research Pilot workspace when it has:

```text
AGENTS.md
wiki/index.md
wiki/log.md
.research-pilot/config.example.toml or .research-pilot/config.toml
```

## Intent Routing

### Initialize Workspace

When the user asks to initialize/create/set up a research workspace:

1. Resolve the requested path. If no path is provided, ask for one concise path.
2. Resolve the plugin root by locating the installed `research-pilot` skill symlink and going two directories up to the Research Pilot repo checkout.
3. Run:

```bash
python3 "$PLUGIN_ROOT/tools/research_pilot_init.py" "$WORKSPACE_PATH"
```

4. Report the workspace path and next steps.

### Inspect Workspace

When the user asks to inspect current Research Pilot status during MVP-A:

1. Check for the workspace detection files.
2. If present, report that the workspace skeleton is initialized.
3. If absent, explain that the user should run initialization first.

## Boundaries

Do not claim graph workflows, Zotero workflows, dashboard support, or paper deep-read automation are available until those MVP slices are extracted.

Do not store private research data in the public plugin repo.
