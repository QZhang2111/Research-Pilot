#!/usr/bin/env python3
"""Agent-facing Zotero setup/status helpers for Research Pilot."""

from __future__ import annotations

import argparse
import json
import os
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional


API_KEY_ENV = "ZOTERO_API_KEY"
ENV_TEMPLATE = f"""# Research Pilot local secrets
# Paste a Zotero key created at https://www.zotero.org/settings/keys/new
{API_KEY_ENV}=
"""

KEY_URL = "https://www.zotero.org/settings/keys/new"
SECRET_GITIGNORE_ENTRIES = (".env", ".env.local")


def load_env_file(path: Path) -> Dict[str, str]:
    values: Dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def parse_simple_toml(path: Path) -> Dict[str, Dict[str, str]]:
    data: Dict[str, Dict[str, str]] = {}
    section = ""
    if not path.exists():
        return data
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].strip()
            data.setdefault(section, {})
            continue
        if "=" in line and section:
            key, value = line.split("=", 1)
            data.setdefault(section, {})[key.strip()] = value.strip().strip('"').strip("'")
    return data


def prepare_env_files(root: Path) -> Dict[str, Any]:
    root = Path(root).expanduser().resolve()
    env_example = root / ".env.example"
    env = root / ".env"
    gitignore = root / ".gitignore"
    env_example_created = not env_example.exists()
    env_created = not env.exists()
    gitignore_updated = ensure_secret_gitignore(gitignore)
    if env_example_created:
        env_example.write_text(ENV_TEMPLATE, encoding="utf-8")
    if env_created:
        env.write_text(ENV_TEMPLATE, encoding="utf-8")
    return {
        "env_example": str(env_example),
        "env_example_created": env_example_created,
        "env": str(env),
        "env_created": env_created,
        "gitignore": str(gitignore),
        "gitignore_updated": gitignore_updated,
        "key_url": KEY_URL,
    }


def ensure_secret_gitignore(path: Path) -> bool:
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    existing_lines = {line.strip() for line in existing.splitlines()}
    missing = [entry for entry in SECRET_GITIGNORE_ENTRIES if entry not in existing_lines]
    if not missing:
        return False

    pieces = [existing] if existing else []
    if existing and not existing.endswith("\n"):
        pieces.append("\n")
    pieces.extend(f"{entry}\n" for entry in missing)
    path.write_text("".join(pieces), encoding="utf-8")
    return True


def validate_key(api_key: str) -> Dict[str, str]:
    request = urllib.request.Request("https://api.zotero.org/keys/current")
    request.add_header("Zotero-API-Key", api_key)
    request.add_header("Accept", "application/json")
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    library_id = str(payload.get("userID") or payload.get("userId") or payload.get("library", {}).get("id") or "")
    return {
        "library_type": "users",
        "library_id": library_id,
    }


def zotero_status(root: Path, validate: bool = True) -> Dict[str, Any]:
    root = Path(root).expanduser().resolve()
    env = load_env_file(root / ".env")
    config = parse_simple_toml(root / ".research-pilot" / "config.toml")
    zotero_config = config.get("zotero", {})
    api_key = env.get(API_KEY_ENV, "") or os.environ.get(API_KEY_ENV, "")
    library_type = zotero_config.get("library_type", "") or os.environ.get("ZOTERO_LIBRARY_TYPE", "") or "user"
    library_id = zotero_config.get("library_id", "") or os.environ.get("ZOTERO_LIBRARY_ID", "")
    env_only_configured = not env.get(API_KEY_ENV, "") and bool(api_key and library_id)
    result: Dict[str, Any] = {
        "configured": False,
        "enabled": bool(api_key and library_id),
        "api_key_present": bool(api_key),
        "api_key_valid": False,
        "library_type": library_type,
        "library_id": library_id,
        "library_id_present": bool(library_id),
        "mode": "env-present" if api_key else "not-configured",
        "key_url": KEY_URL,
    }
    if env_only_configured:
        result["mode"] = "zotero-env"
    if api_key and validate:
        try:
            validation = validate_key(api_key)
        except Exception as exc:
            result["error"] = f"{exc.__class__.__name__}: key validation failed"
            return result
        result.update(validation)
        result["api_key_valid"] = bool(result.get("library_id"))
        result["configured"] = result["api_key_valid"]
        result["enabled"] = bool(api_key and result.get("library_id"))
        result["library_id_present"] = bool(result.get("library_id"))
        result["mode"] = "zotero-web-api" if result["api_key_valid"] else "env-present"
    elif api_key and result.get("library_id"):
        result["configured"] = True
    return result


def print_result(result: Dict[str, Any]) -> None:
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Agent-facing Zotero setup/status helper.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare-env", help="Create local Zotero env files when missing.")
    prepare.add_argument("--repo", default=".")
    prepare.add_argument("--json", action="store_true")

    status = subparsers.add_parser("status", help="Show Zotero setup status.")
    status.add_argument("--repo", default=".")
    status.add_argument("--json", action="store_true")
    status.add_argument("--no-validate", action="store_true")

    args = parser.parse_args(argv)
    if args.command == "prepare-env":
        result = prepare_env_files(Path(args.repo))
    else:
        result = zotero_status(Path(args.repo), validate=not args.no_validate)
    print_result(result)
    return 1 if result.get("error") else 0


if __name__ == "__main__":
    raise SystemExit(main())
