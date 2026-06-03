#!/usr/bin/env python3
"""Workspace scene provenance helpers."""

from __future__ import annotations

from typing import Any

from tools.workspace_scene_contract import db_row_source, derived_source


def db_row(table: str, primary_key: str) -> dict[str, str]:
    return db_row_source(table, primary_key)


def derived(rule: str, inputs: list[Any]) -> dict[str, Any]:
    return derived_source(rule, inputs)
