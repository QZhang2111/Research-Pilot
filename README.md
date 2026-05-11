# Research Pilot

Research Pilot is an agent-operated research memory plugin.

It helps AI agents initialize and operate a private research workspace where papers, project questions, claims, evidence, warrants, limitations, graph deltas, and human decisions can accumulate over time.

## Status

Experimental public extraction.

Current public extraction includes:

- Codex-compatible install instructions;
- a `research-pilot` router skill skeleton;
- a private workspace initializer;
- workspace templates with no private research data;
- graph-event validation;
- graph snapshot generation;
- SQLite graph read-model generation;
- read-only graph query commands;
- read-only gap detection and next-action routing;
- gap-driven search contracts and user-facing gap discovery;
- read-only experiment proposal generation;
- Zotero bridge helpers for configurable metadata/status workflows;
- human-gated delta dry-run, registration, and decision commands;
- project-local paper dossier creation, validation, and delta export;
- Zotero-first source identity intake with manual source-reference capture for setup/dry-run cases;
- required Research Browser dashboard served from plugin UI files over workspace read models.

Dashboard is a required public component and a browser observer. It reads `.dashboard/index.json`, graph snapshots, and graph.db; graph truth remains `wiki/graphs/events/**/*.jsonl`.

## Mental Model

```text
Research Pilot public repo = plugin source and tools
User research workspace = private research memory
Agent chat = primary interface
Markdown files = long-term agent-readable memory
Graph events = append-only project-understanding truth
Generated DB/dashboard files = rebuildable read models
```

## Source Boundaries

```text
Zotero = paper metadata, PDFs, collections, tags, reading status mirror
wiki = digested research understanding and project files
wiki/graphs/events = append-only project understanding graph truth
graph.db/snapshots/reports = rebuildable read models
dashboard = required browser view over read models and wiki state
chat/agent = primary control surface
```

## Quick Start

Install skills for Codex-compatible agents:

```bash
./install.sh codex
```

Initialize a private workspace:

```bash
python3 tools/research_pilot_init.py ~/Research/MyResearchWiki
```

Then start your agent inside that workspace and ask:

```text
Use Research Pilot to inspect this workspace.
```

Run the graph-core smoke test. The `examples/demo/` files are test fixtures, not a product demo workspace:

```bash
./scripts/smoke_mvp_b.sh
```

Build graph read models in a workspace after adding project graph events:

```bash
python3 tools/graph_validate.py --repo ~/Research/MyResearchWiki --project DemoProject
python3 tools/build_graph_snapshot.py --repo ~/Research/MyResearchWiki --project DemoProject
python3 tools/build_graph_db.py --repo ~/Research/MyResearchWiki --project DemoProject
python3 tools/graph_query_cli.py summary --repo ~/Research/MyResearchWiki --project DemoProject --json
```

Detect gaps and recommend next action:

```bash
python3 tools/project_gap_cli.py detect --repo ~/Research/MyResearchWiki --project DemoProject --json
python3 tools/project_next_action_cli.py suggest --repo ~/Research/MyResearchWiki --project DemoProject --json
```

Generate gap-search leads and experiment proposals:

```bash
python3 tools/gap_search_cli.py contract --repo ~/Research/MyResearchWiki --project DemoProject --target RL0 --json
python3 tools/research_gap_discovery_cli.py run --repo ~/Research/MyResearchWiki --project DemoProject --gap RL0 --source memory --json
python3 tools/project_experiment_cli.py suggest --repo ~/Research/MyResearchWiki --project DemoProject --target C0 --json
```

Run the human-gated delta smoke test:

```bash
./scripts/smoke_mvp_c.sh
```

Preview, register, and accept a graph delta:

```bash
python3 tools/graph_delta_cli.py dry-run --repo ~/Research/MyResearchWiki --project DemoProject --delta examples/demo/deltas/refine-demo-claim.json --json
python3 tools/graph_delta_cli.py register --repo ~/Research/MyResearchWiki --project DemoProject --delta examples/demo/deltas/refine-demo-claim.json --json
python3 tools/graph_delta_cli.py decide --repo ~/Research/MyResearchWiki --project DemoProject --id D1 --decision accept --json
```

Create a project-local paper dossier and export proposed deltas:

```bash
python3 tools/paper_dossier_cli.py create --repo ~/Research/MyResearchWiki --project DemoProject --paper paper-a --title "Paper A"
python3 tools/paper_dossier_cli.py validate --dossier ~/Research/MyResearchWiki/wiki/projects/DemoProject/papers/paper-a/index.md --json
python3 tools/paper_dossier_cli.py export-deltas --dossier ~/Research/MyResearchWiki/wiki/projects/DemoProject/papers/paper-a/index.md --output-dir ~/Research/MyResearchWiki/.research-pilot/generated/deltas --json
```

Intake source identity. Normal paper management is Zotero-first; DOI/arXiv/URL/manual refs are setup and emergency identity capture, not a replacement paper manager:

```bash
python3 tools/source_intake_cli.py status --json
python3 tools/source_intake_cli.py intake --repo ~/Research/MyResearchWiki --project DemoProject --paper paper-a --title "Paper A" --zotero-key ABC123 --doi 10.000/demo --json
```

Build and serve the dashboard:

```bash
python3 tools/build_dashboard_index.py --repo ~/Research/MyResearchWiki --output .dashboard/index.json
python3 tools/research_browser_server.py --repo ~/Research/MyResearchWiki --port 8765
```

Run release checks:

```bash
./scripts/release_check.sh
```

## Guides

- [Install](docs/guides/install.md)
- [Workspace](docs/guides/workspace.md)
- [Zotero](docs/guides/zotero.md)
- [Dashboard](docs/guides/dashboard.md)
- [Core workflows](docs/guides/core-workflows.md)
- [Source boundaries](docs/guides/source-boundaries.md)

## Private Data Rule

Do not put real paper PDFs, Zotero API keys, local Zotero databases, private project dossiers, generated private dashboard data, or personal research memory into this public repo.

Each user should keep their research memory in their own private workspace.
