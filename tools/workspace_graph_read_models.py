#!/usr/bin/env python3
"""Workspace graph read model skeleton backed by research-pilot.db."""

from __future__ import annotations

import json
import re
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from tools.research_dataset import dataset_db_path as dataset_path
from tools.research_dataset_read_models import (
    build_experiments_model,
    build_literature_model,
    build_paper_graph_model,
    build_project_graph_model,
    build_sources_model,
)


SCHEMA_VERSION = "workspace-graph-v1"
DB_SOURCE = "research-pilot.db"
DEFAULT_LAYERS = {
    "understanding": "project_overview",
    "literature": "literature_overview",
    "experiments": "evaluation_overview",
}
VALID_LAYERS = {
    "understanding": {"project_overview", "claim_focus", "paper_focus"},
    "literature": {"literature_overview", "literature_route_focus", "literature_paper_focus"},
    "experiments": {"evaluation_overview", "evaluation_setting_focus", "experiment_design_focus"},
}


def build_workspace_graph_model(
    root: Path,
    project_id: str,
    *,
    mode: str = "understanding",
    layer: str = "",
    focus_id: str = "",
    selected_id: str = "",
) -> dict[str, Any]:
    mode = (mode or "understanding").strip()
    if mode not in DEFAULT_LAYERS:
        raise ValueError(f"unknown workspace graph mode: {mode}")
    layer = (layer or DEFAULT_LAYERS[mode]).strip()
    if layer not in VALID_LAYERS[mode]:
        raise ValueError(f"unknown workspace graph layer for {mode}: {layer}")
    if mode == "understanding":
        return _build_understanding(root, project_id, layer, focus_id, selected_id)
    if mode == "literature":
        return _build_literature(root, project_id, layer, focus_id, selected_id)
    return _build_experiments(root, project_id, layer, focus_id, selected_id)


def _base_payload(project_id: str, mode: str, layer: str, focus_id: str = "", selected_id: str = "") -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "source": DB_SOURCE,
        "project_id": project_id,
        "mode": mode,
        "layer": layer,
        "focus_id": focus_id,
        "selected_id": selected_id,
        "breadcrumb": [{"label": "Workspace", "mode": "understanding", "layer": "project_overview", "focus_id": ""}],
        "canvas": {"layout_hint": "island", "nodes": [], "edges": []},
        "inspector": {"kind": "overview", "title": "", "summary": "", "sections": [], "actions": []},
        "available_layers": sorted(VALID_LAYERS[mode]),
        "cross_mode_jumps": [],
        "empty_state": None,
        "warnings": [],
    }


def _json_loads(value: Any, fallback: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(str(value or ""))
    except (TypeError, json.JSONDecodeError):
        return fallback


def _slug(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")[:96] or "unknown"


def _local_id(value: Any) -> str:
    text = str(value or "")
    if not text:
        return ""
    return text.rsplit(":", 1)[-1]


def _node_local_id(node: dict[str, Any]) -> str:
    metadata = node.get("metadata") or {}
    return str(node.get("local_id") or metadata.get("local_id") or node.get("subtitle") or _local_id(node.get("id")))


def _node_graph_id(kind: str, node: dict[str, Any]) -> str:
    return f"{kind}:{_node_local_id(node)}"


def _source_graph_id(source_id: str) -> str:
    return f"source:{source_id}"


def _experiment_graph_id(experiment_id: str) -> str:
    return f"experiment:{experiment_id}"


def _run_graph_id(run_id: str) -> str:
    return f"run:{run_id}"


def _strip_prefix(value: str, prefix: str) -> str:
    text = str(value or "")
    return text[len(prefix) :] if text.startswith(prefix) else text


def _connection(root: Path) -> sqlite3.Connection:
    path = dataset_path(root)
    if not path.exists():
        raise ValueError("research-pilot.db not found")
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def _project_graph(root: Path, project_id: str) -> dict[str, Any]:
    return build_project_graph_model(root, project_id)


def _project_node_maps(graph: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    by_db_id = {node["id"]: node for node in graph.get("nodes", [])}
    by_graph_id = {_node_graph_id(str(node.get("kind") or ""), node): node for node in graph.get("nodes", [])}
    return by_db_id, by_graph_id


def _understanding_node(node: dict[str, Any], *, selected_id: str = "") -> dict[str, Any]:
    kind = str(node.get("kind") or "")
    graph_id = _node_graph_id(kind, node)
    local_id = _node_local_id(node)
    drill = None
    if kind == "claim":
        drill = {"mode": "understanding", "layer": "claim_focus", "focus_id": graph_id}
    return {
        "id": graph_id,
        "entity_type": kind,
        "db_id": node.get("id", ""),
        "local_id": local_id,
        "label": node.get("label") or node.get("text") or local_id,
        "subtitle": node.get("subtitle") or node.get("status") or "",
        "status": node.get("status") or "",
        "confidence": node.get("confidence") or "",
        "drill": drill,
        "inspector": {"selected_id": graph_id},
        "selected": graph_id == selected_id,
        "metadata": node.get("metadata") or {},
    }


def _question_claim_ids(graph: dict[str, Any]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    by_db_id, _by_graph_id = _project_node_maps(graph)
    for node in graph.get("nodes", []):
        if node.get("kind") == "question":
            result[_node_graph_id("question", node)] = []

    for link in graph.get("links", []):
        if str(link.get("relation") or "").lower() != "answers":
            continue
        endpoint_ids = list(link.get("premises") or link.get("source") or []) + list(link.get("target") or [])
        questions = [by_db_id[node_id] for node_id in endpoint_ids if by_db_id.get(node_id, {}).get("kind") == "question"]
        claims = [by_db_id[node_id] for node_id in endpoint_ids if by_db_id.get(node_id, {}).get("kind") == "claim"]
        for question in questions:
            question_id = _node_graph_id("question", question)
            bucket = result.setdefault(question_id, [])
            for claim in claims:
                claim_id = _node_graph_id("claim", claim)
                if claim_id not in bucket:
                    bucket.append(claim_id)
    return result


def _understanding_edges(graph: dict[str, Any]) -> list[dict[str, Any]]:
    by_db_id, _by_graph_id = _project_node_maps(graph)
    edges: list[dict[str, Any]] = []
    for link in graph.get("links", []):
        relation = str(link.get("relation") or "related")
        targets = link.get("target") or []
        sources = link.get("premises") or link.get("source") or []
        for source_db_id in sources:
            for target_db_id in targets:
                source = by_db_id.get(source_db_id)
                target = by_db_id.get(target_db_id)
                if not source or not target:
                    continue
                source_id = _node_graph_id(str(source.get("kind") or ""), source)
                target_id = _node_graph_id(str(target.get("kind") or ""), target)
                edges.append(
                    {
                        "id": f"edge:{_local_id(link.get('id'))}:{source_id}:{target_id}",
                        "source": source_id,
                        "target": target_id,
                        "source_db_id": source_db_id,
                        "target_db_id": target_db_id,
                        "relation": relation,
                        "label": relation,
                        "metadata": {"link_id": link.get("id"), "local_id": link.get("local_id")},
                    }
                )
    return edges


def _question_list_section(graph: dict[str, Any]) -> dict[str, Any]:
    claim_ids_by_question = _question_claim_ids(graph)
    items = []
    for node in graph.get("nodes", []):
        if node.get("kind") != "question":
            continue
        graph_id = _node_graph_id("question", node)
        items.append(
            {
                "id": graph_id,
                "db_id": node.get("id", ""),
                "local_id": _node_local_id(node),
                "label": node.get("label") or "",
                "claim_count": len(claim_ids_by_question.get(graph_id, [])),
                "inspector": {"selected_id": graph_id},
            }
        )
    return {"title": "Questions", "kind": "question_list", "items": items}


def _question_detail(graph: dict[str, Any], selected_id: str) -> dict[str, Any]:
    _by_db_id, by_graph_id = _project_node_maps(graph)
    question = by_graph_id.get(selected_id)
    claim_ids = _question_claim_ids(graph).get(selected_id, [])
    claims = []
    for claim_id in claim_ids:
        claim = by_graph_id.get(claim_id)
        if not claim:
            continue
        claims.append(
            {
                "id": claim_id,
                "db_id": claim.get("id", ""),
                "local_id": _node_local_id(claim),
                "label": claim.get("label") or "",
                "drill": {"mode": "understanding", "layer": "claim_focus", "focus_id": claim_id},
            }
        )
    return {
        "kind": "question_detail",
        "title": _node_local_id(question) if question else "Question",
        "summary": question.get("label", "") if question else "",
        "sections": [{"title": "Linked Claims", "kind": "linked_claims", "items": claims}],
        "actions": [],
    }


def _source_lookup(root: Path, project_id: str) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for source in build_sources_model(root, project_id).get("sources", []):
        for key in (
            source.get("source_id"),
            source.get("locator"),
            source.get("title"),
            source.get("url"),
            source.get("doi"),
            source.get("arxiv_id"),
        ):
            if key:
                lookup[str(key)] = source
    return lookup


def _source_node(source: dict[str, Any], claim_graph_id: str) -> dict[str, Any]:
    source_id = str(source.get("source_id") or source.get("locator") or source.get("title") or "unknown")
    graph_id = _source_graph_id(source_id)
    return {
        "id": graph_id,
        "entity_type": "source",
        "source_id": source_id,
        "path": source.get("locator", ""),
        "label": source.get("title") or source_id,
        "subtitle": "paper/source",
        "status": source.get("reading_status") or "",
        "confidence": "",
        "drill": {"mode": "understanding", "layer": "paper_focus", "focus_id": claim_graph_id, "selected_id": graph_id},
        "inspector": {"selected_id": graph_id},
        "metadata": source,
    }


def _claim_related_nodes(
    root: Path,
    project_id: str,
    graph: dict[str, Any],
    claim_graph_id: str,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]], list[dict[str, Any]]]:
    by_db_id, by_graph_id = _project_node_maps(graph)
    claim = by_graph_id.get(claim_graph_id)
    if not claim:
        return None, [], []

    claim_db_id = claim.get("id")
    related_db_ids: set[str] = set()
    for link in graph.get("links", []):
        targets = set(link.get("target") or [])
        sources = set(link.get("premises") or link.get("source") or [])
        warrants = set(link.get("warrant") or [])
        limitations = set(link.get("limitations") or [])
        if claim_db_id in targets:
            related_db_ids.update(sources)
            related_db_ids.update(warrants)
            related_db_ids.update(limitations)
        if claim_db_id in sources:
            related_db_ids.update(targets)
            related_db_ids.update(warrants)
            related_db_ids.update(limitations)

    related_nodes = [by_db_id[node_id] for node_id in sorted(related_db_ids) if node_id in by_db_id and node_id != claim_db_id]
    sources_by_ref = _source_lookup(root, project_id)
    source_nodes = []
    seen_sources: set[str] = set()
    for node in [claim, *related_nodes]:
        for source_ref in node.get("source_refs") or []:
            source = sources_by_ref.get(str(source_ref))
            if not source:
                continue
            source_id = str(source.get("source_id") or "")
            if not source_id or source_id in seen_sources:
                continue
            seen_sources.add(source_id)
            source_nodes.append(_source_node(source, claim_graph_id))
    return claim, related_nodes, source_nodes


def _claim_detail(claim: dict[str, Any], related_nodes: list[dict[str, Any]], source_nodes: list[dict[str, Any]]) -> dict[str, Any]:
    sections = []
    for kind, title in [
        ("claim", "Supporting Claims"),
        ("evidence", "Evidence / Grounds"),
        ("warrant", "Warrants / Bridges"),
        ("limitation", "Limitations / Boundaries"),
    ]:
        items = [
            {
                "id": _node_graph_id(kind, node),
                "db_id": node.get("id", ""),
                "local_id": _node_local_id(node),
                "label": node.get("label") or "",
                "subtitle": node.get("subtitle") or node.get("status") or "",
            }
            for node in related_nodes
            if node.get("kind") == kind
        ]
        sections.append({"title": title, "kind": kind, "items": items})
    sections.append({"title": "Source Papers", "kind": "sources", "items": source_nodes})
    return {
        "kind": "claim_detail",
        "title": _node_local_id(claim),
        "summary": claim.get("label") or "",
        "sections": sections,
        "actions": [
            {
                "label": "View related experiment results",
                "kind": "cross_mode_jump",
                "target": {"mode": "experiments", "layer": "evaluation_overview", "focus_id": "", "selected_id": _node_graph_id("claim", claim)},
            }
        ],
    }


def _build_understanding(root: Path, project_id: str, layer: str, focus_id: str, selected_id: str) -> dict[str, Any]:
    graph = _project_graph(root, project_id)
    payload = _base_payload(project_id, "understanding", layer, focus_id, selected_id)

    if layer == "project_overview":
        nodes = [_understanding_node(node, selected_id=selected_id) for node in graph.get("nodes", []) if node.get("kind") in {"question", "claim"}]
        overview_ids = {node["id"] for node in nodes}
        payload["canvas"]["nodes"] = nodes
        payload["canvas"]["edges"] = [edge for edge in _understanding_edges(graph) if edge["source"] in overview_ids and edge["target"] in overview_ids]
        if selected_id.startswith("question:"):
            payload["inspector"] = _question_detail(graph, selected_id)
        else:
            payload["inspector"] = {
                "kind": "overview",
                "title": "Questions",
                "summary": "Project questions organize the top-level Understanding graph.",
                "sections": [_question_list_section(graph)],
                "actions": [],
            }
        return payload

    if layer == "claim_focus":
        claim_id = focus_id or selected_id
        claim, related_nodes, source_nodes = _claim_related_nodes(root, project_id, graph, claim_id)
        if not claim:
            raise ValueError(f"unknown claim focus: {claim_id}")
        payload["focus_id"] = claim_id
        payload["canvas"]["nodes"] = [
            _understanding_node(claim, selected_id=selected_id or claim_id),
            *[_understanding_node(node, selected_id=selected_id) for node in related_nodes],
            *source_nodes,
        ]
        related_ids = {node["id"] for node in payload["canvas"]["nodes"]}
        payload["canvas"]["edges"] = [edge for edge in _understanding_edges(graph) if edge["source"] in related_ids and edge["target"] in related_ids]
        payload["inspector"] = _claim_detail(claim, related_nodes, source_nodes)
        return payload

    if layer == "paper_focus":
        claim_id = focus_id
        source_id = _strip_prefix(selected_id, "source:")
        sources_model = build_sources_model(root, project_id)
        source = next((item for item in sources_model.get("sources", []) if item.get("source_id") == source_id), None)
        if not source or not source.get("locator"):
            raise ValueError(f"unknown paper source: {selected_id}")
        paper_graph = build_paper_graph_model(root, root / source["locator"])
        claim, _related_nodes, _source_nodes = _claim_related_nodes(root, project_id, graph, claim_id)
        if not claim:
            raise ValueError(f"unknown claim focus: {claim_id}")
        payload["focus_id"] = claim_id
        payload["selected_id"] = selected_id
        payload["canvas"]["nodes"] = [
            {
                "id": claim_id,
                "entity_type": "project_claim_anchor",
                "db_id": claim.get("id", ""),
                "local_id": _node_local_id(claim),
                "label": claim.get("label") or claim_id,
                "subtitle": "project claim anchor",
                "status": claim.get("status") or "",
                "confidence": claim.get("confidence") or "",
                "drill": {"mode": "understanding", "layer": "claim_focus", "focus_id": claim_id},
                "inspector": {"selected_id": claim_id},
                "metadata": claim,
            },
            *[
                {
                    "id": f"paper_node:{source_id}:{node['id']}",
                    "entity_type": f"paper_{node.get('kind', 'node')}",
                    "db_id": node.get("id", ""),
                    "local_id": node.get("id", ""),
                    "label": node.get("label") or node.get("id") or "",
                    "subtitle": node.get("subtitle") or node.get("kind") or "",
                    "status": "",
                    "confidence": "",
                    "drill": None,
                    "inspector": {"selected_id": f"paper_node:{source_id}:{node['id']}"},
                    "metadata": node,
                }
                for node in paper_graph.get("nodes", [])
            ],
        ]
        payload["canvas"]["edges"] = [
            {
                "id": f"paper_edge:{source_id}:{link.get('id')}:{premise}:{link.get('target')}",
                "source": f"paper_node:{source_id}:{premise}",
                "target": f"paper_node:{source_id}:{link.get('target')}",
                "relation": link.get("relation") or "supports",
                "label": link.get("relation") or "supports",
                "metadata": link,
            }
            for link in paper_graph.get("paper_links", [])
            if link.get("target")
            for premise in link.get("premises", [])
        ]
        payload["inspector"] = {
            "kind": "paper_layer",
            "title": paper_graph.get("title") or source.get("title") or source_id,
            "summary": "Paper argument layer projected beside the selected project claim.",
            "sections": [
                {"title": "Paper Nodes", "kind": "paper_node_list", "items": paper_graph.get("nodes", [])},
                {"title": "Translation Bridge", "kind": "translation_bridge", "items": paper_graph.get("translations", [])},
            ],
            "actions": [],
        }
        return payload

    raise ValueError(f"unknown understanding layer: {layer}")


def _literature_node_id(kind: str, raw_id: str) -> str:
    return f"{kind}:{_slug(raw_id)}"


def _literature_route_raw_id(route: dict[str, Any]) -> str:
    metadata = route.get("metadata") or {}
    return str(route.get("id") or route.get("lane_id") or metadata.get("id") or route.get("label") or "")


def _literature_route_local_id(route: dict[str, Any]) -> str:
    metadata = route.get("metadata") or {}
    return str(metadata.get("id") or route.get("id") or route.get("lane_id") or "")


def _literature_route_status(route: dict[str, Any]) -> str:
    return str(route.get("status") or route.get("review_status") or "")


def _literature_paper_source_id(paper: dict[str, Any]) -> str:
    return str(paper.get("source_id") or paper.get("id") or paper.get("item_id") or paper.get("title") or "unknown")


def _literature_paper_node_id(paper: dict[str, Any]) -> str:
    return _source_graph_id(_literature_paper_source_id(paper))


def _literature_paper_lookup(papers: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for paper in papers:
        for key in (paper.get("source_id"), paper.get("id"), paper.get("item_id"), paper.get("title")):
            if key:
                lookup[str(key)] = paper
    return lookup


def _literature_paper_node(paper: dict[str, Any], *, drill: bool = True) -> dict[str, Any]:
    source_id = _literature_paper_source_id(paper)
    graph_id = _source_graph_id(source_id)
    return {
        "id": graph_id,
        "entity_type": "source",
        "source_id": source_id,
        "local_id": str(paper.get("id") or source_id),
        "label": str(paper.get("title") or paper.get("label") or source_id)[:120],
        "subtitle": str(paper.get("year") or paper.get("role") or "paper"),
        "status": str(paper.get("status") or paper.get("review_status") or ""),
        "confidence": "",
        "drill": {"mode": "literature", "layer": "literature_paper_focus", "focus_id": graph_id} if drill else None,
        "inspector": {"selected_id": graph_id},
        "metadata": paper,
    }


def _build_literature(root: Path, project_id: str, layer: str, focus_id: str, selected_id: str) -> dict[str, Any]:
    model = build_literature_model(root, project_id)
    payload = _base_payload(project_id, "literature", layer, focus_id, selected_id)
    routes = model.get("routes") or []
    papers = model.get("papers") or []
    edges = model.get("explicit_edges") or []
    paper_by_key = _literature_paper_lookup(papers)

    if layer == "literature_overview":
        nodes = []
        for route in routes:
            route_id = _literature_route_raw_id(route)
            graph_id = _literature_node_id("literature_lane", route_id)
            nodes.append(
                {
                    "id": graph_id,
                    "entity_type": "literature_lane",
                    "db_id": route.get("lane_id") or route_id,
                    "local_id": _literature_route_local_id(route),
                    "label": str(route.get("label") or route_id)[:120],
                    "subtitle": _literature_route_status(route) or "route",
                    "status": _literature_route_status(route),
                    "confidence": "",
                    "drill": {"mode": "literature", "layer": "literature_route_focus", "focus_id": graph_id},
                    "inspector": {"selected_id": graph_id},
                    "metadata": route,
                }
            )
        nodes.extend(_literature_paper_node(paper) for paper in papers)
        payload["canvas"]["nodes"] = nodes
        payload["canvas"]["edges"] = [
            {
                "id": f"literature_edge:{index}",
                "source": _literature_paper_node_id(source_paper),
                "target": _literature_paper_node_id(target_paper),
                "relation": str(edge.get("relation") or "related"),
                "label": str(edge.get("relation") or "related"),
                "metadata": edge,
            }
            for index, edge in enumerate(edges)
            for source_paper in [paper_by_key.get(str(edge.get("source") or edge.get("from_item_id") or ""))]
            for target_paper in [paper_by_key.get(str(edge.get("target") or edge.get("to_item_id") or ""))]
            if source_paper and target_paper
        ]
        payload["inspector"] = {
            "kind": "overview",
            "title": "Literature Routes",
            "summary": "Paper-only lineage that supports but does not replace Project Understanding.",
            "sections": [
                {
                    "title": "Routes",
                    "kind": "route_list",
                    "items": [
                        {
                            "id": _literature_node_id("literature_lane", _literature_route_raw_id(route)),
                            "label": route.get("label") or _literature_route_local_id(route),
                            "paper_count": sum(
                                1
                                for paper in papers
                                if paper.get("lane_id") == route.get("id")
                                or paper.get("route") == (route.get("metadata") or {}).get("id")
                            ),
                        }
                        for route in routes
                    ],
                }
            ],
            "actions": [],
        }
        return payload

    if layer == "literature_route_focus":
        route_key = _strip_prefix(focus_id, "literature_lane:")
        route = next((item for item in routes if _slug(_literature_route_raw_id(item)) == route_key), None)
        if not route:
            raise ValueError(f"unknown literature route: {focus_id}")
        route_raw_id = _literature_route_raw_id(route)
        route_local_id = _literature_route_local_id(route)
        route_papers = [
            paper
            for paper in papers
            if paper.get("lane_id") == route_raw_id or paper.get("route") == route_local_id or route_local_id in (paper.get("route_ids") or [])
        ]
        payload["focus_id"] = focus_id
        payload["canvas"]["nodes"] = [
            {
                "id": focus_id,
                "entity_type": "literature_lane",
                "db_id": route.get("lane_id") or route_raw_id,
                "local_id": route_local_id,
                "label": str(route.get("label") or route_local_id or route_raw_id)[:120],
                "subtitle": "route",
                "status": _literature_route_status(route),
                "confidence": "",
                "drill": None,
                "inspector": {"selected_id": focus_id},
                "metadata": route,
            },
            *[_literature_paper_node(paper) for paper in route_papers],
        ]
        payload["inspector"] = {
            "kind": "route_detail",
            "title": route.get("label") or route_local_id or "Route",
            "summary": route.get("summary") or route.get("description") or "",
            "sections": [{"title": "Papers", "kind": "paper_list", "items": route_papers}],
            "actions": [],
        }
        return payload

    if layer == "literature_paper_focus":
        source_key = _strip_prefix(focus_id, "source:")
        paper = next((item for item in papers if _literature_paper_source_id(item) == source_key), None)
        if not paper:
            raise ValueError(f"unknown literature paper: {focus_id}")
        payload["focus_id"] = focus_id
        payload["canvas"]["nodes"] = [_literature_paper_node(paper, drill=False)]
        payload["inspector"] = {
            "kind": "paper_detail",
            "title": paper.get("title") or source_key,
            "summary": paper.get("summary") or paper.get("field_position") or "",
            "sections": [{"title": "Source Metadata", "kind": "source_metadata", "items": [paper]}],
            "actions": [{"label": "Open Paper Detail", "kind": "open_page", "target": {"page": "paper", "source_id": source_key}}],
        }
        return payload

    raise ValueError(f"unknown literature layer: {layer}")


EVALUATION_METRIC_HINTS = {
    "miou": "segmentation overlap",
    "iou": "segmentation overlap",
    "kld": "saliency/heatmap alignment",
    "sim": "saliency/heatmap alignment",
    "nss": "saliency/heatmap alignment",
    "auc": "saliency/heatmap alignment",
    "accuracy": "classification accuracy",
    "top-1": "classification accuracy",
    "top-5": "classification accuracy",
    "cosine": "representation similarity",
    "activation similarity": "representation similarity",
    "qualitative": "qualitative assessment",
    "human rating": "qualitative assessment",
    "rubric": "qualitative assessment",
}
DESCRIPTIVE_METRIC_HINTS = {
    "train images",
    "test images",
    "affordance categories",
    "supervision",
    "hold localization",
    "cut localization",
    "drink localization",
    "evidence type",
    "full-scene response",
    "simplified shape response",
}
SHORT_METRIC_HINTS = {"iou", "kld", "sim", "nss", "auc"}


def _metadata_list(item: dict[str, Any], key: str) -> list[str]:
    metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
    value = metadata.get(key, [])
    if isinstance(value, list):
        return [str(entry) for entry in value if str(entry).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _metadata_text(item: dict[str, Any], key: str) -> str:
    metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
    return str(metadata.get(key) or "").strip()


def _metric_family_from_names(names: list[str]) -> str:
    families = []
    for name in names:
        lower = name.lower()
        if any(hint in lower for hint in DESCRIPTIVE_METRIC_HINTS):
            continue
        for hint, family in EVALUATION_METRIC_HINTS.items():
            if _metric_hint_matches(hint, lower):
                families.append(family)
                break
    unique_families = sorted(set(families))
    if unique_families:
        return " + ".join(unique_families)
    return ""


def _metric_hint_matches(hint: str, lower_name: str) -> bool:
    if hint in SHORT_METRIC_HINTS:
        return re.search(rf"(?<![a-z0-9]){re.escape(hint)}(?![a-z0-9])", lower_name) is not None
    return hint in lower_name


def _planned_metric_family(experiment: dict[str, Any]) -> str:
    return _metric_family_from_names(_metadata_list(experiment, "metrics")) or "qualitative assessment"


def _experiment_setting(experiment: dict[str, Any], runs: list[dict[str, Any]]) -> dict[str, Any]:
    metric_names = [str(metric.get("name") or "") for run in runs for metric in run.get("metrics", [])]
    metric_benchmark = next(
        (
            metric.get("benchmark") or metric.get("benchmark_name")
            for run in runs
            for metric in run.get("metrics", [])
            if metric.get("benchmark") or metric.get("benchmark_name")
        ),
        "",
    )
    metric_dataset = next(
        (
            metric.get("dataset") or metric.get("dataset_name")
            for run in runs
            for metric in run.get("metrics", [])
            if metric.get("dataset") or metric.get("dataset_name")
        ),
        "",
    )
    benchmark = str(metric_benchmark or experiment.get("benchmark") or experiment.get("benchmark_name") or _metadata_text(experiment, "benchmark") or "Unspecified benchmark")
    dataset = str(metric_dataset or experiment.get("dataset") or experiment.get("dataset_name") or _metadata_text(experiment, "dataset") or "Unspecified dataset")
    family = _metric_family_from_names(metric_names) or _planned_metric_family(experiment) or "qualitative assessment"
    setting_id = f"evaluation_setting:{_slug(benchmark)}:{_slug(dataset)}:{_slug(family)}"
    return {
        "id": setting_id,
        "entity_type": "evaluation_setting",
        "label": f"{benchmark} / {dataset} / {family}",
        "benchmark": benchmark,
        "dataset": dataset,
        "metric_family": family,
        "metadata": {"raw_benchmark": benchmark, "raw_dataset": dataset},
    }


def _experiments_by_id(model: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {experiment["id"]: experiment for experiment in model.get("experiments", [])}


def _runs_by_experiment(model: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for run in model.get("runs", []):
        grouped.setdefault(run.get("experiment_id", ""), []).append(run)
    return grouped


def _evaluation_settings(model: dict[str, Any]) -> list[dict[str, Any]]:
    runs_by_experiment = _runs_by_experiment(model)
    by_id: dict[str, dict[str, Any]] = {}
    for experiment in model.get("experiments", []):
        runs = runs_by_experiment.get(experiment.get("id"), [])
        setting = _experiment_setting(experiment, runs)
        current = by_id.setdefault(
            setting["id"],
            {**setting, "experiment_ids": set(), "run_ids": set(), "imported_evidence_count": 0, "local_result_count": 0},
        )
        current["experiment_ids"].add(experiment.get("id", ""))
        for run in runs:
            current["run_ids"].add(run.get("id", ""))
            if run.get("origin_type") == "imported_paper":
                current["imported_evidence_count"] += 1
            if run.get("origin_type") == "local":
                current["local_result_count"] += 1

    result = []
    for setting in by_id.values():
        experiment_ids = sorted(item for item in setting["experiment_ids"] if item)
        run_ids = sorted(item for item in setting["run_ids"] if item)
        result.append(
            {
                **{key: value for key, value in setting.items() if key not in {"experiment_ids", "run_ids"}},
                "experiment_ids": experiment_ids,
                "run_ids": run_ids,
                "experiment_count": len(experiment_ids),
                "run_count": len(run_ids),
            }
        )
    return sorted(result, key=lambda item: item["label"])


def _claim_impacts(root: Path, project_id: str, run_id: str) -> list[dict[str, Any]]:
    impacts: list[dict[str, Any]] = []
    with closing(_connection(root)) as connection:
        rows = connection.execute(
            """
            SELECT relation_type, to_entity_id, metadata_json
            FROM entity_links
            WHERE project_id = ?
              AND from_entity_type = 'experiment_run'
              AND from_entity_id = ?
              AND relation_type LIKE 'claim_impact:%'
            ORDER BY relation_type, to_entity_id
            """,
            (project_id, run_id),
        ).fetchall()
    for row in rows:
        metadata = _json_loads(row["metadata_json"], {})
        impact = row["relation_type"].split(":", 1)[-1]
        local_claim = metadata.get("claim") or _local_id(row["to_entity_id"])
        impacts.append(
            {
                "id": f"claim_impact:{run_id}:{impact}:{local_claim}",
                "target_id": f"claim:{local_claim}",
                "target_db_id": row["to_entity_id"],
                "impact": impact,
                "strength": metadata.get("strength", ""),
                "metadata": metadata,
                "jump": {"mode": "understanding", "layer": "claim_focus", "focus_id": f"claim:{local_claim}"},
            }
        )
    return impacts


def _support_node(kind: str, experiment_id: str, index: int, value: str) -> dict[str, Any]:
    node_id = f"{kind}:{experiment_id}:{index}"
    return {
        "id": node_id,
        "entity_type": kind,
        "label": str(value),
        "subtitle": kind,
        "status": "",
        "confidence": "",
        "metadata": {"experiment_id": experiment_id, "value": value},
        "drill": None,
        "inspector": {"selected_id": node_id},
    }


def _run_inspector(root: Path, project_id: str, selected_id: str, runs: list[dict[str, Any]]) -> dict[str, Any]:
    run_id = _strip_prefix(selected_id, "run:")
    run = next((item for item in runs if item.get("id") == run_id), None)
    if not run:
        raise ValueError(f"unknown run: {selected_id}")
    impacts = _claim_impacts(root, project_id, run_id)
    actions = []
    for item in impacts:
        action = dict(item["jump"])
        action.update({"label": f"Open {item['target_id']}", "kind": "cross_mode_jump"})
        actions.append(action)
    return {
        "kind": "run_detail",
        "title": run.get("run_label") or run_id,
        "summary": run.get("summary") or "",
        "sections": [
            {"title": "Metric Values", "kind": "metric_values", "items": run.get("metrics") or []},
            {"title": "Artifacts", "kind": "artifacts", "items": run.get("artifacts") or []},
            {"title": "Interpretation", "kind": "text", "items": [{"text": _metadata_text(run, "interpretation")}]},
            {"title": "Weaknesses", "kind": "weakness_list", "items": [{"text": item} for item in _metadata_list(run, "weaknesses")]},
            {"title": "Project Understanding Impact", "kind": "project_understanding_impact", "items": impacts},
        ],
        "actions": actions,
    }


def _build_experiments(root: Path, project_id: str, layer: str, focus_id: str, selected_id: str) -> dict[str, Any]:
    model = build_experiments_model(root, project_id)
    payload = _base_payload(project_id, "experiments", layer, focus_id, selected_id)
    experiments = _experiments_by_id(model)
    runs_by_experiment = _runs_by_experiment(model)
    settings = _evaluation_settings(model)

    if layer == "evaluation_overview":
        payload["canvas"]["nodes"] = [
            {
                "id": setting["id"],
                "entity_type": "evaluation_setting",
                "label": setting["label"],
                "subtitle": f"{setting['experiment_count']} experiments / {setting['run_count']} runs",
                "status": "",
                "confidence": "",
                "drill": {"mode": "experiments", "layer": "evaluation_setting_focus", "focus_id": setting["id"]},
                "inspector": {"selected_id": setting["id"]},
                "metadata": setting,
            }
            for setting in settings
        ]
        payload["inspector"] = {
            "kind": "overview",
            "title": "Evaluation Settings",
            "summary": "Datasets, benchmarks/tasks, and metric families organize Experiments before claim impact.",
            "sections": [{"title": "Evaluation Settings", "kind": "evaluation_setting_list", "items": settings}],
            "actions": [],
        }
        return payload

    if layer == "evaluation_setting_focus":
        setting = next((item for item in settings if item["id"] == focus_id), None)
        if not setting:
            raise ValueError(f"unknown evaluation setting: {focus_id}")
        payload["focus_id"] = focus_id
        metric_id = f"metric_family:{_slug(setting['metric_family'])}"
        benchmark_id = f"benchmark:{_slug(setting['benchmark'])}"
        dataset_id = f"dataset:{_slug(setting['dataset'])}"
        experiment_nodes = []
        for experiment_id in setting["experiment_ids"]:
            experiment = experiments.get(experiment_id)
            if not experiment:
                continue
            runs = runs_by_experiment.get(experiment_id, [])
            graph_id = _experiment_graph_id(experiment_id)
            experiment_nodes.append(
                {
                    "id": graph_id,
                    "entity_type": "experiment",
                    "db_id": experiment_id,
                    "local_id": experiment_id,
                    "label": experiment.get("title") or experiment_id,
                    "subtitle": f"{len(runs)} runs / {experiment.get('status', '')}",
                    "status": experiment.get("status") or "",
                    "confidence": "",
                    "drill": {"mode": "experiments", "layer": "experiment_design_focus", "focus_id": graph_id},
                    "inspector": {"selected_id": graph_id},
                    "metadata": experiment,
                }
            )
        payload["canvas"]["nodes"] = [
            {
                "id": setting["id"],
                "entity_type": "evaluation_setting",
                "label": setting["label"],
                "subtitle": "selected setting",
                "status": "",
                "confidence": "",
                "drill": None,
                "inspector": {"selected_id": setting["id"]},
                "metadata": setting,
            },
            {
                "id": dataset_id,
                "entity_type": "dataset",
                "label": setting["dataset"],
                "subtitle": "dataset",
                "status": "",
                "confidence": "",
                "metadata": setting,
                "drill": None,
                "inspector": {"selected_id": dataset_id},
            },
            {
                "id": benchmark_id,
                "entity_type": "benchmark",
                "label": setting["benchmark"],
                "subtitle": "benchmark/task",
                "status": "",
                "confidence": "",
                "metadata": setting,
                "drill": None,
                "inspector": {"selected_id": benchmark_id},
            },
            {
                "id": metric_id,
                "entity_type": "metric_family",
                "label": setting["metric_family"],
                "subtitle": "metric family",
                "status": "",
                "confidence": "",
                "metadata": setting,
                "drill": None,
                "inspector": {"selected_id": metric_id},
            },
            *experiment_nodes,
        ]
        payload["canvas"]["edges"] = [
            {"id": f"setting-dataset:{focus_id}", "source": dataset_id, "target": focus_id, "relation": "defines", "label": "defines", "metadata": {}},
            {"id": f"setting-benchmark:{focus_id}", "source": benchmark_id, "target": focus_id, "relation": "defines", "label": "defines", "metadata": {}},
            {"id": f"setting-metric:{focus_id}", "source": metric_id, "target": focus_id, "relation": "measured_by", "label": "measured by", "metadata": {}},
            *[
                {"id": f"setting-exp:{focus_id}:{node['id']}", "source": focus_id, "target": node["id"], "relation": "used_by", "label": "used by", "metadata": {}}
                for node in experiment_nodes
            ],
        ]
        payload["inspector"] = {
            "kind": "evaluation_setting_detail",
            "title": setting["label"],
            "summary": "This setting groups experiment designs by benchmark/task, dataset, and metric family.",
            "sections": [
                {"title": "Dataset", "kind": "dataset", "items": [{"label": setting["dataset"]}]},
                {"title": "Benchmark / Task", "kind": "benchmark", "items": [{"label": setting["benchmark"]}]},
                {"title": "Metric Family", "kind": "metric_family", "items": [{"label": setting["metric_family"]}]},
                {"title": "Experiment Designs", "kind": "experiment_list", "items": experiment_nodes},
            ],
            "actions": [],
        }
        return payload

    if layer == "experiment_design_focus":
        experiment_id = _strip_prefix(focus_id, "experiment:")
        experiment = experiments.get(experiment_id)
        if not experiment:
            raise ValueError(f"unknown experiment: {focus_id}")
        runs = runs_by_experiment.get(experiment_id, [])
        payload["focus_id"] = _experiment_graph_id(experiment_id)
        run_nodes = [
            {
                "id": _run_graph_id(run["id"]),
                "entity_type": "run",
                "db_id": run["id"],
                "local_id": run["id"],
                "label": run.get("run_label") or run.get("id"),
                "subtitle": f"{run.get('origin_type', '')} / {run.get('status', '')}",
                "status": run.get("status") or "",
                "confidence": "",
                "drill": None,
                "inspector": {"selected_id": _run_graph_id(run["id"])},
                "metadata": run,
            }
            for run in runs
        ]
        exp_node = {
            "id": _experiment_graph_id(experiment_id),
            "entity_type": "experiment",
            "db_id": experiment_id,
            "local_id": experiment_id,
            "label": experiment.get("title") or experiment_id,
            "subtitle": experiment.get("status") or "experiment",
            "status": experiment.get("status") or "",
            "confidence": "",
            "drill": None,
            "inspector": {"selected_id": _experiment_graph_id(experiment_id)},
            "metadata": experiment,
        }
        support_nodes = []
        for kind, values in [
            ("model", _metadata_list(experiment, "models")),
            ("baseline", _metadata_list(experiment, "baselines")),
            ("protocol", experiment.get("protocol") or _metadata_list(experiment, "protocol")),
            ("metric_family", _metadata_list(experiment, "metrics")),
        ]:
            for index, value in enumerate(values, start=1):
                support_nodes.append(_support_node(kind, experiment_id, index, value))
        payload["canvas"]["nodes"] = [exp_node, *support_nodes, *run_nodes]
        payload["canvas"]["edges"] = [
            *[
                {"id": f"exp-support:{node['id']}", "source": node["id"], "target": exp_node["id"], "relation": "defines", "label": "defines", "metadata": {}}
                for node in support_nodes
            ],
            *[
                {
                    "id": f"exp-run:{experiment_id}:{node['local_id']}",
                    "source": exp_node["id"],
                    "target": node["id"],
                    "relation": "produces",
                    "label": "produces",
                    "metadata": {},
                }
                for node in run_nodes
            ],
        ]
        if selected_id.startswith("run:"):
            payload["inspector"] = _run_inspector(root, project_id, selected_id, runs)
        else:
            payload["inspector"] = {
                "kind": "experiment_detail",
                "title": experiment.get("title") or experiment_id,
                "summary": experiment.get("question") or "",
                "sections": [
                    {"title": "Hypothesis", "kind": "text", "items": [{"text": experiment.get("hypothesis") or ""}]},
                    {"title": "Expected Evidence", "kind": "text", "items": [{"text": _metadata_text(experiment, "expected_evidence")}]},
                    {"title": "Risks", "kind": "risk_list", "items": [{"text": item} for item in _metadata_list(experiment, "risks")]},
                    {"title": "Runs", "kind": "run_list", "items": run_nodes},
                ],
                "actions": [],
            }
        payload["selected_id"] = selected_id
        return payload

    raise ValueError(f"unknown experiments layer: {layer}")
