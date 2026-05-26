---
description: Agent-internal compatibility runbook for starting or inspecting a Research Pilot workspace from natural-language project-tracking intent.
argument-hint: "[workspace_path]"
---

# Research Pilot Start/Track Runbook

This is an agent-internal compatibility runbook, not a user command surface.

Users should ask a natural-language intent:

```text
Use Research Pilot to track this project.
```

The agent may use this runbook to resolve plugin root, initialize a workspace, inspect status, and hand off to `research-pilot-first-run`.

## Arguments

- `workspace_path`: optional path for the private research workspace.

If no path is provided:

- if the current directory is already a Research Pilot workspace, inspect it and continue;
- otherwise ask for one concise workspace path.

## Plugin Root

Resolve `PLUGIN_ROOT` in this order:

```text
~/.research-pilot/repo
~/.research-pilot-plugin
current directory, only if it is the Research Pilot plugin repo
```

Stop with a clear install instruction if no plugin root is found:

```bash
curl -fsSL https://raw.githubusercontent.com/QZhang2111/Research-Pilot/main/install.sh | bash
```

## Natural-Language Operation

When the user asks to use Research Pilot to track a project, the agent must resolve `PLUGIN_ROOT`, run `tools/research_pilot_init.py` from that plugin root, and report the same completion summary.

## Workflow

1. Classify current location:
   - `plugin_repo`: plugin source, not user research memory.
   - `initialized_workspace`: continue in this workspace.
   - `plain_directory`: ask for or use `workspace_path`.
   - `unknown`: explain uncertainty before writing.
2. Initialize the workspace if missing:

```bash
python3 "$PLUGIN_ROOT/tools/research_pilot_init.py" "$WORKSPACE_PATH"
```

3. Explain the boundary once:

```text
Research Pilot plugin = hidden agent capability.
Workspace = visible private research memory.
research-pilot.db = primary workspace dataset.
Dashboard = read-only observer.
Strict review = optional graph/D* mode.
```

4. Collect only minimum first-project intake:
   - project id or short name;
   - one-sentence research direction;
   - first question, uncertainty, or claim;
   - optional Zotero setup/status only if the user provides a Zotero source or asks for Zotero setup.
5. Use `research-pilot-first-run` to create missing project skeleton files.
6. Record initial project brief or UnderstandingUpdate.
7. Offer to open the dashboard.
8. Use strict-review D* only if the user explicitly asks for formal graph review.

## Completion

End with:

```text
Workspace:
Project:
Initial memory:
Dashboard:
Strict review:
Next natural prompts:
```
