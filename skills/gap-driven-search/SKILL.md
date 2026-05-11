---
name: gap-driven-search
description: Use when a graph gap or Evidence Need should become a targeted paper-search contract or candidate lead list.
argument-hint: "<project> <gap-id>"
---

# Gap-Driven Search

This skill is a workflow boundary in the current public extraction.

Use `project-gap-analysis` first:

```bash
python3 "$PLUGIN_ROOT/tools/project_gap_cli.py" detect --repo "$WORKSPACE_PATH" --project "$PROJECT_ID" --json
```

If the user asks to search, explain that full gap-search tooling is a later extraction slice unless present in this plugin version.

Do not approve papers, write Zotero records, or append graph events.

