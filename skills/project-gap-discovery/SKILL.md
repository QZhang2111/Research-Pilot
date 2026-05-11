---
name: project-gap-discovery
description: Use when the user wants papers to consider for a graph gap or missing evidence need.
argument-hint: "<project> <gap-id>"
---

# Project Gap Discovery

This skill owns the user-facing path:

```text
graph gap -> evidence need -> search -> lead scoring -> human chooses deep-read
```

In the current public extraction, use `project-gap-analysis` to expose the gap first. Full search/lead tooling is a later extraction slice unless installed.

Do not add papers to Zotero, approve candidates, or append graph events.

