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
    ("experiments", "evaluation_arena_focus"): "experiments.evaluation_arena_focus",
    ("experiments", "evaluation_setting_focus"): "experiments.evaluation_arena_focus",
    ("experiments", "experiment_design_focus"): "experiments.experiment_design_focus",
}

DEFAULT_V1_LAYERS: dict[str, str] = {
    "understanding": "project_overview",
    "literature": "literature_overview",
    "experiments": "evaluation_overview",
}

SCENE_FORBIDDEN_FIELDS = {"canvas", "drill", "position", "display", "nodeTypes", "edgeTypes"}
ENTITY_FORBIDDEN_FIELDS = {"canvas", "drill", "position", "display", "style", "className"}
RELATION_FORBIDDEN_FIELDS = ENTITY_FORBIDDEN_FIELDS
GROUP_FORBIDDEN_FIELDS = ENTITY_FORBIDDEN_FIELDS
PORTAL_FORBIDDEN_FIELDS = ENTITY_FORBIDDEN_FIELDS
VALID_CAPABILITIES = {"inspectable", "drillable", "portalable", "none"}
VALID_PROJECTED_INTERACTIONS = {"none", "inspect", "drill", "portal"}
VALID_PROJECTED_ROLES = {"anchor", "entity", "terminal", "portal"}
VALID_SOURCE_KINDS = {"db_row", "derived"}


def normalize_workspace_layer(mode: str, layer: str = "") -> str:
    normalized_mode = str(mode or "understanding").strip()
    if normalized_mode not in DEFAULT_V1_LAYERS:
        raise ValueError(f"unknown workspace mode: {normalized_mode}")
    normalized_layer = str(layer or DEFAULT_V1_LAYERS.get(normalized_mode, "")).strip()
    if "." in normalized_layer:
        layer_mode = normalized_layer.split(".", 1)[0]
        if layer_mode != normalized_mode:
            raise ValueError(f"workspace layer mode mismatch: {normalized_mode}/{normalized_layer}")
        if normalized_layer not in set(V1_TO_V2_LAYER.values()):
            raise ValueError(f"unknown workspace layer: {normalized_mode}/{normalized_layer}")
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
        _validate_source_kind(entity.get("source") or {}, "WorkspaceScene entity")
    for relation in scene.get("relations", []):
        _reject_forbidden_contract_fields(relation, RELATION_FORBIDDEN_FIELDS, "WorkspaceScene relation")
        for key in ("canonical_id", "relation_type", "source_id", "target_id", "source"):
            if key not in relation:
                raise ValueError(f"WorkspaceScene relation missing required field: {key}")
        _validate_source_kind(relation.get("source") or {}, "WorkspaceScene relation")
    for group in scene.get("groups", []):
        _reject_forbidden_contract_fields(group, GROUP_FORBIDDEN_FIELDS, "WorkspaceScene group")
        source = group.get("source") or {}
        if source.get("kind") != "derived":
            raise ValueError("WorkspaceScene groups must be derived")
    for portal in scene.get("portals", []):
        _reject_forbidden_contract_fields(portal, PORTAL_FORBIDDEN_FIELDS, "WorkspaceScene portal")
        if "source" not in portal:
            raise ValueError("WorkspaceScene portal missing required field: source")
        _validate_source_kind(portal.get("source") or {}, "WorkspaceScene portal")
    return scene


def validate_projected_graph(projected: dict[str, Any]) -> dict[str, Any]:
    if projected.get("schema_version") != PROJECTION_SCHEMA_VERSION:
        raise ValueError("ProjectedGraph schema_version must be workspace-projection-v1")
    for key in ("project_id", "mode", "layer", "nodes", "edges", "frames", "portals", "layout", "warnings"):
        if key not in projected:
            raise ValueError(f"ProjectedGraph missing required field: {key}")
    projected_node_ids = {str(node.get("projected_id") or "") for node in projected.get("nodes", [])}
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
        _validate_source_kind(node.get("source") or {}, "ProjectedGraph node")
    for edge in projected.get("edges", []):
        if edge.get("aggregation") and not edge.get("member_relation_ids"):
            raise ValueError("aggregated projected edges must retain member_relation_ids")
        if edge.get("source_id") not in projected_node_ids or edge.get("target_id") not in projected_node_ids:
            raise ValueError("projected edge references missing node")
        _validate_source_kind(edge.get("source") or {}, "ProjectedGraph edge")
    for frame in projected.get("frames", []):
        for member_node_id in frame.get("member_node_ids") or []:
            if member_node_id not in projected_node_ids:
                raise ValueError("projected frame references missing node")
        _validate_source_kind(frame.get("source") or {}, "ProjectedGraph frame")
    for portal in projected.get("portals", []):
        if portal.get("from_node_id") not in projected_node_ids:
            raise ValueError("projected portal references missing node")
        _validate_source_kind(portal.get("source") or {}, "ProjectedGraph portal")
    return projected


def _validate_source_kind(source: dict[str, Any], label: str) -> None:
    if source.get("kind") not in VALID_SOURCE_KINDS:
        raise ValueError(f"{label} source.kind must be db_row or derived")


def _reject_forbidden_contract_fields(payload: dict[str, Any], forbidden_fields: set[str], label: str) -> None:
    forbidden = forbidden_fields & set(payload)
    if forbidden:
        raise ValueError(f"{label} must not contain UI field: {sorted(forbidden)[0]}")
