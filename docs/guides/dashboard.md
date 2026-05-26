# Dashboard Guide

Dashboard is a read-only browser observer over workspace read models.

Normal user path:

```text
Open the Research Pilot dashboard.
```

The agent detects the workspace, starts or reuses the local dashboard server, waits for readiness, and opens or reports the URL.

It reads:

- `.dashboard/index.json`;
- graph snapshots;
- `wiki/graphs/graph.db`;
- project understanding updates from `wiki/understanding/events/<Project>.jsonl`;
- related-work lineage artifacts under `wiki/projects/<Project>/literature-rounds/<Round>/related-work-lineage.json`;
- project markdown.

Advanced strict-review graph events remain:

```text
wiki/graphs/events/**/*.jsonl
```

Project understanding updates are durable agent memory, but not graph truth. The project page renders them as read-only recent understanding and next moves.

Generated read models remain disposable. If `.dashboard/index.json` is missing, the local server rebuilds it when the dashboard requests it.

`lineage.html` shows paper-only related-work technical lanes. It is read-only and does not write PUG truth.

Ask the agent with the normal path prompt above.

## Agent/Internal Fallback

Direct helper fallback:

```bash
python3 tools/build_dashboard_index.py --repo "$WORKSPACE" --output .dashboard/index.json
python3 tools/research_browser_server.py --repo "$WORKSPACE" --port 8765
```

Public example workspace:

```bash
python3 tools/research_browser_server.py --repo examples/workspaces --port 8765
```

That example workspace has `research-pilot.db` at its root and includes `DemoVisualAffordance` as one project in the DB.

## Project Display Semantics

Project cards prefer `overview.md` display metadata. `project-query-pack.md` title is only a fallback when `overview.md` is missing.

Projects with `demo: true`, such as `DemoVisualAffordance`, display a `Demo` badge; this marks example data only.

Example workspace source should not include `.dashboard/`, `wiki/graphs/graph.db`, or graph snapshots. Build or serve commands recreate those artifacts locally.

Dashboard question labels distinguish:

- `seed_questions`: setup prompts for early project formation;
- `search_questions`: prompts for finding or collecting baseline papers;
- `accepted_questions`: human-approved graph questions or explicitly approved overview content;
- `current_questions`: accepted project questions or explicitly approved overview current questions. Seed and search prompts must not be included.

Seed and search prompts are not project truth.
