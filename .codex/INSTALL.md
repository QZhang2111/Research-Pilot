# Research Pilot Codex Install

This installer makes Research Pilot skills available to Codex-compatible agents.

## Install From A Local Checkout

From the Research Pilot repo root:

```bash
./install.sh codex
```

The installer links each skill directory from this repo into:

```text
~/.agents/skills/
```

## Initialize A Workspace

After installation, create a private workspace:

```bash
python3 tools/research_pilot_init.py ~/Research/MyResearchWiki
```

Then run Codex from inside the workspace and ask:

```text
Use Research Pilot to inspect this workspace.
```

## Current Status

The public extraction includes the router skill, workspace initializer, graph read models, human-gated delta loop, paper dossier workflow, source identity intake, gap/next-action commands, and dashboard server.

Zotero remains the normal paper source of truth. Current public source intake records Zotero identity and supporting DOI/arXiv/URL refs; full Zotero bridge automation is a later extraction slice.

Dashboard is a required public browser component, but graph truth remains `wiki/graphs/events/**/*.jsonl`.
