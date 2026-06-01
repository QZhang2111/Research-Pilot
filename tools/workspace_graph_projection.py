#!/usr/bin/env python3
"""Project WorkspaceScene objects into render-ready graph contracts."""

from __future__ import annotations

from typing import Any

from tools.workspace_scene_contract import PROJECTION_SCHEMA_VERSION, validate_projected_graph


TERMINAL_ENTITY_TYPES = {"evidence", "warrant", "limitation", "run", "metric", "artifact"}
FORBIDDEN_PAYLOAD_FIELDS = {"canvas", "nodeTypes", "edgeTypes", "className"}


def build_projected_graph(scene: dict[str, Any]) -> dict[str, Any]:
    _reject_forbidden_fields(scene, "scene")
    nodes = [_project_node(scene, entity) for entity in scene.get("entities", [])]
    semantic_to_projected = {node["semantic_id"]: node["projected_id"] for node in nodes}
    projected = {
        "schema_version": PROJECTION_SCHEMA_VERSION,
        "project_id": scene["project_id"],
        "mode": scene["mode"],
        "layer": scene["layer"],
        "focus_id": scene.get("focus_id", ""),
        "breadcrumb": _breadcrumb(scene),
        "nodes": nodes,
        "edges": [_project_edge(relation, semantic_to_projected) for relation in scene.get("relations", [])],
        "frames": [_project_frame(group, semantic_to_projected) for group in scene.get("groups", [])],
        "portals": [_project_portal(portal, semantic_to_projected) for portal in scene.get("portals", [])],
        "inspector_default_id": _inspector_default_id(scene),
        "layout": {"kind": "layered", "direction": "vertical"},
        "warnings": list(scene.get("warnings") or []),
    }
    _validate_projection_edges(projected)
    return validate_projected_graph(projected)


def _project_node(scene: dict[str, Any], entity: dict[str, Any]) -> dict[str, Any]:
    _reject_forbidden_fields(entity, f"entity {entity.get('canonical_id', '')}")
    role = _node_role(scene, entity)
    return {
        "projected_id": f"node:{entity['canonical_id']}",
        "semantic_id": entity["canonical_id"],
        "role": role,
        "visual_kind": entity["entity_type"],
        "title": entity["title"],
        "display_id": entity["display_id"],
        "interaction": _interaction(scene, entity, role),
        "source": entity["source"],
        "layout_hints": _layout_hints(scene, entity, role),
    }


def _node_role(scene: dict[str, Any], entity: dict[str, Any]) -> str:
    if scene.get("focus_id") and entity["canonical_id"] == scene.get("focus_id"):
        return "anchor"
    if entity["entity_type"] in TERMINAL_ENTITY_TYPES:
        return "terminal"
    if entity["entity_type"] == "source" and "portalable" in set(entity.get("capabilities") or []):
        return "portal"
    return "entity"


def _interaction(scene: dict[str, Any], entity: dict[str, Any], role: str) -> dict[str, Any]:
    capabilities = set(entity.get("capabilities") or [])
    if role == "terminal":
        if "inspectable" in capabilities:
            return {"kind": "inspect", "inspector_id": entity["canonical_id"]}
        return {"kind": "none"}
    if "portalable" in capabilities:
        return {"kind": "portal", "target": _portal_target(scene, entity)}
    if _can_drill_to_claim_focus(scene, entity, capabilities):
        return {
            "kind": "drill",
            "target": {
                "mode": "understanding",
                "layer": "understanding.claim_focus",
                "focus_id": entity["canonical_id"],
            },
        }
    if _can_drill_to_source_focus(entity, capabilities):
        return {
            "kind": "drill",
            "target": {
                "mode": "understanding",
                "layer": "understanding.paper_focus",
                "focus_id": scene.get("focus_id", ""),
                "selected_id": entity["canonical_id"],
            },
        }
    if "inspectable" in capabilities:
        return {"kind": "inspect", "inspector_id": entity["canonical_id"]}
    return {"kind": "none"}


def _can_drill_to_claim_focus(scene: dict[str, Any], entity: dict[str, Any], capabilities: set[str]) -> bool:
    return (
        "drillable" in capabilities
        and entity["entity_type"] == "claim"
        and scene["layer"] == "understanding.project_overview"
    )


def _can_drill_to_source_focus(entity: dict[str, Any], capabilities: set[str]) -> bool:
    return "drillable" in capabilities and entity["entity_type"] == "source"


def _portal_target(scene: dict[str, Any], entity: dict[str, Any]) -> dict[str, str]:
    metadata = entity.get("metadata") or {}
    return {
        "mode": str(metadata.get("target_mode") or scene.get("mode") or ""),
        "layer": str(metadata.get("target_layer") or scene.get("layer") or ""),
        "focus_id": str(metadata.get("target_focus_id") or entity.get("canonical_id") or ""),
    }


def _layout_hints(scene: dict[str, Any], entity: dict[str, Any], role: str) -> dict[str, Any]:
    lane = ""
    for group in scene.get("groups", []):
        if entity["canonical_id"] in group.get("member_ids", []):
            lane = str(group.get("title") or "")
            break
    return {"role": role, "lane": lane}


def _project_edge(relation: dict[str, Any], semantic_to_projected: dict[str, str]) -> dict[str, Any]:
    _reject_forbidden_fields(relation, f"relation {relation.get('canonical_id', '')}")
    member_id = relation["canonical_id"]
    source_id = relation["source_id"]
    target_id = relation["target_id"]
    _require_projected_ref(source_id, semantic_to_projected, f"projected relation references missing entity: {member_id}")
    _require_projected_ref(target_id, semantic_to_projected, f"projected relation references missing entity: {member_id}")
    return {
        "projected_id": f"edge:{member_id}",
        "relation_type": relation["relation_type"],
        "source_id": semantic_to_projected[source_id],
        "target_id": semantic_to_projected[target_id],
        "label": relation["relation_type"],
        "member_relation_ids": [member_id],
        "aggregation": None,
        "source": relation["source"],
    }


def _project_frame(group: dict[str, Any], semantic_to_projected: dict[str, str]) -> dict[str, Any]:
    _reject_forbidden_fields(group, f"group {group.get('canonical_id', '')}")
    member_entity_ids = list(group.get("member_ids") or [])
    for member_id in member_entity_ids:
        _require_projected_ref(member_id, semantic_to_projected, f"projected frame references missing entity: {group['canonical_id']}")
    return {
        "projected_id": f"frame:{group['canonical_id']}",
        "semantic_id": group["canonical_id"],
        "frame_kind": group.get("group_type") or "frame",
        "title": group["title"],
        "member_entity_ids": member_entity_ids,
        "member_node_ids": [semantic_to_projected[member_id] for member_id in member_entity_ids],
        "interaction": {"kind": "none"},
        "source": group["source"],
    }


def _project_portal(portal: dict[str, Any], semantic_to_projected: dict[str, str]) -> dict[str, Any]:
    _reject_forbidden_fields(portal, f"portal {portal.get('canonical_id', '')}")
    from_id = portal.get("from_id", "")
    _require_projected_ref(from_id, semantic_to_projected, f"projected portal references missing entity: {portal['canonical_id']}")
    return {
        "projected_id": portal["canonical_id"],
        "from_node_id": semantic_to_projected[from_id],
        "label": portal.get("title") or "",
        "target": portal.get("target") or {},
        "source": portal["source"],
    }


def _breadcrumb(scene: dict[str, Any]) -> list[dict[str, str]]:
    items = [{"label": "Workspace", "mode": scene["mode"], "layer": scene["layer"], "focus_id": ""}]
    if scene.get("focus_id"):
        items.append(
            {
                "label": str(scene.get("focus_id")).rsplit(":", 1)[-1],
                "mode": scene["mode"],
                "layer": scene["layer"],
                "focus_id": scene["focus_id"],
            }
        )
    return items


def _inspector_default_id(scene: dict[str, Any]) -> str:
    inspector = scene.get("inspector") or {}
    return str(inspector.get("subject_id") or scene.get("focus_id") or "")


def _validate_projection_edges(projected: dict[str, Any]) -> None:
    for edge in projected["edges"]:
        if not edge.get("member_relation_ids"):
            raise ValueError("projected edges must retain member_relation_ids")
        source = edge.get("source") or {}
        if source.get("kind") not in {"db_row", "derived"}:
            raise ValueError("projected edge source.kind must be db_row or derived")


def _reject_forbidden_fields(payload: dict[str, Any], label: str) -> None:
    forbidden = FORBIDDEN_PAYLOAD_FIELDS & set(payload)
    if forbidden:
        raise ValueError(f"ProjectedGraph must not contain UI field: {sorted(forbidden)[0]} in {label}")


def _require_projected_ref(semantic_id: str, semantic_to_projected: dict[str, str], message: str) -> None:
    if semantic_id not in semantic_to_projected:
        raise ValueError(message)
