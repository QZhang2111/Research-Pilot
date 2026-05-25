# Research Pilot Trial Defects Full Coverage Design

Date: 2026-05-12
Status: Review
Source feedback: `docs/research-pilot-trial-defects.md`

## Goal

Fix the full RP-001 through RP-013 trial defect set by turning Research Pilot from a tool bundle into a stage-aware, agent-operated product flow.

Success means a user can enter an initialized workspace, talk only to the agent, understand current project stage, create an early project shell without forcing graph truth, connect Zotero through a guided local setup, see accurate dashboard labels, and receive clear plugin health/update guidance.

## Product Boundary

The user-facing interface remains chat with the agent.

CLI tools are agent-facing execution helpers. They may also be runnable for diagnostics, but docs and workflows should not require users to memorize commands.

Dashboard remains a read-model observer. It must not become source of truth and must not accept graph deltas, approve papers, or mutate Zotero.

Zotero remains paper source of truth. Research Pilot owns project-local interpretation, graph deltas, and human-gated memory.

## Scope

This design covers:

- RP-001: real first-run inspection finding replacing the seed defect.
- RP-002: stage-aware workspace guidance.
- RP-003: slash command failure fallback and command availability health check.
- RP-004: maturity-aware project intake.
- RP-005: project shell before understanding graph.
- RP-006: durable research job records and subagent boundary.
- RP-007: dashboard title should use user-facing project metadata.
- RP-008: dashboard should not present seed prompts as accepted current questions.
- RP-009: API-key-first Zotero onboarding flow.
- RP-010: canonical agent-facing Zotero setup/status helper that reads workspace `.env`.
- RP-011: built-in Zotero `Research_Pilot` collection tree setup.
- RP-012: remove Zotero MCP dependency from user-facing workflow.
- RP-013: plugin update/status UX.

## Non-Goals

- No automatic acceptance of project graph truth.
- No automatic promotion of project-core or global-core papers.
- No Zotero MCP dependency in docs, skills, or setup flow.
- No dashboard write APIs for graph or Zotero truth.
- No background execution engine beyond durable job records and clear handoff guidance.

## Architecture

Add five focused capability slices:

1. Workspace status:
   - agent-facing status detector reads workspace markers, projects, open deltas, paper dossiers, graph read models, dashboard index, Zotero config, and plugin install state;
   - returns stage and next actions as structured JSON;
   - router and first-run skills use this before telling the user what to do.

2. Project shell lifecycle:
   - first-run protocol allows `project_shell` before graph truth;
   - project metadata captures display title, target venue, maturity stage, direction, baseline anchors, and setup prompts;
   - first graph delta is deferred until the user gives a real question, claim, evidence pressure, search result, paper dossier, or synthesis result.

3. Dashboard semantics:
   - dashboard index prefers project display metadata from `overview.md`;
   - query pack remains a linked core artifact, not a project title source;
   - dashboard separates `seed_questions`, `search_questions`, and `accepted_questions`.

4. Zotero setup:
   - add one agent-facing setup/status helper that reads `.env`, validates `ZOTERO_API_KEY`, discovers My Library, and never prints secrets;
   - add collection tree creation/reuse through Zotero Web API;
   - persist collection keys in ignored workspace config;
   - skills present this as chat-guided setup, not user-facing command memorization.

5. Plugin health and jobs:
   - add plugin status/update health helper that reports local version, source path, linked skills, command fallback, and restart guidance;
   - add durable research job records for search, deep read, and synthesis tasks so main chat keeps human gate ownership.

## Data Model

### Workspace Status JSON

`tools/research_pilot_status.py` returns:

```json
{
  "valid_workspace": true,
  "stage": "empty_workspace",
  "projects": [],
  "open_deltas": 0,
  "paper_dossiers": 0,
  "read_models": {
    "dashboard_index": "missing",
    "graph_db": "missing",
    "snapshots": "missing"
  },
  "zotero": {
    "configured": false,
    "api_key_present": false,
    "api_key_valid": false,
    "library_type": "",
    "library_id": "",
    "mode": "not-configured"
  },
  "plugin": {
    "source_path": "/Users/example/.research-pilot/repo",
    "version": "0.1.0",
    "commands_visible": "unknown",
    "dashboard_fallback_available": true
  },
  "next_actions": [
    {
      "id": "create_project_shell",
      "label": "Create first project shell",
      "reason": "Workspace has no projects yet."
    }
  ]
}
```

Stage values:

```text
plugin_repo
plain_directory
initialized_workspace
empty_workspace
project_shell
project_has_graph
open_deltas
papers_present
read_models_stale
zotero_setup_needed
unknown
```

### Project Overview Frontmatter

`wiki/projects/<ProjectId>/overview.md` gets stable display metadata:

```yaml
---
title: "AAAI 2027 Affordance Estimation"
type: project-overview
project_id: EXAMPLE_VENUEAffordance
display_title: "AAAI 2027 Affordance Estimation"
target_venue: "AAAI 2027"
maturity_stage: "project_shell"
research_direction: "Affordance estimation from visual observations."
baseline_anchors: []
human_review: pending
---
```

Allowed `maturity_stage` values:

```text
project_shell
baseline_collection
question_forming
graph_started
active_research
archived
```

### Question Semantics

Dashboard project overview uses separate arrays:

```json
{
  "seed_questions": ["What baseline papers should anchor this project?"],
  "search_questions": ["Which affordance estimation papers define the AAAI contribution bar?"],
  "accepted_questions": []
}
```

`accepted_questions` comes only from human-approved graph events or explicitly approved overview content. Seed/search prompts must not be labeled as current research questions.

### Zotero Config

Workspace `.env` contains secrets and stays ignored:

```bash
ZOTERO_API_KEY=
```

Workspace `.research-pilot/config.toml` persists non-secret Zotero metadata:

```toml
[zotero]
enabled = true
library_type = "users"
library_id = "123456"
root_collection_key = "ABCDE123"
inbox_collection_key = "FGHIJ456"
projects_collection_key = "KLMNO789"
areas_collection_key = "PQRST123"
campaigns_collection_key = "UVWXY456"
archive_collection_key = "ZABCD789"
```

The helper may create `.env.example` and `.env` when missing, but must never print the key or write secrets into committed templates.

### Job Records

Durable job records live under `.research-pilot/jobs/` because they are execution state, not research truth.

Example:

```json
{
  "id": "job-20260512-001",
  "type": "paper_search",
  "project": "EXAMPLE_VENUEAffordance",
  "status": "needs_review",
  "created_at": "2026-05-12T00:00:00Z",
  "updated_at": "2026-05-12T00:10:00Z",
  "owner": "agent",
  "human_gate": "required_before_graph_update",
  "inputs": {
    "gap_id": "RL0"
  },
  "artifacts": [
    "wiki/projects/EXAMPLE_VENUEAffordance/literature-rounds/round-001/search-results.md"
  ],
  "result_summary": "Search produced candidate papers. No graph truth changed."
}
```

Dashboard may display these records as execution status, but job records are not graph truth.

## User Flows

### Enter Workspace

1. User opens Codex inside a Research Pilot workspace.
2. Agent runs workspace status helper.
3. Agent says current stage in one concise paragraph.
4. Agent offers one or two next actions.

No graph mutation happens.

### Create Early Project

1. Agent collects missing project shell fields:
   - project id or display title;
   - target venue if known;
   - maturity stage;
   - broad direction;
   - baseline papers if available;
   - Zotero now/later.
2. Agent creates project shell files with `human_review: pending`.
3. Agent does not create graph nodes unless user supplied a real graph-level question or claim.
4. Dashboard shows project shell and setup/search prompts with non-truth labels.

### Create First Graph Update

1. User provides question, claim, evidence pressure, paper synthesis, or experiment result.
2. Agent drafts D*.
3. Agent dry-runs delta.
4. Agent stops for human accept/reject/park/revise.
5. Only explicit acceptance appends graph event and rebuilds read models.

### Zotero Setup

1. Agent detects Zotero is not configured.
2. Agent creates `.env.example` and `.env` if missing.
3. Agent gives Zotero key URL and tells user to paste only `ZOTERO_API_KEY` locally.
4. User says done.
5. Agent validates key through Web API, discovers My Library, writes non-secret config.
6. Agent asks permission before creating/reusing collection tree.
7. Agent creates/reuses:

```text
Research_Pilot/
  00 Inbox
  10 Projects
  20 Research Areas
  30 Review Campaigns
  90 Archive
```

8. For a project, agent creates/reuses collections under `10 Projects/<project>`.

### Plugin Health

1. Agent runs plugin health helper during onboarding or when user asks update/status.
2. Helper reports install source, manifest version, git commit, skill links, command files, helper bins, dashboard fallback availability, and update command.
3. If slash commands are unavailable in host Codex, agent gives conversational fallback and can start dashboard through the server helper.

## Error Handling

- Missing workspace markers: report not initialized; offer init path.
- In plugin repo: explain repo/workspace boundary; ask or infer workspace path.
- Missing `.env`: create template and explain paste step.
- Invalid Zotero key: say key validation failed without printing key; ask user to replace local value.
- Zotero API network error: report validation could not complete; keep config pending.
- Existing Zotero collections: reuse by name, persist keys.
- Duplicate project shell: update only missing metadata unless user asks overwrite.
- Stale read models: recommend rebuild; do not mutate graph truth.
- Slash command not exposed: provide fallback server command through agent action, not as primary UX.

## Testing Strategy

Add focused tests for each slice:

- workspace status classification for plugin repo, empty workspace, project shell, graph project, stale read models, Zotero missing;
- first-run protocol text allows project shell before graph delta;
- project overview metadata extraction prefers `display_title` from `overview.md`;
- dashboard separates seed/search/accepted questions;
- source intake or new Zotero setup helper reads workspace `.env`;
- Zotero helper masks secrets in JSON and errors;
- Zotero collection planner creates/reuses expected collection names using fake Web API responses;
- plugin health reports fallback when command files exist but host visibility is unknown;
- job record validation accepts valid records and rejects graph-mutating claims.

## Implementation Slices

1. Workspace status and onboarding language.
2. Project shell lifecycle and first-run protocol update.
3. Dashboard display metadata and question semantics.
4. Agent-facing Zotero setup/status helper.
5. Zotero collection tree setup.
6. Plugin health/update fallback.
7. Durable job record schema and dashboard index exposure.
8. Docs and retest queue update.

Each slice must preserve human gate and avoid changing graph truth unless an explicit delta decision exists.

## Acceptance Criteria

- RP-001 has a concrete first-run inspection result, replacing the seed entry.
- RP-002 status helper returns stage-specific next actions.
- RP-003 docs and skills include dashboard fallback when slash commands are unavailable.
- RP-004 first-run intake supports venue, maturity stage, rough direction, and baseline anchors.
- RP-005 project shell can exist without graph events.
- RP-006 durable job records define background task boundaries.
- RP-007 dashboard title uses overview/display metadata, not query pack title.
- RP-008 dashboard labels seed/search prompts separately from accepted questions.
- RP-009 agent-guided Zotero setup creates local env files without printing secrets.
- RP-010 Zotero status reads workspace `.env` and validates via Web API.
- RP-011 Zotero collection tree create/reuse path exists and persists keys.
- RP-012 user-facing docs and skills do not depend on Zotero MCP.
- RP-013 plugin health/status exposes version, relink, fallback, update, and restart guidance.
