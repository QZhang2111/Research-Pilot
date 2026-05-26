#!/usr/bin/env python3
"""Workspace graph read model skeleton backed by research-pilot.db."""

from __future__ import annotations

import json
import re
import sqlite3
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


def _build_literature(root: Path, project_id: str, layer: str, focus_id: str, selected_id: str) -> dict[str, Any]:
    raise NotImplementedError


def _build_experiments(root: Path, project_id: str, layer: str, focus_id: str, selected_id: str) -> dict[str, Any]:
    raise NotImplementedError
