# Research Pilot Codex Install

This repo is a Codex plugin source. The plugin manifest lives at:

```text
.codex-plugin/plugin.json
```

The installer keeps plugin source in a hidden checkout by default and exposes Research Pilot skills and commands to Codex-compatible agents.

## Install

From any shell:

```bash
curl -fsSL https://raw.githubusercontent.com/QZhang2111/Research-Pilot/main/install.sh | bash
```

The installer clones or updates plugin source into:

```text
~/.research-pilot/repo
```

It links each skill directory into:

```text
~/.agents/skills/
```

It also creates:

```text
~/.research-pilot-plugin
~/.research-pilot/bin/research-pilot-init
```

## Initialize A Workspace

After installation, use the plugin command:

```text
/research-init ~/Research/MyResearchWiki
```

Manual fallback:

```bash
~/.research-pilot/bin/research-pilot-init ~/Research/MyResearchWiki
```

Then run Codex from inside the workspace and ask:

```text
Use Research Pilot to inspect this workspace.
```

## Current Status

The public extraction includes the plugin manifest, router skill, first-run skill, workspace initializer, graph read models, human-gated delta loop, paper dossier workflow, source identity intake, gap/next-action commands, and dashboard server.

Zotero remains the normal paper source of truth. Public tooling includes source identity intake plus configurable Zotero bridge helpers for metadata, collection, and status-mirror workflows. Credentialed Zotero operations require user-provided local config.

Dashboard is a required public browser component, but graph truth remains `wiki/graphs/events/**/*.jsonl`.
