# Research Pilot Codex Install

This repo is a Codex plugin source. The plugin manifest lives at:

```text
.codex-plugin/plugin.json
```

The local installer below makes Research Pilot skills available to Codex-compatible agents while plugin-manager distribution matures.

## Install From A Local Checkout

From the Research Pilot repo root:

```bash
./install.sh codex
```

The installer links each skill directory from this repo into:

```text
~/.agents/skills/
```

The plugin manifest points Codex-compatible plugin tooling at the same skill directory:

```text
skills/
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

The public extraction includes the plugin manifest, router skill, first-run skill, workspace initializer, graph read models, human-gated delta loop, paper dossier workflow, source identity intake, gap/next-action commands, and dashboard server.

Zotero remains the normal paper source of truth. Public tooling includes source identity intake plus configurable Zotero bridge helpers for metadata, collection, and status-mirror workflows. Credentialed Zotero operations require user-provided local config.

Dashboard is a required public browser component, but graph truth remains `wiki/graphs/events/**/*.jsonl`.
