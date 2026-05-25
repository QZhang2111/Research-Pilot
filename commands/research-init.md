---
description: Initialize or inspect a private Research Pilot workspace, then guide first project setup and the first human-gated graph update.
argument-hint: "[workspace_path]"
---

# Research Pilot Init Workflow

Initialize Research Pilot for a private research workspace. This is an agent workflow document, not a guaranteed Codex slash command registration.

Status: **chat-first shim**. Keep this command document as an installable
fallback route. The core product surface is agent chat plus local workspace
dataset plus read-only dashboard, not a slash-command UI.

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

## Chat-First Operation

When the user asks to initialize Research Pilot, the agent must resolve `PLUGIN_ROOT`, run `tools/research_pilot_init.py` from that plugin root, and report the same completion summary. Slash command visibility is not required.

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
Zotero = paper manager.
Graph events = project-understanding truth.
Human gate = required before graph truth changes.
```

4. Collect only minimum first-project intake:
   - project id or short name;
   - one-sentence research direction;
   - first question, uncertainty, or claim;
   - Zotero status: configured now or later.
5. Use `research-pilot-first-run` to create missing project skeleton files.
6. Convert the first question or claim into a D* delta proposal.
7. Dry-run the delta.
8. Stop for human `accept`, `reject`, `park`, or `revise`.
9. Only after explicit acceptance, append graph events and rebuild read models.

## Completion

End with:

```text
Workspace:
Project:
First graph update:
Human gate result:
Generated read models:
Next possible moves:
```
