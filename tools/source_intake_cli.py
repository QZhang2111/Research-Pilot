#!/usr/bin/env python3
"""Zotero-first source intake with manual source-reference capture."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

THIS_DIR = Path(__file__).resolve().parent
ROOT_DIR = THIS_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from tools.paper_dossier_cli import create_dossier, dossier_path


def source_refs_from_args(args: argparse.Namespace) -> List[str]:
    refs: List[str] = []
    if args.zotero_key:
        refs.append(f"zotero:item:{args.zotero_key}")
    if args.doi:
        refs.append(f"doi:{args.doi}")
    if args.arxiv:
        refs.append(f"arxiv:{args.arxiv}")
    if args.url:
        refs.append(args.url)
    refs.extend(args.source_ref or [])
    return refs


def zotero_status() -> Dict[str, Any]:
    api_key = os.environ.get("ZOTERO_API_KEY", "")
    library_id = os.environ.get("ZOTERO_LIBRARY_ID", "")
    library_type = os.environ.get("ZOTERO_LIBRARY_TYPE", "user")
    return {
        "enabled": bool(api_key and library_id),
        "library_id_present": bool(library_id),
        "api_key_present": bool(api_key),
        "library_type": library_type,
        "mode": "zotero-env" if api_key and library_id else "manual-source-identity",
    }


def intake_source(args: argparse.Namespace) -> Dict[str, Any]:
    root = Path(args.repo).resolve()
    refs = source_refs_from_args(args)
    primary_ref = refs[0] if refs else ""
    create_result = create_dossier(root, args.project, args.paper, args.title, primary_ref, overwrite=args.overwrite)
    path = dossier_path(root, args.project, args.paper)
    if create_result.get("valid") and refs:
        append_source_identity(path, refs)
    return {
        "valid": bool(create_result.get("valid")),
        "created": bool(create_result.get("created")),
        "path": create_result.get("path"),
        "source_refs": refs,
        "zotero": zotero_status(),
        "error": create_result.get("error", ""),
    }


def append_source_identity(path: Path, refs: List[str]) -> None:
    text = path.read_text(encoding="utf-8")
    block = "\n".join(f"- `{ref}`" for ref in refs)
    marker = "## Source Identity\n\n"
    if marker in text:
        text = text.replace(marker, f"{marker}Durable source references:\n\n{block}\n\n", 1)
    path.write_text(text, encoding="utf-8")


def print_result(result: Dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Intake paper/source identity into a project-local dossier.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    status = subparsers.add_parser("status", help="Show Zotero environment status.")
    status.add_argument("--json", action="store_true")

    intake = subparsers.add_parser("intake", help="Create a project-local dossier from source identity.")
    intake.add_argument("--repo", default=".")
    intake.add_argument("--project", required=True)
    intake.add_argument("--paper", required=True)
    intake.add_argument("--title", required=True)
    intake.add_argument("--zotero-key", default="")
    intake.add_argument("--doi", default="")
    intake.add_argument("--arxiv", default="")
    intake.add_argument("--url", default="")
    intake.add_argument("--source-ref", action="append", default=[])
    intake.add_argument("--overwrite", action="store_true")
    intake.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    result = zotero_status() if args.command == "status" else intake_source(args)
    print_result(result, bool(getattr(args, "json", False)))
    return 0 if result.get("valid", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
