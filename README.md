# Research Pilot

<p align="center">
  <img src="asset/research-pilot-hero.png" alt="Research Pilot turns scattered papers, chats, claims, and experiments into agent-operated project memory with graph deltas and next research moves.">
</p>

Research Pilot helps AI agents maintain and advance paper-heavy work through private project memory.

It turns Zotero papers, paper dossiers, project claims, evidence, warrants, limitations, and human decisions into an append-only Project Understanding Graph that agents can inspect, update through human gates, and use to recommend next research moves.

Stop re-explaining your project every session. Start from the current research state.

## What It Gives Your Agent

| Feature | What it means |
| --- | --- |
| Project Memory | Keep project direction, claims, evidence, gaps, and decisions in a durable workspace the agent can read. |
| Evidence Gap Detection | Surface unsupported claims, weak warrants, missing paper evidence, and experiment needs before choosing the next action. |
| Paper-to-Graph Reading | Convert a paper dossier into claim, evidence, limitation, and delta proposals tied to project context. |
| Human-Gated Deltas | Let the agent propose graph changes while the human accepts, rejects, parks, or revises before memory changes. |
| Next Research Move | Ask what to read, test, clarify, or update next based on the current project graph. |
| Research Browser | Inspect papers, claims, graph snapshots, deltas, gaps, and project state through a local dashboard. |

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
- project understanding update and evidence synthesis workflow protocols;
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

Project understanding update and evidence synthesis are agent workflows, not direct approval shortcuts. Use:

```text
skills/project-understanding-update
skills/project-evidence-synthesis
wiki/_system/workflows/project-understanding-update.md
wiki/_system/workflows/project-evidence-synthesis.md
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
