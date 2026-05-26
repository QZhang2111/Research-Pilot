# Research Pilot Workspace Instructions

This directory is a private Research Pilot workspace.

## Core Rule

Agent operates the workspace through chat. Files and databases are durable memory and execution state, not the main human UI.

## Source Boundaries

```text
research-pilot.db = primary workspace dataset
wiki = durable agent-readable context and compatibility artifacts
wiki/program = research taste and north-star context only
dashboard = read-only observer over workspace read models
chat/agent = primary control surface
graph events/deltas = advanced strict review
Zotero = optional supported adapter
```

## Program Context

`wiki/program/` is an agent context layer for taste and north-star framing. It is not evidence, not project truth, and not a decision source.

Read it when it helps interpret the user's research style. Do not use it to make project decisions for the user. Do not copy program context into project truth.

## Normal Project Memory

After meaningful research work, record durable project understanding through Research Pilot tools. Prefer workspace dataset / UnderstandingUpdate style records for normal updates.

Meaningful work includes:

- starting or reframing a project;
- reading or comparing a source;
- mapping literature structure;
- recording experiment design or result evidence;
- revising a claim, uncertainty, limitation, or project brief.

## Strict Review

Use graph events and D* deltas only for advanced strict review:

- user explicitly asks for strict review;
- high-impact project claim/evidence changes need formal approval;
- compatibility workflows require graph-level Q/C/E/W/L/RL/TL changes.

Only the human may approve:

- strict-review graph delta acceptance;
- project-core papers;
- global-core memory;
- research direction decisions;
- experiment result interpretation as confirmed project evidence.

## Private Data

Do not publish this workspace unless the human explicitly says it is sanitized.
Do not commit PDFs, API keys, local Zotero databases, private workspace datasets, or generated SQLite/dashboard read models.
