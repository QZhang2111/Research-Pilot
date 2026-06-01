#!/usr/bin/env python3
"""Understanding mode WorkspaceScene builders."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tools.research_dataset_read_models import build_project_graph_model, build_sources_model
from tools.workspace_scene_builders.provenance import db_row, derived
from tools.workspace_scene_contract import (
    DB_SOURCE,
    SCENE_SCHEMA_VERSION,
    canonical_source_id,
    canonical_understanding_id,
)


def build_understanding_scene(
    root: Path,
    project_id: str,
    layer: str,
    *,
    focus_id: str = "",
    selected_id: str = "",
) -> dict[str, Any]:
    graph = build_project_graph_model(root, project_id)
    if layer == "understanding.project_overview":
        return _project_overview_scene(project_id, graph, selected_id=selected_id)
    if layer == "understanding.claim_focus":
        return _claim_focus_scene(root, project_id, graph, focus_id=focus_id, selected_id=selected_id)
    raise ValueError(f"workspace-scene-v2 not implemented for layer: {layer}")


def _base_scene(project_id: str, layer: str, focus_id: str = "") -> dict[str, Any]:
    return {
        "schema_version": SCENE_SCHEMA_VERSION,
        "project_id": project_id,
        "mode": "understanding",
        "layer": layer,
        "focus_id": focus_id,
        "source": DB_SOURCE,
        "entities": [],
        "relations": [],
        "groups": [],
        "portals": [],
        "inspector": {},
        "warnings": [],
    }


def _project_overview_scene(project_id: str, graph: dict[str, Any], *, selected_id: str = "") -> dict[str, Any]:
    scene = _base_scene(project_id, "understanding.project_overview")
    scene["entities"] = [
        _understanding_entity(project_id, node)
        for node in graph.get("nodes", [])
        if node.get("kind") in {"question", "claim"}
    ]
    visible_ids = {entity["canonical_id"] for entity in scene["entities"]}
    scene["relations"] = [
        relation
        for relation in _understanding_relations(project_id, graph)
        if relation["source_id"] in visible_ids and relation["target_id"] in visible_ids
    ]
    scene["groups"] = [
        _derived_group(
            "understanding.project_overview",
            "questions",
            "Questions",
            [entity["canonical_id"] for entity in scene["entities"] if entity["entity_type"] == "question"],
        ),
        _derived_group(
            "understanding.project_overview",
            "claims",
            "Claims",
            [entity["canonical_id"] for entity in scene["entities"] if entity["entity_type"] == "claim"],
        ),
    ]
    scene["inspector"] = {"kind": "overview", "subject_id": selected_id, "title": "Questions"}
    return scene


def _claim_focus_scene(root: Path, project_id: str, graph: dict[str, Any], *, focus_id: str, selected_id: str = "") -> dict[str, Any]:
    claim = _node_by_focus_id(project_id, graph, focus_id)
    if not claim or claim.get("kind") != "claim":
        raise ValueError(f"unknown claim focus: {focus_id}")

    focus_canonical_id = _entity_id(project_id, claim)
    scene = _base_scene(project_id, "understanding.claim_focus", focus_canonical_id)
    related_nodes = _claim_related_nodes(graph, claim)
    source_entities = _source_entities_for_nodes(root, project_id, [claim, *related_nodes])
    scene["entities"] = [
        _understanding_entity(project_id, claim, force_capabilities=["inspectable"]),
        *[
            _understanding_entity(project_id, node, force_capabilities=["inspectable"])
            for node in related_nodes
            if node.get("kind") in {"evidence", "warrant", "limitation"}
        ],
        *source_entities,
    ]
    visible_ids = {entity["canonical_id"] for entity in scene["entities"]}
    scene["relations"] = [
        relation
        for relation in _understanding_relations(project_id, graph)
        if relation["source_id"] in visible_ids and relation["target_id"] in visible_ids
    ]
    scene["groups"] = [
        _derived_group(
            "understanding.claim_focus",
            "evidence",
            "Evidence / Grounds",
            [entity["canonical_id"] for entity in scene["entities"] if entity["entity_type"] == "evidence"],
            focus_canonical_id,
        ),
        _derived_group(
            "understanding.claim_focus",
            "warrants",
            "Warrants / Bridges",
            [entity["canonical_id"] for entity in scene["entities"] if entity["entity_type"] == "warrant"],
            focus_canonical_id,
        ),
        _derived_group(
            "understanding.claim_focus",
            "limitations",
            "Limitations / Boundaries",
            [entity["canonical_id"] for entity in scene["entities"] if entity["entity_type"] == "limitation"],
            focus_canonical_id,
        ),
        _derived_group(
            "understanding.claim_focus",
            "sources",
            "Source Papers",
            [entity["canonical_id"] for entity in scene["entities"] if entity["entity_type"] == "source"],
            focus_canonical_id,
        ),
    ]
    scene["inspector"] = {"kind": "claim_detail", "subject_id": selected_id or focus_canonical_id, "title": _local_id(claim)}
    return scene


def _understanding_entity(project_id: str, node: dict[str, Any], force_capabilities: list[str] | None = None) -> dict[str, Any]:
    kind = str(node.get("kind") or "")
    local_id = _local_id(node)
    capabilities = force_capabilities or (["inspectable", "drillable"] if kind == "claim" else ["inspectable"])
    return {
        "canonical_id": canonical_understanding_id(project_id, kind, local_id),
        "display_id": local_id,
        "entity_type": kind,
        "title": node.get("label") or local_id,
        "summary": node.get("subtitle") or "",
        "status": node.get("status") or "",
        "confidence": node.get("confidence") or "",
        "capabilities": capabilities,
        "source": db_row("understanding_nodes", str(node.get("id") or "")),
        "metadata": node.get("metadata") or {},
    }


def _source_entities_for_nodes(root: Path, project_id: str, nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sources = build_sources_model(root, project_id).get("sources", [])
    by_key: dict[str, dict[str, Any]] = {}
    for source in sources:
        for key in (source.get("source_id"), source.get("locator"), source.get("title"), source.get("url"), source.get("doi"), source.get("arxiv_id")):
            if key:
                by_key[str(key)] = source

    result = []
    seen: set[str] = set()
    for node in nodes:
        for ref in node.get("source_refs") or []:
            source = by_key.get(str(ref))
            if not source:
                continue
            source_id = str(source.get("source_id") or "")
            if not source_id or source_id in seen:
                continue
            seen.add(source_id)
            result.append(
                {
                    "canonical_id": canonical_source_id(source_id),
                    "display_id": source_id,
                    "entity_type": "source",
                    "title": source.get("title") or source_id,
                    "summary": source.get("short_summary") or "",
                    "status": source.get("reading_status") or "",
                    "confidence": "",
                    "capabilities": ["inspectable", "drillable"],
                    "source": db_row("sources", source_id),
                    "metadata": source,
                }
            )
    return result


def _understanding_relations(project_id: str, graph: dict[str, Any]) -> list[dict[str, Any]]:
    by_db_id = {node["id"]: node for node in graph.get("nodes", [])}
    relations = []
    for link in graph.get("links", []):
        relation_type = str(link.get("relation") or "related")
        targets = link.get("target") or []
        sources = link.get("premises") or link.get("source") or []
        for source_db_id in sources:
            for target_db_id in targets:
                source = by_db_id.get(source_db_id)
                target = by_db_id.get(target_db_id)
                if not source or not target:
                    continue
                relations.append(
                    {
                        "canonical_id": f"relation:project:{project_id}:{_local_id_from_value(link.get('id'))}:{_local_id(source)}:{_local_id(target)}",
                        "relation_type": relation_type,
                        "source_id": _entity_id(project_id, source),
                        "target_id": _entity_id(project_id, target),
                        "direction": "forward",
                        "weight": 1,
                        "source": db_row("understanding_links", str(link.get("id") or "")),
                    }
                )
    return relations


def _claim_related_nodes(graph: dict[str, Any], claim: dict[str, Any]) -> list[dict[str, Any]]:
    by_db_id = {node["id"]: node for node in graph.get("nodes", [])}
    claim_db_id = claim.get("id")
    related_ids: set[str] = set()
    for link in graph.get("links", []):
        targets = set(link.get("target") or [])
        sources = set(link.get("premises") or link.get("source") or [])
        warrants = set(link.get("warrant") or [])
        limitations = set(link.get("limitations") or [])
        if claim_db_id in targets:
            related_ids.update(sources | warrants | limitations)
        if claim_db_id in sources:
            related_ids.update(targets | warrants | limitations)
    return [by_db_id[node_id] for node_id in sorted(related_ids) if node_id in by_db_id and node_id != claim_db_id]


def _derived_group(layer: str, slug: str, title: str, member_ids: list[str], focus_id: str = "") -> dict[str, Any]:
    inputs = [focus_id] if focus_id else list(member_ids)
    return {
        "canonical_id": f"derived:group:{layer}:{slug}",
        "group_type": "lane",
        "title": title,
        "member_ids": member_ids,
        "visual_role": "frame",
        "source": derived(f"{title} members for {layer}", inputs),
    }


def _node_by_focus_id(project_id: str, graph: dict[str, Any], focus_id: str) -> dict[str, Any] | None:
    for node in graph.get("nodes", []):
        candidates = {
            str(node.get("id") or ""),
            f"{node.get('kind')}:{_local_id(node)}",
            _entity_id(project_id, node),
        }
        if focus_id in candidates:
            return node
    return None


def _entity_id(project_id: str, node: dict[str, Any]) -> str:
    return canonical_understanding_id(project_id, str(node.get("kind") or ""), _local_id(node))


def _local_id(node: dict[str, Any]) -> str:
    metadata = node.get("metadata") or {}
    return str(metadata.get("local_id") or _local_id_from_value(node.get("id")))


def _local_id_from_value(value: Any) -> str:
    return str(value or "").rsplit(":", 1)[-1]
