# UnderstandingUpdate Architecture PRD

Date: 2026-05-23
Status: Draft v0.1

## 1. Summary

Research-Pilot should add an `UnderstandingUpdate` layer as the normal architecture path for ambient agent research work. The user keeps working with the agent in chat. After meaningful research work, the agent records a compact semantic update. Research-Pilot projects those updates into current project understanding: project brief, sources, claims, evidence, gaps, recent changes, and next moves.

This PRD is architecture-first. It does not redesign dashboard pages, remove the existing demo project, replace graph tooling, or delete current workflows. It adds a product-level truth layer beside the existing graph-event layer so Research-Pilot can become lighter for normal use while preserving rigorous internals for advanced use.

## 2. Problem

Research-Pilot currently has strong internal machinery, but the repo architecture is centered on formal workflows, graph events, graph deltas, paper dossiers, Zotero identity, and generated read models. That makes sense for rigor, but it is too heavy as the default path for normal agent-assisted research.

The product direction is ambient:

```text
User asks agent normal research question
-> agent reads / compares / reasons / writes
-> Research-Pilot records useful project understanding
-> current project state can be observed
-> user asks a better next prompt
```

The current graph-delta model answers:

```text
How exactly should graph state mutate?
```

The missing architecture object answers:

```text
What did the agent learn or change about project understanding?
```

Without that object, every useful agent observation must become a formal graph patch, dossier, or workflow artifact. That keeps normal use procedural instead of ambient.

## 3. Product Goal

Add a durable semantic update layer that lets agents record useful project understanding after normal research tasks.

The repo should support this mental model:

```text
Agent work produces UnderstandingUpdates.
UnderstandingUpdates compile into ProjectUnderstanding.
ProjectUnderstanding powers read-only observation surfaces.
Graph events and deltas remain available as advanced/internal rigor.
```

## 4. Non-Goals

This PRD does not include:

- dashboard page redesign
- dashboard visual layout changes
- removal of `DemoVisualAffordance`
- deletion or replacement of existing graph-event tooling
- deletion or replacement of graph delta review flow
- mandatory Zotero changes
- full source connector implementation
- interactive website editing
- paper-writing pipeline
- migration of all existing data into a new format
- replacing current tests wholesale

## 5. Architecture Decision

Use two truth layers for now.

### Product Truth

Normal use writes append-only understanding events:

```text
wiki/understanding/events/<project_id>.jsonl
```

These events are product-semantic and source-agnostic. They describe meaningful changes in project understanding.

### Advanced Graph Truth

Existing graph events remain:

```text
wiki/graphs/events/projects/<project_id>.jsonl
```

Graph events continue to support formal claim/evidence/link semantics, validation, delta review, graph snapshots, SQLite indexes, and advanced workflows.

### Relationship

```text
UnderstandingUpdate = semantic product layer
GraphDelta / graph event = optional formalization layer
ProjectUnderstanding = projected current state for read-only surfaces
```

Rule:

```text
Every graph delta may originate from an UnderstandingUpdate.
Not every UnderstandingUpdate must become a graph delta.
```

## 6. Core Objects

### UnderstandingUpdate

One agent-observed change in project understanding after a meaningful research task.

Suggested fields:

```json
{
  "schema_version": "understanding-update-v1",
  "update_id": "UU0001",
  "project_id": "DemoVisualAffordance",
  "created_at": "2026-05-23T00:00:00Z",
  "actor": "agent",
  "task": {
    "kind": "read_source",
    "summary": "Read source S12 and compared it with claim C2."
  },
  "source_refs": ["arxiv:0000.00000"],
  "new_sources": [],
  "changed_claims": [],
  "new_evidence": [],
  "new_gaps": [],
  "status_changes": [],
  "recent_change_summary": "C2 is now supported only indirectly; a counterfactual interaction gap was added.",
  "next_moves": [],
  "confidence": "agent-inferred"
}
```

### SourceRecord

Source identity and lightweight state. Zotero is one adapter, not required identity.

Fields:

```text
source_id
type: pdf | url | arxiv | doi | markdown_note | experiment_result | zotero_item | manual
locator
title
status: seen | skimmed | read | used
relevance
related_claims
related_gaps
created_at
updated_at
```

### SourceNote

Optional source-level interpretation. A source may have no full dossier. Depth can vary.

Fields:

```text
source_id
depth: seen | skimmed | read | used
summary
useful_for
limitations
project_relevance
source_refs
```

### ProjectUnderstanding

Generated current state from understanding events plus optional existing graph/read-model inputs.

Fields:

```text
project_brief
sources
claims
evidence
gaps
recent_changes
next_moves
generated_at
inputs
```

## 7. Agent Behavior

Agents should write an `UnderstandingUpdate` after meaningful research work.

Meaningful tasks include:

- reading or skimming a source
- summarizing a paper or note
- comparing methods
- finding related work
- checking a project claim
- reviewing experiment results
- discussing project direction
- identifying a gap
- planning next work
- drafting or revising research text when project understanding changes

Agents should not need to ask the user to operate formal workflow commands during normal use.

## 8. MVP Scope

MVP should add architecture foundation only.

Included:

- `UnderstandingUpdate` schema and validation
- append-only understanding event log per project
- helper API/CLI for appending updates
- projector that builds `ProjectUnderstanding` JSON
- recent changes projection
- source records with source-agnostic types and depth labels
- compatibility with existing `DemoVisualAffordance`
- compatibility with current graph events and graph delta tools
- docs explaining architecture boundary

Excluded:

- dashboard page redesign
- dashboard route changes
- new visual components
- demo removal or replacement
- full Zotero rework
- full connector framework
- automatic graph-delta compiler, unless needed as a small optional adapter

## 9. Data Flow

Normal ambient path:

```text
agent research work
-> UnderstandingUpdate
-> wiki/understanding/events/<project>.jsonl
-> ProjectUnderstanding projector
-> generated read model JSON
-> read-only observation surface
```

Advanced path:

```text
UnderstandingUpdate
-> optional graph-delta compiler
-> graph delta dry-run / review
-> wiki/graphs/events/projects/<project>.jsonl
-> existing graph read models
```

## 10. Compatibility Requirements

- Existing graph tests should continue to pass.
- Existing `DemoVisualAffordance` files should remain.
- Existing dashboard assets and pages should not be modified by this PRD.
- Existing graph event schema should remain valid.
- Existing delta workflow should remain available as advanced/internal machinery.
- Existing Zotero bridge should remain optional.

## 11. Acceptance Criteria

MVP succeeds when:

1. A workspace can contain `wiki/understanding/events/<project>.jsonl`.
2. A valid `UnderstandingUpdate` can be appended after an agent research task.
3. A source can be recorded without Zotero.
4. A source can have status `seen`, `skimmed`, `read`, or `used`.
5. A `ProjectUnderstanding` JSON file can be generated from understanding events.
6. Generated state includes recent changes and next moves.
7. Existing graph-event tooling still works.
8. Existing demo project remains in repo.
9. No dashboard page redesign is required for MVP.
10. Documentation explains `UnderstandingUpdate` as product truth and graph events as advanced rigor.

## 12. Risks

### Risk: Two truth layers create confusion

Mitigation: name layers clearly.

```text
Understanding events = normal product truth.
Graph events = advanced graph truth.
Read models = generated projections.
```

### Risk: Product truth becomes too loose

Mitigation: validate update schema, require source refs when available, include confidence/status labels, and keep optional graph formalization.

### Risk: Website or read models become stale

Mitigation: include generated timestamps, recent update IDs, and stale-state indicators in projected JSON.

### Risk: Old workflow and new ambient path diverge

Mitigation: keep graph-delta compiler optional, and document when advanced review mode should be used.

## 13. Open Questions

1. Should `ProjectUnderstanding` read existing graph events directly, or only understanding events in MVP?
2. Should `UnderstandingUpdate` IDs be timestamp-based, monotonic per project, or content-hash based?
3. Should source records live in their own file, or be derived entirely from understanding events?
4. Should the optional graph-delta compiler be in MVP or postponed?
5. What exact confidence/status vocabulary should be allowed in v1?

## 14. Recommended Implementation Phases

### Phase 1: Foundation

- Add schema for `UnderstandingUpdate`.
- Add append/read helpers.
- Add validation tests.
- Add simple projector to `ProjectUnderstanding` JSON.

### Phase 2: Agent Integration

- Add skill/workflow guidance: after meaningful research work, write compact update.
- Add helper CLI for agent use.
- Add examples using `DemoVisualAffordance`.

### Phase 3: Read Model Integration

- Feed projected understanding into existing read-only surfaces without redesigning dashboard pages.
- Add recent changes and next moves data where existing surfaces can already consume it.

### Phase 4: Advanced Formalization

- Add optional compiler from selected `UnderstandingUpdate` records to graph deltas.
- Keep human-gated review as advanced mode.

## 15. Strategic Principle

Research-Pilot should feel lighter at the product layer and more rigorous underneath.

The architecture should let users experience:

```text
My agent is accumulating observable understanding of my project.
```

without forcing them to operate:

```text
graph events
deltas
SQLite read models
Zotero setup
formal dossier workflows
```

