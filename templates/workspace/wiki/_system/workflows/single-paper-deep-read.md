# Single Paper Deep Read Workflow

Use this workflow when a user asks an agent to read one paper into a project-local dossier.

## Boundary

- Normal paper source management is Zotero-first.
- DOI/arXiv/URL/manual notes may be used only as setup, dry-run, or emergency source identity capture.
- The paper dossier is project-local working memory, not global approved memory.

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

Graph deltas remain proposals until the human approves them through the graph delta loop.
