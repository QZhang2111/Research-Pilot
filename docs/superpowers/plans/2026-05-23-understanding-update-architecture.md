# UnderstandingUpdate Architecture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an `UnderstandingUpdate` product-truth layer beside existing graph truth, with validation, append/read helpers, `ProjectUnderstanding` projection, workspace template support, and docs.

**Architecture:** Add a small Python core module for semantic understanding events, a thin CLI wrapper, JSON schemas copied into new workspaces, and tests around validation/projection/CLI behavior. Existing graph events, graph delta flow, dashboard files, and `DemoVisualAffordance` remain unchanged.

**Tech Stack:** Python 3 standard library, `unittest`, JSONL files, existing Research-Pilot workspace templates and CLI patterns.

---

## Scope Guard

Do not edit:

- `dashboard/**`
- `examples/workspaces/demo-visual-affordance/**`
- existing `wiki/graphs/events/**` templates beyond untouched schema files

Do not remove:

- graph event schema
- graph delta CLI/API
- Zotero bridge
- demo project files

Allowed new product-truth path:

```text
wiki/understanding/events/<project_id>.jsonl
wiki/understanding/project-understanding/<project_id>.json
wiki/understanding/schema/understanding-update.schema.json
wiki/understanding/schema/project-understanding.schema.json
```

## File Map

Create:

- `tools/understanding_store.py`
  - Core validation, JSONL read/write, source normalization, and projection helpers.
- `tools/understanding_cli.py`
  - Thin CLI for `append`, `validate`, and `build-project-understanding`.
- `templates/workspace/wiki/understanding/events/.gitkeep`
  - Keeps product-truth event directory in initialized workspaces.
- `templates/workspace/wiki/understanding/project-understanding/.gitkeep`
  - Keeps generated projection directory in initialized workspaces.
- `templates/workspace/wiki/understanding/schema/understanding-update.schema.json`
  - Contract for semantic update records.
- `templates/workspace/wiki/understanding/schema/project-understanding.schema.json`
  - Contract for generated projection.
- `tests/test_understanding_store.py`
  - Unit tests for validation, append/read, duplicate IDs, and projection.
- `tests/test_understanding_cli.py`
  - CLI tests for append/validate/build flows.
- `tests/test_understanding_schema_contracts.py`
  - Schema presence and key enum contract tests.
- `docs/guides/understanding-updates.md`
  - Architecture guide for new layer.

Modify:

- `tools/README.md`
  - Add `understanding` area and truth-boundary note.
- `docs/guides/core-workflows.md`
  - Add ambient update as normal path, graph delta as advanced path.

---

### Task 1: Add Understanding Schema Contracts

**Files:**
- Create: `templates/workspace/wiki/understanding/schema/understanding-update.schema.json`
- Create: `templates/workspace/wiki/understanding/schema/project-understanding.schema.json`
- Create: `templates/workspace/wiki/understanding/events/.gitkeep`
- Create: `templates/workspace/wiki/understanding/project-understanding/.gitkeep`
- Test: `tests/test_understanding_schema_contracts.py`

- [ ] **Step 1: Write failing schema contract tests**

Create `tests/test_understanding_schema_contracts.py`:

```python
import json
import unittest
from pathlib import Path


class UnderstandingSchemaContractsTest(unittest.TestCase):
    def test_workspace_templates_include_understanding_contracts(self):
        schema_dir = Path("templates/workspace/wiki/understanding/schema")
        update_schema = json.loads((schema_dir / "understanding-update.schema.json").read_text(encoding="utf-8"))
        projection_schema = json.loads((schema_dir / "project-understanding.schema.json").read_text(encoding="utf-8"))

        self.assertEqual(update_schema["$id"], "https://research-pilot.local/schema/understanding-update-v1")
        self.assertEqual(update_schema["properties"]["schema_version"]["const"], "understanding-update-v1")
        self.assertIn("read_source", update_schema["$defs"]["taskKind"]["enum"])
        self.assertIn("agent-inferred", update_schema["$defs"]["confidenceStatus"]["enum"])
        self.assertIn("skimmed", update_schema["$defs"]["sourceStatus"]["enum"])
        self.assertEqual(projection_schema["$id"], "https://research-pilot.local/schema/project-understanding-v1")
        self.assertEqual(projection_schema["properties"]["schema_version"]["const"], "project-understanding-v1")
        self.assertIn("recent_changes", projection_schema["required"])
        self.assertIn("next_moves", projection_schema["required"])

    def test_workspace_templates_keep_understanding_directories(self):
        root = Path("templates/workspace/wiki/understanding")
        self.assertTrue((root / "events" / ".gitkeep").is_file())
        self.assertTrue((root / "project-understanding" / ".gitkeep").is_file())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m unittest tests.test_understanding_schema_contracts -v
```

Expected: FAIL with missing schema files.

- [ ] **Step 3: Add understanding update schema**

Create `templates/workspace/wiki/understanding/schema/understanding-update.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://research-pilot.local/schema/understanding-update-v1",
  "title": "Research Pilot Understanding Update v1",
  "type": "object",
  "required": [
    "schema_version",
    "update_id",
    "project_id",
    "created_at",
    "actor",
    "task",
    "source_refs",
    "recent_change_summary",
    "confidence"
  ],
  "properties": {
    "schema_version": { "const": "understanding-update-v1" },
    "update_id": { "type": "string", "minLength": 1 },
    "project_id": { "type": "string", "minLength": 1 },
    "created_at": { "type": "string", "minLength": 1 },
    "actor": { "type": "string", "enum": ["agent", "human", "system"] },
    "task": {
      "type": "object",
      "required": ["kind", "summary"],
      "properties": {
        "kind": { "$ref": "#/$defs/taskKind" },
        "summary": { "type": "string", "minLength": 1 }
      },
      "additionalProperties": true
    },
    "source_refs": { "type": "array", "items": { "type": "string" } },
    "new_sources": { "type": "array", "items": { "$ref": "#/$defs/sourceRecord" } },
    "changed_claims": { "type": "array", "items": { "$ref": "#/$defs/claimChange" } },
    "new_evidence": { "type": "array", "items": { "$ref": "#/$defs/evidenceRecord" } },
    "new_gaps": { "type": "array", "items": { "$ref": "#/$defs/gapRecord" } },
    "status_changes": { "type": "array", "items": { "$ref": "#/$defs/statusChange" } },
    "recent_change_summary": { "type": "string", "minLength": 1 },
    "next_moves": { "type": "array", "items": { "$ref": "#/$defs/nextMove" } },
    "confidence": { "$ref": "#/$defs/confidenceStatus" },
    "metadata": { "type": "object" }
  },
  "$defs": {
    "taskKind": {
      "type": "string",
      "enum": [
        "read_source",
        "skim_source",
        "summarize_source",
        "compare_sources",
        "find_related_work",
        "check_claim",
        "review_experiment",
        "discuss_direction",
        "identify_gap",
        "plan_next_work",
        "draft_research_text",
        "manual_note"
      ]
    },
    "sourceType": {
      "type": "string",
      "enum": ["pdf", "url", "arxiv", "doi", "markdown_note", "experiment_result", "zotero_item", "manual"]
    },
    "sourceStatus": {
      "type": "string",
      "enum": ["seen", "skimmed", "read", "used"]
    },
    "confidenceStatus": {
      "type": "string",
      "enum": ["agent-inferred", "source-backed", "user-confirmed", "contested", "weak", "stale"]
    },
    "sourceRecord": {
      "type": "object",
      "required": ["source_id", "type", "title", "status"],
      "properties": {
        "source_id": { "type": "string", "minLength": 1 },
        "type": { "$ref": "#/$defs/sourceType" },
        "locator": { "type": "string" },
        "title": { "type": "string", "minLength": 1 },
        "status": { "$ref": "#/$defs/sourceStatus" },
        "relevance": { "type": "string" },
        "related_claims": { "type": "array", "items": { "type": "string" } },
        "related_gaps": { "type": "array", "items": { "type": "string" } }
      },
      "additionalProperties": true
    },
    "claimChange": {
      "type": "object",
      "required": ["claim_id", "text"],
      "properties": {
        "claim_id": { "type": "string", "minLength": 1 },
        "text": { "type": "string", "minLength": 1 },
        "change": { "type": "string" },
        "status": { "$ref": "#/$defs/confidenceStatus" },
        "supporting_sources": { "type": "array", "items": { "type": "string" } },
        "challenging_sources": { "type": "array", "items": { "type": "string" } },
        "weakness": { "type": "string" }
      },
      "additionalProperties": true
    },
    "evidenceRecord": {
      "type": "object",
      "required": ["evidence_id", "text"],
      "properties": {
        "evidence_id": { "type": "string", "minLength": 1 },
        "text": { "type": "string", "minLength": 1 },
        "source_refs": { "type": "array", "items": { "type": "string" } },
        "related_claims": { "type": "array", "items": { "type": "string" } }
      },
      "additionalProperties": true
    },
    "gapRecord": {
      "type": "object",
      "required": ["gap_id", "text"],
      "properties": {
        "gap_id": { "type": "string", "minLength": 1 },
        "text": { "type": "string", "minLength": 1 },
        "type": { "type": "string" },
        "related_claims": { "type": "array", "items": { "type": "string" } },
        "related_sources": { "type": "array", "items": { "type": "string" } }
      },
      "additionalProperties": true
    },
    "statusChange": {
      "type": "object",
      "required": ["target_id", "status"],
      "properties": {
        "target_id": { "type": "string", "minLength": 1 },
        "target_type": { "type": "string" },
        "status": { "$ref": "#/$defs/confidenceStatus" },
        "reason": { "type": "string" }
      },
      "additionalProperties": true
    },
    "nextMove": {
      "type": "object",
      "required": ["move_id", "type", "text"],
      "properties": {
        "move_id": { "type": "string", "minLength": 1 },
        "type": { "type": "string", "enum": ["read", "search", "compare", "test", "revise", "write", "clarify"] },
        "text": { "type": "string", "minLength": 1 },
        "rationale": { "type": "string" },
        "suggested_prompt": { "type": "string" }
      },
      "additionalProperties": true
    }
  }
}
```

- [ ] **Step 4: Add project understanding schema**

Create `templates/workspace/wiki/understanding/schema/project-understanding.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://research-pilot.local/schema/project-understanding-v1",
  "title": "Research Pilot Project Understanding v1",
  "type": "object",
  "required": [
    "schema_version",
    "project_id",
    "generated_at",
    "project_brief",
    "sources",
    "claims",
    "evidence",
    "gaps",
    "recent_changes",
    "next_moves",
    "inputs"
  ],
  "properties": {
    "schema_version": { "const": "project-understanding-v1" },
    "project_id": { "type": "string", "minLength": 1 },
    "generated_at": { "type": "string", "minLength": 1 },
    "project_brief": { "type": "object" },
    "sources": { "type": "array", "items": { "type": "object" } },
    "claims": { "type": "array", "items": { "type": "object" } },
    "evidence": { "type": "array", "items": { "type": "object" } },
    "gaps": { "type": "array", "items": { "type": "object" } },
    "recent_changes": { "type": "array", "items": { "type": "object" } },
    "next_moves": { "type": "array", "items": { "type": "object" } },
    "inputs": { "type": "array", "items": { "type": "string" } }
  }
}
```

- [ ] **Step 5: Add directory keep files**

Create empty files:

```text
templates/workspace/wiki/understanding/events/.gitkeep
templates/workspace/wiki/understanding/project-understanding/.gitkeep
```

- [ ] **Step 6: Run schema tests**

Run:

```bash
python3 -m unittest tests.test_understanding_schema_contracts -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add templates/workspace/wiki/understanding tests/test_understanding_schema_contracts.py
git commit -m "feat: add understanding schema contracts"
```

---

### Task 2: Add Understanding Core Store

**Files:**
- Create: `tools/understanding_store.py`
- Test: `tests/test_understanding_store.py`

- [ ] **Step 1: Write failing store tests**

Create `tests/test_understanding_store.py`:

```python
import tempfile
import unittest
from pathlib import Path

from tools.understanding_store import (
    append_understanding_update,
    build_project_understanding,
    project_understanding_path,
    read_understanding_updates,
    understanding_event_path,
    validate_understanding_update,
)


def sample_update(update_id: str = "UU0001") -> dict:
    return {
        "schema_version": "understanding-update-v1",
        "update_id": update_id,
        "project_id": "DemoProject",
        "created_at": "2026-05-23T00:00:00Z",
        "actor": "agent",
        "task": {"kind": "read_source", "summary": "Read S1 and checked claim C1."},
        "source_refs": ["arxiv:1234.56789"],
        "new_sources": [
            {
                "source_id": "S1",
                "type": "arxiv",
                "locator": "https://arxiv.org/abs/1234.56789",
                "title": "Counterfactual Affordance Benchmark",
                "status": "read",
                "relevance": "Tests affordance reasoning indirectly.",
                "related_claims": ["C1"],
                "related_gaps": ["G1"],
            }
        ],
        "changed_claims": [
            {
                "claim_id": "C1",
                "text": "VLMs may encode affordance priors.",
                "change": "weakened",
                "status": "weak",
                "supporting_sources": ["S1"],
                "challenging_sources": [],
                "weakness": "Evidence is indirect.",
            }
        ],
        "new_evidence": [
            {
                "evidence_id": "E1",
                "text": "S1 reports affordance recognition but not causal interaction tests.",
                "source_refs": ["S1"],
                "related_claims": ["C1"],
            }
        ],
        "new_gaps": [
            {
                "gap_id": "G1",
                "text": "Need counterfactual interaction evidence.",
                "type": "missing evidence",
                "related_claims": ["C1"],
                "related_sources": ["S1"],
            }
        ],
        "status_changes": [
            {
                "target_id": "C1",
                "target_type": "claim",
                "status": "weak",
                "reason": "Support is indirect.",
            }
        ],
        "recent_change_summary": "C1 weakened after reading S1; G1 added.",
        "next_moves": [
            {
                "move_id": "N1",
                "type": "search",
                "text": "Find counterfactual VLM affordance benchmarks.",
                "rationale": "C1 lacks direct evidence.",
                "suggested_prompt": "Find papers testing VLM affordance reasoning under counterfactual object interactions.",
            }
        ],
        "confidence": "agent-inferred",
    }


class UnderstandingStoreTest(unittest.TestCase):
    def test_validate_accepts_sample_update(self):
        result = validate_understanding_update(sample_update())
        self.assertEqual([], result["errors"])
        self.assertTrue(result["valid"])

    def test_validate_rejects_missing_required_fields(self):
        update = sample_update()
        update.pop("task")
        result = validate_understanding_update(update)
        self.assertFalse(result["valid"])
        self.assertIn("missing task", result["errors"])

    def test_append_and_read_update_jsonl(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = append_understanding_update(root, "DemoProject", sample_update())
            updates = read_understanding_updates(root, "DemoProject")

        self.assertTrue(result["appended"])
        self.assertEqual("wiki/understanding/events/DemoProject.jsonl", result["event_path"])
        self.assertEqual(["UU0001"], [item["update_id"] for item in updates])

    def test_append_rejects_duplicate_update_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            append_understanding_update(root, "DemoProject", sample_update())
            result = append_understanding_update(root, "DemoProject", sample_update())

        self.assertFalse(result["appended"])
        self.assertIn("duplicate update_id: UU0001", result["errors"])

    def test_project_understanding_projection_collects_current_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            append_understanding_update(root, "DemoProject", sample_update("UU0001"))
            projection = build_project_understanding(root, "DemoProject", generated_at="2026-05-23T00:10:00Z")

        self.assertEqual("project-understanding-v1", projection["schema_version"])
        self.assertEqual("DemoProject", projection["project_id"])
        self.assertEqual("Counterfactual Affordance Benchmark", projection["sources"][0]["title"])
        self.assertEqual("VLMs may encode affordance priors.", projection["claims"][0]["text"])
        self.assertEqual("Need counterfactual interaction evidence.", projection["gaps"][0]["text"])
        self.assertEqual("C1 weakened after reading S1; G1 added.", projection["recent_changes"][0]["summary"])
        self.assertEqual("Find counterfactual VLM affordance benchmarks.", projection["next_moves"][0]["text"])
        self.assertIn("wiki/understanding/events/DemoProject.jsonl", projection["inputs"])

    def test_paths_are_under_understanding_directory(self):
        root = Path("/tmp/research-pilot-test")
        self.assertEqual(root / "wiki" / "understanding" / "events" / "DemoProject.jsonl", understanding_event_path(root, "DemoProject"))
        self.assertEqual(root / "wiki" / "understanding" / "project-understanding" / "DemoProject.json", project_understanding_path(root, "DemoProject"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m unittest tests.test_understanding_store -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'tools.understanding_store'`.

- [ ] **Step 3: Implement `tools/understanding_store.py`**

Create `tools/understanding_store.py`:

```python
#!/usr/bin/env python3
"""Semantic understanding-event helpers for Research Pilot workspaces."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Sequence


SCHEMA_VERSION = "understanding-update-v1"
PROJECTION_SCHEMA_VERSION = "project-understanding-v1"
ACTORS = {"agent", "human", "system"}
TASK_KINDS = {
    "read_source",
    "skim_source",
    "summarize_source",
    "compare_sources",
    "find_related_work",
    "check_claim",
    "review_experiment",
    "discuss_direction",
    "identify_gap",
    "plan_next_work",
    "draft_research_text",
    "manual_note",
}
SOURCE_TYPES = {"pdf", "url", "arxiv", "doi", "markdown_note", "experiment_result", "zotero_item", "manual"}
SOURCE_STATUSES = {"seen", "skimmed", "read", "used"}
CONFIDENCE_STATUSES = {"agent-inferred", "source-backed", "user-confirmed", "contested", "weak", "stale"}
NEXT_MOVE_TYPES = {"read", "search", "compare", "test", "revise", "write", "clarify"}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def relpath(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def understanding_event_path(root: Path, project_id: str) -> Path:
    return Path(root).resolve() / "wiki" / "understanding" / "events" / f"{project_id}.jsonl"


def project_understanding_path(root: Path, project_id: str) -> Path:
    return Path(root).resolve() / "wiki" / "understanding" / "project-understanding" / f"{project_id}.json"


def _require_string(update: Dict[str, Any], field: str, errors: List[str]) -> None:
    if not isinstance(update.get(field), str) or not update.get(field):
        errors.append(f"missing {field}")


def _require_list(update: Dict[str, Any], field: str, errors: List[str]) -> None:
    if not isinstance(update.get(field), list):
        errors.append(f"{field} must be an array")


def validate_understanding_update(update: Dict[str, Any]) -> Dict[str, Any]:
    errors: List[str] = []
    for field in ["schema_version", "update_id", "project_id", "created_at", "actor", "recent_change_summary", "confidence"]:
        _require_string(update, field, errors)
    for field in ["source_refs"]:
        _require_list(update, field, errors)
    if not isinstance(update.get("task"), dict):
        errors.append("missing task")
    if errors:
        return {"valid": False, "errors": errors}

    if update["schema_version"] != SCHEMA_VERSION:
        errors.append("schema_version must be understanding-update-v1")
    if update["actor"] not in ACTORS:
        errors.append(f"unsupported actor: {update['actor']}")
    if update["confidence"] not in CONFIDENCE_STATUSES:
        errors.append(f"unsupported confidence: {update['confidence']}")

    task = update["task"]
    if not isinstance(task.get("kind"), str) or not task.get("kind"):
        errors.append("task.kind must be a non-empty string")
    elif task["kind"] not in TASK_KINDS:
        errors.append(f"unsupported task.kind: {task['kind']}")
    if not isinstance(task.get("summary"), str) or not task.get("summary"):
        errors.append("task.summary must be a non-empty string")

    for source in update.get("new_sources") or []:
        if not isinstance(source, dict):
            errors.append("new_sources items must be objects")
            continue
        if not source.get("source_id"):
            errors.append("source.source_id must be non-empty")
        if source.get("type") not in SOURCE_TYPES:
            errors.append(f"unsupported source.type: {source.get('type')}")
        if source.get("status") not in SOURCE_STATUSES:
            errors.append(f"unsupported source.status: {source.get('status')}")
        if not source.get("title"):
            errors.append("source.title must be non-empty")

    for move in update.get("next_moves") or []:
        if not isinstance(move, dict):
            errors.append("next_moves items must be objects")
            continue
        if not move.get("move_id"):
            errors.append("next_move.move_id must be non-empty")
        if move.get("type") not in NEXT_MOVE_TYPES:
            errors.append(f"unsupported next_move.type: {move.get('type')}")
        if not move.get("text"):
            errors.append("next_move.text must be non-empty")

    return {"valid": not errors, "errors": errors}


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    records: List[Dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_number}: expected JSON object")
        records.append(value)
    return records


def read_understanding_updates(root: Path, project_id: str) -> List[Dict[str, Any]]:
    return read_jsonl(understanding_event_path(root, project_id))


def append_understanding_update(root: Path, project_id: str, update: Dict[str, Any]) -> Dict[str, Any]:
    root = Path(root).resolve()
    validation = validate_understanding_update(update)
    if not validation["valid"]:
        return {"valid": False, "appended": False, "errors": validation["errors"], "warnings": []}
    if update["project_id"] != project_id:
        return {"valid": False, "appended": False, "errors": ["project_id mismatch"], "warnings": []}

    path = understanding_event_path(root, project_id)
    existing = read_jsonl(path)
    update_id = str(update["update_id"])
    if update_id in {str(item.get("update_id") or "") for item in existing}:
        return {"valid": False, "appended": False, "errors": [f"duplicate update_id: {update_id}"], "warnings": []}

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(stable_json(update) + "\n")
    return {"valid": True, "appended": True, "update_id": update_id, "event_path": relpath(path, root), "errors": [], "warnings": []}


def _upsert_by_id(items: Dict[str, Dict[str, Any]], item: Dict[str, Any], key: str, update_id: str) -> None:
    value = str(item.get(key) or "")
    if not value:
        return
    merged = dict(items.get(value) or {})
    merged.update(item)
    merged["last_update_id"] = update_id
    items[value] = merged


def build_project_understanding(root: Path, project_id: str, generated_at: str | None = None) -> Dict[str, Any]:
    root = Path(root).resolve()
    updates = read_understanding_updates(root, project_id)
    sources: Dict[str, Dict[str, Any]] = {}
    claims: Dict[str, Dict[str, Any]] = {}
    evidence: Dict[str, Dict[str, Any]] = {}
    gaps: Dict[str, Dict[str, Any]] = {}
    next_moves: Dict[str, Dict[str, Any]] = {}
    recent_changes: List[Dict[str, Any]] = []

    for update in updates:
        update_id = str(update.get("update_id") or "")
        for source in update.get("new_sources") or []:
            _upsert_by_id(sources, dict(source), "source_id", update_id)
        for claim in update.get("changed_claims") or []:
            _upsert_by_id(claims, dict(claim), "claim_id", update_id)
        for item in update.get("new_evidence") or []:
            _upsert_by_id(evidence, dict(item), "evidence_id", update_id)
        for gap in update.get("new_gaps") or []:
            _upsert_by_id(gaps, dict(gap), "gap_id", update_id)
        for move in update.get("next_moves") or []:
            _upsert_by_id(next_moves, dict(move), "move_id", update_id)
        recent_changes.append(
            {
                "update_id": update_id,
                "created_at": str(update.get("created_at") or ""),
                "task": update.get("task") or {},
                "summary": str(update.get("recent_change_summary") or ""),
                "source_refs": list(update.get("source_refs") or []),
                "confidence": str(update.get("confidence") or ""),
            }
        )

    event_path = understanding_event_path(root, project_id)
    return {
        "schema_version": PROJECTION_SCHEMA_VERSION,
        "project_id": project_id,
        "generated_at": generated_at or utc_now(),
        "project_brief": {},
        "sources": list(sources.values()),
        "claims": list(claims.values()),
        "evidence": list(evidence.values()),
        "gaps": list(gaps.values()),
        "recent_changes": recent_changes,
        "next_moves": list(next_moves.values()),
        "inputs": [relpath(event_path, root)] if event_path.exists() else [],
    }


def write_project_understanding(root: Path, project_id: str, generated_at: str | None = None) -> Dict[str, Any]:
    root = Path(root).resolve()
    projection = build_project_understanding(root, project_id, generated_at=generated_at)
    output = project_understanding_path(root, project_id)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(projection, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"valid": True, "written": True, "path": relpath(output, root), "project_understanding": projection}
```

- [ ] **Step 4: Run store tests**

Run:

```bash
python3 -m unittest tests.test_understanding_store -v
```

Expected: PASS.

- [ ] **Step 5: Run graph regression tests**

Run:

```bash
python3 -m unittest tests.test_graph_core tests.test_graph_delta_loop -v
```

Expected: PASS. Graph path unchanged.

- [ ] **Step 6: Commit**

```bash
git add tools/understanding_store.py tests/test_understanding_store.py
git commit -m "feat: add understanding update store"
```

---

### Task 3: Add Understanding CLI

**Files:**
- Create: `tools/understanding_cli.py`
- Test: `tests/test_understanding_cli.py`

- [ ] **Step 1: Write failing CLI tests**

Create `tests/test_understanding_cli.py`:

```python
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.test_understanding_store import sample_update


class UnderstandingCliTest(unittest.TestCase):
    def test_append_validate_and_build_project_understanding(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            update_path = root / "update.json"
            update_path.write_text(json.dumps(sample_update(), ensure_ascii=False), encoding="utf-8")

            append = subprocess.run(
                [
                    sys.executable,
                    "tools/understanding_cli.py",
                    "append",
                    "--repo",
                    str(root),
                    "--project",
                    "DemoProject",
                    "--update",
                    str(update_path),
                    "--json",
                ],
                cwd=Path(__file__).resolve().parents[1],
                check=False,
                capture_output=True,
                text=True,
            )
            validate = subprocess.run(
                [
                    sys.executable,
                    "tools/understanding_cli.py",
                    "validate",
                    "--repo",
                    str(root),
                    "--project",
                    "DemoProject",
                    "--json",
                ],
                cwd=Path(__file__).resolve().parents[1],
                check=False,
                capture_output=True,
                text=True,
            )
            build = subprocess.run(
                [
                    sys.executable,
                    "tools/understanding_cli.py",
                    "build-project-understanding",
                    "--repo",
                    str(root),
                    "--project",
                    "DemoProject",
                    "--json",
                ],
                cwd=Path(__file__).resolve().parents[1],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(0, append.returncode, append.stderr)
        self.assertTrue(json.loads(append.stdout)["appended"])
        self.assertEqual(0, validate.returncode, validate.stderr)
        self.assertTrue(json.loads(validate.stdout)["valid"])
        self.assertEqual(0, build.returncode, build.stderr)
        build_result = json.loads(build.stdout)
        self.assertTrue(build_result["written"])
        self.assertEqual("wiki/understanding/project-understanding/DemoProject.json", build_result["path"])

    def test_append_invalid_update_returns_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            update_path = root / "bad.json"
            update = sample_update()
            update["confidence"] = "certain"
            update_path.write_text(json.dumps(update, ensure_ascii=False), encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    "tools/understanding_cli.py",
                    "append",
                    "--repo",
                    str(root),
                    "--project",
                    "DemoProject",
                    "--update",
                    str(update_path),
                    "--json",
                ],
                cwd=Path(__file__).resolve().parents[1],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(1, completed.returncode)
        self.assertIn("unsupported confidence", completed.stdout)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m unittest tests.test_understanding_cli -v
```

Expected: FAIL because `tools/understanding_cli.py` does not exist.

- [ ] **Step 3: Implement CLI**

Create `tools/understanding_cli.py`:

```python
#!/usr/bin/env python3
"""CLI for Research Pilot understanding updates."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

THIS_DIR = Path(__file__).resolve().parent
ROOT_DIR = THIS_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from tools.understanding_store import (
    append_understanding_update,
    read_understanding_updates,
    validate_understanding_update,
    write_project_understanding,
)


def load_json(path: Path) -> Dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON file must contain an object")
    return value


def print_result(result: Dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage Research Pilot understanding updates.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    append = subparsers.add_parser("append", help="Append an UnderstandingUpdate JSON file.")
    append.add_argument("--repo", default=".")
    append.add_argument("--project", required=True)
    append.add_argument("--update", required=True)
    append.add_argument("--json", action="store_true")

    validate = subparsers.add_parser("validate", help="Validate understanding updates for a project.")
    validate.add_argument("--repo", default=".")
    validate.add_argument("--project", required=True)
    validate.add_argument("--json", action="store_true")

    build = subparsers.add_parser("build-project-understanding", help="Build ProjectUnderstanding JSON.")
    build.add_argument("--repo", default=".")
    build.add_argument("--project", required=True)
    build.add_argument("--json", action="store_true")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    root = Path(args.repo).expanduser().resolve()

    if args.command == "append":
        try:
            update = load_json(Path(args.update).expanduser().resolve())
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            result = {"valid": False, "appended": False, "errors": [str(exc)], "warnings": []}
            print_result(result, bool(args.json))
            return 1
        result = append_understanding_update(root, args.project, update)
        print_result(result, bool(args.json))
        return 0 if result.get("valid") else 1

    if args.command == "validate":
        errors = []
        updates = read_understanding_updates(root, args.project)
        for index, update in enumerate(updates, start=1):
            validation = validate_understanding_update(update)
            for error in validation["errors"]:
                errors.append({"line": index, "update_id": update.get("update_id", ""), "error": error})
        result = {"valid": not errors, "update_count": len(updates), "errors": errors}
        print_result(result, bool(args.json))
        return 0 if result["valid"] else 1

    result = write_project_understanding(root, args.project)
    output = dict(result)
    output.pop("project_understanding", None)
    print_result(output, bool(args.json))
    return 0 if result.get("valid") else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

- [ ] **Step 4: Run CLI tests**

Run:

```bash
python3 -m unittest tests.test_understanding_cli -v
```

Expected: PASS.

- [ ] **Step 5: Run combined understanding tests**

Run:

```bash
python3 -m unittest tests.test_understanding_schema_contracts tests.test_understanding_store tests.test_understanding_cli -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add tools/understanding_cli.py tests/test_understanding_cli.py
git commit -m "feat: add understanding update CLI"
```

---

### Task 4: Integrate Workspace Initialization and Docs

**Files:**
- Modify: `tools/README.md`
- Modify: `docs/guides/core-workflows.md`
- Create: `docs/guides/understanding-updates.md`
- Test: `tests/test_research_pilot_status.py` only if status expectations need update; otherwise no test change.

- [ ] **Step 1: Verify template copy already covers understanding directories**

Run:

```bash
python3 -m unittest tests.test_project_shell_cli.ProjectShellCliTest.test_create_project_shell_without_graph_events -v
```

Expected after Task 1: PASS. `research_pilot_init.py` copies `templates/workspace` recursively, so no code change needed for template copy.

- [ ] **Step 2: Add docs guide**

Create `docs/guides/understanding-updates.md`:

```markdown
# Understanding Updates

Research Pilot has two durable layers.

Normal product layer:

```text
wiki/understanding/events/<project>.jsonl
```

This layer stores `UnderstandingUpdate` records. Agents write these after meaningful research work: reading a source, comparing papers, checking a claim, identifying a gap, or suggesting next work.

Advanced graph layer:

```text
wiki/graphs/events/projects/<project>.jsonl
```

This layer keeps formal graph events and graph deltas for rigorous claim/evidence/link workflows.

## Normal Agent Rule

After meaningful research work, write one compact understanding update:

```bash
python3 tools/understanding_cli.py append \
  --repo /path/to/workspace \
  --project DemoVisualAffordance \
  --update /path/to/update.json
```

Then build the current project understanding:

```bash
python3 tools/understanding_cli.py build-project-understanding \
  --repo /path/to/workspace \
  --project DemoVisualAffordance
```

## Boundary

Understanding updates are product truth for normal ambient use. Graph events remain advanced graph truth. Read models are generated projections.

Do not require Zotero for an understanding update. A source may be a PDF, URL, arXiv link, DOI, Markdown note, experiment result, Zotero item, or manual reference.
```

- [ ] **Step 3: Update `tools/README.md`**

Modify truth boundaries near top:

```markdown
- `wiki/understanding/events/**/*.jsonl` is normal product truth for ambient agent understanding updates.
- `wiki/graphs/events/**/*.jsonl` is advanced graph truth.
```

Add table row:

```markdown
| understanding | `understanding_store.py`, `understanding_cli.py` | Record ambient UnderstandingUpdates and build ProjectUnderstanding read models. |
```

- [ ] **Step 4: Update `docs/guides/core-workflows.md`**

Add section near core loop:

```markdown
## Ambient Understanding Updates

Normal Research Pilot use starts with chat. After a meaningful research task, the agent records an `UnderstandingUpdate` in `wiki/understanding/events/<project>.jsonl`. This captures what changed in project understanding: sources seen, claims changed, evidence added, gaps found, and next moves suggested.

Graph deltas remain available for advanced review mode. They are not required for every lightweight source note or agent observation.
```

- [ ] **Step 5: Run docs-related smoke tests**

Run:

```bash
python3 -m unittest tests.test_hidden_installer tests.test_plugin_health tests.test_project_shell_cli -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add tools/README.md docs/guides/core-workflows.md docs/guides/understanding-updates.md
git commit -m "docs: document understanding update layer"
```

---

### Task 5: Add Agent-Facing Example Without Changing Demo Project

**Files:**
- Create: `examples/demo/understanding/demo-understanding-update.json`
- Test: `tests/test_understanding_store.py`

- [ ] **Step 1: Add failing example validation test**

Append this test to `UnderstandingStoreTest` in `tests/test_understanding_store.py`:

```python
    def test_demo_understanding_update_example_is_valid(self):
        import json

        path = Path("examples/demo/understanding/demo-understanding-update.json")
        update = json.loads(path.read_text(encoding="utf-8"))
        result = validate_understanding_update(update)

        self.assertTrue(result["valid"], result["errors"])
        self.assertEqual("DemoVisualAffordance", update["project_id"])
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m unittest tests.test_understanding_store.UnderstandingStoreTest.test_demo_understanding_update_example_is_valid -v
```

Expected: FAIL because example file is missing.

- [ ] **Step 3: Add demo understanding update example**

Create `examples/demo/understanding/demo-understanding-update.json`:

```json
{
  "actor": "agent",
  "changed_claims": [
    {
      "challenging_sources": [],
      "change": "qualified",
      "claim_id": "C-demo-affordance-prior",
      "status": "weak",
      "supporting_sources": [
        "S-demo-luo2022-agd20k"
      ],
      "text": "Affordance models may capture object-use priors, but current evidence does not prove causal interaction understanding.",
      "weakness": "The support is indirect and benchmark-bound."
    }
  ],
  "confidence": "agent-inferred",
  "created_at": "2026-05-23T00:00:00Z",
  "metadata": {
    "example_only": true
  },
  "new_evidence": [
    {
      "evidence_id": "E-demo-agd20k-indirect",
      "related_claims": [
        "C-demo-affordance-prior"
      ],
      "source_refs": [
        "S-demo-luo2022-agd20k"
      ],
      "text": "AGD20K-style affordance grounding supports affordance localization, but does not isolate causal interaction reasoning."
    }
  ],
  "new_gaps": [
    {
      "gap_id": "G-demo-counterfactual-interaction",
      "related_claims": [
        "C-demo-affordance-prior"
      ],
      "related_sources": [
        "S-demo-luo2022-agd20k"
      ],
      "text": "Need counterfactual tests that separate object co-occurrence from interaction understanding.",
      "type": "missing evidence"
    }
  ],
  "new_sources": [
    {
      "locator": "wiki/projects/DemoVisualAffordance/papers/luo2022-agd20k/index.md",
      "related_claims": [
        "C-demo-affordance-prior"
      ],
      "related_gaps": [
        "G-demo-counterfactual-interaction"
      ],
      "relevance": "Useful for affordance grounding context, but indirect for causal interaction understanding.",
      "source_id": "S-demo-luo2022-agd20k",
      "status": "used",
      "title": "Learning Affordance Grounding from Exocentric Images",
      "type": "manual"
    }
  ],
  "next_moves": [
    {
      "move_id": "N-demo-counterfactual-search",
      "rationale": "The claim is weak because current evidence does not isolate interaction causality.",
      "suggested_prompt": "Find papers that test affordance or interaction reasoning under counterfactual object-use settings.",
      "text": "Search for counterfactual affordance or interaction-reasoning benchmarks.",
      "type": "search"
    }
  ],
  "project_id": "DemoVisualAffordance",
  "recent_change_summary": "Qualified the affordance-prior claim as weak and added a counterfactual interaction evidence gap.",
  "schema_version": "understanding-update-v1",
  "source_refs": [
    "wiki/projects/DemoVisualAffordance/papers/luo2022-agd20k/index.md"
  ],
  "status_changes": [
    {
      "reason": "Evidence supports affordance grounding but not causal interaction understanding.",
      "status": "weak",
      "target_id": "C-demo-affordance-prior",
      "target_type": "claim"
    }
  ],
  "task": {
    "kind": "check_claim",
    "summary": "Checked whether affordance grounding evidence supports interaction-understanding claims."
  },
  "update_id": "UU-demo-0001"
}
```

- [ ] **Step 4: Run understanding tests**

Run:

```bash
python3 -m unittest tests.test_understanding_store -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add examples/demo/understanding/demo-understanding-update.json tests/test_understanding_store.py
git commit -m "test: add demo understanding update example"
```

---

### Task 6: Final Verification

**Files:**
- No planned file edits.

- [ ] **Step 1: Run targeted understanding suite**

Run:

```bash
python3 -m unittest tests.test_understanding_schema_contracts tests.test_understanding_store tests.test_understanding_cli -v
```

Expected: PASS.

- [ ] **Step 2: Run compatibility suite**

Run:

```bash
python3 -m unittest tests.test_graph_core tests.test_graph_delta_loop tests.test_project_shell_cli tests.test_plugin_health -v
```

Expected: PASS.

- [ ] **Step 3: Run release check**

Run:

```bash
./scripts/release_check.sh
```

Expected: PASS. If it fails, inspect failure and fix only issues caused by this work.

- [ ] **Step 4: Verify no dashboard or demo workspace changes**

Run:

```bash
git status --short
git diff --name-only
```

Expected:

```text
docs/guides/core-workflows.md
docs/guides/understanding-updates.md
examples/demo/understanding/demo-understanding-update.json
templates/workspace/wiki/understanding/events/.gitkeep
templates/workspace/wiki/understanding/project-understanding/.gitkeep
templates/workspace/wiki/understanding/schema/project-understanding.schema.json
templates/workspace/wiki/understanding/schema/understanding-update.schema.json
tests/test_understanding_cli.py
tests/test_understanding_schema_contracts.py
tests/test_understanding_store.py
tools/README.md
tools/understanding_cli.py
tools/understanding_store.py
```

There must be no `dashboard/**` path and no `examples/workspaces/demo-visual-affordance/**` path.

- [ ] **Step 5: Commit verification fixes**

If verification required edits:

```bash
git add <changed-files>
git commit -m "test: verify understanding update architecture"
```

If no edits needed, skip commit.

---

## Self-Review Checklist

- PRD coverage:
  - `UnderstandingUpdate` schema and validation: Task 1, Task 2.
  - Append-only log per project: Task 2.
  - Helper CLI: Task 3.
  - `ProjectUnderstanding` projection: Task 2, Task 3.
  - Source-agnostic source records and depth labels: Task 1, Task 2.
  - Compatibility with demo and graph tools: Task 5, Task 6.
  - Docs explaining boundary: Task 4.
- Scope guard:
  - No dashboard file edits.
  - No `DemoVisualAffordance` workspace edits.
  - Existing graph and delta tools remain.
- Type consistency:
  - `understanding-update-v1` and `project-understanding-v1` used consistently.
  - CLI commands: `append`, `validate`, `build-project-understanding`.
  - Paths match PRD: `wiki/understanding/events` and `wiki/understanding/project-understanding`.
