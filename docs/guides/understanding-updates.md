# Understanding Updates

Research Pilot has two durable layers.

Normal product layer:

```text
wiki/understanding/events/<project>.jsonl
```

This layer stores `UnderstandingUpdate` records. Agents write these after meaningful research work: reading a source, comparing papers, checking a claim, identifying a gap, or suggesting next work.

Advanced graph layer:

```text
wiki/graphs/events/projects/<project>.jsonl
```

This layer keeps formal graph events and graph deltas for rigorous claim/evidence/link workflows.

## Normal Agent Rule

After meaningful research work, write one compact understanding update:

```bash
python3 tools/understanding_cli.py append \
  --repo /path/to/workspace \
  --project DemoVisualAffordance \
  --update /path/to/update.json
```

Then build the current project understanding:

```bash
python3 tools/understanding_cli.py build-project-understanding \
  --repo /path/to/workspace \
  --project DemoVisualAffordance
```

## Boundary

Understanding updates are product truth for normal ambient use. Graph events remain advanced graph truth. Read models are generated projections.

Do not require Zotero for an understanding update. A source may be a PDF, URL, arXiv link, DOI, Markdown note, experiment result, Zotero item, or manual reference.
