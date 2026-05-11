# Research Pilot

Research Pilot is an agent-operated research memory plugin.

It helps AI agents initialize and operate a private research workspace where papers, project questions, claims, evidence, warrants, limitations, graph deltas, and human decisions can accumulate over time.

## Status

Experimental public extraction.

MVP-A only includes:

- Codex-compatible install instructions;
- a `research-pilot` router skill skeleton;
- a private workspace initializer;
- workspace templates with no private research data.

Graph tools, Zotero workflows, dashboard support, and full paper-to-delta automation are extracted in later MVP slices.

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
dashboard = optional browser view over read models and wiki state
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

## Private Data Rule

Do not put real paper PDFs, Zotero API keys, local Zotero databases, private project dossiers, generated private dashboard data, or personal research memory into this public repo.

Each user should keep their research memory in their own private workspace.
