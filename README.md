# Research Pilot

<p align="center">
  <strong>Turn papers, notes, research chats, and experiments into a private project memory your AI agent can explore, update, and use to choose the next research move.</strong>
  <br>
  <em>Works with Codex-compatible agents. Zotero-first. Local workspace. Human-gated updates.</em>
</p>

<p align="center">
  <a href="#-quick-start"><img src="https://img.shields.io/badge/Quick_Start-Run_Research_Pilot-0A7ACA?style=for-the-badge" alt="Quick Start"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-D4A017?style=for-the-badge" alt="MIT License"></a>
  <a href="#-quick-start"><img src="https://img.shields.io/badge/Codex-Compatible-111111?style=for-the-badge" alt="Codex Compatible"></a>
  <a href="#-zotero-first-source-boundary"><img src="https://img.shields.io/badge/Zotero-First-CB2D3E?style=for-the-badge" alt="Zotero First"></a>
  <a href="#-research-browser"><img src="https://img.shields.io/badge/Research_Browser-Dashboard-31A8D6?style=for-the-badge" alt="Research Browser"></a>
  <a href="#-private-by-design"><img src="https://img.shields.io/badge/Local_Private-Workspace-6D3FD9?style=for-the-badge" alt="Local Private Workspace"></a>
</p>

<p align="center">
  <img src="asset/research-pilot-hero.png" alt="Research Pilot turns scattered papers, chats, claims, and experiments into agent-operated project memory with graph deltas and next research moves.">
</p>

Research Pilot does not just store papers. It keeps your research project oriented.

It gives an AI agent a durable workspace for project direction, Zotero-managed papers, paper dossiers, claims, evidence, warrants, limitations, open gaps, graph deltas, and human decisions. The public repo is the plugin; your research memory stays in your private workspace.

## 🧭 Analyze Research Projects

Point Research Pilot at a private research workspace and let the agent work from the current project state, not a blank chat. The agent can inspect the Project Understanding Graph, find missing evidence, read papers in context, propose graph updates, and recommend what to do next.

|  |  |
| --- | --- |
| 🔎 **Find Missing Evidence** | Surface unsupported claims, weak warrants, missing paper evidence, and experiment needs. |
| 📄 **Read Papers In Context** | Turn project-local paper dossiers into claims, evidence, limitations, and graph delta proposals. |
| 🧠 **Maintain Project Memory** | Keep direction, decisions, evidence, and open questions in an agent-readable workspace. |
| ✅ **Approve Memory Updates** | Let the agent propose deltas while the human accepts, rejects, parks, or revises before memory changes. |
| 🧭 **Choose The Next Move** | Ask what to read, test, clarify, or update next based on the current graph. |
| 🖥️ **Open The Research Browser** | Inspect papers, claims, graph snapshots, deltas, gaps, and project state in a local dashboard. |

## 🚀 Quick Start

Install Research Pilot skills for Codex-compatible agents:

```bash
./install.sh codex
```

Create your private research workspace:

```bash
python3 tools/research_pilot_init.py ~/Research/MyResearchWiki
```

Start your agent inside that workspace and ask:

```text
Use Research Pilot to inspect this workspace and tell me the next research gap.
```

Open the Research Browser:

```bash
python3 tools/build_dashboard_index.py --repo ~/Research/MyResearchWiki --output .dashboard/index.json
python3 tools/research_browser_server.py --repo ~/Research/MyResearchWiki --port 8765
```

Then visit:

```text
http://127.0.0.1:8765/dashboard/index.html
```

## 🧪 What You Can Ask The Agent

- "Where does this project stand?"
- "What claim has the weakest evidence?"
- "Read this paper in project context and propose graph deltas."
- "Show open deltas waiting for human review."
- "What paper should I search for next?"
- "What experiment would most reduce uncertainty?"
- "Open the Research Browser for this workspace."

## 🧩 Core Workflows

Research Pilot keeps the agent workflow explicit:

```text
Zotero papers
-> project-local paper dossiers
-> claims / evidence / warrants / limitations
-> proposed graph deltas
-> human gate
-> append-only graph events
-> snapshots / SQLite / dashboard
-> next research move
```

The graph event log is the source of truth for project understanding. Snapshots, SQLite, markdown reports, and dashboard data are rebuildable read models.

## 🖥️ Research Browser

The Research Browser is a local dashboard over generated read models. It helps you inspect project state, papers, graph snapshots, deltas, gaps, and experiment proposals.

It is not source of truth. It observes:

```text
.dashboard/index.json
wiki/graphs/snapshots/
wiki/graphs/graph.db
wiki/projects/
```

Graph truth remains:

```text
wiki/graphs/events/**/*.jsonl
```

## 🔬 Operator Commands

Run the full release check:

```bash
./scripts/release_check.sh
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
python3 tools/build_project_graph_report.py --repo ~/Research/MyResearchWiki --project DemoProject
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

Project understanding update and evidence synthesis are agent workflows, not direct approval shortcuts:

```text
skills/project-understanding-update
skills/project-evidence-synthesis
wiki/_system/workflows/project-understanding-update.md
wiki/_system/workflows/project-evidence-synthesis.md
```

## 📦 Current Public Alpha

Current public extraction includes:

- Codex-compatible install instructions;
- `research-pilot` router skill;
- private workspace initializer;
- workspace templates with no private research data;
- graph-event validation;
- graph snapshot generation;
- SQLite graph read-model generation;
- generated project graph markdown reports;
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

## 🧱 Mental Model

```text
Research Pilot public repo = plugin source and tools
User research workspace = private research memory
Agent chat = primary interface
Markdown files = long-term agent-readable memory
Graph events = append-only project-understanding truth
Generated DB/dashboard files = rebuildable read models
```

## 🔗 Zotero-First Source Boundary

```text
Zotero = paper metadata, PDFs, collections, tags, reading status mirror
wiki = digested research understanding and project files
wiki/graphs/events = append-only project understanding graph truth
graph.db/snapshots/reports = rebuildable read models
dashboard = required browser view over read models and wiki state
chat/agent = primary control surface
```

## 📚 Guides

- [Install](docs/guides/install.md)
- [Workspace](docs/guides/workspace.md)
- [Zotero](docs/guides/zotero.md)
- [Dashboard](docs/guides/dashboard.md)
- [Core workflows](docs/guides/core-workflows.md)
- [Source boundaries](docs/guides/source-boundaries.md)

## 🔒 Private By Design

Do not put real paper PDFs, Zotero API keys, local Zotero databases, private project dossiers, generated private dashboard data, or personal research memory into this public repo.

Each user should keep their research memory in their own private workspace.
