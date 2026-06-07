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
    "experiments": {"evaluation_overview", "evaluation_arena_focus", "evaluation_setting_focus", "experiment_design_focus"},
}
MODE_ROOT_LABELS = {
    "understanding": "Understanding",
    "literature": "Literature",
    "experiments": "Experiments",
}
ENTITY_DISPLAY = {
    "question": {"tone": "question", "label": "Question"},
    "claim": {"tone": "claim", "label": "Claim"},
    "evidence": {"tone": "evidence", "label": "Evidence"},
    "warrant": {"tone": "warrant", "label": "Warrant"},
    "limitation": {"tone": "limitation", "label": "Limitation"},
    "source": {"tone": "source", "label": "Source"},
    "paper": {"tone": "source", "label": "Paper"},
    "literature_lane": {"tone": "source", "label": "Literature Lane"},
    "evaluation_setting": {"tone": "claim", "label": "Evaluation Setting"},
    "evaluation_arena": {"tone": "claim", "label": "Evaluation Arena"},
    "experiment": {"tone": "evidence", "label": "Experiment"},
    "run": {"tone": "run", "label": "Run"},
    "dataset": {"tone": "source", "label": "Dataset"},
    "benchmark": {"tone": "source", "label": "Benchmark"},
    "metric_family": {"tone": "warrant", "label": "Metric Family"},
    "model": {"tone": "warrant", "label": "Model"},
    "baseline": {"tone": "limitation", "label": "Baseline"},
    "protocol": {"tone": "warrant", "label": "Protocol"},
    "project_claim_anchor": {"tone": "claim", "label": "Project Claim"},
    "paper_question": {"tone": "question", "label": "Paper Question"},
    "paper_claim": {"tone": "claim", "label": "Paper Claim"},
    "paper_evidence": {"tone": "evidence", "label": "Paper Evidence"},
    "paper_warrant": {"tone": "warrant", "label": "Paper Warrant"},
    "paper_limitation": {"tone": "limitation", "label": "Paper Limitation"},
}

ROLE_BADGE_ALLOWLIST = {
    ("question", "framing"): {"key": "question_role", "label": "Framing", "tone": "question"},
    ("question", "primary"): {"key": "question_role", "label": "Primary", "tone": "question"},
    ("question", "validation"): {"key": "question_role", "label": "Validation", "tone": "question"},
    ("claim", "central thesis"): {"key": "claim_role", "label": "Central Thesis", "tone": "claim"},
    ("claim", "geometry primitive"): {"key": "claim_role", "label": "Geometry Primitive", "tone": "claim"},
    ("claim", "interaction primitive"): {"key": "claim_role", "label": "Interaction Primitive", "tone": "claim"},
    ("claim", "mechanistic bridge"): {"key": "claim_role", "label": "Mechanistic Bridge", "tone": "claim"},
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
    if mode == "experiments" and layer == "evaluation_setting_focus":
        layer = "evaluation_arena_focus"
    if mode == "understanding":
        model = _build_understanding(root, project_id, layer, focus_id, selected_id)
    elif mode == "literature":
        model = _build_literature(root, project_id, layer, focus_id, selected_id)
    else:
        model = _build_experiments(root, project_id, layer, focus_id, selected_id)
    return _finalize_payload(model)


def _base_payload(project_id: str, mode: str, layer: str, focus_id: str = "", selected_id: str = "") -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "source": DB_SOURCE,
        "project_id": project_id,
        "mode": mode,
        "layer": layer,
        "focus_id": focus_id,
        "selected_id": selected_id,
        "breadcrumb": [_mode_root_crumb(mode)],
        "canvas": {"layout_hint": "island", "nodes": [], "edges": []},
        "inspector": {"kind": "overview", "title": "", "summary": "", "sections": [], "actions": []},
        "available_layers": sorted(VALID_LAYERS[mode]),
        "cross_mode_jumps": [],
        "empty_state": None,
        "warnings": [],
    }


def _mode_root_crumb(mode: str) -> dict[str, Any]:
    return {"label": MODE_ROOT_LABELS.get(mode, mode.title()), "mode": mode, "layer": DEFAULT_LAYERS[mode], "focus_id": ""}


def _breadcrumb(mode: str, *crumbs: dict[str, Any]) -> list[dict[str, Any]]:
    return [_mode_root_crumb(mode), *crumbs]


def _json_loads(value: Any, fallback: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(str(value or ""))
    except (TypeError, json.JSONDecodeError):
        return fallback


def _display_for_entity(entity_type: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    metadata = metadata if isinstance(metadata, dict) else {}
    entity = ENTITY_DISPLAY.get(entity_type, {"tone": "unknown", "label": entity_type or "Node"})
    badges = [{"key": "entity_type", "label": entity["label"], "tone": entity["tone"]}]
    warnings = []
    raw_role = str(metadata.get("role") or "").strip().lower()
    if raw_role:
        role_badge = ROLE_BADGE_ALLOWLIST.get((entity_type, raw_role))
        if role_badge:
            badges.append(dict(role_badge))
        else:
            warnings.append("Unsupported metadata.role was not rendered.")
    return {"tone": entity["tone"], "badges": badges, "warnings": warnings}


def _normalize_node_display(node: dict[str, Any]) -> dict[str, Any]:
    entity_type = str(node.get("entity_type") or "unknown")
    metadata = node.get("metadata") if isinstance(node.get("metadata"), dict) else {}
    existing_display = node.get("display") if isinstance(node.get("display"), dict) else {}
    node["metadata"] = metadata
    display = _display_for_entity(entity_type, metadata)
    if existing_display.get("tone"):
        display["tone"] = str(existing_display["tone"])
    node["display"] = display
    return node


def _finalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    warnings = list(payload.get("warnings") or [])
    for node in payload.get("canvas", {}).get("nodes", []):
        _normalize_node_display(node)
        for warning in node["display"]["warnings"]:
            warnings.append({"node_id": node.get("id", ""), "message": warning})
    payload["warnings"] = warnings
    return payload


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


def _display_title(*records: dict[str, Any] | None, fallback: str = "Item") -> str:
    for record in records:
        if not isinstance(record, dict):
            continue
        for key in ("title", "label", "name", "run_label", "id"):
            value = str(record.get(key) or "").strip()
            if value:
                return value
    return fallback


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
    inspector = {"selected_id": graph_id} if kind in {"question", "evidence", "warrant", "limitation"} else None
    result = {
        "id": graph_id,
        "entity_type": kind,
        "db_id": node.get("id", ""),
        "local_id": local_id,
        "label": node.get("label") or node.get("text") or local_id,
        "subtitle": node.get("subtitle") or node.get("status") or "",
        "status": node.get("status") or "",
        "confidence": node.get("confidence") or "",
        "selected": graph_id == selected_id,
        "metadata": node.get("metadata") or {},
    }
    if drill:
        result["drill"] = drill
    if inspector:
        result["inspector"] = inspector
    return result


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


def _argument_atom_detail(selected_id: str, related_nodes: list[dict[str, Any]], source_nodes: list[dict[str, Any]]) -> dict[str, Any] | None:
    selected_node = next(
        (
            node
            for node in related_nodes
            if node.get("kind") in {"evidence", "warrant", "limitation"}
            and _node_graph_id(str(node.get("kind") or ""), node) == selected_id
        ),
        None,
    )
    if not selected_node:
        return None
    source_refs = [str(ref) for ref in selected_node.get("source_refs") or [] if str(ref).strip()]
    matched_sources = []
    for source_node in source_nodes:
        metadata = source_node.get("metadata") if isinstance(source_node.get("metadata"), dict) else {}
        source_keys = {
            str(source_node.get("source_id") or ""),
            str(source_node.get("path") or ""),
            str(source_node.get("label") or ""),
            str(metadata.get("source_id") or ""),
            str(metadata.get("locator") or ""),
            str(metadata.get("title") or ""),
            str(metadata.get("url") or ""),
            str(metadata.get("doi") or ""),
            str(metadata.get("arxiv_id") or ""),
        }
        if any(ref in source_keys for ref in source_refs):
            matched_sources.append(source_node)
    sections = [
        {
            "title": "Source Refs",
            "kind": "source_refs",
            "items": [{"id": ref, "label": ref} for ref in source_refs],
        }
    ]
    if matched_sources:
        sections.append({"title": "Related Source Papers", "kind": "sources", "items": matched_sources})
    return {
        "kind": "argument_atom_detail",
        "title": _node_local_id(selected_node),
        "summary": selected_node.get("label") or "",
        "sections": sections,
        "actions": [],
    }


def _paper_layer_node(source_id: str, node: dict[str, Any]) -> dict[str, Any]:
    node_id = str(node.get("id") or "")
    return {
        "id": f"paper_node:{source_id}:{node_id}",
        "entity_type": f"paper_{node.get('kind', 'node')}",
        "db_id": node_id,
        "local_id": node_id,
        "label": node.get("label") or node_id,
        "subtitle": node.get("subtitle") or node.get("kind") or "",
        "status": "",
        "confidence": "",
        "drill": None,
        "inspector": {"selected_id": f"paper_node:{source_id}:{node_id}"},
        "metadata": node,
    }


def _paper_layer_edges(source_id: str, paper_graph: dict[str, Any], claim_id: str = "") -> list[dict[str, Any]]:
    edges = [
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
    if not claim_id:
        return edges
    claim_local_id = _strip_prefix(claim_id, "claim:")
    edges.extend(
        {
            "id": f"translation_edge:{source_id}:{translation.get('id')}:{paper_node_id}:{claim_id}",
            "source": f"paper_node:{source_id}:{paper_node_id}",
            "target": claim_id,
            "relation": "translation",
            "label": "translation",
            "metadata": translation,
        }
        for translation in paper_graph.get("translations", [])
        if not translation.get("project_nodes")
        or claim_local_id in [str(node_id) for node_id in translation.get("project_nodes", [])]
        for paper_node_id in translation.get("paper_nodes", [])
    )
    return edges


PAPER_BRIEF_SECTION_MAP = {
    "core contribution": "Core Contribution",
    "evidence relevant to demo pug": "Evidence Boundary",
    "limitations / what not to infer": "What Not To Overlearn",
    "5. method mechanism": "Method View",
    "6. experiment logic": "Experiment Logic",
    "8. position for the target project": "Project Consequence",
    "9. what not to learn": "What Not To Overlearn",
}


def _markdown_sections(text: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current = ""
    for line in text.splitlines():
        if line.startswith("### "):
            current = line[4:].strip().lower()
            sections.setdefault(current, [])
            continue
        if current:
            sections[current].append(line)
    return {key: "\n".join(value).strip() for key, value in sections.items() if "\n".join(value).strip()}


def _paper_dossier_brief(root: Path, source: dict[str, Any]) -> list[dict[str, str]]:
    locator = source.get("locator") or source.get("path") or ""
    if not locator:
        return []
    root_path = Path(root).resolve()
    locator_path = Path(str(locator))
    if locator_path.is_absolute():
        return []
    path = (root_path / locator_path).resolve()
    try:
        path.relative_to(root_path)
    except ValueError:
        return []
    if not path.exists():
        return []
    sections = _markdown_sections(path.read_text(encoding="utf-8"))
    brief = []
    seen_labels: set[str] = set()
    for source_heading, label in PAPER_BRIEF_SECTION_MAP.items():
        text = sections.get(source_heading, "")
        if not text or label in seen_labels:
            continue
        seen_labels.add(label)
        brief.append({"label": label, "text": text})
    return brief


def _paper_layer_inspector(
    root: Path,
    paper_graph: dict[str, Any],
    source: dict[str, Any],
    source_id: str,
    summary: str,
    extra_sections: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    brief_items = _paper_dossier_brief(root, source)
    sections = []
    if brief_items:
        sections.append({"title": "Paper Brief", "kind": "paper_brief", "items": brief_items})
    sections.extend(extra_sections or [])
    sections.extend(
        [
            {"title": "Paper Argument Nodes", "kind": "paper_node_list", "items": paper_graph.get("nodes", [])},
            {"title": "Translation Bridge", "kind": "translation_bridge", "items": paper_graph.get("translations", [])},
        ]
    )
    return {
        "kind": "paper_focus",
        "title": paper_graph.get("title") or source.get("title") or source_id,
        "summary": summary,
        "sections": sections,
        "actions": [],
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
        payload["breadcrumb"] = _breadcrumb(
            "understanding",
            {
                "label": _node_local_id(claim) or claim_id,
                "mode": "understanding",
                "layer": "claim_focus",
                "focus_id": claim_id,
                "selected_id": "",
            },
        )
        canvas_related_nodes = [node for node in related_nodes if node.get("kind") != "claim"]
        payload["canvas"]["nodes"] = [
            _understanding_node(claim, selected_id=claim_id),
            *[_understanding_node(node, selected_id=selected_id) for node in canvas_related_nodes],
            *source_nodes,
        ]
        related_ids = {node["id"] for node in payload["canvas"]["nodes"]}
        payload["canvas"]["edges"] = [edge for edge in _understanding_edges(graph) if edge["source"] in related_ids and edge["target"] in related_ids]
        payload["inspector"] = _argument_atom_detail(selected_id, related_nodes, source_nodes) or _claim_detail(claim, related_nodes, source_nodes)
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
        payload["breadcrumb"] = _breadcrumb(
            "understanding",
            {
                "label": _node_local_id(claim) or claim_id,
                "mode": "understanding",
                "layer": "claim_focus",
                "focus_id": claim_id,
                "selected_id": "",
            },
            {
                "label": _display_title(paper_graph, source, fallback=source_id),
                "mode": "understanding",
                "layer": "paper_focus",
                "focus_id": claim_id,
                "selected_id": selected_id,
            },
        )
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
            *[_paper_layer_node(source_id, node) for node in paper_graph.get("nodes", [])],
        ]
        payload["canvas"]["edges"] = _paper_layer_edges(source_id, paper_graph, claim_id)
        payload["inspector"] = _paper_layer_inspector(
            root,
            paper_graph,
            source,
            source_id,
            "Paper argument layer projected beside the selected project claim.",
        )
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


def _literature_route_key(route: dict[str, Any]) -> str:
    metadata = route.get("metadata") if isinstance(route.get("metadata"), dict) else {}
    return str(metadata.get("id") or route.get("route") or _local_id(_literature_route_raw_id(route)) or _literature_route_raw_id(route))


def _literature_route_index_lookup(routes: list[dict[str, Any]]) -> dict[str, int]:
    lookup: dict[str, int] = {}
    for index, route in enumerate(routes):
        raw_id = _literature_route_raw_id(route)
        local_id = _literature_route_key(route)
        for key in {raw_id, local_id, _slug(raw_id), _slug(local_id)}:
            if key:
                lookup[str(key)] = index
    return lookup


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


def _literature_paper_route_key(paper: dict[str, Any]) -> str:
    return str(paper.get("route") or _local_id(str(paper.get("lane_id") or "")) or paper.get("lane_id") or "")


def _literature_route_for_paper(paper: dict[str, Any], routes: list[dict[str, Any]]) -> dict[str, Any] | None:
    paper_route_key = _literature_paper_route_key(paper)
    route_ids = {str(value) for value in (paper.get("route_ids") or []) if str(value).strip()}
    for route in routes:
        route_key = _literature_route_key(route)
        route_local_id = _literature_route_local_id(route)
        if paper_route_key == route_key or route_local_id in route_ids:
            return route
    return None


def _literature_route_crumb(route: dict[str, Any]) -> dict[str, Any]:
    route_raw_id = _literature_route_raw_id(route)
    graph_id = _literature_node_id("literature_lane", route_raw_id)
    return {
        "label": _display_title(route, fallback=_literature_route_local_id(route) or "Route"),
        "mode": "literature",
        "layer": "literature_route_focus",
        "focus_id": graph_id,
        "selected_id": "",
    }


def _literature_paper_crumb(paper: dict[str, Any], source: dict[str, Any] | None, focus_id: str) -> dict[str, Any]:
    source_key = _strip_prefix(focus_id, "source:")
    return {
        "label": _display_title(paper, source, fallback=source_key),
        "mode": "literature",
        "layer": "literature_paper_focus",
        "focus_id": focus_id,
        "selected_id": focus_id,
    }


def _literature_paper_sort_year(paper: dict[str, Any]) -> int:
    for value in (paper.get("year"), paper.get("id"), paper.get("source_id"), paper.get("item_id"), paper.get("title")):
        if value is None:
            continue
        match = re.search(r"(19|20)\d{2}", str(value))
        if match:
            return int(match.group(0))
    return 9999


def _literature_paper_sort_month(paper: dict[str, Any]) -> int:
    try:
        return max(1, min(12, int(str(paper.get("month") or "12"))))
    except ValueError:
        return 12


def _literature_paper_node(paper: dict[str, Any], *, drill: bool = True, route_indexes: dict[str, int] | None = None) -> dict[str, Any]:
    source_id = _literature_paper_source_id(paper)
    graph_id = _source_graph_id(source_id)
    route_key = _literature_paper_route_key(paper)
    route_index = (route_indexes or {}).get(route_key, 0)
    metadata = dict(paper)
    metadata["route_key"] = route_key
    metadata["route_index"] = route_index
    metadata["sort_year"] = _literature_paper_sort_year(paper)
    metadata["sort_month"] = _literature_paper_sort_month(paper)
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
        "metadata": metadata,
        "display": {"tone": f"route-{route_index % 6}"},
    }


def _build_literature(root: Path, project_id: str, layer: str, focus_id: str, selected_id: str) -> dict[str, Any]:
    model = build_literature_model(root, project_id)
    payload = _base_payload(project_id, "literature", layer, focus_id, selected_id)
    routes = model.get("routes") or []
    papers = model.get("papers") or []
    edges = model.get("explicit_edges") or []
    paper_by_key = _literature_paper_lookup(papers)
    route_indexes = _literature_route_index_lookup(routes)

    if layer == "literature_overview" and not routes and not papers:
        payload["empty_state"] = {
            "title": "No literature structure",
            "message": "No literature structure has been recorded for this project yet.",
        }
        payload["inspector"] = {
            "kind": "overview",
            "title": "Literature Routes",
            "summary": "No literature structure has been recorded.",
            "sections": [],
            "actions": [],
        }
        return payload

    if layer == "literature_overview":
        nodes = []
        for route_index, route in enumerate(routes):
            route_id = _literature_route_raw_id(route)
            graph_id = _literature_node_id("literature_lane", route_id)
            route_key = _literature_route_key(route)
            route_metadata = dict(route)
            route_metadata["route_key"] = route_key
            route_metadata["route_index"] = route_index
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
                    "metadata": route_metadata,
                    "display": {"tone": f"route-{route_index % 6}"},
                }
            )
        nodes.extend(_literature_paper_node(paper, route_indexes=route_indexes) for paper in papers)
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
                                if _literature_paper_route_key(paper) == _literature_route_key(route)
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
        route_key = _literature_route_key(route)
        route_index = route_indexes.get(route_key, 0)
        route_papers = [
            paper
            for paper in papers
            if _literature_paper_route_key(paper) == route_key or route_local_id in (paper.get("route_ids") or [])
        ]
        route_metadata = dict(route)
        route_metadata["route_key"] = route_key
        route_metadata["route_index"] = route_index
        payload["focus_id"] = focus_id
        payload["breadcrumb"] = _breadcrumb("literature", _literature_route_crumb(route))
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
                "metadata": route_metadata,
                "display": {"tone": f"route-{route_index % 6}"},
            },
            *[_literature_paper_node(paper, route_indexes=route_indexes) for paper in route_papers],
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
        sources_model = build_sources_model(root, project_id)
        source = next((item for item in sources_model.get("sources", []) if item.get("source_id") == source_key), None)
        route = _literature_route_for_paper(paper, routes)
        paper_crumbs = []
        if route:
            paper_crumbs.append(_literature_route_crumb(route))
        paper_crumbs.append(_literature_paper_crumb(paper, source, focus_id))
        if source and source.get("locator"):
            paper_graph = build_paper_graph_model(root, root / source["locator"])
            payload["focus_id"] = focus_id
            payload["selected_id"] = selected_id or focus_id
            payload["breadcrumb"] = _breadcrumb("literature", *paper_crumbs)
            payload["canvas"]["nodes"] = [_paper_layer_node(source_key, node) for node in paper_graph.get("nodes", [])]
            payload["canvas"]["edges"] = _paper_layer_edges(source_key, paper_graph)
            payload["inspector"] = _paper_layer_inspector(
                root,
                paper_graph,
                source,
                source_key,
                "Paper argument layer reused from the deep-read source record.",
                [{"title": "Literature Context", "kind": "source_metadata", "items": [paper]}],
            )
            return payload
        payload["focus_id"] = focus_id
        payload["selected_id"] = selected_id or focus_id
        payload["breadcrumb"] = _breadcrumb("literature", *paper_crumbs)
        payload["canvas"]["nodes"] = [_literature_paper_node(paper, drill=False, route_indexes=route_indexes)]
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


def _experiment_setting_inspector_item(setting: dict[str, Any]) -> dict[str, Any]:
    return {
        "label": setting.get("benchmark") or setting.get("label") or "Evaluation setting",
        "subtitle": " / ".join(str(value) for value in [setting.get("dataset"), setting.get("metric_family")] if value),
        "impact": f"{setting.get('experiment_count', 0)} experiments / {setting.get('run_count', 0)} runs",
    }


def _experiment_metric_families(experiment: dict[str, Any], runs: list[dict[str, Any]]) -> list[str]:
    names = [str(metric.get("name") or "") for run in runs for metric in run.get("metrics", [])]
    family = _metric_family_from_names(names) or _planned_metric_family(experiment)
    return [item.strip() for item in family.split("+") if item.strip()]


def _canonical_experiment_datasets(experiment: dict[str, Any]) -> list[str]:
    text = " ".join(
        [
            str(experiment.get("dataset") or ""),
            str(experiment.get("dataset_name") or ""),
            _metadata_text(experiment, "dataset"),
        ]
    ).lower()
    datasets: list[str] = []
    if "agd20k" in text:
        datasets.append("AGD20K")
    if "umd" in text:
        datasets.append("UMD")
    return datasets or [str(experiment.get("dataset") or experiment.get("dataset_name") or "Unspecified dataset")]


def _canonical_experiment_tasks(experiment: dict[str, Any]) -> list[str]:
    text = " ".join(
        [
            str(experiment.get("benchmark") or ""),
            str(experiment.get("benchmark_name") or ""),
            str(experiment.get("title") or ""),
            _metadata_text(experiment, "benchmark"),
        ]
    ).lower()
    tasks: list[str] = []
    if "heatmap" in text or "zero-shot" in text:
        tasks.append("affordance heatmap estimation")
    if "segmentation" in text or "miou" in text:
        tasks.append("affordance segmentation")
    if "qualitative" in text or "validation" in text:
        tasks.append("affordance localization qualitative validation")
    if "semantic assimilation" in text or "control" in text:
        tasks.append("semantic assimilation control")
    return tasks or [str(experiment.get("benchmark") or experiment.get("benchmark_name") or "Unspecified benchmark")]


def _canonical_experiment_metrics(experiment: dict[str, Any], runs: list[dict[str, Any]]) -> list[str]:
    names = [str(metric.get("name") or "") for run in runs for metric in run.get("metrics", [])]
    names.extend(_metadata_list(experiment, "metrics"))
    text = " ".join(names).lower()
    metrics: list[str] = []
    for label, aliases in [
        ("KLD", ["kld"]),
        ("SIM", ["sim"]),
        ("NSS", ["nss"]),
        ("mIoU", ["miou", "m iou"]),
        ("linear-probe separability", ["linear-probe", "linear probe", "separability"]),
        ("part-level PCA coherence", ["pca"]),
        ("qualitative contact-region alignment", ["qualitative", "contact-region", "contact region"]),
        ("cosine similarity response", ["cosine"]),
    ]:
        if any(alias in text for alias in aliases):
            metrics.append(label)
    if not metrics:
        metrics = _experiment_metric_families(experiment, runs)
    return metrics


def _experiment_arena_key(experiment: dict[str, Any], runs: list[dict[str, Any]]) -> str:
    text = " ".join(
        [
            str(experiment.get("id") or ""),
            str(experiment.get("title") or ""),
            str(experiment.get("benchmark") or ""),
            str(experiment.get("dataset") or ""),
            " ".join(_experiment_metric_families(experiment, runs)),
        ]
    ).lower()
    if "mug-handle" in text or "semantic assimilation" in text:
        return "semantic_assimilation_control"
    if "agd20k" in text and ("kld" in text or "heatmap" in text or "flux" in text or "quantitative" in text):
        return "agd20k_affordance_localization"
    if "umd" in text or "segmentation" in text or "miou" in text or "linear probe" in text:
        return "umd_geometry_segmentation_probe"
    if "agd20k" in text or "heatmap" in text or "flux" in text:
        return "agd20k_affordance_localization"
    return "other_experiment_arena"


ARENA_DISPLAY = {
    "agd20k_affordance_localization": {
        "label": "AGD20K Affordance Localization",
        "summary": "Verb-conditioned attention, geometry fusion, heatmap metrics, and qualitative localization evidence.",
    },
    "umd_geometry_segmentation_probe": {
        "label": "UMD Geometry / Segmentation Probe",
        "summary": "Geometry-aware VFM representations tested against object-part affordance segmentation evidence.",
    },
    "semantic_assimilation_control": {
        "label": "Semantic Assimilation Control",
        "summary": "Controls that bound whether apparent geometry evidence is pure shape or entangled with object semantics.",
    },
    "other_experiment_arena": {
        "label": "Other Experiment Arena",
        "summary": "Experiment designs not assigned to the primary demo arenas.",
    },
}


def _experiment_arenas(model: dict[str, Any]) -> list[dict[str, Any]]:
    runs_by_experiment = _runs_by_experiment(model)
    arenas: dict[str, dict[str, Any]] = {}
    for experiment in model.get("experiments", []):
        experiment_runs = runs_by_experiment.get(experiment.get("id"), [])
        arena_key = _experiment_arena_key(experiment, experiment_runs)
        display = ARENA_DISPLAY[arena_key]
        current = arenas.setdefault(
            arena_key,
            {
                "id": f"evaluation_arena:{arena_key}",
                "entity_type": "evaluation_arena",
                "key": arena_key,
                "label": display["label"],
                "summary": display["summary"],
                "experiment_ids": [],
                "run_ids": [],
                "datasets": set(),
                "benchmarks": set(),
                "metric_families": set(),
                "origin_types": set(),
            },
        )
        current["experiment_ids"].append(experiment["id"])
        for dataset in _canonical_experiment_datasets(experiment):
            current["datasets"].add(dataset)
        for task in _canonical_experiment_tasks(experiment):
            current["benchmarks"].add(task)
        for family in _canonical_experiment_metrics(experiment, experiment_runs):
            current["metric_families"].add(family)
        for run in experiment_runs:
            current["run_ids"].append(run["id"])
            if run.get("origin_type"):
                current["origin_types"].add(run["origin_type"])

    result = []
    order = [
        "agd20k_affordance_localization",
        "umd_geometry_segmentation_probe",
        "semantic_assimilation_control",
        "other_experiment_arena",
    ]
    for key in order:
        arena = arenas.get(key)
        if not arena:
            continue
        arena["experiment_ids"] = sorted(set(arena["experiment_ids"]))
        arena["run_ids"] = sorted(set(arena["run_ids"]))
        arena["datasets"] = sorted(arena["datasets"])
        arena["benchmarks"] = sorted(arena["benchmarks"])
        arena["metric_families"] = sorted(arena["metric_families"])
        arena["origin_types"] = sorted(arena["origin_types"])
        arena["experiment_count"] = len(arena["experiment_ids"])
        arena["run_count"] = len(arena["run_ids"])
        result.append(arena)
    return result


def _arena_id_for_legacy_setting(model: dict[str, Any], focus_id: str, arenas: list[dict[str, Any]]) -> str:
    if not str(focus_id or "").startswith("evaluation_setting:"):
        return focus_id
    settings = _evaluation_settings(model)
    setting = next((item for item in settings if item["id"] == focus_id), None)
    if not setting:
        return focus_id
    setting_experiments = set(setting.get("experiment_ids") or [])
    if not setting_experiments:
        return focus_id
    ranked = sorted(
        (
            (len(setting_experiments & set(arena.get("experiment_ids") or [])), arena.get("id", ""))
            for arena in arenas
        ),
        reverse=True,
    )
    overlap, arena_id = ranked[0] if ranked else (0, "")
    return arena_id if overlap else focus_id


def _experiments_breadcrumb(current: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    return _breadcrumb("experiments", *([current] if current else []))


def _arena_for_experiment(experiment_id: str, arenas: list[dict[str, Any]]) -> dict[str, Any] | None:
    matches = [arena for arena in arenas if experiment_id in set(arena.get("experiment_ids") or [])]
    if not matches:
        return None
    return matches[0]


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


def _experiment_method_node(experiment: dict[str, Any], experiment_id: str) -> dict[str, Any]:
    metadata = {
        "experiment_id": experiment_id,
        "models": _metadata_list(experiment, "models"),
        "baselines": _metadata_list(experiment, "baselines"),
        "protocol": experiment.get("protocol") or _metadata_list(experiment, "protocol"),
        "ablations": _metadata_list(experiment, "ablations"),
    }
    counts = [
        len(metadata["models"]),
        len(metadata["baselines"]),
        len(metadata["protocol"]),
        len(metadata["ablations"]),
    ]
    return {
        "id": f"experiment_method:{experiment_id}",
        "entity_type": "experiment_method",
        "label": "Design Method",
        "subtitle": f"{sum(counts)} records / models, baselines, protocol",
        "status": "",
        "confidence": "",
        "metadata": metadata,
        "drill": None,
        "inspector": {"selected_id": f"experiment_method:{experiment_id}"},
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


def _experiment_inspector(experiment: dict[str, Any], run_nodes: list[dict[str, Any]]) -> dict[str, Any]:
    experiment_id = experiment.get("id") or _local_id(experiment.get("entity_id")) or "experiment"
    return {
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


def _experiment_method_inspector(experiment: dict[str, Any], selected_id: str) -> dict[str, Any]:
    method_kind = selected_id.rsplit(":", 1)[-1]
    metadata_key = {
        "model": "models",
        "baseline": "baselines",
        "protocol": "protocol",
        "ablation": "ablations",
    }.get(method_kind, "")
    title = {
        "model": "Models",
        "baseline": "Baselines",
        "protocol": "Protocol",
        "ablation": "Ablations",
    }.get(method_kind, "Design Method")
    values = experiment.get("protocol") if metadata_key == "protocol" else _metadata_list(experiment, metadata_key)
    if isinstance(values, str):
        values = [values]
    items = [{"label": str(value)} for value in values or []]
    return {
        "kind": "experiment_method_detail",
        "title": title,
        "summary": f"{title} used by {experiment.get('id') or 'this experiment'}.",
        "sections": [{"title": title, "kind": method_kind or "method", "items": items}],
        "actions": [],
    }


def _build_experiments(root: Path, project_id: str, layer: str, focus_id: str, selected_id: str) -> dict[str, Any]:
    model = build_experiments_model(root, project_id)
    payload = _base_payload(project_id, "experiments", layer, focus_id, selected_id)
    experiments = _experiments_by_id(model)
    runs_by_experiment = _runs_by_experiment(model)
    arenas = _experiment_arenas(model)

    if layer == "evaluation_overview":
        payload["canvas"]["nodes"] = [
            {
                "id": arena["id"],
                "entity_type": "evaluation_arena",
                "label": arena["label"],
                "subtitle": f"{arena['experiment_count']} experiments / {arena['run_count']} runs",
                "status": "",
                "confidence": "",
                "drill": {"mode": "experiments", "layer": "evaluation_arena_focus", "focus_id": arena["id"]},
                "inspector": {"selected_id": arena["id"]},
                "metadata": arena,
            }
            for arena in arenas
        ]
        narrative = model.get("narrative_summary") or {}
        payload["inspector"] = {
            "kind": "overview",
            "title": "Evaluation Arenas",
            "summary": narrative.get("strongest_current_evidence") or "Evaluation arenas organize experiments before claim impact.",
            "sections": [
                {
                    "title": "Evaluation Arenas",
                    "kind": "evaluation_arena_list",
                    "items": [
                        {
                            "id": arena["id"],
                            "label": arena["label"],
                            "subtitle": ", ".join(arena["metric_families"]) or "mixed metrics",
                            "impact": f"{arena['experiment_count']} experiments / {arena['run_count']} runs",
                        }
                        for arena in arenas
                    ],
                },
                {"title": "Next Moves", "kind": "next_move_list", "items": model.get("next_moves") or []},
            ],
            "actions": [],
        }
        return payload

    if layer == "evaluation_arena_focus":
        focus_id = _arena_id_for_legacy_setting(model, focus_id, arenas)
        arena = next((item for item in arenas if item["id"] == focus_id), None)
        if not arena:
            raise ValueError(f"unknown evaluation arena: {focus_id}")
        payload["focus_id"] = focus_id
        payload["breadcrumb"] = _experiments_breadcrumb(
            {
                "label": arena["label"],
                "mode": "experiments",
                "layer": "evaluation_arena_focus",
                "focus_id": focus_id,
                "selected_id": "",
            }
        )
        experiment_nodes = []
        for experiment_id in arena["experiment_ids"]:
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
        context_node = {
            "id": f"evaluation_context:{_strip_prefix(focus_id, 'evaluation_arena:')}",
            "entity_type": "evaluation_context",
            "label": "Dataset / Benchmark / Metrics",
            "subtitle": (
                f"{len(arena['datasets'])} datasets / "
                f"{len(arena['benchmarks'])} benchmarks / "
                f"{len(arena['metric_families'])} metric families"
            ),
            "status": "",
            "confidence": "",
            "metadata": {
                "arena_id": focus_id,
                "datasets": arena["datasets"],
                "benchmarks": arena["benchmarks"],
                "metric_families": arena["metric_families"],
            },
            "drill": None,
            "inspector": {"selected_id": f"evaluation_context:{_strip_prefix(focus_id, 'evaluation_arena:')}"},
        }
        arena_node = {
            "id": arena["id"],
            "entity_type": "evaluation_arena",
            "label": arena["label"],
            "subtitle": f"{arena['experiment_count']} experiments / {arena['run_count']} runs",
            "status": "",
            "confidence": "",
            "drill": None,
            "inspector": {"selected_id": arena["id"]},
            "metadata": arena,
        }
        payload["canvas"]["nodes"] = [arena_node, context_node, *experiment_nodes]
        payload["canvas"]["edges"] = [
            {
                "id": f"arena-context:{focus_id}:{context_node['id']}",
                "source": context_node["id"],
                "target": focus_id,
                "relation": "defines",
                "label": "defines",
                "metadata": {},
            },
            *[
                {
                    "id": f"arena-exp:{focus_id}:{node['id']}",
                    "source": focus_id,
                    "target": node["id"],
                    "relation": "uses",
                    "label": "uses",
                    "metadata": {},
                }
                for node in experiment_nodes
            ],
        ]
        if selected_id.startswith("run:"):
            payload["inspector"] = _run_inspector(root, project_id, selected_id, model.get("runs", []))
        elif selected_id.startswith("experiment:"):
            experiment_id = _strip_prefix(selected_id, "experiment:")
            experiment = experiments.get(experiment_id)
            if not experiment:
                raise ValueError(f"unknown experiment: {selected_id}")
            owned_runs = [
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
                for run in runs_by_experiment.get(experiment_id, [])
            ]
            payload["inspector"] = _experiment_inspector(experiment, owned_runs)
        else:
            payload["inspector"] = {
                "kind": "arena_detail",
                "title": arena["label"],
                "summary": arena["summary"],
                "sections": [
                    {"title": "Datasets", "kind": "dataset", "items": [{"label": item} for item in arena["datasets"]]},
                    {"title": "Benchmarks / Tasks", "kind": "benchmark", "items": [{"label": item} for item in arena["benchmarks"]]},
                    {"title": "Metric Families", "kind": "metric_family", "items": [{"label": item} for item in arena["metric_families"]]},
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
        experiment_crumb = {
            "label": experiment.get("id") or experiment_id,
            "mode": "experiments",
            "layer": "experiment_design_focus",
            "focus_id": _experiment_graph_id(experiment_id),
            "selected_id": "",
        }
        parent_arena = _arena_for_experiment(experiment_id, arenas)
        if parent_arena:
            payload["breadcrumb"] = _breadcrumb(
                "experiments",
                {
                    "label": parent_arena["label"],
                    "mode": "experiments",
                    "layer": "evaluation_arena_focus",
                    "focus_id": parent_arena["id"],
                    "selected_id": "",
                },
                experiment_crumb,
            )
        else:
            payload["breadcrumb"] = _experiments_breadcrumb(experiment_crumb)
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
        method_node = _experiment_method_node(experiment, experiment_id)
        payload["canvas"]["nodes"] = [exp_node, method_node, *run_nodes]
        payload["canvas"]["edges"] = [
            {
                "id": f"exp-method:{experiment_id}",
                "source": method_node["id"],
                "target": exp_node["id"],
                "relation": "defines",
                "label": "defines",
                "metadata": {},
            },
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
        elif selected_id.startswith("experiment_method:"):
            payload["inspector"] = _experiment_method_inspector(experiment, selected_id)
        else:
            payload["inspector"] = _experiment_inspector(experiment, run_nodes)
        payload["selected_id"] = selected_id
        return payload

    raise ValueError(f"unknown experiments layer: {layer}")
