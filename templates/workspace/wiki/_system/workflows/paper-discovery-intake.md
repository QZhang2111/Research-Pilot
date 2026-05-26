# Source Intake

Purpose: add source identity into Research Pilot project memory without forcing a paper-manager workflow.

Accepted source types:

- PDF path;
- URL;
- arXiv link;
- DOI;
- Markdown note;
- experiment result;
- manual reference;
- Zotero item.

## Core Boundary

Research Pilot records project-scoped source identity, source state, and relevance. Zotero is an optional supported adapter for paper metadata/PDF management; it is not required for first-run value.

## Command

Agent may use this internal tool when command-line support is useful:

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

DOI/arXiv/URL/manual refs, files, notes, experiment refs, and Zotero keys are supported source identity inputs.

## Human Gate

Agent may create candidate dossiers and source identity records.

Human decides paper approval, project-core status, global-core status, and any D* graph update.
