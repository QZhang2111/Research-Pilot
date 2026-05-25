#!/usr/bin/env python3
"""Import legacy Research Pilot demo files into the local SQLite dataset."""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.build_dashboard_index import extract_section, first_sentence, normalize_slug, read_markdown, relpath
from tools.experiment_store import build_project_experiments
from tools.graph_store import build_snapshot_from_event_files
from tools.research_dataset import connect_dataset, dataset_db_path, initialize_dataset, json_dumps, require_valid_project_id
from tools.understanding_store import read_understanding_updates


DELETE_TABLES = (
    "audit_events",
    "updates",
    "activity_sessions",
    "entity_links",
    "experiment_artifacts",
    "experiment_metrics",
    "experiment_runs",
    "experiments",
    "literature_relations",
    "literature_items",
    "literature_lanes",
    "project_positionings",
    "understanding_link_endpoints",
    "understanding_links",
    "understanding_nodes",
    "sources",
    "projects",
)

NODE_TYPES = {
    "Question": "question",
    "Claim": "claim",
    "Evidence": "evidence",
    "Warrant": "warrant",
    "Limitation": "limitation",
}
LINK_TYPES = {"ReasoningLink": "reasoning", "TranslationLink": "translation"}
ENDPOINT_FIELDS = {
    "from_nodes": "from",
    "to_nodes": "to",
    "warrant_nodes": "warrant",
    "limitation_nodes": "limitation",
    "project_warrant_nodes": "project_warrant",
    "project_limitation_nodes": "project_limitation",
}
ORIGIN_TYPES = {
    "imported_paper_evidence": "imported_paper",
    "local_experiment_result": "local",
    "replication_result": "replication",
    "external_result": "external",
}
DEFAULT_RUN_SOURCE = "paper:zhang2026-geometry-interaction-vfm"


def import_demo_visual_affordance(root: Path, *, reset: bool = False) -> dict[str, Any]:
    return import_legacy_project(root, "DemoVisualAffordance", reset=reset)


def import_legacy_project(root: Path, project_id: str, *, reset: bool = False) -> dict[str, Any]:
    require_valid_project_id(project_id)
    root = Path(root)
    if not dataset_db_path(root).exists():
        initialize_dataset(root)

    timestamp = _utc_timestamp()
    warnings: list[str] = []

    connection = connect_dataset(root)
    try:
        exists = connection.execute("SELECT 1 FROM projects WHERE project_id = ?", (project_id,)).fetchone()
        if exists is not None and not reset:
            raise ValueError(f"project {project_id} already imported")

        with connection:
            if reset:
                for table in DELETE_TABLES:
                    connection.execute(f"DELETE FROM {table} WHERE project_id = ?", (project_id,))

            project = _build_project(root, project_id, warnings, timestamp)
            _insert_project(connection, project)

            audit_rows: list[tuple[str, str]] = [("projects", project_id)]

            sources = _build_sources(root, project_id, warnings, timestamp)
            _insert_many(connection, "sources", sources)
            audit_rows.extend(("sources", row["source_id"]) for row in sources)
            source_ids = {row["source_id"] for row in sources}
            source_matcher = _source_matcher(sources)

            nodes, links, endpoints = _build_graph_rows(root, project_id, warnings, timestamp, source_ids)
            _insert_many(connection, "understanding_nodes", nodes)
            _insert_many(connection, "understanding_links", links)
            _insert_many(connection, "understanding_link_endpoints", endpoints)
            audit_rows.extend(("understanding_nodes", row["node_id"]) for row in nodes)
            audit_rows.extend(("understanding_links", row["link_id"]) for row in links)
            paper_nodes, paper_links, paper_endpoints = _build_paper_understanding_rows(root, project_id, sources, timestamp)
            _insert_many(connection, "understanding_nodes", paper_nodes)
            _insert_many(connection, "understanding_links", paper_links)
            _insert_many(connection, "understanding_link_endpoints", paper_endpoints)
            audit_rows.extend(("understanding_nodes", row["node_id"]) for row in paper_nodes)
            audit_rows.extend(("understanding_links", row["link_id"]) for row in paper_links)
            nodes.extend(paper_nodes)
            links.extend(paper_links)
            node_ids = {row["node_id"] for row in nodes}

            understanding_sources, understanding_nodes = _import_understanding_updates(
                connection,
                root,
                project_id,
                warnings,
                timestamp,
                source_ids,
                node_ids,
            )
            sources.extend(understanding_sources)
            nodes.extend(understanding_nodes)
            audit_rows.extend(("sources", row["source_id"]) for row in understanding_sources)
            audit_rows.extend(("understanding_nodes", row["node_id"]) for row in understanding_nodes)

            claim_node_by_local = _claim_node_by_local_id(nodes)
            experiments, runs, metrics, artifacts, run_nodes, entity_links = _build_experiment_rows(
                root,
                project_id,
                warnings,
                timestamp,
                source_ids,
                claim_node_by_local,
            )
            _insert_many(connection, "experiments", experiments)
            _insert_many(connection, "experiment_runs", runs)
            _insert_many(connection, "experiment_metrics", metrics)
            _insert_many(connection, "experiment_artifacts", artifacts)
            _insert_many(connection, "understanding_nodes", run_nodes)
            _insert_many(connection, "entity_links", entity_links)
            audit_rows.extend(("experiments", row["experiment_id"]) for row in experiments)
            audit_rows.extend(("experiment_runs", row["run_id"]) for row in runs)
            audit_rows.extend(("experiment_metrics", row["metric_id"]) for row in metrics)
            audit_rows.extend(("experiment_artifacts", row["artifact_id"]) for row in artifacts)
            audit_rows.extend(("understanding_nodes", row["node_id"]) for row in run_nodes)
            audit_rows.extend(("entity_links", row["entity_link_id"]) for row in entity_links)

            lanes, items, relations, positionings = _build_literature_rows(
                root,
                project_id,
                warnings,
                timestamp,
                source_matcher,
            )
            _insert_many(connection, "literature_lanes", lanes)
            _insert_many(connection, "literature_items", items)
            _insert_many(connection, "literature_relations", relations)
            _insert_many(connection, "project_positionings", positionings)
            audit_rows.extend(("literature_lanes", row["lane_id"]) for row in lanes)
            audit_rows.extend(("literature_items", row["item_id"]) for row in items)
            audit_rows.extend(("literature_relations", row["relation_id"]) for row in relations)
            audit_rows.extend(("project_positionings", row["positioning_id"]) for row in positionings)

            session_id, update_id = _insert_activity(connection, project_id, timestamp)
            _insert_audits(connection, project_id, update_id, timestamp, audit_rows)
    finally:
        connection.close()

    return {
        "valid": True,
        "project_id": project_id,
        "sources": len(sources),
        "understanding_nodes": len(nodes) + len(run_nodes),
        "understanding_links": len(links),
        "experiments": len(experiments),
        "experiment_runs": len(runs),
        "experiment_metrics": len(metrics),
        "literature_lanes": len(lanes),
        "literature_items": len(items),
        "warnings": warnings,
    }


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _build_project(root: Path, project_id: str, warnings: list[str], timestamp: str) -> dict[str, Any]:
    overview = root / "wiki" / "projects" / project_id / "overview.md"
    query_pack = root / "wiki" / "projects" / project_id / "project-query-pack.md"
    overview_frontmatter: dict[str, Any] = {}
    overview_body = ""
    query_body = ""
    if overview.exists():
        overview_frontmatter, overview_body = read_markdown(overview)
    else:
        warnings.append(f"missing source file: {relpath(overview, root)}")
    if query_pack.exists():
        _, query_body = read_markdown(query_pack)
    else:
        warnings.append(f"missing source file: {relpath(query_pack, root)}")

    title = str(overview_frontmatter.get("title") or project_id).strip().strip("\"'")
    summary = first_sentence(extract_section(overview_body, "Project Direction")) or first_sentence(query_body)
    main_question = _first_bullet(extract_section(overview_body, "Current Questions")) or _first_bullet(
        extract_section(overview_body, "Accepted Questions")
    )
    stage = str(overview_frontmatter.get("stage") or "literature_mapping").strip().strip("\"'")
    return {
        "project_id": project_id,
        "slug": normalize_slug(project_id),
        "title": title,
        "summary": summary,
        "main_question": main_question,
        "working_hypothesis": "",
        "target_contribution": "",
        "stage": stage,
        "status": "active",
        "created_at": timestamp,
        "updated_at": timestamp,
        "created_by": "legacy_import",
        "updated_by": "legacy_import",
        "confirmation": str(overview_frontmatter.get("human_review") or "unconfirmed"),
        "metadata_json": json_dumps({"legacy_import": True}),
    }


def _build_sources(root: Path, project_id: str, warnings: list[str], timestamp: str) -> list[dict[str, Any]]:
    papers_dir = root / "wiki" / "projects" / project_id / "papers"
    if not papers_dir.exists():
        warnings.append(f"missing source directory: {relpath(papers_dir, root)}")
        return []

    rows = []
    for path in sorted(papers_dir.glob("*/index.md")):
        frontmatter, body = read_markdown(path)
        folder_slug = path.parent.name
        source_identity = extract_section(body, "Source Identity")
        source_id = str(frontmatter.get("paper_id") or f"paper:{folder_slug}").strip()
        url = str(frontmatter.get("url") or _identity_value(source_identity, "Source URL")).strip(" `")
        canonical = _identity_value(source_identity, "Canonical source ref")
        title = str(frontmatter.get("title") or _identity_value(source_identity, "Source title") or path.stem).strip().strip("\"'")
        summary = (
            first_sentence(extract_section(body, "Summary"))
            or first_sentence(extract_section(body, "Core Contribution"))
            or first_sentence(extract_section(body, "Abstract"))
        )
        rows.append(
            {
                "source_id": source_id,
                "project_id": project_id,
                "source_type": "paper",
                "title": title,
                "authors": _string_frontmatter(frontmatter, "authors"),
                "year": _string_frontmatter(frontmatter, "year"),
                "locator": relpath(path, root),
                "doi": _string_frontmatter(frontmatter, "doi"),
                "arxiv_id": _string_frontmatter(frontmatter, "arxiv_id"),
                "url": url,
                "zotero_key": _string_frontmatter(frontmatter, "zotero_key"),
                "attachment_locator_type": "",
                "attachment_locator": "",
                "reading_status": "deep_read",
                "reading_depth": "deep_structured",
                "short_summary": summary,
                "created_at": timestamp,
                "updated_at": timestamp,
                "created_by": "legacy_import",
                "updated_by": "legacy_import",
                "confirmation": str(frontmatter.get("human_review") or "unconfirmed"),
                "metadata_json": json_dumps({"legacy_import": True, "canonical_source_ref": canonical}),
            }
        )
    return rows


def _build_graph_rows(
    root: Path,
    project_id: str,
    warnings: list[str],
    timestamp: str,
    source_ids: set[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    graph_path = root / "wiki" / "graphs" / "events" / "projects" / f"{project_id}.jsonl"
    understanding_path = root / "wiki" / "understanding" / "events" / f"{project_id}.jsonl"
    if not understanding_path.exists():
        warnings.append(f"missing source file: {relpath(understanding_path, root)}")
    if not graph_path.exists():
        warnings.append(f"missing source file: {relpath(graph_path, root)}")
        return [], [], []

    snapshot = build_snapshot_from_event_files([graph_path])
    nodes = []
    for node in snapshot.get("nodes") or []:
        node_type = NODE_TYPES.get(str(node.get("node_type") or ""))
        if not node_type:
            continue
        source_refs = list(node.get("source_refs") or [])
        metadata = dict(node.get("metadata") or {})
        metadata["local_id"] = node.get("local_id") or ""
        nodes.append(
            {
                "node_id": node["node_id"],
                "project_id": project_id,
                "scope": node.get("scope") or "project",
                "source_id": _first_known_source(source_refs, source_ids),
                "node_type": node_type,
                "text": node.get("text") or "",
                "status": node.get("status") or "active",
                "confidence": node.get("confidence") or "unknown",
                "confirmation": node.get("human_review") or "unconfirmed",
                "created_at": timestamp,
                "updated_at": timestamp,
                "created_by": "legacy_import",
                "updated_by": "legacy_import",
                "source_refs_json": json_dumps(source_refs),
                "metadata_json": json_dumps(metadata),
            }
        )

    node_ids = {row["node_id"] for row in nodes}
    links = []
    endpoints = []
    for link in snapshot.get("links") or []:
        link_type = LINK_TYPES.get(str(link.get("link_type") or ""))
        if not link_type:
            continue
        source_refs = list(link.get("source_refs") or [])
        metadata = {"local_id": link.get("local_id") or ""}
        links.append(
            {
                "link_id": link["link_id"],
                "project_id": project_id,
                "scope": link.get("scope") or "project",
                "link_type": link_type,
                "relation": link.get("relation") or "",
                "confidence": link.get("confidence") or "unknown",
                "confirmation": link.get("human_review") or "unconfirmed",
                "created_at": timestamp,
                "updated_at": timestamp,
                "created_by": "legacy_import",
                "updated_by": "legacy_import",
                "source_refs_json": json_dumps(source_refs),
                "metadata_json": json_dumps(metadata),
            }
        )
        for field, role in ENDPOINT_FIELDS.items():
            for position, node_id in enumerate(link.get(field) or []):
                if node_id not in node_ids:
                    continue
                endpoints.append(
                    {
                        "endpoint_id": f"endpoint:{link['link_id']}:{role}:{position}:{node_id}",
                        "project_id": project_id,
                        "link_id": link["link_id"],
                        "node_id": node_id,
                        "role": role,
                        "position": position,
                        "metadata_json": json_dumps({}),
                    }
                )
    return nodes, links, endpoints


PAPER_UNDERSTANDING_SECTIONS = (
    ("question", "P-Q1", ("Paper's real question", "real question")),
    ("claim", "P-C1", ("Author's core hypothesis", "Core Contribution", "core hypothesis")),
    ("evidence", "P-E1", ("Evidence Relevant To Demo PUG", "Experiment logic", "Evidence")),
    ("warrant", "P-W1", ("Warrants / Assumptions", "Warrant")),
    ("limitation", "P-L1", ("Limitations / What Not To Infer", "What not to learn", "Limitations")),
)


def _build_paper_understanding_rows(
    root: Path,
    project_id: str,
    sources: list[dict[str, Any]],
    timestamp: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    nodes: list[dict[str, Any]] = []
    links: list[dict[str, Any]] = []
    endpoints: list[dict[str, Any]] = []
    for source in sources:
        source_id = str(source.get("source_id") or "")
        locator = str(source.get("locator") or "")
        if not source_id or not locator or "/papers/" not in locator:
            continue
        path = root / locator
        if not path.exists():
            continue
        _, body = read_markdown(path)
        paper_nodes: dict[str, str] = {}
        for node_type, local_id, headings in PAPER_UNDERSTANDING_SECTIONS:
            text = _paper_section_text(body, headings)
            if not text:
                continue
            node_id = f"paper-node:{source_id}:{local_id}"
            paper_nodes[node_type] = node_id
            nodes.append(
                {
                    "node_id": node_id,
                    "project_id": project_id,
                    "scope": "paper",
                    "source_id": source_id,
                    "node_type": node_type,
                    "text": text,
                    "status": "active",
                    "confidence": str(source.get("confirmation") or "medium"),
                    "confirmation": str(source.get("confirmation") or "unconfirmed"),
                    "created_at": timestamp,
                    "updated_at": timestamp,
                    "created_by": "legacy_import",
                    "updated_by": "legacy_import",
                    "source_refs_json": json_dumps([locator]),
                    "metadata_json": json_dumps(
                        {
                            "local_id": local_id,
                            "source_title": source.get("title") or "",
                            "source_locator": locator,
                            "section_headings": list(headings),
                            "legacy_paper_dossier_import": True,
                        }
                    ),
                }
            )
        claim_id = paper_nodes.get("claim")
        if not claim_id:
            continue
        link_id = f"paper-link:{source_id}:RL1"
        links.append(
            {
                "link_id": link_id,
                "project_id": project_id,
                "scope": "paper",
                "link_type": "reasoning",
                "relation": "supports",
                "confidence": str(source.get("confirmation") or "medium"),
                "confirmation": str(source.get("confirmation") or "unconfirmed"),
                "created_at": timestamp,
                "updated_at": timestamp,
                "created_by": "legacy_import",
                "updated_by": "legacy_import",
                "source_refs_json": json_dumps([locator]),
                "metadata_json": json_dumps({"local_id": "P-RL1", "source_id": source_id, "legacy_paper_dossier_import": True}),
            }
        )
        endpoint_specs = [
            ("from", paper_nodes.get("evidence"), 0),
            ("warrant", paper_nodes.get("warrant"), 0),
            ("limitation", paper_nodes.get("limitation"), 0),
            ("to", claim_id, 0),
        ]
        for role, node_id, position in endpoint_specs:
            if not node_id:
                continue
            endpoints.append(
                {
                    "endpoint_id": f"endpoint:{link_id}:{role}:{position}:{node_id}",
                    "project_id": project_id,
                    "link_id": link_id,
                    "node_id": node_id,
                    "role": role,
                    "position": position,
                    "metadata_json": json_dumps({}),
                }
            )
    return nodes, links, endpoints


def _paper_section_text(body: str, headings: tuple[str, ...]) -> str:
    for heading in headings:
        section = _markdown_heading_section(body, heading)
        text = _compact_markdown_text(section)
        if text:
            return text
    return ""


def _markdown_heading_section(body: str, heading: str) -> str:
    target = _normalized_heading(heading)
    matches = list(re.finditer(r"^(#{2,6})\s+(.+?)\s*$", body, flags=re.MULTILINE))
    for index, match in enumerate(matches):
        current = _normalized_heading(match.group(2))
        if target not in current and current not in target:
            continue
        level = len(match.group(1))
        start = match.end()
        end = len(body)
        for next_match in matches[index + 1 :]:
            if len(next_match.group(1)) <= level:
                end = next_match.start()
                break
        return body[start:end]
    return ""


def _normalized_heading(value: str) -> str:
    text = re.sub(r"^\s*\d+[\).\s-]+", "", str(value or "").lower().strip())
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _compact_markdown_text(value: str, *, limit: int = 620) -> str:
    lines = []
    for line in str(value or "").splitlines():
        stripped = re.sub(r"^\s*[-*]\s+", "", line).strip()
        if not stripped or stripped.startswith("#"):
            continue
        lines.append(stripped)
    text = " ".join(lines)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        return text[: limit - 3].rstrip() + "..."
    return text


def _import_understanding_updates(
    connection: Any,
    root: Path,
    project_id: str,
    warnings: list[str],
    timestamp: str,
    source_ids: set[str],
    node_ids: set[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    path = root / "wiki" / "understanding" / "events" / f"{project_id}.jsonl"
    if not path.exists():
        warnings.append(f"missing source file: {relpath(path, root)}")
        return [], []

    updates = read_understanding_updates(root, project_id)
    inserted_sources: list[dict[str, Any]] = []
    inserted_nodes: list[dict[str, Any]] = []
    used_update_ids: set[str] = {
        str(row["update_id"])
        for row in connection.execute("SELECT update_id FROM updates")
    }
    for update in updates:
        original_update_id = str(update.get("update_id") or uuid.uuid4().hex)
        update_row_id = _safe_update_id(original_update_id, used_update_ids)
        used_update_ids.add(update_row_id)
        task = update.get("task") if isinstance(update.get("task"), dict) else {}
        created_at = str(update.get("created_at") or timestamp)
        session_id = f"session:{project_id}:understanding:{_safe_id_fragment(original_update_id)}"
        summary = str(task.get("summary") or update.get("recent_change_summary") or "Imported legacy understanding update.")
        recent_summary = str(update.get("recent_change_summary") or summary)
        connection.execute(
            """
            INSERT INTO activity_sessions(session_id, project_id, actor, activity_type, started_at, ended_at, summary, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                project_id,
                str(update.get("actor") or "agent"),
                str(task.get("kind") or "legacy_understanding_update"),
                created_at,
                created_at,
                summary,
                json_dumps({"legacy_understanding_update": original_update_id}),
            ),
        )
        connection.execute(
            """
            INSERT INTO updates(update_id, project_id, session_id, summary, confidence, created_at, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                update_row_id,
                project_id,
                session_id,
                recent_summary,
                str(update.get("confidence") or "unknown"),
                created_at,
                json_dumps(update),
            ),
        )
        connection.execute(
            """
            INSERT INTO audit_events(
                audit_event_id, project_id, update_id, entity_type, entity_id, operation,
                before_json, after_json, reason, created_at
            )
            VALUES (?, ?, ?, 'understanding_update', ?, 'import', '{}', ?, ?, ?)
            """,
            (
                f"audit:{project_id}:understanding:{_safe_id_fragment(original_update_id)}:{uuid.uuid4().hex[:8]}",
                project_id,
                update_row_id,
                original_update_id,
                json_dumps(update),
                "Imported legacy understanding update.",
                created_at,
            ),
        )

        for source in _dict_items(update.get("new_sources")):
            source_id = str(source.get("source_id") or "")
            if not source_id or source_id in source_ids:
                continue
            row = {
                "source_id": source_id,
                "project_id": project_id,
                "source_type": str(source.get("type") or "manual"),
                "title": str(source.get("title") or source_id),
                "authors": "",
                "year": "",
                "locator": str(source.get("locator") or ""),
                "doi": "",
                "arxiv_id": "",
                "url": "",
                "zotero_key": "",
                "attachment_locator_type": "",
                "attachment_locator": "",
                "reading_status": str(source.get("status") or "seen"),
                "reading_depth": "lightweight_update",
                "short_summary": str(source.get("relevance") or ""),
                "created_at": created_at,
                "updated_at": created_at,
                "created_by": "legacy_import",
                "updated_by": "legacy_import",
                "confirmation": str(update.get("confidence") or "unconfirmed"),
                "metadata_json": json_dumps({"legacy_understanding_update": original_update_id, "raw": source}),
            }
            _insert_many(connection, "sources", [row])
            source_ids.add(source_id)
            inserted_sources.append(row)

        for evidence in _dict_items(update.get("new_evidence")):
            node_id = str(evidence.get("evidence_id") or "")
            if not node_id or node_id in node_ids:
                continue
            source_refs = [str(item) for item in evidence.get("source_refs") or [] if str(item)]
            row = _understanding_update_node_row(
                project_id=project_id,
                node_id=node_id,
                node_type="evidence",
                text=str(evidence.get("text") or ""),
                confidence=str(update.get("confidence") or "unknown"),
                created_at=created_at,
                source_id=_first_known_source(source_refs, source_ids),
                source_refs=source_refs,
                metadata={
                    "legacy_understanding_update": original_update_id,
                    "related_claims": evidence.get("related_claims") or [],
                },
            )
            _insert_many(connection, "understanding_nodes", [row])
            node_ids.add(node_id)
            inserted_nodes.append(row)

        for claim in _dict_items(update.get("changed_claims")):
            node_id = str(claim.get("claim_id") or "")
            if not node_id or node_id in node_ids:
                continue
            claim_sources = list(claim.get("supporting_sources") or []) + list(claim.get("challenging_sources") or [])
            source_refs = [str(item) for item in claim_sources if str(item)]
            row = _understanding_update_node_row(
                project_id=project_id,
                node_id=node_id,
                node_type="claim",
                text=str(claim.get("text") or ""),
                confidence=str(claim.get("status") or update.get("confidence") or "unknown"),
                created_at=created_at,
                source_id=_first_known_source(source_refs, source_ids),
                source_refs=source_refs,
                metadata={
                    "legacy_understanding_update": original_update_id,
                    "weakness": claim.get("weakness") or "",
                    "change": claim.get("change") or "",
                    "supporting_sources": claim.get("supporting_sources") or [],
                    "challenging_sources": claim.get("challenging_sources") or [],
                },
            )
            _insert_many(connection, "understanding_nodes", [row])
            node_ids.add(node_id)
            inserted_nodes.append(row)

    return inserted_sources, inserted_nodes


def _safe_update_id(original_update_id: str, used_update_ids: set[str]) -> str:
    if original_update_id not in used_update_ids:
        return original_update_id
    candidate = f"understanding:{original_update_id}"
    if candidate not in used_update_ids:
        return candidate
    suffix = 2
    while f"{candidate}:{suffix}" in used_update_ids:
        suffix += 1
    return f"{candidate}:{suffix}"


def _safe_id_fragment(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.:-]+", "-", value).strip("-") or uuid.uuid4().hex


def _dict_items(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _understanding_update_node_row(
    *,
    project_id: str,
    node_id: str,
    node_type: str,
    text: str,
    confidence: str,
    created_at: str,
    source_id: str | None,
    source_refs: list[str],
    metadata: dict[str, Any],
) -> dict[str, Any]:
    return {
        "node_id": node_id,
        "project_id": project_id,
        "scope": "update",
        "source_id": source_id,
        "node_type": node_type,
        "text": text,
        "status": "active",
        "confidence": confidence,
        "confirmation": "unconfirmed",
        "created_at": created_at,
        "updated_at": created_at,
        "created_by": "legacy_import",
        "updated_by": "legacy_import",
        "source_refs_json": json_dumps(source_refs),
        "metadata_json": json_dumps(metadata),
    }


def _build_experiment_rows(
    root: Path,
    project_id: str,
    warnings: list[str],
    timestamp: str,
    source_ids: set[str],
    claim_node_by_local: dict[str, str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    path = root / "wiki" / "projects" / project_id / "experiments" / "experiments.json"
    if not path.exists():
        warnings.append(f"missing source file: {relpath(path, root)}")
        return [], [], [], [], [], []

    model = build_project_experiments(root, project_id)
    experiments = []
    for experiment in model.get("experiments") or []:
        experiment_id = str(experiment.get("id") or "").strip()
        metadata = {key: value for key, value in experiment.items() if key not in _experiment_columns_json_source()}
        experiments.append(
            {
                "experiment_id": experiment_id,
                "project_id": project_id,
                "title": str(experiment.get("title") or experiment_id),
                "question": str(experiment.get("question") or ""),
                "hypothesis": str(experiment.get("hypothesis") or ""),
                "experiment_type": str(experiment.get("experiment_type") or "benchmark_eval"),
                "status": str(experiment.get("status") or "planned"),
                "protocol_summary": "\n".join(str(item) for item in experiment.get("protocol") or []),
                "benchmark_name": str(experiment.get("benchmark") or ""),
                "dataset_name": str(experiment.get("dataset") or ""),
                "planned_at": str(experiment.get("planned_at") or ""),
                "created_at": timestamp,
                "updated_at": timestamp,
                "created_by": "legacy_import",
                "updated_by": "legacy_import",
                "confirmation": "unconfirmed",
                "metadata_json": json_dumps(metadata),
            }
        )

    runs = []
    metrics = []
    artifacts = []
    run_nodes = []
    entity_links = []
    fallback_source = DEFAULT_RUN_SOURCE if DEFAULT_RUN_SOURCE in source_ids else None
    for run in model.get("runs") or []:
        run_id = str(run.get("id") or "").strip()
        experiment_id = str(run.get("experiment_id") or "").strip()
        origin_type = ORIGIN_TYPES.get(str(run.get("evidence_type") or ""), "local")
        source_id = _resolve_run_source(run, source_ids) or fallback_source
        metadata = {key: value for key, value in run.items() if key not in _run_columns_json_source()}
        runs.append(
            {
                "run_id": run_id,
                "project_id": project_id,
                "experiment_id": experiment_id,
                "origin_type": origin_type,
                "status": str(run.get("status") or "not_started"),
                "method_name": str(run.get("method_name") or ""),
                "run_label": str(run.get("run_label") or run_id),
                "source_id": source_id,
                "completed_at": str(run.get("completed_at") or ""),
                "summary": str(run.get("summary") or run.get("interpretation") or ""),
                "created_at": timestamp,
                "updated_at": timestamp,
                "created_by": "legacy_import",
                "updated_by": "legacy_import",
                "confirmation": "unconfirmed",
                "metadata_json": json_dumps(metadata),
            }
        )
        for index, metric in enumerate(run.get("metrics") or []):
            value = str(metric.get("value") or "")
            metrics.append(
                {
                    "metric_id": f"metric:{run_id}:{index}:{normalize_slug(str(metric.get('name') or 'metric'))}",
                    "project_id": project_id,
                    "run_id": run_id,
                    "name": str(metric.get("name") or ""),
                    "value_text": value,
                    "value_numeric": _numeric(value),
                    "unit": str(metric.get("unit") or ""),
                    "direction": str(metric.get("direction") or "neutral"),
                    "benchmark_name": str(metric.get("benchmark") or ""),
                    "dataset_name": str(metric.get("dataset") or ""),
                    "split_name": str(metric.get("split") or ""),
                    "created_at": timestamp,
                    "metadata_json": json_dumps({key: value for key, value in metric.items() if key not in {"name", "value", "unit", "direction"}}),
                }
            )
        for index, artifact in enumerate(run.get("artifacts") or []):
            artifacts.append(
                {
                    "artifact_id": f"artifact:{run_id}:{index}:{normalize_slug(str(artifact.get('label') or artifact.get('type') or 'artifact'))}",
                    "project_id": project_id,
                    "run_id": run_id,
                    "artifact_type": str(artifact.get("type") or ""),
                    "locator_type": "url" if str(artifact.get("path_or_url") or "").startswith("http") else "local_path",
                    "locator": str(artifact.get("path_or_url") or ""),
                    "label": str(artifact.get("label") or ""),
                    "description": str(artifact.get("description") or ""),
                    "created_at": timestamp,
                    "metadata_json": json_dumps({}),
                }
            )
        evidence_node_id = f"run:{run_id}:evidence"
        run_nodes.append(
            {
                "node_id": evidence_node_id,
                "project_id": project_id,
                "scope": "experiment",
                "source_id": source_id,
                "node_type": "evidence",
                "text": str(run.get("summary") or run.get("interpretation") or run_id),
                "status": "active",
                "confidence": "medium",
                "confirmation": "unconfirmed",
                "created_at": timestamp,
                "updated_at": timestamp,
                "created_by": "legacy_import",
                "updated_by": "legacy_import",
                "source_refs_json": json_dumps([source_id] if source_id else []),
                "metadata_json": json_dumps({"experiment_id": experiment_id, "run_id": run_id, "origin_type": origin_type}),
            }
        )
        entity_links.append(_entity_link(project_id, "experiment_run", run_id, "understanding_node", evidence_node_id, "produces", timestamp))
        for impact in run.get("claim_impacts") or []:
            claim_node_id = claim_node_by_local.get(str(impact.get("claim") or ""))
            if claim_node_id:
                relation = f"claim_impact:{impact.get('impact') or 'mentions'}"
                entity_links.append(_entity_link(project_id, "experiment_run", run_id, "understanding_node", claim_node_id, relation, timestamp, impact))
    return experiments, runs, metrics, artifacts, run_nodes, entity_links


def _build_literature_rows(
    root: Path,
    project_id: str,
    warnings: list[str],
    timestamp: str,
    source_matcher: dict[str, str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    rounds_dir = root / "wiki" / "projects" / project_id / "literature-rounds"
    paths = sorted(rounds_dir.glob("*/related-work-lineage.json")) if rounds_dir.exists() else []
    if not paths:
        warnings.append(f"missing source file: {relpath(rounds_dir / '*' / 'related-work-lineage.json', root)}")
        return [], [], [], []

    lanes = []
    items = []
    relations = []
    positionings = []
    item_by_paper: dict[str, str] = {}
    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        round_id = str(data.get("round") or path.parent.name)
        for route in data.get("routes") or []:
            lane_id = f"lineage:{round_id}:{route.get('id')}"
            lanes.append(
                {
                    "lane_id": lane_id,
                    "project_id": project_id,
                    "title": str(route.get("label") or route.get("id") or ""),
                    "description": str(route.get("description") or ""),
                    "status": str(route.get("review_status") or data.get("status") or "active"),
                    "created_at": timestamp,
                    "updated_at": timestamp,
                    "metadata_json": json_dumps(route),
                }
            )
        lane_ids = {str(route.get("id")): f"lineage:{round_id}:{route.get('id')}" for route in data.get("routes") or []}
        for paper in data.get("papers") or []:
            paper_id = str(paper.get("id") or "")
            item_id = f"lineage:{round_id}:{paper_id}"
            item_by_paper[paper_id] = item_id
            source_id = _match_source(paper, source_matcher)
            items.append(
                {
                    "item_id": item_id,
                    "project_id": project_id,
                    "source_id": source_id,
                    "lane_id": lane_ids.get(str(paper.get("route") or "")),
                    "role": _first_list_value(paper.get("roles")) or str(paper.get("artifact_type") or "background"),
                    "importance": "medium",
                    "summary": str(paper.get("summary") or paper.get("source_evidence") or ""),
                    "created_at": timestamp,
                    "updated_at": timestamp,
                    "metadata_json": json_dumps(paper),
                }
            )
        for index, edge in enumerate(data.get("explicit_edges") or []):
            from_item = item_by_paper.get(str(edge.get("source") or ""))
            to_item = item_by_paper.get(str(edge.get("target") or ""))
            if not from_item or not to_item:
                continue
            relations.append(
                {
                    "relation_id": f"lineage:{round_id}:edge:{index}",
                    "project_id": project_id,
                    "from_item_id": from_item,
                    "to_item_id": to_item,
                    "relation_type": str(edge.get("relation") or ""),
                    "rationale": str(edge.get("rationale") or ""),
                    "created_at": timestamp,
                    "updated_at": timestamp,
                    "metadata_json": json_dumps(edge),
                }
            )
        scope = data.get("baseline_paper_field_scope") or {}
        pieces = [
            str(data.get("title") or ""),
            str(data.get("topic_name") or ""),
            str(scope.get("primary_problem") or ""),
            str(scope.get("survey_boundary") or ""),
            str(data.get("positioning_note") or data.get("approval_note") or ""),
        ]
        text = "\n\n".join(piece for piece in pieces if piece)
        positionings.append(
            {
                "positioning_id": f"lineage:{round_id}:positioning",
                "project_id": project_id,
                "text": text,
                "confidence": "medium",
                "created_at": timestamp,
                "updated_at": timestamp,
                "metadata_json": json_dumps({"path": relpath(path, root)}),
            }
        )
    return lanes, items, relations, positionings


def _insert_project(connection: Any, row: dict[str, Any]) -> None:
    _insert_many(connection, "projects", [row])


def _insert_many(connection: Any, table: str, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    columns = list(rows[0])
    placeholders = ", ".join("?" for _ in columns)
    connection.executemany(
        f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})",
        [tuple(row[column] for column in columns) for row in rows],
    )


def _insert_activity(connection: Any, project_id: str, timestamp: str) -> tuple[str, str]:
    suffix = uuid.uuid4().hex[:8]
    session_id = f"session:{project_id}:legacy_import:{suffix}"
    update_id = f"update:{project_id}:legacy_import:{suffix}"
    summary = "Imported legacy project files into research-pilot.db."
    connection.execute(
        """
        INSERT INTO activity_sessions(session_id, project_id, actor, activity_type, started_at, ended_at, summary, metadata_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (session_id, project_id, "legacy_import", "legacy_import", timestamp, timestamp, summary, json_dumps({})),
    )
    connection.execute(
        """
        INSERT INTO updates(update_id, project_id, session_id, summary, confidence, created_at, metadata_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (update_id, project_id, session_id, summary, "high", timestamp, json_dumps({})),
    )
    return session_id, update_id


def _insert_audits(connection: Any, project_id: str, update_id: str, timestamp: str, rows: list[tuple[str, str]]) -> None:
    connection.executemany(
        """
        INSERT INTO audit_events(
            audit_event_id, project_id, update_id, entity_type, entity_id, operation,
            before_json, after_json, reason, created_at
        )
        VALUES (?, ?, ?, ?, ?, 'create', '{}', '{}', ?, ?)
        """,
        [
            (
                f"audit:{project_id}:legacy_import:{index}:{uuid.uuid4().hex[:8]}",
                project_id,
                update_id,
                entity_type,
                entity_id,
                "Imported legacy project files into research-pilot.db.",
                timestamp,
            )
            for index, (entity_type, entity_id) in enumerate(rows)
        ],
    )


def _first_bullet(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            return stripped[2:].strip()
    return ""


def _identity_value(text: str, label: str) -> str:
    pattern = re.compile(rf"^[-*]\s+{re.escape(label)}:\s*(.+)$", re.IGNORECASE)
    for line in text.splitlines():
        match = pattern.match(line.strip())
        if match:
            return match.group(1).strip().strip("`").strip("\"'")
    return ""


def _string_frontmatter(frontmatter: dict[str, Any], key: str) -> str:
    value = frontmatter.get(key)
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value).strip().strip("\"'")


def _first_known_source(source_refs: list[str], source_ids: set[str]) -> str | None:
    for source_ref in source_refs:
        if source_ref in source_ids:
            return source_ref
    return None


def _claim_node_by_local_id(nodes: list[dict[str, Any]]) -> dict[str, str]:
    result = {}
    for node in nodes:
        if node["node_type"] != "claim":
            continue
        metadata = json.loads(node["metadata_json"])
        local_id = str(metadata.get("local_id") or "")
        if local_id:
            result[local_id] = node["node_id"]
    return result


def _entity_link(
    project_id: str,
    from_type: str,
    from_id: str,
    to_type: str,
    to_id: str,
    relation: str,
    timestamp: str,
    metadata: Any | None = None,
) -> dict[str, Any]:
    return {
        "entity_link_id": f"entity_link:{from_type}:{from_id}:{relation}:{to_type}:{to_id}",
        "project_id": project_id,
        "from_entity_type": from_type,
        "from_entity_id": from_id,
        "to_entity_type": to_type,
        "to_entity_id": to_id,
        "relation_type": relation,
        "created_at": timestamp,
        "metadata_json": json_dumps(metadata or {}),
    }


def _experiment_columns_json_source() -> set[str]:
    return {"id", "title", "question", "hypothesis", "experiment_type", "status", "protocol", "benchmark", "dataset", "planned_at"}


def _run_columns_json_source() -> set[str]:
    return {"id", "experiment_id", "status", "evidence_type", "method_name", "run_label", "completed_at", "summary"}


def _numeric(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _resolve_run_source(run: dict[str, Any], source_ids: set[str]) -> str | None:
    for key in ("source_id", "source"):
        value = str(run.get(key) or "")
        if value in source_ids:
            return value
    for artifact in run.get("artifacts") or []:
        locator = str(artifact.get("path_or_url") or "")
        for source_id in source_ids:
            if source_id.replace("paper:", "") in locator:
                return source_id
    return None


def _source_matcher(sources: list[dict[str, Any]]) -> dict[str, str]:
    matcher = {}
    for source in sources:
        source_id = source["source_id"]
        matcher[normalize_slug(source_id.replace("paper:", ""))] = source_id
        matcher[normalize_slug(source["title"])] = source_id
        metadata = json.loads(source["metadata_json"])
        canonical = str(metadata.get("canonical_source_ref") or "")
        if canonical:
            matcher[normalize_slug(canonical)] = source_id
    return matcher


def _match_source(paper: dict[str, Any], source_matcher: dict[str, str]) -> str | None:
    for value in (paper.get("id"), paper.get("title")):
        source_id = source_matcher.get(normalize_slug(str(value or "")))
        if source_id:
            return source_id
    return None


def _first_list_value(value: Any) -> str:
    if isinstance(value, list) and value:
        return str(value[0])
    return ""
