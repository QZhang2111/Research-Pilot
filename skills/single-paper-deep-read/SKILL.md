---
name: single-paper-deep-read
description: Use when the user wants an agent to create or update a project-local paper dossier from one paper or source, without requiring Zotero.
argument-hint: "<project> <paper-id> <source>"
---

# Single Paper Deep Read

Create or update a project-local paper dossier:

```text
wiki/projects/<Project>/papers/<paper-id>/index.md
```

If the dossier does not exist, create it with:

```bash
python3 "$PLUGIN_ROOT/tools/paper_dossier_cli.py" create --repo "$WORKSPACE_PATH" --project "$PROJECT_ID" --paper "$PAPER_ID" --title "$TITLE"
```

Then fill the dossier with source identity, claims, evidence, methods, limitations, project relevance, and possible graph delta JSON proposals.

Do not mark paper findings as project-core or global-core without explicit human approval.
