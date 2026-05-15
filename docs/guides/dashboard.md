# Dashboard Guide

Dashboard is a required public browser component and a read-model observer.

It reads:

- `.dashboard/index.json`;
- graph snapshots;
- `wiki/graphs/graph.db`;
- related-work lineage artifacts under `wiki/projects/<Project>/literature-rounds/<Round>/related-work-lineage.json`;
- project markdown.

Graph truth remains:

```text
wiki/graphs/events/**/*.jsonl
```

`lineage.html` shows paper-only related-work technical lanes. It is read-only and does not write PUG truth.

Ask the agent:

```text
Use Research Pilot to open the dashboard for ~/Research/MyResearchWiki.
```

Direct helper fallback:

```bash
python3 tools/build_dashboard_index.py --repo "$WORKSPACE" --output .dashboard/index.json
python3 tools/research_browser_server.py --repo "$WORKSPACE" --port 8765
```

## Project Display Semantics

Project cards prefer `overview.md` display metadata. `project-query-pack.md` title is only a fallback when `overview.md` is missing.

Projects with `demo: true`, such as `DemoVisualAffordance`, display a `Demo` badge; this marks example data only.

Dashboard question labels distinguish:

- `seed_questions`: setup prompts for early project formation;
- `search_questions`: prompts for finding or collecting baseline papers;
- `accepted_questions`: human-approved graph questions or explicitly approved overview content;
- `current_questions`: accepted project questions or explicitly approved overview current questions. Seed and search prompts must not be included.

Seed and search prompts are not project truth.
