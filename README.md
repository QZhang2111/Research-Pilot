<h1 align="center">Research Pilot</h1>

<p align="center" style="max-width: 980px; margin: 0 auto;">
  <strong>Give your research agent local project memory and a read-only dashboard for what it currently understands.</strong>
  <br />
  <em>Chat-first. Local workspace. Source-agnostic. Read-only project dashboard.</em>
</p>

<p align="center">
  <a href="#quick-start"><img src="https://img.shields.io/badge/Quick_Start-Run_Research_Pilot-0A7ACA?style=for-the-badge" alt="Quick Start"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-D4A017?style=for-the-badge" alt="MIT License"></a>
  <a href="#quick-start"><img src="https://img.shields.io/badge/Codex-Compatible-111111?style=for-the-badge" alt="Codex Compatible"></a>
  <a href="#source-agnostic-intake"><img src="https://img.shields.io/badge/Source_Agnostic-PDF_URL_arXiv_DOI_Zotero-4C8A2B?style=for-the-badge" alt="Source Agnostic"></a>
  <a href="#research-browser"><img src="https://img.shields.io/badge/Research_Browser-Dashboard-31A8D6?style=for-the-badge" alt="Research Browser"></a>
  <a href="#private-by-design"><img src="https://img.shields.io/badge/Local_Private-Workspace-6D3FD9?style=for-the-badge" alt="Local Private Workspace"></a>
</p>

<p align="center">
  <img src="asset/research-pilot-hero.png" width="92%" alt="Research Pilot turns scattered papers, chats, claims, and experiments into agent-operated project memory with graph deltas and next research moves.">
</p>

---

**You are researching through an AI agent. The agent reads, compares, reasons, and writes, but important project understanding can disappear into chat history.**

Research Pilot gives that agent a local project memory. Each workspace has one `research-pilot.db` that stores projects, sources, paper understanding, project understanding, literature structure, experiments, updates, and audit history by `project_id`.

The user-facing interface is still chat. Ask the agent normal research questions. Research Pilot provides the local dataset, typed tools, workspace templates, and read-only dashboard that let the agent keep durable project state.

The dashboard is an observer. It shows the current project state from local read models; it is not where users operate workflows or edit research memory.

> **Research Pilot does not replace your judgment, your research taste, or your paper manager. It helps your agent accumulate observable local understanding of a project instead of starting over from each chat.**

---

## What It Helps You Do

### Track project understanding through chat

Ask the agent to track a project. Research Pilot creates or updates local project memory while the conversation stays natural.

### Keep sources connected to the project

Give the agent a PDF, URL, arXiv link, DOI, note, experiment result, or Zotero item. The agent records source identity, reading depth, relevance, and project impact.

### Preserve what changed after agent work

After meaningful research work, the agent can record an UnderstandingUpdate: what source was used, what claim changed, what evidence or uncertainty appeared, and what should be inspected next.

### Observe without operating workflows

Open the read-only dashboard to see project state, papers, technical lineage, experiments, recent understanding, and graph views where available.

### Use strict review when needed

Formal graph events and D* review still exist as advanced strict review mode for high-impact claim/evidence changes. They are not required for normal first-run use.

---

## Quick Start

### 1. Install Research Pilot

```bash
curl -fsSL https://raw.githubusercontent.com/QZhang2111/Research-Pilot/main/install.sh | bash
```

This installs the local plugin source under `~/.research-pilot/repo`, links Research Pilot skills for Codex-compatible agents, and keeps helper tools available for the agent.

### 2. Start Codex

```bash
codex
```

Then ask:

```text
Use Research Pilot to track this project.
```

Give the agent your topic, current question, source, note, or experiment result. If a workspace path is needed, the agent will ask for one concise path.

### 3. Work normally in chat

Example:

```text
My project asks whether vision-language models understand object interactions or only learn object co-occurrence.
Track this with Research Pilot.
```

The agent creates or selects a local workspace, initializes `research-pilot.db`, creates or selects a project, records the initial project brief or UnderstandingUpdate, and keeps working from chat.

Fresh workspaces include `DemoVisualAffordance` by default so the dashboard has visible example data. The public repo includes an example initialized workspace at `examples/workspaces`; its root `research-pilot.db` contains `DemoVisualAffordance` as one project.

### 4. Add sources naturally

```text
Read this arXiv paper and record what matters for the project: https://arxiv.org/...
```

Research Pilot supports PDF paths, URLs, arXiv links, DOI strings, Markdown notes, experiment results, manual references, and Zotero items. Zotero is optional.

### 5. Open the dashboard

```text
Open the Research Pilot dashboard.
```

The agent starts or reuses the local dashboard server, waits until it is ready, then opens the browser or reports the local URL.

---

## What You Can Ask The Agent

```text
Use Research Pilot to track this project.
```

```text
Read this source and record what matters for the project.
```

```text
What does the project currently understand?
```

```text
Compare this paper with our current claim.
```

```text
Record this experiment result as project evidence.
```

```text
Open the Research Pilot dashboard.
```

```text
Use strict review for this claim update.
```

---

## Core Loop

```text
user asks agent
-> agent reads / compares / reasons / writes
-> agent records durable project understanding
-> workspace-local research-pilot.db stores project data
-> dashboard renders read-only project state
-> user observes and asks the next better prompt
```

Normal updates go through typed Research Pilot tools and UnderstandingUpdates. Advanced strict review can still use graph deltas and human approval when formal graph truth changes are needed.

---

## Mental Model

```text
Research Pilot repo = plugin source and implementation resources
User workspace = private local research dataset
research-pilot.db = primary workspace dataset, one DB per workspace
Agent chat = primary user control surface
Dashboard = read-only observation surface
Skills/tools = agent-operated internal resources
Wiki/Markdown = agent-readable context and compatibility artifacts
Graph events/deltas = advanced strict review mode
Zotero = optional supported paper-manager adapter
```

---

## Source-Agnostic Intake

Research Pilot can track sources from PDF paths, URLs, arXiv links, DOI strings, Markdown notes, experiment results, manual references, and Zotero items.

Zotero remains a supported adapter, not a required first step. The agent should record source identity, project relevance, reading depth, and impact on current understanding.

---

## Research Browser

The Research Browser is a local read-only dashboard over workspace read models. It helps inspect project state, papers, technical lineage, experiments, recent understanding, graph views, and next research moves where available.

It observes local project state; it is not where users operate workflows or edit research memory.

---

## What Is Included

- Codex plugin manifest at `.codex-plugin/plugin.json`.
- Chat-first Research Pilot router skills.
- Agent workflow docs for initialization and dashboard fallback.
- Curl-based Codex-compatible installer.
- `research-pilot` router skill.
- Private workspace initializer.
- Workspace templates with no private research data.
- Program context template for taste/north-star markdown.
- Graph-event validation.
- Graph snapshot generation.
- SQLite graph read-model generation.
- Generated project graph markdown reports.
- Read-only graph query commands.
- Read-only gap detection and next-action routing.
- Project understanding update and evidence synthesis protocols.
- Gap-driven search contracts and user-facing gap discovery.
- Read-only experiment proposal generation.
- Zotero bridge helpers for configurable metadata/status workflows.
- Human-gated delta dry-run, registration, and decision commands.
- Project-local paper dossier creation, validation, and delta export.
- Source identity intake with manual source-reference capture for setup/dry-run cases.
- Paper-only related-work lineage workflow for project-scoped technical route maps.
- Related-work lineage dashboard view over generated read models.
- Research Browser dashboard served from plugin UI files over workspace read models.

---

## Advanced Internal Tools

Normal users should not need these commands. They are kept for agent internals, diagnostics, compatibility, and strict review mode.

Run the full release check:

```bash
./scripts/release_check.sh
```

Run the graph-core smoke test:

```bash
./scripts/smoke_mvp_b.sh
```

Build graph read models in a workspace:

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
python3 tools/graph_delta_cli.py dry-run --repo ~/Research/MyResearchWiki --project DemoProject --delta examples/archive/legacy-demo-fixtures/demo/deltas/refine-demo-claim.json --json
python3 tools/graph_delta_cli.py register --repo ~/Research/MyResearchWiki --project DemoProject --delta examples/archive/legacy-demo-fixtures/demo/deltas/refine-demo-claim.json --json
python3 tools/graph_delta_cli.py decide --repo ~/Research/MyResearchWiki --project DemoProject --id D1 --decision accept --json
```

Create a project-local paper dossier and export proposed deltas:

```bash
python3 tools/paper_dossier_cli.py create --repo ~/Research/MyResearchWiki --project DemoProject --paper paper-a --title "Paper A"
python3 tools/paper_dossier_cli.py validate --dossier ~/Research/MyResearchWiki/wiki/projects/DemoProject/papers/paper-a/index.md --json
python3 tools/paper_dossier_cli.py export-deltas --dossier ~/Research/MyResearchWiki/wiki/projects/DemoProject/papers/paper-a/index.md --output-dir ~/Research/MyResearchWiki/.research-pilot/generated/deltas --json
```

Project understanding update and evidence synthesis are agent workflows, not direct approval shortcuts:

```text
skills/project-understanding-update
skills/project-evidence-synthesis
wiki/_system/workflows/project-understanding-update.md
wiki/_system/workflows/project-evidence-synthesis.md
```

---

## Guides

- [Install](docs/guides/install.md)
- [Workspace](docs/guides/workspace.md)
- [Zotero](docs/guides/zotero.md)
- [Dashboard](docs/guides/dashboard.md)
- [Core workflows](docs/guides/core-workflows.md)
- [Source boundaries](docs/guides/source-boundaries.md)

---

## Private By Design

Do not put real paper PDFs, Zotero API keys, local Zotero databases, private project dossiers, generated private dashboard data, or personal research memory into this public repo.

Each user should keep their research memory in their own private workspace.

---

## Contributing

This project is an early public extraction. Useful contributions should preserve the core boundary:

```text
agent chat = primary interaction
workspace data = private
public repo = reusable plugin kit
strict review = available for formal project-truth changes
```
