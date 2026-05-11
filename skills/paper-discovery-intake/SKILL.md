---
name: paper-discovery-intake
description: Use when the user wants to add Zotero-first paper/source identity into a Research Pilot project.
argument-hint: "<project> <paper-id> <title>"
---

# Paper Discovery Intake

Create a project-local source dossier from Zotero identity fields, with DOI/arXiv/URL refs allowed as supporting identity.

Use Zotero identity as the normal path:

```bash
python3 "$PLUGIN_ROOT/tools/source_intake_cli.py" intake --repo "$WORKSPACE_PATH" --project "$PROJECT_ID" --paper "$PAPER_ID" --title "$TITLE" --zotero-key "$ZOTERO_ITEM_KEY" --json
```

Use DOI/arXiv/URL/manual refs only for setup, dry-run, or emergency source identity capture:

```bash
python3 "$PLUGIN_ROOT/tools/source_intake_cli.py" intake --repo "$WORKSPACE_PATH" --project "$PROJECT_ID" --paper "$PAPER_ID" --title "$TITLE" --doi "$DOI" --url "$URL" --json
```

This skill currently records durable source identity. It does not replace Zotero as the paper source of truth.
