# Single Paper Deep Read Workflow

Use this workflow when a user asks an agent to read one paper into a project-local dossier.

## Boundary

- Source identity can come from PDF, URL, arXiv, DOI, manual note, experiment result, or Zotero.
- Zotero is optional unless the user gives a Zotero item or asks for Zotero setup.
- The source/paper note is project-local working memory, not global approved memory.
- Project-level impact should be recorded through normal project memory; use strict review only when formal graph changes are requested or required.

## Output

Create or update:

```text
wiki/projects/<Project>/papers/<paper-id>/index.md
```

Use:

```bash
python3 tools/paper_dossier_cli.py create --repo "$WORKSPACE" --project "$PROJECT" --paper "$PAPER_ID" --title "$TITLE"
```

Then fill the dossier with:

- source identity;
- key claims;
- evidence and methods;
- assumptions and limitations;
- project relevance;
- proposed graph delta JSON blocks when the paper changes project understanding.

Strict-review graph deltas remain proposals until the human explicitly approves them.
