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
  --arxiv "$ARXIV_ID" \
  --url "$URL" \
  --source-ref "$SOURCE_REF" \
  --source-ref "$ANOTHER_SOURCE_REF" \
  --json
```

Use CLI flags by source identity:

- PDF path: `--source-ref "file:/absolute/path/to/source.pdf"`
- Markdown note: `--source-ref "note:/absolute/path/to/note.md"` or another stable note locator.
- Experiment result: `--source-ref "experiment:<experiment-id-or-result-ref>"`
- Manual reference: `--source-ref "manual:<citation-or-description>"`
- URL: `--url "$URL"`
- DOI: `--doi "$DOI"`
- arXiv: `--arxiv "$ARXIV_ID"`
- Zotero item: `--zotero-key "$ZOTERO_ITEM_KEY"`

Repeat `--source-ref` for multiple file, note, experiment, or manual references.

## Human Gate

Agent may create candidate dossiers and source identity records.

Human decides paper approval, project-core status, global-core status, and any D* graph update.
