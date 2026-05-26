# Research Pilot Skills

Skills are agent-facing routing instructions. Users should not need to know skill
names or workflow names. The normal user surface is chat; skills let the agent
operate Research Pilot's local dataset, source adapters, dashboard observer, and
advanced review tools.

## Skill Status

| Status | Meaning |
| --- | --- |
| Core | Normal chat-first project tracking, source recording, dashboard opening, and project-understanding updates. |
| Supported adapter | Useful bridge into project understanding, but not product identity or first-run requirement. |
| Advanced | Strict review / graph rigor kept behind the normal product surface. |
| Transition | Still tested and usable, but naming or product role should be replaced before expanding. |

## Core

- `research-pilot`: intent router for project tracking, workspace inspection, dashboard opening, source recording, project updates, literature mapping, experiment records, and strict review.
- `research-pilot-first-run`: first workspace/project setup with DB/project brief defaults.
- `project-understanding-update`: ambient project understanding updates from agent work.
- `related-work-lineage`: paper-only literature structure and technical lineage.

## Supported Adapters

- `single-paper-deep-read`: source-level deep-read note creation.
- `paper-discovery-intake`: source identity capture and Zotero/manual bridge.
- `project-evidence-synthesis`: compare source evidence against current project understanding.

## Advanced

- `delta-update-protocol`: human-gated graph delta review.
- `deep-read-to-delta`: export paper deep-read notes into graph delta proposals.
- `project-gap-analysis`: inspect graph-derived evidence gaps.

## Transition

- `project-next-action`: keep as read-only advanced router; do not expand as core product surface.
- `project-experiment-proposal`: keep compatibility; future product direction is project experiment design/result records.
- `gap-driven-search`: keep compatibility; should fold under source/literature discovery.
- `project-gap-discovery`: keep compatibility; should fold under source/literature discovery.

## Cleanup Rule

Do not delete a skill only because it is advanced or transition. Delete after:

1. router references are removed;
2. workspace workflow docs are updated;
3. tests and smoke scripts stop depending on it;
4. replacement user path exists.
