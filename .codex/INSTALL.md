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

MVP-A installs the router skill and workspace initializer only.

Graph workflows, Zotero workflows, dashboard support, and deep-read automation are later MVP slices.
