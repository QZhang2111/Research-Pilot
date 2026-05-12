# Research Pilot Workspace Instructions

This directory is a private Research Pilot workspace.

## Core Rule

Agent operates the workspace through chat. Files are durable memory and execution state, not the main human UI.

## Source Boundaries

```text
Zotero = paper metadata, PDFs, collections, tags, reading status mirror
wiki = digested research understanding and project files
wiki/graphs/events = append-only project understanding graph truth
graph.db/snapshots/reports = rebuildable read models
dashboard = required browser view over read models
chat/agent = primary control surface
```

## Human Gate

Agent may propose, summarize, lint, query, and draft graph deltas.

Only the human may approve:

- project-core papers;
- global-core memory;
- graph delta acceptance;
- research direction changes;
- experiment result interpretation.

## Project Lifecycle

Early projects may start as project shells with venue, broad direction, baseline anchors, and setup prompts.
Project shells are not graph truth.
Create graph deltas only after the human supplies or approves a graph-level question, claim, evidence pressure, paper synthesis, or experiment result.

## Private Data

Do not publish this workspace unless the human explicitly says it is sanitized.
Do not commit PDFs, API keys, local Zotero databases, or generated SQLite/dashboard read models.
