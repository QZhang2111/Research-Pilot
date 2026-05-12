#!/usr/bin/env python3
"""Agent-facing Zotero setup/status helpers for Research Pilot."""

from __future__ import annotations

import argparse
import json
import os
import tomllib
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
SECRET_CONFIG_KEY_ALIASES = {API_KEY_ENV, "api_key"}
COLLECTION_TREE = (
    ("root_collection_key", "Research_Pilot", ""),
    ("inbox_collection_key", "00 Inbox", "root_collection_key"),
    ("projects_collection_key", "10 Projects", "root_collection_key"),
    ("areas_collection_key", "20 Research Areas", "root_collection_key"),
    ("campaigns_collection_key", "30 Review Campaigns", "root_collection_key"),
    ("archive_collection_key", "90 Archive", "root_collection_key"),
)


def normalized_config_key(key: str) -> str:
    key = str(key).strip()
    if len(key) >= 2 and key[0] == key[-1] and key[0] in {'"', "'"}:
        key = key[1:-1]
    return key.lower().replace("_", "").replace("-", "")


def toml_key_segments(key: str) -> List[str]:
    try:
        parsed = tomllib.loads(f"[zotero]\n{key} = \"value\"\n")["zotero"]
    except tomllib.TOMLDecodeError:
        return []

    segments: List[str] = []

    def visit(value: Any) -> None:
        if not isinstance(value, dict):
            return
        for item_key, item_value in value.items():
            segments.append(str(item_key))
            visit(item_value)

    visit(parsed)
    return segments


def is_secret_config_key(key: str) -> bool:
    segments = toml_key_segments(key) or [key]
    secret_aliases = {normalized_config_key(alias) for alias in SECRET_CONFIG_KEY_ALIASES}
    return any(normalized_config_key(segment) in secret_aliases for segment in segments)


def contains_secret_config_key(value: Any) -> bool:
    secret_aliases = {normalized_config_key(alias) for alias in SECRET_CONFIG_KEY_ALIASES}

    def visit(item: Any) -> bool:
        if isinstance(item, dict):
            for key, child in item.items():
                if normalized_config_key(str(key)) in secret_aliases or visit(child):
                    return True
        elif isinstance(item, list):
            return any(visit(child) for child in item)
        return False

    return visit(value)


def is_supported_zotero_config_value(value: str) -> bool:
    try:
        parsed = tomllib.loads(f"value = {value}\n")["value"]
    except tomllib.TOMLDecodeError:
        return False
    return isinstance(parsed, (str, bool, int, float))


def is_supported_zotero_config_entry(key: str, value: str) -> bool:
    try:
        parsed = tomllib.loads(f"[zotero]\n{key} = {value}\n")["zotero"]
    except tomllib.TOMLDecodeError:
        return False
    return bool(parsed)


def is_valid_zotero_entry(entry: str) -> bool:
    try:
        parsed = tomllib.loads(f"[zotero]\n{entry}\n")["zotero"]
    except tomllib.TOMLDecodeError:
        return False
    return bool(parsed) and not contains_secret_config_key(parsed)


def zotero_entry_key(entry: str) -> str:
    first_line = entry.splitlines()[0]
    key, _value = first_line.split("=", 1)
    return key.strip()


def zotero_entry_id(key: str) -> str:
    return normalized_config_key(key)


def zotero_entry_starts_multiline(value: str) -> bool:
    stripped = value.strip()
    return stripped in {"[", "{", '"""', "'''"} or stripped.startswith(('"""', "'''"))


def line_starts_top_level_assignment(line: str) -> bool:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return False
    try:
        parsed = tomllib.loads(f"[zotero]\n{stripped}\n")["zotero"]
    except tomllib.TOMLDecodeError:
        return False
    return bool(parsed)


def zotero_entry_starts_multiline_string(value: str) -> bool:
    return value.strip().startswith(('"""', "'''"))


def is_section_header(line: str) -> bool:
    return bool(table_header_token(line))


def table_header_token(line: str) -> str:
    stripped = line.strip()
    if not stripped.startswith("["):
        return ""

    quote = ""
    escaped = False
    bracket_depth = 0
    for index, char in enumerate(stripped):
        if quote:
            if quote == '"' and char == "\\" and not escaped:
                escaped = True
                continue
            if char == quote and not escaped:
                quote = ""
            escaped = False
            continue
        if char in {'"', "'"}:
            quote = char
            continue
        if char == "[":
            bracket_depth += 1
            continue
        if char == "]":
            bracket_depth -= 1
            if bracket_depth == 0:
                token = stripped[: index + 1]
                tail = stripped[index + 1 :].strip()
                return token if not tail or tail.startswith("#") else ""
    return ""


def section_path(line: str) -> str:
    stripped = table_header_token(line)
    if stripped.startswith("[[") and stripped.endswith("]]"):
        return stripped[2:-2].strip()
    return stripped[1:-1].strip()


def is_zotero_root_section(line: str) -> bool:
    if not is_section_header(line):
        return False
    segments = toml_key_segments(section_path(line))
    return len(segments) == 1 and normalized_config_key(segments[0]) == "zotero"


def is_secret_zotero_section(line: str) -> bool:
    if not is_section_header(line):
        return False
    segments = toml_key_segments(section_path(line))
    if not segments or normalized_config_key(segments[0]) != "zotero":
        return False
    secret_aliases = {normalized_config_key(alias) for alias in SECRET_CONFIG_KEY_ALIASES}
    return any(normalized_config_key(segment) in secret_aliases for segment in segments[1:])


def is_zotero_child_section(line: str) -> bool:
    if not is_section_header(line):
        return False
    segments = toml_key_segments(section_path(line))
    return bool(segments and normalized_config_key(segments[0]) == "zotero" and len(segments) > 1)


def without_secret_zotero_sections(lines: List[str]) -> List[str]:
    filtered: List[str] = []
    index = 0
    while index < len(lines):
        if is_secret_zotero_section(lines[index]):
            index += 1
            while index < len(lines) and not is_section_header(lines[index]):
                index += 1
            continue
        filtered.append(lines[index])
        index += 1
    return filtered


def sanitize_zotero_child_sections(lines: List[str]) -> List[str]:
    sanitized: List[str] = []
    index = 0
    while index < len(lines):
        if not is_zotero_child_section(lines[index]):
            sanitized.append(lines[index])
            index += 1
            continue

        header = lines[index]
        index += 1
        body: List[str] = []
        while index < len(lines) and not is_section_header(lines[index]):
            body.append(lines[index])
            index += 1

        sanitized.append(header)
        entries = collect_existing_zotero_entries(body)
        for key in sorted(entries):
            sanitized.extend(entries[key].splitlines())
    return sanitized


def entry_continuation_can_resync(value: str, line: str) -> bool:
    return line_starts_top_level_assignment(line)


def multiline_string_delimiter(value: str) -> str:
    stripped = value.strip()
    if stripped.startswith('"""'):
        return '"""'
    if stripped.startswith("'''"):
        return "'''"
    return ""


def collect_existing_zotero_entries(lines: List[str]) -> Dict[str, str]:
    entries: Dict[str, str] = {}
    index = 0
    while index < len(lines):
        stripped = lines[index].strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            index += 1
            continue

        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip()
        if is_secret_config_key(key):
            index += 1
            continue

        delimiter = multiline_string_delimiter(value)
        if delimiter:
            candidate = [stripped]
            if is_valid_zotero_entry("\n".join(candidate)):
                entries[zotero_entry_id(key)] = "\n".join(candidate)
                index += 1
                continue
            cursor = index + 1
            closed = False
            while cursor < len(lines):
                candidate.append(lines[cursor])
                if delimiter in lines[cursor]:
                    if is_valid_zotero_entry("\n".join(candidate)):
                        entries[zotero_entry_id(key)] = "\n".join(candidate)
                    cursor += 1
                    closed = True
                    break
                cursor += 1
            index = max(cursor, index + 1) if closed else index + 1
            continue

        candidate = [stripped]
        if is_valid_zotero_entry("\n".join(candidate)):
            entries[zotero_entry_id(key)] = "\n".join(candidate)
            index += 1
            continue

        cursor = index + 1
        while cursor < len(lines):
            next_stripped = lines[cursor].strip()
            if entry_continuation_can_resync(value, lines[cursor]):
                break
            candidate.append(lines[cursor])
            if is_valid_zotero_entry("\n".join(candidate)):
                entries[zotero_entry_id(key)] = "\n".join(candidate)
                cursor += 1
                break
            cursor += 1
        index = max(cursor, index + 1)
    return entries


def render_incoming_zotero_entry(key: Any, value: Any) -> Optional[str]:
    key = str(key)
    if is_secret_config_key(key) or value in ("", None):
        return None
    value_text = json.dumps(str(value), ensure_ascii=False)
    if not is_supported_zotero_config_entry(key, value_text):
        return None
    return f"{key} = {value_text}"


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
        if is_section_header(line):
            section = section_path(line)
            data.setdefault(section, {})
            continue
        if "=" in line and section:
            key, value = line.split("=", 1)
            data.setdefault(section, {})[key.strip()] = value.strip().strip('"').strip("'")
    return data


def collection_name(collection: Dict[str, Any]) -> str:
    data = collection.get("data", collection)
    return str(data.get("name") or "")


def collection_key(collection: Dict[str, Any]) -> str:
    data = collection.get("data", collection)
    return str(data.get("key") or collection.get("key") or "")


def collection_parent(collection: Dict[str, Any]) -> str:
    data = collection.get("data", collection)
    parent = data.get("parentCollection")
    return "" if parent is False or parent is None else str(parent)


def find_collection(collections: List[Dict[str, Any]], name: str, parent_collection: str = "") -> Optional[Dict[str, Any]]:
    parent = parent_collection or ""
    for collection in collections:
        if collection_name(collection) == name and collection_parent(collection) == parent:
            return collection
    return None


def ensure_collection_tree(client: Any) -> Dict[str, str]:
    collections = list(client.fetch_collections())
    result: Dict[str, str] = {}

    for config_key, name, parent_ref in COLLECTION_TREE:
        parent_collection = result.get(parent_ref, "") if parent_ref else ""
        collection = find_collection(collections, name, parent_collection)
        if collection is None:
            collection = client.create_collection(name, parent_collection=parent_collection)
            key = collection_key(collection)
            if key and not any(collection_key(existing) == key for existing in collections):
                collections.append(collection)
        result[config_key] = collection_key(collection)

    return result


def write_zotero_config(root: Path, config: Dict[str, Any]) -> Path:
    root = Path(root).expanduser().resolve()
    path = root / ".research-pilot" / "config.toml"
    path.parent.mkdir(parents=True, exist_ok=True)

    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    existing_lines = sanitize_zotero_child_sections(without_secret_zotero_sections(existing.splitlines()))
    filtered_existing = "\n".join(existing_lines)
    if existing.endswith("\n") and filtered_existing:
        filtered_existing += "\n"
    start = None
    end = len(existing_lines)
    for index, line in enumerate(existing_lines):
        if is_zotero_root_section(line):
            start = index
            break
    if start is not None:
        for index in range(start + 1, len(existing_lines)):
            if is_section_header(existing_lines[index]):
                end = index
                break

    existing_zotero = collect_existing_zotero_entries(existing_lines[start + 1 : end]) if start is not None else {}
    incoming_config: Dict[str, str] = {}
    for key, value in config.items():
        entry = render_incoming_zotero_entry(key, value)
        if entry is not None:
            incoming_config[zotero_entry_id(str(key))] = entry

    merged_config = {**existing_zotero, **incoming_config}
    lines = ["[zotero]"]
    for key in sorted(merged_config):
        lines.extend(merged_config[key].splitlines())
    zotero_section = "\n".join(lines) + "\n"

    if not existing.strip():
        path.write_text(zotero_section, encoding="utf-8")
        return path

    if start is None:
        separator = "" if filtered_existing.endswith("\n\n") else "\n"
        if not filtered_existing.endswith("\n"):
            separator = "\n\n"
        path.write_text(filtered_existing + separator + zotero_section, encoding="utf-8")
        return path

    replacement = zotero_section.rstrip("\n").splitlines()
    new_lines = existing_lines[:start] + replacement + existing_lines[end:]
    path.write_text("\n".join(new_lines).rstrip() + "\n", encoding="utf-8")
    return path


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

    collections = subparsers.add_parser("ensure-collections")
    collections.add_argument("--repo", default=".")
    collections.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    if args.command == "prepare-env":
        result = prepare_env_files(Path(args.repo))
    elif args.command == "ensure-collections":
        root = Path(args.repo).expanduser().resolve()
        target = zotero_status(root, validate=False)
        result = zotero_status(root, validate=True)
        if result.get("api_key_valid"):
            from tools.zotero_bridge import ZoteroClient

            env = load_env_file(root / ".env")
            api_key = env.get(API_KEY_ENV, "") or os.environ.get(API_KEY_ENV, "")
            if target.get("library_id_present"):
                target_library_id = str(target.get("library_id") or "")
                target_library_type = str(target.get("library_type") or "users")
            else:
                target_library_id = str(result.get("library_id") or "")
                target_library_type = str(result.get("library_type") or "users")
            client = ZoteroClient(
                library_id=target_library_id,
                library_type=target_library_type,
                api_key=api_key,
            )
            collection_config = ensure_collection_tree(client)
            config = {
                "library_type": target_library_type,
                "library_id": target_library_id,
                **collection_config,
            }
            write_zotero_config(root, config)
            result["library_type"] = target_library_type
            result["library_id"] = target_library_id
            result.update(collection_config)
            result["config"] = str(root / ".research-pilot" / "config.toml")
        else:
            result["error"] = result.get("error") or "Zotero API key validation required before collection setup"
    else:
        result = zotero_status(Path(args.repo), validate=not args.no_validate)
    print_result(result)
    return 1 if result.get("error") else 0


if __name__ == "__main__":
    raise SystemExit(main())
