# Demo Project Design

Date: 2026-05-14
Status: Draft

## Context

Research Pilot now has dashboard pages for project state, paper library, and related-work lineage, but a fresh plugin checkout has no realistic project data. The existing `examples/demo` fixture only contains small graph-event JSON and is useful for tests, not for visual inspection.

The local workspace at `/Users/qing/Research/PersonalResearchWiki/wiki/projects/CVPR2026_VisualAffordance` is a better source shape because it has project overview, query pack, paper dossiers, graph read-model content, and enough related-work material to exercise dashboard views. It must not be copied as-is because it contains private absolute paths, Zotero attachment references, submission-specific wording, and unpublished project claims.

## Goal

Add a built-in, deletable demo project so new users and local developers can immediately inspect Research Pilot behavior in the dashboard.

The demo should make these surfaces observable:

- project overview and query-pack display;
- project graph read models after rebuild;
- paper dossiers;
- related-work lineage dashboard page;
- source-boundary language that separates demo artifacts from Project Understanding Graph truth.

## Non-Goals

- Do not publish the raw `CVPR2026_VisualAffordance` workspace.
- Do not commit PDFs, Zotero local paths, Zotero attachment IDs, generated dashboard indexes, SQLite DB files, or private submission text.
- Do not make the dashboard mutate or delete projects.
- Do not turn demo data into a required product dependency.

## Recommended Architecture

### Demo Source

Create a sanitized workspace example:

```text
examples/workspaces/demo-visual-affordance/
  AGENTS.md
  wiki/
    index.md
    log.md
    projects/DemoVisualAffordance/
    graphs/events/projects/DemoVisualAffordance.jsonl
    _system/
  .research-pilot/config.example.toml
```

The demo project should be adapted from the local visual-affordance project, but renamed and scrubbed:

- project id: `DemoVisualAffordance`;
- user-facing title: `Demo Visual Affordance`;
- frontmatter includes `demo: true`;
- all private paths removed;
- all submission-specific wording rewritten as generic demo framing;
- public-paper dossiers retained only when their content does not expose private local state;
- private project paper dossier removed or converted into a small synthetic demo note with clear `demo: true`;
- related-work lineage artifact added under the existing lineage path:

```text
wiki/projects/DemoVisualAffordance/literature-rounds/demo-affordance-lineage/
  related-work-lineage.json
  related-work-lineage.md
```

### Workspace Initialization

Enhance `tools/research_pilot_init.py`:

- default behavior copies the normal workspace template plus the demo project;
- add `--no-demo` to skip demo copy;
- add `--demo-only` only if useful for tests or local dashboard development;
- never overwrite a user-modified demo project unless `--overwrite` is set;
- print a short note that demo data is deletable.

Default demo visibility matches the user expectation: new users see one project immediately. `--no-demo` preserves clean-workspace setups.

### Delete Model

MVP deletion is file-based, not dashboard-based. Docs should say:

```bash
rm -rf wiki/projects/DemoVisualAffordance
rm -f wiki/graphs/events/projects/DemoVisualAffordance.jsonl
python3 "$PLUGIN_ROOT/tools/build_dashboard_index.py" --repo "$WORKSPACE"
```

If graph snapshot/DB files exist, the normal rebuild commands can refresh them. The dashboard remains read-only.

### Dashboard Behavior

Dashboard should detect `demo: true` from project metadata or read-model fields and show a small `Demo` badge on project cards and project headers.

No new dashboard editing surface is needed.

## Sanitization Rules

Before committing the demo, run a repository scan against the demo tree. The demo must not contain:

- `/Users/qing`;
- `Zotero/storage`;
- local PDF paths;
- Zotero attachment IDs;
- unpublished submission PDF names;
- `CVPR2026_VisualAffordance`;
- private future-project references such as `AAAI2027`;
- generated `.dashboard` files;
- `graph.db`;
- raw PDF files.

Public paper names and ordinary bibliographic facts can remain. Project-specific conclusions should be rewritten as demo examples, not asserted as a real submitted paper's claims.

## Test Plan

Add tests for:

- init copies demo by default;
- init `--no-demo` skips demo;
- init does not overwrite demo files without `--overwrite`;
- dashboard index includes demo metadata;
- dashboard render code can show a demo badge;
- demo tree scan rejects private paths and generated files;
- related-work lineage in demo validates with `tools/related_work_lineage_cli.py`.

Run:

```bash
python3 -m unittest tests.test_plugin_commands tests.test_dashboard_public tests.test_related_work_lineage_cli -v
python3 tools/related_work_lineage_cli.py validate --path examples/workspaces/demo-visual-affordance/wiki/projects/DemoVisualAffordance/literature-rounds/demo-affordance-lineage/related-work-lineage.json --json
scripts/release_check.sh
```

## Open Decisions

1. Whether init should default to `--with-demo` forever or only while product is young.
2. Whether demo should include a full graph event history or a compact minimal graph event file plus rich markdown artifacts.
3. Whether the dashboard should include a "delete demo" hint in empty/new-workspace states.

Recommended MVP answers:

- default include demo now;
- use compact graph events plus rich project markdown and lineage artifacts;
- document deletion in guides, do not add dashboard deletion.
