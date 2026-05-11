# Research Pilot Public Plugin Extraction Plan

Date: 2026-05-11
Status: Draft
Spec: `docs/superpowers/specs/2026-05-11-research-pilot-public-plugin-design.md`

## Goal

Extract the existing private research-memory system into `Research-Pilot` as a public Codex-first plugin.

This is extraction, packaging, and cleanup. It is not a feature redesign.

## Non-Negotiables

Keep current system behavior:

- Zotero-first paper management.
- Existing skills and workflows.
- Graph events as source of truth.
- Human-gated D* delta updates.
- Dashboard as required public component.
- Agent/chat as primary operation layer.

Do not add during MVP extraction:

- Zotero-free paper manager.
- Fake demo workspace.
- Dashboard redesign.
- New research workflow semantics.
- Public product polish beyond basic install/use docs.

## Phase 0: Public Boundary Cleanup

Purpose: make the target repo clearly plugin-oriented.

Tasks:

1. Update `README.md` title and product statement.
2. State:
   - public repo is plugin source;
   - user workspace is private research memory;
   - Zotero remains paper source of truth;
   - dashboard is required browser view;
   - graph events are truth.
3. Add public `.gitignore` for generated files, PDFs, secrets, caches.
4. Keep existing `docs/superpowers/` spec and plan structure.

Acceptance:

- README cannot be confused with a public copy of a private wiki.
- README does not imply Zotero-free operation.

## Phase 1: Plugin Skeleton

Purpose: create public plugin package shape.

Tasks:

1. Add `.codex/INSTALL.md`.
2. Add `install.sh` or equivalent documented install path that:
   - clones/updates the public repo;
   - links skills into the user's Codex-compatible skill directory;
   - does not require a marketplace.
3. Add Codex plugin metadata only if exact format is confirmed. Do not let metadata block MVP extraction.
4. Add `skills/research-pilot/SKILL.md` as main router skill.
5. Add initializer command stub if needed:
   - `tools/research_pilot_init.py`.

Acceptance:

- Plugin repo has install and initialization entry points.
- Codex-compatible installation does not depend on unresolved marketplace/plugin metadata.
- No private data is introduced.

## Phase 2: Workspace Templates And Config

Purpose: make user workspace creation reproducible before copying large subsystems.

Tasks:

1. Add workspace template:
   - `AGENTS.md`;
   - `wiki/index.md`;
   - `wiki/log.md`;
   - `wiki/projects/.gitkeep`;
   - `wiki/graphs/events/.gitkeep`;
   - `wiki/graphs/schema/`;
   - `wiki/_system/workflows/`;
   - `wiki/_system/templates/`;
   - `.research-pilot/config.example.toml`.
2. Add public `AGENTS.md` template.
3. Add Zotero config example.
4. Add graph/event directory skeleton.
5. Ensure generated workspace has no private data.
6. Add a workspace-init smoke command to the plan once the initializer exists.

Acceptance:

- User workspace can be created without private data.
- User knows where to configure Zotero.
- Empty workspace has enough structure for graph tools to fail clearly or run on fixtures.

## Phase 3: Copy Workflows

Purpose: preserve working protocol docs.

Copy from current private system:

- delta update protocol;
- graph store architecture/API contracts if needed;
- project gap analysis;
- gap-driven search;
- project gap discovery;
- deep-read-to-delta;
- paper discovery intake;
- single-paper deep read;
- Zotero source protocol;
- project experiment proposal;
- project next action.

Tasks:

1. Copy workflow docs into public location.
2. Remove private project names, local paths, and personal context.
3. Preserve Zotero-first assumptions.
4. Preserve command contracts where possible.
5. Update internal links if layout changes.

Acceptance:

- Workflows read as generic Research Pilot protocol docs.
- No behavior change except path/config generalization.
- Leak scan for private project names, absolute maintainer paths, secrets, and local PDF paths passes after this phase.

## Phase 4: Copy Skills

Purpose: preserve agent-facing workflows.

Copy existing stable skills:

- `research-pilot` router if new;
- `delta-update-protocol`;
- `deep-read-to-delta`;
- `paper-discovery-intake`;
- `single-paper-deep-read`;
- `project-gap-analysis`;
- `project-gap-discovery`;
- `gap-driven-search`;
- `project-experiment-proposal`;
- `project-next-action`;
- Zotero-related skill/workflow if currently separate.

Tasks:

1. Copy skill directories.
2. Replace private repo paths with workspace-relative instructions.
3. Keep existing command names where possible.
4. Update skill routing so `research-pilot` is the default user entry.
5. Do not simplify or rewrite Zotero behavior.

Acceptance:

- Skills remain compatible with current workflow semantics.
- User does not need to know all subskill names.
- Router can explain which workflow it will call for common user intents.
- Leak scan passes after this phase.

## Phase 5: Copy Graph Core Tools

Purpose: move the local executors needed for the graph-first core loop before Zotero/dashboard expansion.

Copy core tools:

- graph store;
- graph DB/snapshot/report builders;
- graph query CLI;
- graph delta API/CLI;
- paper dossier CLI;
- project gap CLI;
- gap search / project gap discovery CLIs;
- project experiment CLI;
- project next action CLI;

Tasks:

1. Copy tools.
2. Replace hardcoded private paths with:
   - current working directory;
   - explicit `--workspace`;
   - config file values.
3. Keep command output contracts stable.
4. Add or update `tools/README.md`.
5. Add temporary synthetic fixtures if needed for smoke tests. These are test fixtures, not demo workspace.

Acceptance:

- Tools run from public repo against a user workspace.
- Tools do not reference private local paths.
- Graph DB rebuild, graph query, and delta dry-run/apply can run against synthetic fixture events.
- Leak scan passes after this phase.

## Phase 6: Early Smoke Tests And Leak Scan

Purpose: catch extraction breakage before Zotero and dashboard add more moving parts.

Test minimum:

1. workspace init;
2. no private path leakage;
3. graph DB rebuild from sample minimal events;
4. graph query;
5. delta dry-run/apply;
6. gap detection;
7. project next action.

Acceptance:

- Tests or documented smoke commands pass in public repo.
- Tests do not need private data.
- No private project names, absolute maintainer paths, API keys/secrets, raw PDFs, or real paper dossiers are present.

## Phase 7: Copy Zotero Bridge

Purpose: preserve Zotero-first paper workflows after graph core is portable.

Tasks:

1. Copy `zotero_bridge.py` and any required helpers.
2. Replace hardcoded private paths with:
   - current working directory;
   - explicit `--workspace`;
   - config file values;
   - environment variables.
3. Preserve Zotero bridge behavior.
4. Add Zotero config validation and dry-run behavior.
5. Ensure real credentials are not required for basic tests.

Acceptance:

- Zotero bridge is configurable by user.
- Zotero tests use mocked or dry-run mode unless explicitly marked integration.
- No maintainer library IDs, API keys, or local Zotero paths are present.

## Phase 8: Copy Dashboard

Purpose: make public version observable.

Tasks:

1. Copy current dashboard.
2. Copy dashboard server/build tools.
3. Make workspace root configurable.
4. Remove any hardcoded private project assumptions.
5. Ensure dashboard can read a newly initialized workspace.
6. Do not redesign dashboard as part of extraction.

Acceptance:

- Dashboard is present in public repo.
- Dashboard opens user workspace data.
- Dashboard does not require private generated `.dashboard` files.
- Dashboard can open a freshly initialized workspace or show a clear empty-state.

## Phase 9: Full Test Pass

Purpose: prove extraction did not break core behavior.

Test minimum:

1. workspace init;
2. no private path leakage;
3. graph DB rebuild from sample minimal events;
4. graph query;
5. delta dry-run/apply;
6. gap detection;
7. project next action;
8. dashboard index build;
9. Zotero config validation with mocked or dry-run mode.

No fake demo workspace required. Tests may create temporary synthetic fixtures.

Acceptance:

- Tests pass in public repo.
- Tests do not need private data.
- Zotero tests do not require real credentials unless explicitly marked integration.

## Phase 10: Documentation

Purpose: make plugin usable.

Docs needed:

1. README quick start.
2. Install guide for Codex.
3. Workspace initialization guide.
4. Zotero configuration guide.
5. Dashboard guide.
6. Core workflow guide:
   - project status;
   - paper discovery;
   - deep read;
   - delta update;
   - experiment proposal;
   - next action.
7. Source boundary guide.

Acceptance:

- User understands plugin vs workspace.
- User understands Zotero requirement.
- User understands dashboard role.

## Phase 11: Extraction Review

Purpose: prevent accidental leak or behavior drift.

Checks:

1. Search for private project names.
2. Search for absolute maintainer paths.
3. Search for API keys/secrets.
4. Search for raw PDFs.
5. Search for real paper dossiers.
6. Run tests.
7. Run one fresh workspace initialization.
8. Open dashboard against fresh workspace.

Acceptance:

- No private data.
- Existing workflow semantics preserved.
- Public repo can serve as plugin source.

## Implementation Order

Recommended order:

1. Phase 0: README/boundary cleanup.
2. Phase 1: plugin skeleton.
3. Phase 2: workspace templates/config.
4. Phase 3: workflows.
5. Phase 4: skills.
6. Phase 5: graph core tools.
7. Phase 6: early smoke tests and leak scan.
8. Phase 7: Zotero bridge.
9. Phase 8: dashboard.
10. Phase 9: full test pass.
11. Phase 10: docs.
12. Phase 11: review.

Reason:

Install/init boundary should exist before copying larger subsystems. Graph core should prove portability before Zotero and dashboard are added.

## Stop Rule

Stop before changing workflow semantics.

If extraction reveals a tool or skill needs redesign, record it as follow-up. Do not fold redesign into public MVP extraction unless it blocks basic portability.
