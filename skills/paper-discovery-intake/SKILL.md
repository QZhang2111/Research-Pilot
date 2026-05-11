---
name: paper-discovery-intake
description: Use when the user wants to add paper/source identity into a Research Pilot project without requiring Zotero API access.
argument-hint: "<project> <paper-id> <title>"
---

# Paper Discovery Intake

Create a project-local source dossier from manual or Zotero identity fields.

Use Zotero identity when available:

```bash
python3 "$PLUGIN_ROOT/tools/source_intake_cli.py" intake --repo "$WORKSPACE_PATH" --project "$PROJECT_ID" --paper "$PAPER_ID" --title "$TITLE" --zotero-key "$ZOTERO_ITEM_KEY" --json
```

Use manual fallback when Zotero API credentials are unavailable:

```bash
python3 "$PLUGIN_ROOT/tools/source_intake_cli.py" intake --repo "$WORKSPACE_PATH" --project "$PROJECT_ID" --paper "$PAPER_ID" --title "$TITLE" --doi "$DOI" --url "$URL" --json
```

This skill does not call the Zotero API in MVP-E. It records durable source identity and keeps the workflow usable without keys.
