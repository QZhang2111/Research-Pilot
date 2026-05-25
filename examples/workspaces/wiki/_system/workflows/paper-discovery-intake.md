# Paper Discovery Intake

Purpose: add paper/source identity into the Zotero-first Research Pilot workflow without approving the paper or changing project graph truth.

## Core Boundary

Zotero is the normal source of truth for paper metadata, PDFs, collections, and tags.

Research Pilot source intake records durable identity in a project-local paper dossier. It does not approve papers, set project-core status, or append graph events.

## Command

```bash
python3 tools/source_intake_cli.py intake \
  --repo "$WORKSPACE" \
  --project "$PROJECT" \
  --paper "$PAPER_ID" \
  --title "$TITLE" \
  --zotero-key "$ZOTERO_ITEM_KEY" \
  --doi "$DOI" \
  --url "$URL" \
  --json
```

Zotero item key is the preferred identity. DOI/arXiv/URL/manual refs are supporting source identity and setup/dry-run capture, not a replacement paper manager.

## Human Gate

Agent may create candidate dossiers and source identity records.

Human decides paper approval, project-core status, global-core status, and any D* graph update.

