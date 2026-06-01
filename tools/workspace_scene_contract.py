#!/usr/bin/env python3
"""Workspace scene and projection contract helpers."""

from __future__ import annotations

from typing import Any


SCENE_SCHEMA_VERSION = "workspace-scene-v2"
PROJECTION_SCHEMA_VERSION = "workspace-projection-v1"
DB_SOURCE = "research-pilot.db"

V1_TO_V2_LAYER: dict[tuple[str, str], str] = {
    ("understanding", "project_overview"): "understanding.project_overview",
    ("understanding", "claim_focus"): "understanding.claim_focus",
    ("understanding", "paper_focus"): "understanding.paper_focus",
    ("literature", "literature_overview"): "literature.overview",
    ("literature", "literature_route_focus"): "literature.route_focus",
    ("literature", "literature_paper_focus"): "literature.paper_focus",
    ("experiments", "evaluation_overview"): "experiments.evaluation_overview",
    ("experiments", "evaluation_setting_focus"): "experiments.evaluation_setting_focus",
    ("experiments", "experiment_design_focus"): "experiments.experiment_design_focus",
}

DEFAULT_V1_LAYERS: dict[str, str] = {
    "understanding": "project_overview",
    "literature": "literature_overview",
    "experiments": "evaluation_overview",
}

SCENE_FORBIDDEN_FIELDS = {"canvas", "drill", "position", "display", "nodeTypes", "edgeTypes"}
ENTITY_FORBIDDEN_FIELDS = {"canvas", "drill", "position", "display", "style", "className"}
VALID_CAPABILITIES = {"inspectable", "drillable", "portalable", "none"}
VALID_PROJECTED_INTERACTIONS = {"none", "inspect", "drill", "portal"}
VALID_PROJECTED_ROLES = {"anchor", "entity", "terminal", "portal"}


def normalize_workspace_layer(mode: str, layer: str = "") -> str:
    normalized_mode = str(mode or "understanding").strip()
    normalized_layer = str(layer or DEFAULT_V1_LAYERS.get(normalized_mode, "")).strip()
    if "." in normalized_layer:
        return normalized_layer
    try:
        return V1_TO_V2_LAYER[(normalized_mode, normalized_layer)]
    except KeyError as exc:
        raise ValueError(f"unknown workspace layer: {normalized_mode}/{normalized_layer}") from exc


def canonical_source_id(source_id: str) -> str:
    value = str(source_id or "").strip()
    if not value:
        raise ValueError("source_id must be non-empty")
    return value if value.startswith("source:") else f"source:{value}"


def canonical_understanding_id(project_id: str, node_type: str, local_id: str) -> str:
    value = str(local_id or "").strip()
    if not value:
        raise ValueError("understanding local id must be non-empty")
    return f"understanding:project:{project_id}:{node_type}:{value}"


def db_row_source(table: str, primary_key: str) -> dict[str, str]:
    return {"kind": "db_row", "table": table, "primary_key": primary_key}


def derived_source(rule: str, inputs: list[Any]) -> dict[str, Any]:
    return {"kind": "derived", "rule": rule, "inputs": inputs}


def validate_workspace_scene(scene: dict[str, Any]) -> dict[str, Any]:
    if scene.get("schema_version") != SCENE_SCHEMA_VERSION:
        raise ValueError("WorkspaceScene schema_version must be workspace-scene-v2")
    forbidden = SCENE_FORBIDDEN_FIELDS & set(scene)
    if forbidden:
        raise ValueError(f"WorkspaceScene must not contain UI field: {sorted(forbidden)[0]}")
    for key in ("project_id", "mode", "layer", "source", "entities", "relations", "groups", "portals", "inspector", "warnings"):
        if key not in scene:
            raise ValueError(f"WorkspaceScene missing required field: {key}")
    for entity in scene.get("entities", []):
        forbidden_entity = ENTITY_FORBIDDEN_FIELDS & set(entity)
        if forbidden_entity:
            raise ValueError(f"WorkspaceScene entity must not contain UI field: {sorted(forbidden_entity)[0]}")
        for key in ("canonical_id", "display_id", "entity_type", "title", "capabilities", "source"):
            if key not in entity:
                raise ValueError(f"WorkspaceScene entity missing required field: {key}")
        capabilities = set(entity.get("capabilities") or [])
        if not capabilities <= VALID_CAPABILITIES:
            raise ValueError("WorkspaceScene entity has invalid capability")
        source = entity.get("source") or {}
        if source.get("kind") not in {"db_row", "derived"}:
            raise ValueError("WorkspaceScene entity source.kind must be db_row or derived")
    for relation in scene.get("relations", []):
        for key in ("canonical_id", "relation_type", "source_id", "target_id", "source"):
            if key not in relation:
                raise ValueError(f"WorkspaceScene relation missing required field: {key}")
    for group in scene.get("groups", []):
        source = group.get("source") or {}
        if source.get("kind") != "derived":
            raise ValueError("WorkspaceScene groups must be derived")
    return scene


def validate_projected_graph(projected: dict[str, Any]) -> dict[str, Any]:
    if projected.get("schema_version") != PROJECTION_SCHEMA_VERSION:
        raise ValueError("ProjectedGraph schema_version must be workspace-projection-v1")
    for key in ("project_id", "mode", "layer", "nodes", "edges", "frames", "portals", "layout", "warnings"):
        if key not in projected:
            raise ValueError(f"ProjectedGraph missing required field: {key}")
    for node in projected.get("nodes", []):
        role = node.get("role")
        if role not in VALID_PROJECTED_ROLES:
            raise ValueError("ProjectedGraph node has invalid role")
        interaction = node.get("interaction") or {}
        kind = interaction.get("kind")
        if kind not in VALID_PROJECTED_INTERACTIONS:
            raise ValueError("ProjectedGraph node has invalid interaction")
        if role == "terminal" and kind == "drill":
            raise ValueError("terminal projected nodes must not drill")
        for key in ("projected_id", "semantic_id", "visual_kind", "title", "display_id", "source"):
            if key not in node:
                raise ValueError(f"ProjectedGraph node missing required field: {key}")
    for edge in projected.get("edges", []):
        if edge.get("aggregation") and not edge.get("member_relation_ids"):
            raise ValueError("aggregated projected edges must retain member_relation_ids")
    return projected
