#!/usr/bin/env python3
"""Workspace scene builder dispatch."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tools.workspace_scene_builders.understanding_scene import build_understanding_scene
from tools.workspace_scene_contract import normalize_workspace_layer, validate_workspace_scene


def build_workspace_scene(
    root: Path,
    project_id: str,
    *,
    mode: str = "understanding",
    layer: str = "",
    focus_id: str = "",
    selected_id: str = "",
) -> dict[str, Any]:
    v2_layer = normalize_workspace_layer(mode, layer)
    if v2_layer.startswith("understanding."):
        scene = build_understanding_scene(root, project_id, v2_layer, focus_id=focus_id, selected_id=selected_id)
        return validate_workspace_scene(scene)
    raise ValueError(f"workspace-scene-v2 not implemented for layer: {v2_layer}")
