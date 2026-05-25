---
name: project-gap-discovery
description: Use when the user wants papers to consider for a graph gap or missing evidence need.
argument-hint: "<project> <gap-id>"
---

# Project Gap Discovery

Status: **transition**. Keep for graph-derived evidence discovery. Do not expose
as a core first-run workflow; future source/literature discovery should absorb
this path.

This skill owns the user-facing path:

```text
graph gap -> evidence need -> search -> lead scoring -> human chooses deep-read
```

Run the user-facing discovery command:

```bash
python3 "$PLUGIN_ROOT/tools/research_gap_discovery_cli.py" run --repo "$WORKSPACE_PATH" --project "$PROJECT_ID" --gap "$GAP_TARGET" --source memory --json
```

Do not add papers to Zotero, approve candidates, or append graph events.
