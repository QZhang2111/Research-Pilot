# Zotero Adapter Protocol

Core rule:

```text
Research Pilot is source-agnostic for first-run project memory.
Zotero is an optional supported adapter for paper metadata, PDFs, collections, and operational paper triage.
```

Research Pilot does not reimplement citation management and does not require Zotero before first value.

## Public Boundary

Source intake records durable source identity from:

- PDF path;
- URL;
- arXiv ID;
- DOI;
- manual source refs;
- experiment result refs;
- Zotero item key.

Public tooling includes configurable Zotero bridge helpers for metadata, collection, and status-mirror workflows. Credentialed Zotero operations require user-provided local config and must preserve the optional-adapter boundary.

## Human Gate

Agent may intake, summarize, and propose. Human decides approval, project-core status, and graph delta acceptance.
