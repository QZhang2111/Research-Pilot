#!/usr/bin/env python3
"""Read models backed by research-pilot.db."""

from __future__ import annotations

import sqlite3
from collections import Counter, defaultdict
from contextlib import closing
from pathlib import Path
from typing import Any

from tools.experiment_store import _legacy_proposals
from tools.research_dataset import connect_dataset, dataset_db_path, json_loads


DB_SOURCE = "research-pilot.db"


def project_exists_in_dataset(root: Path, project_id: str) -> bool:
    if not dataset_db_path(root).exists():
        return False
    try:
        with closing(connect_dataset(root)) as connection:
            row = connection.execute("SELECT 1 FROM projects WHERE project_id = ?", (project_id,)).fetchone()
    except sqlite3.Error:
        return False
    return row is not None


def build_project_summary_model(root: Path, project_id: str) -> dict[str, Any]:
    with closing(_project_connection(root, project_id)) as connection:
        project = connection.execute("SELECT * FROM projects WHERE project_id = ?", (project_id,)).fetchone()
        source_count = _count(connection, "sources", project_id)
        experiment_count = _count(connection, "experiments", project_id)
        node_counts = _node_counts(connection, project_id)
    return {
        "project_id": project["project_id"],
        "title": project["title"],
        "summary": project["summary"],
        "main_question": project["main_question"],
        "stage": project["stage"],
        "status": project["status"],
        "source_count": source_count,
        "claim_count": node_counts.get("claim", 0),
        "evidence_count": node_counts.get("evidence", 0),
        "experiment_count": experiment_count,
        "source": DB_SOURCE,
    }


def build_sources_model(root: Path, project_id: str) -> dict[str, Any]:
    with closing(_project_connection(root, project_id)) as connection:
        sources = [_source_item(row) for row in _source_rows(connection, project_id)]
        counts = _paper_understanding_counts(connection, project_id)
    for source in sources:
        source["paper_understanding_count"] = counts.get(source["source_id"], 0)
    return {"project_id": project_id, "source": DB_SOURCE, "sources": sources}


def build_source_detail_model(root: Path, project_id: str, source_id: str) -> dict[str, Any]:
    with closing(_project_connection(root, project_id)) as connection:
        row = connection.execute(
            """
            SELECT *
            FROM sources
            WHERE project_id = ? AND source_id = ?
            """,
            (project_id, source_id),
        ).fetchone()
        if row is None:
            raise ValueError("source not found")
        source = _source_item(row)
        nodes = [
            _node_item(node)
            for node in connection.execute(
                """
                SELECT *
                FROM understanding_nodes
                WHERE project_id = ? AND source_id = ? AND scope = 'paper'
                ORDER BY node_id
                """,
                (project_id, source_id),
            )
        ]
    source["paper_understanding_count"] = len(nodes)
    source["paper_understanding_nodes"] = nodes
    source["source"] = DB_SOURCE
    return source


def build_project_graph_model(root: Path, project_id: str) -> dict[str, Any]:
    with closing(_project_connection(root, project_id)) as connection:
        nodes = [
            _node_item(row)
            for row in connection.execute(
                """
                SELECT *
                FROM understanding_nodes
                WHERE project_id = ? AND scope = 'project'
                ORDER BY node_id
                """,
                (project_id,),
            )
        ]
        links = [_link_item(connection, row) for row in _link_rows(connection, project_id)]
        link_counts = _link_counts(connection, project_id)
    counts = Counter(node["kind"] for node in nodes)
    counts.update(link_counts)
    return {
        "project": project_id,
        "source": DB_SOURCE,
        "nodes": nodes,
        "links": links,
        "counts": {kind: counts.get(kind, 0) for kind in ("question", "claim", "evidence", "warrant", "limitation", "reasoning", "translation")},
    }


def build_experiments_model(root: Path, project_id: str) -> dict[str, Any]:
    with closing(_project_connection(root, project_id)) as connection:
        experiments = [_experiment_item(row) for row in _experiment_rows(connection, project_id)]
        runs = [_run_item(row) for row in _run_rows(connection, project_id)]
        metrics_by_run = _metrics_by_run(connection, project_id)
        artifacts_by_run = _artifacts_by_run(connection, project_id)
    for run in runs:
        run["metrics"] = metrics_by_run.get(run["id"], [])
        run["artifacts"] = artifacts_by_run.get(run["id"], [])
    return {
        "schema_version": "experiments-v1",
        "project_id": project_id,
        "source_boundary": "project_experiments_from_research_dataset",
        "mutating": False,
        "summary": _experiment_summary(experiments, runs),
        "experiments": experiments,
        "runs": runs,
        "next_moves": [],
        "legacy_proposals": _legacy_proposals(Path(root), project_id),
    }


def build_literature_model(root: Path, project_id: str) -> dict[str, Any]:
    with closing(_project_connection(root, project_id)) as connection:
        routes = [_lane_item(row) for row in _lane_rows(connection, project_id)]
        papers = [_literature_item(row) for row in _literature_rows(connection, project_id)]
        explicit_edges = [_relation_item(row) for row in _relation_rows(connection, project_id)]
        positioning = [_positioning_item(row) for row in _positioning_rows(connection, project_id)]
    return {
        "project": project_id,
        "source": DB_SOURCE,
        "routes": routes,
        "papers": papers,
        "explicit_edges": explicit_edges,
        "positioning": positioning,
    }


def build_paper_graph_model(root: Path, target: Path) -> dict[str, Any]:
    root = Path(root)
    target = Path(target)
    locator = _relative_locator(root, target)
    project_id, paper_slug = _paper_project_and_slug(locator)
    with closing(_project_connection(root, project_id)) as connection:
        source = connection.execute(
            """
            SELECT *
            FROM sources
            WHERE project_id = ? AND locator = ?
            """,
            (project_id, locator),
        ).fetchone()
        if source is None:
            raise ValueError("source not found")
        rows = list(
            connection.execute(
                """
                SELECT *
                FROM understanding_nodes
                WHERE project_id = ? AND scope = 'paper' AND source_id = ?
                ORDER BY node_id
                """,
                (project_id, source["source_id"]),
            )
        )
        if not rows:
            raise ValueError("paper understanding not found")
        nodes = [_paper_node_item(row) for row in rows]
        paper_id_by_node_id = {row["node_id"]: node["id"] for row, node in zip(rows, nodes)}
        links = [_paper_link_item(connection, row, paper_id_by_node_id) for row in _paper_link_rows(connection, project_id, set(paper_id_by_node_id))]
        links = [link for link in links if link["target"] and (link["premises"] or link["warrant"] or link["limitations"])]
        translations = _paper_translations(connection, project_id, locator, source["source_id"], paper_id_by_node_id)
    return {
        "schema_version": "paper-graph-v1",
        "project": project_id,
        "paper": paper_slug,
        "title": source["title"] or paper_slug,
        "path": locator,
        "source": DB_SOURCE,
        "source_boundary": "paper_understanding_from_research_dataset",
        "nodes": nodes,
        "paper_links": links,
        "translations": translations,
        "deltas": [],
    }


def build_recent_updates_model(root: Path, project_id: str, limit: int = 10) -> dict[str, Any]:
    with closing(_project_connection(root, project_id)) as connection:
        updates = [
            {
                "id": row["update_id"],
                "activity_type": row["activity_type"],
                "summary": row["summary"],
                "confidence": row["confidence"],
                "created_at": row["created_at"],
                "audit_event_count": row["audit_event_count"],
            }
            for row in connection.execute(
                """
                SELECT
                    updates.update_id,
                    activity_sessions.activity_type,
                    updates.summary,
                    updates.confidence,
                    updates.created_at,
                    COUNT(audit_events.audit_event_id) AS audit_event_count
                FROM updates
                LEFT JOIN activity_sessions ON activity_sessions.session_id = updates.session_id
                LEFT JOIN audit_events ON audit_events.update_id = updates.update_id
                WHERE updates.project_id = ?
                GROUP BY updates.update_id
                ORDER BY updates.created_at DESC, updates.update_id DESC
                LIMIT ?
                """,
                (project_id, max(0, int(limit))),
            )
        ]
    return {"project_id": project_id, "source": DB_SOURCE, "updates": updates}


def _project_connection(root: Path, project_id: str) -> sqlite3.Connection:
    if not project_exists_in_dataset(root, project_id):
        raise ValueError("project not found")
    return connect_dataset(root)


def _count(connection: sqlite3.Connection, table: str, project_id: str) -> int:
    return int(connection.execute(f"SELECT COUNT(*) FROM {table} WHERE project_id = ?", (project_id,)).fetchone()[0])


def _node_counts(connection: sqlite3.Connection, project_id: str) -> dict[str, int]:
    return {
        row["node_type"]: row["count"]
        for row in connection.execute(
            """
            SELECT node_type, COUNT(*) AS count
            FROM understanding_nodes
            WHERE project_id = ? AND scope = 'project'
            GROUP BY node_type
            """,
            (project_id,),
        )
    }


def _source_rows(connection: sqlite3.Connection, project_id: str) -> list[sqlite3.Row]:
    return list(connection.execute("SELECT * FROM sources WHERE project_id = ? ORDER BY title, source_id", (project_id,)))


def _source_item(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "source_id": row["source_id"],
        "title": row["title"],
        "source_type": row["source_type"],
        "authors": row["authors"],
        "year": row["year"],
        "locator": row["locator"],
        "url": row["url"],
        "doi": row["doi"],
        "arxiv_id": row["arxiv_id"],
        "reading_status": row["reading_status"],
        "reading_depth": row["reading_depth"],
        "short_summary": row["short_summary"],
    }


def _paper_understanding_counts(connection: sqlite3.Connection, project_id: str) -> dict[str, int]:
    return {
        row["source_id"]: row["count"]
        for row in connection.execute(
            """
            SELECT source_id, COUNT(*) AS count
            FROM understanding_nodes
            WHERE project_id = ? AND scope = 'paper' AND source_id IS NOT NULL
            GROUP BY source_id
            """,
            (project_id,),
        )
    }


def _node_item(row: sqlite3.Row) -> dict[str, Any]:
    metadata = json_loads(row["metadata_json"], {})
    return {
        "id": row["node_id"],
        "kind": row["node_type"],
        "label": row["text"],
        "subtitle": metadata.get("local_id") or row["source_id"] or "",
        "status": row["status"],
        "confidence": row["confidence"],
        "source_refs": json_loads(row["source_refs_json"], []),
        "metadata": metadata,
    }


def _link_rows(connection: sqlite3.Connection, project_id: str) -> list[sqlite3.Row]:
    return list(
        connection.execute(
            """
            SELECT *
            FROM understanding_links
            WHERE project_id = ? AND scope = 'project'
            ORDER BY link_id
            """,
            (project_id,),
        )
    )


def _link_counts(connection: sqlite3.Connection, project_id: str) -> dict[str, int]:
    return {
        row["link_type"]: row["count"]
        for row in connection.execute(
            """
            SELECT link_type, COUNT(*) AS count
            FROM understanding_links
            WHERE project_id = ? AND scope = 'project'
            GROUP BY link_type
            """,
            (project_id,),
        )
    }


def _link_item(connection: sqlite3.Connection, row: sqlite3.Row) -> dict[str, Any]:
    endpoints = [
        {"role": endpoint["role"], "node_id": endpoint["node_id"], "position": endpoint["position"]}
        for endpoint in connection.execute(
            """
            SELECT role, node_id, position
            FROM understanding_link_endpoints
            WHERE project_id = ? AND link_id = ?
            ORDER BY position, role, node_id
            """,
            (row["project_id"], row["link_id"]),
        )
    ]
    by_role: dict[str, list[str]] = defaultdict(list)
    for endpoint in endpoints:
        by_role[endpoint["role"]].append(endpoint["node_id"])
    warrant = [
        endpoint["node_id"]
        for endpoint in endpoints
        if endpoint["role"] in {"warrant", "project_warrant"}
    ]
    limitations = [
        endpoint["node_id"]
        for endpoint in endpoints
        if endpoint["role"] in {"limitation", "project_limitation"}
    ]
    local_id = json_loads(row["metadata_json"], {}).get("local_id") or row["link_id"]
    link_type = _legacy_link_type(row["link_type"])
    return {
        "id": row["link_id"],
        "link_id": row["link_id"],
        "local_id": local_id,
        "link_type": link_type,
        "type": link_type,
        "relation": row["relation"],
        "source": by_role.get("from", []),
        "premises": by_role.get("from", []),
        "target": by_role.get("to", []),
        "warrant": warrant,
        "limitations": limitations,
        "endpoints": endpoints,
        "confidence": row["confidence"],
        "source_refs": json_loads(row["source_refs_json"], []),
    }


def _legacy_link_type(value: str) -> str:
    if value == "reasoning":
        return "ReasoningLink"
    if value == "translation":
        return "TranslationLink"
    return value


def _relative_locator(root: Path, target: Path) -> str:
    try:
        return target.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return target.as_posix()


def _paper_project_and_slug(locator: str) -> tuple[str, str]:
    parts = Path(locator).parts
    try:
        project_index = parts.index("projects")
        papers_index = parts.index("papers")
    except ValueError as error:
        raise ValueError("paper path not under project papers") from error
    if project_index + 1 >= len(parts) or papers_index + 1 >= len(parts):
        raise ValueError("paper path not under project papers")
    return parts[project_index + 1], parts[papers_index + 1]


def _paper_node_item(row: sqlite3.Row) -> dict[str, Any]:
    metadata = json_loads(row["metadata_json"], {})
    local_id = metadata.get("local_id") or row["node_id"]
    return {
        "id": local_id,
        "kind": row["node_type"],
        "label": row["text"],
        "subtitle": _paper_node_subtitle(row["node_type"]),
        "project_node": "",
        "source_refs": json_loads(row["source_refs_json"], []),
        "metadata": metadata,
    }


def _paper_node_subtitle(node_type: str) -> str:
    return {
        "question": "paper question",
        "claim": "paper claim",
        "evidence": "paper evidence",
        "warrant": "paper warrant",
        "limitation": "paper limitation",
    }.get(node_type, "paper node")


def _paper_link_rows(connection: sqlite3.Connection, project_id: str, node_ids: set[str]) -> list[sqlite3.Row]:
    if not node_ids:
        return []
    placeholders = ", ".join("?" for _ in node_ids)
    return list(
        connection.execute(
            f"""
            SELECT DISTINCT understanding_links.*
            FROM understanding_links
            JOIN understanding_link_endpoints
              ON understanding_link_endpoints.project_id = understanding_links.project_id
             AND understanding_link_endpoints.link_id = understanding_links.link_id
            WHERE understanding_links.project_id = ?
              AND understanding_links.scope = 'paper'
              AND understanding_link_endpoints.node_id IN ({placeholders})
            ORDER BY understanding_links.link_id
            """,
            (project_id, *sorted(node_ids)),
        )
    )


def _paper_link_item(
    connection: sqlite3.Connection,
    row: sqlite3.Row,
    paper_id_by_node_id: dict[str, str],
) -> dict[str, Any]:
    endpoints = [
        endpoint
        for endpoint in connection.execute(
            """
            SELECT role, node_id, position
            FROM understanding_link_endpoints
            WHERE project_id = ? AND link_id = ?
            ORDER BY position, role, node_id
            """,
            (row["project_id"], row["link_id"]),
        )
        if endpoint["node_id"] in paper_id_by_node_id
    ]
    by_role: dict[str, list[str]] = defaultdict(list)
    for endpoint in endpoints:
        by_role[endpoint["role"]].append(paper_id_by_node_id[endpoint["node_id"]])
    metadata = json_loads(row["metadata_json"], {})
    return {
        "id": metadata.get("local_id") or row["link_id"],
        "relation": row["relation"],
        "premises": by_role.get("from", []),
        "target": (by_role.get("to", []) or [""])[0],
        "warrant": (by_role.get("warrant", []) or [""])[0],
        "limitations": by_role.get("limitation", []),
        "project_link": "",
    }


def _paper_translations(
    connection: sqlite3.Connection,
    project_id: str,
    locator: str,
    source_id: str,
    paper_id_by_node_id: dict[str, str],
) -> list[dict[str, Any]]:
    project_nodes = [
        _node_item(row)
        for row in connection.execute(
            """
            SELECT *
            FROM understanding_nodes
            WHERE project_id = ? AND scope = 'project'
            ORDER BY node_id
            """,
            (project_id,),
        )
        if locator in json_loads(row["source_refs_json"], []) or source_id in json_loads(row["source_refs_json"], [])
    ]
    paper_ids = list(paper_id_by_node_id.values())
    if not paper_ids or not project_nodes:
        return []
    translations = []
    for index, project_node in enumerate(project_nodes[:8], start=1):
        translations.append(
            {
                "id": f"TL{index}",
                "paper_nodes": paper_ids,
                "project_nodes": [project_node["metadata"].get("local_id") or project_node["id"]],
                "relation": "paper_understanding_supports_project_node",
                "interpretation": f"Paper understanding contributes to project node {project_node['metadata'].get('local_id') or project_node['id']}.",
                "caveat": "Derived DB read model; project graph remains separate.",
            }
        )
    return translations


def _experiment_rows(connection: sqlite3.Connection, project_id: str) -> list[sqlite3.Row]:
    return list(connection.execute("SELECT * FROM experiments WHERE project_id = ? ORDER BY experiment_id", (project_id,)))


def _experiment_item(row: sqlite3.Row) -> dict[str, Any]:
    metadata = json_loads(row["metadata_json"], {})
    protocol = [line for line in row["protocol_summary"].splitlines() if line]
    return {
        "id": row["experiment_id"],
        "title": row["title"],
        "question": row["question"],
        "hypothesis": row["hypothesis"],
        "experiment_type": row["experiment_type"],
        "status": row["status"],
        "protocol": protocol,
        "benchmark": row["benchmark_name"],
        "dataset": row["dataset_name"],
        "planned_at": row["planned_at"],
        "metadata": metadata,
    }


def _run_rows(connection: sqlite3.Connection, project_id: str) -> list[sqlite3.Row]:
    return list(connection.execute("SELECT * FROM experiment_runs WHERE project_id = ? ORDER BY run_id", (project_id,)))


def _run_item(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["run_id"],
        "experiment_id": row["experiment_id"],
        "origin_type": row["origin_type"],
        "status": row["status"],
        "method_name": row["method_name"],
        "run_label": row["run_label"],
        "completed_at": row["completed_at"],
        "summary": row["summary"],
        "metrics": [],
        "artifacts": [],
    }


def _metrics_by_run(connection: sqlite3.Connection, project_id: str) -> dict[str, list[dict[str, Any]]]:
    metrics: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in connection.execute(
        """
        SELECT *
        FROM experiment_metrics
        WHERE project_id = ?
        ORDER BY metric_id
        """,
        (project_id,),
    ):
        metrics[row["run_id"]].append(
            {
                "id": row["metric_id"],
                "name": row["name"],
                "value": row["value_text"],
                "unit": row["unit"],
                "direction": row["direction"],
                "benchmark": row["benchmark_name"],
                "dataset": row["dataset_name"],
                "split": row["split_name"],
                "metadata": json_loads(row["metadata_json"], {}),
            }
        )
    return metrics


def _artifacts_by_run(connection: sqlite3.Connection, project_id: str) -> dict[str, list[dict[str, Any]]]:
    artifacts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in connection.execute(
        """
        SELECT *
        FROM experiment_artifacts
        WHERE project_id = ?
        ORDER BY artifact_id
        """,
        (project_id,),
    ):
        artifacts[row["run_id"]].append(
            {
                "id": row["artifact_id"],
                "type": row["artifact_type"],
                "locator_type": row["locator_type"],
                "locator": row["locator"],
                "label": row["label"],
                "description": row["description"],
                "metadata": json_loads(row["metadata_json"], {}),
            }
        )
    return artifacts


def _experiment_summary(experiments: list[dict[str, Any]], runs: list[dict[str, Any]]) -> dict[str, Any]:
    experiment_statuses = Counter(experiment["status"] for experiment in experiments)
    run_statuses = Counter(run["status"] for run in runs)
    origins = Counter(run["origin_type"] for run in runs)
    summary: dict[str, Any] = {
        "total_experiments": len(experiments),
        "total_runs": len(runs),
        "completed_runs": run_statuses.get("completed", 0),
        "imported_evidence_runs": origins.get("imported_paper", 0),
        "local_result_runs": origins.get("local", 0),
    }
    for status, count in sorted(experiment_statuses.items()):
        summary[status] = count
    for status, count in sorted(run_statuses.items()):
        summary[f"{status}_runs"] = count
    for origin, count in sorted(origins.items()):
        summary[f"{origin}_runs"] = count
    return summary


def _lane_rows(connection: sqlite3.Connection, project_id: str) -> list[sqlite3.Row]:
    return list(connection.execute("SELECT * FROM literature_lanes WHERE project_id = ? ORDER BY lane_id", (project_id,)))


def _lane_item(row: sqlite3.Row) -> dict[str, Any]:
    metadata = json_loads(row["metadata_json"], {})
    return {
        "id": row["lane_id"],
        "label": row["title"],
        "description": row["description"],
        "review_status": row["status"],
        "metadata": metadata,
    }


def _literature_rows(connection: sqlite3.Connection, project_id: str) -> list[sqlite3.Row]:
    return list(
        connection.execute(
            """
            SELECT literature_items.*, sources.title AS source_title, sources.authors, sources.year, sources.url, sources.doi, sources.arxiv_id
            FROM literature_items
            LEFT JOIN sources ON sources.source_id = literature_items.source_id
            WHERE literature_items.project_id = ?
            ORDER BY literature_items.item_id
            """,
            (project_id,),
        )
    )


def _literature_item(row: sqlite3.Row) -> dict[str, Any]:
    metadata = json_loads(row["metadata_json"], {})
    item = dict(metadata)
    item.update(
        {
            "id": item.get("id") or row["item_id"],
            "item_id": row["item_id"],
            "source_id": row["source_id"],
            "lane_id": row["lane_id"],
            "role": row["role"],
            "importance": row["importance"],
            "summary": row["summary"],
            "source_title": row["source_title"],
            "authors": row["authors"],
            "year": row["year"],
            "url": row["url"],
            "doi": row["doi"],
            "arxiv_id": row["arxiv_id"],
        }
    )
    return item


def _relation_rows(connection: sqlite3.Connection, project_id: str) -> list[sqlite3.Row]:
    return list(connection.execute("SELECT * FROM literature_relations WHERE project_id = ? ORDER BY relation_id", (project_id,)))


def _relation_item(row: sqlite3.Row) -> dict[str, Any]:
    metadata = json_loads(row["metadata_json"], {})
    edge = dict(metadata)
    edge.update(
        {
            "id": row["relation_id"],
            "source": edge.get("source") or row["from_item_id"],
            "target": edge.get("target") or row["to_item_id"],
            "relation": edge.get("relation") or row["relation_type"],
            "rationale": row["rationale"],
            "from_item_id": row["from_item_id"],
            "to_item_id": row["to_item_id"],
        }
    )
    return edge


def _positioning_rows(connection: sqlite3.Connection, project_id: str) -> list[sqlite3.Row]:
    return list(connection.execute("SELECT * FROM project_positionings WHERE project_id = ? ORDER BY positioning_id", (project_id,)))


def _positioning_item(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["positioning_id"],
        "text": row["text"],
        "confidence": row["confidence"],
        "metadata": json_loads(row["metadata_json"], {}),
    }
