#!/usr/bin/env python3
"""Bridge Zotero paper metadata into durable wiki cards when explicitly requested."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
import urllib.parse
import urllib.request
from copy import deepcopy
from datetime import date
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


FRONTMATTER_ORDER = [
    "title",
    "type",
    "created",
    "updated",
    "authors",
    "year",
    "venue",
    "domains",
    "tags",
    "aliases",
    "sources",
    "source_system",
    "zotero_key",
    "zotero_library_id",
    "zotero_select",
    "zotero_attachment_keys",
    "zotero_collections",
    "zotero_tags",
    "betterbibtex_key",
    "doi",
    "arxiv",
    "url",
    "pdf_status",
    "review_status",
    "status",
    "human_review",
    "confidence",
    "projects",
    "project_core_for",
    "global_core",
    "global_core_reason",
    "human_selected",
    "summary_status",
    "read_level",
    "read_date",
    "read_sources",
]

PROTECTED_FIELDS = {
    "created",
    "domains",
    "tags",
    "aliases",
    "review_status",
    "status",
    "human_review",
    "confidence",
    "project_core_for",
    "global_core",
    "global_core_reason",
    "human_selected",
    "summary_status",
}

VALID_REVIEW_STATUSES = {
    "inbox",
    "candidate",
    "triaged",
    "reading",
    "summarized",
    "approved",
    "rejected",
    "archived",
}

REVIEW_STATUS_TAG_PREFIX = "rw/status/"
PROJECT_CORE_TAG = "role/project-core"
PROJECT_TAG_PREFIX = "project/"


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue
        value = value.strip().strip('"').strip("'")
        os.environ[key] = value


def infer_review_status(frontmatter: Dict[str, Any]) -> str:
    explicit = str(frontmatter.get("review_status") or "").strip()
    if explicit in VALID_REVIEW_STATUSES:
        return explicit

    status = str(frontmatter.get("status") or "").strip()
    human_review = str(frontmatter.get("human_review") or "").strip()
    summary_status = str(frontmatter.get("summary_status") or "").strip()

    if human_review == "rejected" or status == "rejected":
        return "rejected"
    if status == "archived":
        return "archived"
    if human_review == "approved":
        return "approved"
    if summary_status in {"agent-draft", "human-reviewed"}:
        return "summarized"
    if status == "triaged":
        return "triaged"
    if status in {"active", "candidate", "needs-review", "stub"}:
        return "candidate"
    return "inbox"


def review_status_tag(review_status: str) -> str:
    status = str(review_status or "").strip()
    if status not in VALID_REVIEW_STATUSES:
        raise ValueError(f"Invalid review_status: {review_status}")
    return f"{REVIEW_STATUS_TAG_PREFIX}{status}"


def infer_review_status_from_zotero_tags(tags: Sequence[Dict[str, Any]]) -> str:
    tag_names = {str(tag.get("tag") or "") for tag in tags or []}
    for status in ("approved", "rejected", "archived", "summarized", "triaged", "reading", "candidate", "inbox"):
        if review_status_tag(status) in tag_names:
            return status
    return "inbox"


def replace_review_status_tags(tags: Sequence[Dict[str, Any]], review_status: str) -> List[Dict[str, Any]]:
    desired = review_status_tag(review_status)
    result: List[Dict[str, Any]] = []
    desired_seen = False
    for tag in tags or []:
        tag_name = str(tag.get("tag") or "")
        if tag_name.startswith(REVIEW_STATUS_TAG_PREFIX):
            if tag_name == desired and not desired_seen:
                result.append(deepcopy(tag))
                desired_seen = True
            continue
        result.append(deepcopy(tag))
    if not desired_seen:
        result.append({"tag": desired})
    return result


def replace_human_gate_tags(
    tags: Sequence[Dict[str, Any]],
    *,
    review_status: str,
    project_core_for: Sequence[Any],
) -> List[Dict[str, Any]]:
    result = replace_review_status_tags(tags, review_status)
    if project_core_for:
        if PROJECT_CORE_TAG not in {str(tag.get("tag") or "") for tag in result}:
            result.append({"tag": PROJECT_CORE_TAG})
    else:
        result = [tag for tag in result if str(tag.get("tag") or "") != PROJECT_CORE_TAG]
    return result


def remove_project_binding_from_item_data(
    data: Dict[str, Any],
    *,
    project: str,
    project_collection: str,
    force: bool = False,
) -> Tuple[Dict[str, Any], bool, str]:
    """Remove non-core project collection/tag bindings from a Zotero item."""
    updated = deepcopy(data)
    tags = updated.get("tags") or []
    tag_names = {str(tag.get("tag") or "") for tag in tags}
    if not force and (
        PROJECT_CORE_TAG in tag_names
        or review_status_tag("approved") in tag_names
        or review_status_tag("archived") in tag_names
    ):
        return updated, False, "skipped-human-gated"

    old_collections = list(updated.get("collections") or [])
    old_tags = list(tags)
    project_tag = f"{PROJECT_TAG_PREFIX}{project}"

    new_collections = [key for key in old_collections if str(key) != str(project_collection)]
    new_tags = [tag for tag in old_tags if str(tag.get("tag") or "") != project_tag]

    changed = new_collections != old_collections or new_tags != old_tags
    updated["collections"] = new_collections
    updated["tags"] = new_tags
    return updated, changed, "updated" if changed else "unchanged"


def today_string() -> str:
    return date.today().isoformat()


def strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def parse_value(value: str) -> Any:
    value = value.strip()
    if value == "":
        return ""
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value == "[]":
        return []
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else value
        except json.JSONDecodeError:
            return [strip_quotes(part.strip()) for part in inner.split(",") if part.strip()]
    if re.fullmatch(r"\d{4}", value):
        return int(value)
    return strip_quotes(value)


def format_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, list):
        return "[" + ", ".join(format_list_item(item) for item in value) + "]"
    return json.dumps(str(value), ensure_ascii=False)


def format_list_item(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    return json.dumps(str(value), ensure_ascii=False)


def parse_frontmatter(text: str) -> Tuple[Dict[str, Any], str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            frontmatter: Dict[str, Any] = {}
            for line in lines[1:idx]:
                if not line.strip() or line.lstrip().startswith("#") or ":" not in line:
                    continue
                key, value = line.split(":", 1)
                frontmatter[key.strip()] = parse_value(value)
            body = "\n".join(lines[idx + 1 :]).lstrip("\n")
            return frontmatter, body
    return {}, text


def render_frontmatter(frontmatter: Dict[str, Any]) -> str:
    ordered_keys = [key for key in FRONTMATTER_ORDER if key in frontmatter]
    ordered_keys.extend(key for key in frontmatter if key not in ordered_keys)
    lines = ["---"]
    for key in ordered_keys:
        lines.append(f"{key}: {format_value(frontmatter[key])}")
    lines.append("---")
    return "\n".join(lines) + "\n\n"


def normalize_identity(value: Any) -> str:
    text = str(value or "").lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", "", text)


def slugify(value: str) -> str:
    text = unicodedata.normalize("NFKD", value)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "untitled"


def creator_name(creator: Dict[str, Any]) -> Optional[str]:
    if creator.get("name"):
        return str(creator["name"]).strip()
    first = str(creator.get("firstName") or "").strip()
    last = str(creator.get("lastName") or "").strip()
    name = " ".join(part for part in [first, last] if part)
    return name or None


def extract_authors(data: Dict[str, Any]) -> List[str]:
    creators = data.get("creators") or []
    authors = []
    for creator in creators:
        if creator.get("creatorType") not in {None, "author"}:
            continue
        name = creator_name(creator)
        if name:
            authors.append(name)
    return authors


def extract_year(data: Dict[str, Any]) -> Optional[int]:
    for key in ["date", "dateAdded", "dateModified"]:
        match = re.search(r"(19|20)\d{2}", str(data.get(key) or ""))
        if match:
            return int(match.group(0))
    return None


def extract_venue(data: Dict[str, Any]) -> str:
    for key in [
        "publicationTitle",
        "conferenceName",
        "proceedingsTitle",
        "bookTitle",
        "university",
        "publisher",
    ]:
        value = str(data.get(key) or "").strip()
        if value:
            return value
    return ""


def extract_arxiv(data: Dict[str, Any]) -> str:
    candidates = [
        data.get("archiveLocation"),
        data.get("DOI"),
        data.get("url"),
        data.get("extra"),
    ]
    for candidate in candidates:
        text = str(candidate or "")
        match = re.search(r"arxiv[:/.\s]+(?:abs/|pdf/)?([0-9]{4}\.[0-9]{4,5}(?:v\d+)?)", text, re.I)
        if match:
            return match.group(1)
    return ""


def is_pdf_attachment(attachment: Dict[str, Any]) -> bool:
    data = attachment.get("data", attachment)
    content_type = str(data.get("contentType") or "").lower()
    title = str(data.get("title") or "").lower()
    return content_type == "application/pdf" or "pdf" in title


def pdf_status_for_attachments(attachments: Sequence[Dict[str, Any]]) -> str:
    pdf_attachments = [attachment for attachment in attachments or [] if is_pdf_attachment(attachment)]
    if not pdf_attachments:
        return "missing"

    for attachment in pdf_attachments:
        data = attachment.get("data", attachment)
        link_mode = str(data.get("linkMode") or "").lower()
        if link_mode and link_mode != "linked_url":
            return "present"
        if not link_mode and str(data.get("url") or "").strip() == "":
            return "present"
    return "open-pdf-url"


def zotero_select_uri(library_id: str, library_type: str, item_key: str) -> str:
    if canonical_library_type(library_type) == "groups":
        return f"zotero://select/groups/{library_id}/items/{item_key}"
    return f"zotero://select/library/items/{item_key}"


def canonical_library_type(library_type: str) -> str:
    value = (library_type or "users").lower()
    if value in {"user", "users"}:
        return "users"
    if value in {"group", "groups"}:
        return "groups"
    raise ValueError("library_type must be users or groups")


def build_record(
    item: Dict[str, Any],
    *,
    library_id: str,
    library_type: str = "users",
    attachments: Optional[Sequence[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    data = item.get("data", item)
    item_key = str(data.get("key") or item.get("key") or "").strip()
    if not item_key:
        raise ValueError("Zotero item is missing key")
    if data.get("itemType") == "attachment":
        raise ValueError(f"Zotero item {item_key} is an attachment, not a paper")

    pdf_keys = [
        str(attachment.get("data", attachment).get("key") or attachment.get("key"))
        for attachment in (attachments or [])
        if is_pdf_attachment(attachment)
    ]
    pdf_keys = [key for key in pdf_keys if key and key != "None"]
    data_tags = data.get("tags") or []
    review_status = infer_review_status_from_zotero_tags(data_tags)

    return {
        "title": str(data.get("title") or "Untitled Paper").strip(),
        "type": "paper",
        "created": today_string(),
        "updated": today_string(),
        "authors": extract_authors(data),
        "year": extract_year(data),
        "venue": extract_venue(data),
        "sources": [f"zotero:item:{item_key}"],
        "source_system": "zotero",
        "zotero_key": item_key,
        "zotero_library_id": str(library_id),
        "zotero_select": zotero_select_uri(str(library_id), library_type, item_key),
        "zotero_attachment_keys": pdf_keys,
        "zotero_collections": list(data.get("collections") or []),
        "zotero_tags": [str(tag.get("tag")) for tag in data_tags if tag.get("tag")],
        "betterbibtex_key": "",
        "doi": str(data.get("DOI") or "").strip(),
        "arxiv": extract_arxiv(data),
        "url": str(data.get("url") or "").strip(),
        "pdf_status": pdf_status_for_attachments(attachments or []),
        "review_status": review_status,
        "status": "candidate",
        "human_review": "pending",
        "confidence": "medium",
        "projects": [],
        "project_core_for": [],
        "global_core": False,
        "summary_status": "agent-draft" if review_status == "summarized" else "metadata-only",
    }


def slug_for_record(record: Dict[str, Any]) -> str:
    authors = record.get("authors") or []
    first_author = str(authors[0]).split()[-1] if authors else "Unknown"
    author_slug = re.sub(r"[^A-Za-z0-9]", "", first_author) or "Unknown"
    year = record.get("year") or "nd"
    title_slug = slugify(str(record.get("title") or "untitled"))
    return f"{author_slug}{year}-{title_slug}"


def list_union(left: Iterable[Any], right: Iterable[Any]) -> List[Any]:
    result: List[Any] = []
    for item in list(left or []) + list(right or []):
        if item not in result:
            result.append(item)
    return result


def merge_frontmatter(existing: Dict[str, Any], generated: Dict[str, Any]) -> Dict[str, Any]:
    merged = deepcopy(existing)
    if "review_status" not in merged:
        merged["review_status"] = infer_review_status(existing)
    for key, value in generated.items():
        if key in PROTECTED_FIELDS and key in existing and existing[key] not in ("", None, []):
            continue
        if key == "sources":
            merged[key] = list_union(existing.get(key, []), value or [])
            continue
        if key == "projects":
            merged[key] = list_union(existing.get(key, []), value or [])
            continue
        merged[key] = value
    if existing.get("created"):
        merged["created"] = existing["created"]
    merged["updated"] = generated.get("updated") or today_string()
    if existing and "review_status" not in existing:
        merged["review_status"] = infer_review_status(existing)
    return merged


def new_card_body(record: Dict[str, Any]) -> str:
    title = record.get("title") or "Untitled Paper"
    key = record.get("zotero_key") or ""
    doi = record.get("doi") or ""
    arxiv = record.get("arxiv") or ""
    url = record.get("url") or ""
    return f"""# {title}

## Core Contribution

Agent draft pending.

## Problem Setting

Agent draft pending.

## Method

Agent draft pending.

## Evidence

Agent draft pending.

## Claims

- Claim:
  - Evidence:
  - Caveat:

## Limitations

Agent draft pending.

## Connections

- Project links pending.

## Open Questions

- Question:

## Human Notes

Human review pending.

## Source Identity

- Zotero item: `zotero:item:{key}`
- DOI: {doi}
- arXiv: {arxiv}
- URL: {url}
"""


class ZoteroClient:
    def __init__(self, *, library_id: str, library_type: str = "users", api_key: str = ""):
        self.library_id = str(library_id)
        self.library_type = canonical_library_type(library_type)
        self.api_key = api_key

    @property
    def base_url(self) -> str:
        return f"https://api.zotero.org/{self.library_type}/{self.library_id}"

    def get_json(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        query = urllib.parse.urlencode(params or {})
        url = f"{self.base_url}{path}"
        if query:
            url = f"{url}?{query}"
        request = urllib.request.Request(url)
        if self.api_key:
            request.add_header("Zotero-API-Key", self.api_key)
        request.add_header("Accept", "application/json")
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))

    def update_item_data(self, data: Dict[str, Any]) -> None:
        item_key = str(data.get("key") or "").strip()
        if not item_key:
            raise ValueError("Zotero item data is missing key")
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/items/{item_key}",
            data=payload,
            method="PUT",
        )
        if self.api_key:
            request.add_header("Zotero-API-Key", self.api_key)
        request.add_header("Content-Type", "application/json")
        request.add_header("Accept", "application/json")
        if data.get("version"):
            request.add_header("If-Unmodified-Since-Version", str(data["version"]))
        with urllib.request.urlopen(request, timeout=30) as response:
            response.read()

    def fetch_item(self, item_key: str) -> Dict[str, Any]:
        return self.get_json(f"/items/{item_key}")

    def fetch_children(self, item_key: str) -> List[Dict[str, Any]]:
        return self.get_json(f"/items/{item_key}/children")

    def fetch_collection_items(self, collection_key: str, *, limit: int = 100) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        start = 0
        while True:
            batch = self.get_json(
                f"/collections/{collection_key}/items/top",
                {"format": "json", "limit": limit, "start": start},
            )
            if not batch:
                break
            items.extend(batch)
            if len(batch) < limit:
                break
            start += limit
        return [item for item in items if item.get("data", {}).get("itemType") != "attachment"]

    def fetch_collections(self, *, limit: int = 100) -> List[Dict[str, Any]]:
        collections: List[Dict[str, Any]] = []
        start = 0
        while True:
            batch = self.get_json("/collections", {"format": "json", "limit": limit, "start": start})
            if not batch:
                break
            collections.extend(batch)
            if len(batch) < limit:
                break
            start += limit
        return collections


class ZoteroBridge:
    def __init__(self, *, root: Path, library_id: str, library_type: str = "users"):
        self.root = Path(root)
        self.library_id = str(library_id)
        self.library_type = canonical_library_type(library_type)
        self.papers_dir = self.root / "wiki/library/papers"

    def existing_cards(self) -> List[Tuple[Path, Dict[str, Any], str]]:
        cards = []
        if not self.papers_dir.exists():
            return cards
        for path in sorted(self.papers_dir.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            frontmatter, body = parse_frontmatter(text)
            cards.append((path, frontmatter, body))
        return cards

    def paper_review_status_records(self) -> List[Dict[str, Any]]:
        records = []
        for path, frontmatter, _body in self.existing_cards():
            zotero_key = str(frontmatter.get("zotero_key") or "").strip()
            if not zotero_key:
                continue
            review_status = infer_review_status(frontmatter)
            records.append(
                {
                    "path": path,
                    "zotero_key": zotero_key,
                    "title": frontmatter.get("title") or path.stem,
                    "review_status": review_status,
                    "project_core_for": frontmatter.get("project_core_for") or [],
                }
            )
        return records

    def find_existing_path(self, record: Dict[str, Any]) -> Optional[Path]:
        record_key = normalize_identity(record.get("zotero_key"))
        record_doi = normalize_identity(record.get("doi"))
        record_title = normalize_identity(record.get("title"))
        fallback = self.papers_dir / f"{slug_for_record(record)}.md"
        for path, frontmatter, _body in self.existing_cards():
            if record_key and normalize_identity(frontmatter.get("zotero_key")) == record_key:
                return path
            if record_key and f"zotero:item:{record.get('zotero_key')}" in (frontmatter.get("sources") or []):
                return path
            if record_doi and normalize_identity(frontmatter.get("doi")) == record_doi:
                return path
            if record_title and normalize_identity(frontmatter.get("title")) == record_title:
                return path
        return fallback if fallback.exists() else None

    def sync_items(
        self,
        item_pairs: Sequence[Tuple[Dict[str, Any], Sequence[Dict[str, Any]]]],
        *,
        project: str = "",
        apply: bool = False,
        create_durable_cards: bool = False,
    ) -> Dict[str, Any]:
        self.papers_dir.mkdir(parents=True, exist_ok=True)
        report: Dict[str, Any] = {
            "dry_run": not apply,
            "created": 0,
            "updated": 0,
            "unchanged": 0,
            "skipped": 0,
            "project_links_added": 0,
            "items": [],
        }
        inbox_rows: List[Tuple[str, str, str]] = []
        for item, attachments in item_pairs:
            record = build_record(
                item,
                library_id=self.library_id,
                library_type=self.library_type,
                attachments=attachments,
            )
            existing_path = self.find_existing_path(record)
            if not existing_path and not create_durable_cards:
                report["skipped"] += 1
                report["items"].append(
                    {
                        "action": "skipped",
                        "changed": False,
                        "title": record.get("title"),
                        "zotero_key": record.get("zotero_key"),
                        "path": "",
                        "pdf_status": record.get("pdf_status"),
                        "reason": "no-existing-durable-card",
                    }
                )
                continue

            if project:
                record["projects"] = [project]
                if record.get("review_status") == "inbox":
                    record["review_status"] = "candidate"
            path = existing_path or self.papers_dir / f"{slug_for_record(record)}.md"
            action, changed = self.write_card(path, record, apply=apply)
            report[action] += 1
            report["items"].append(
                {
                    "action": action,
                    "changed": changed,
                    "title": record.get("title"),
                    "zotero_key": record.get("zotero_key"),
                    "path": str(path.relative_to(self.root)),
                    "pdf_status": record.get("pdf_status"),
                }
            )
            inbox_rows.append((path.stem, record["title"], record["zotero_key"]))

        if project and inbox_rows:
            added = self.update_project_inbox(project, inbox_rows, apply=apply)
            report["project_links_added"] = added
        return report

    def mirror_review_status_tags(self, client: ZoteroClient, *, apply: bool = False) -> Dict[str, Any]:
        report: Dict[str, Any] = {
            "dry_run": not apply,
            "updated": 0,
            "unchanged": 0,
            "skipped": 0,
            "items": [],
        }
        for record in self.paper_review_status_records():
            item_key = record["zotero_key"]
            try:
                item = client.fetch_item(item_key)
            except Exception as exc:  # pragma: no cover - network/API failure path
                report["skipped"] += 1
                report["items"].append(
                    {
                        "action": "skipped",
                        "title": record["title"],
                        "zotero_key": item_key,
                        "review_status": record["review_status"],
                        "path": str(record["path"].relative_to(self.root)),
                        "reason": str(exc),
                    }
                )
                continue

            data = deepcopy(item.get("data", item))
            old_tags = data.get("tags") or []
            new_tags = replace_human_gate_tags(
                old_tags,
                review_status=record["review_status"],
                project_core_for=record["project_core_for"],
            )
            changed = new_tags != old_tags
            action = "updated" if changed else "unchanged"
            if changed and apply:
                data["tags"] = new_tags
                client.update_item_data(data)
            report[action] += 1
            report["items"].append(
                {
                    "action": action,
                    "title": record["title"],
                    "zotero_key": item_key,
                    "review_status": record["review_status"],
                    "path": str(record["path"].relative_to(self.root)),
                    "tag": review_status_tag(record["review_status"]),
                }
            )
        return report

    def demote_project_candidates(
        self,
        client: ZoteroClient,
        item_keys: Sequence[str],
        *,
        project: str,
        project_collection: str,
        apply: bool = False,
        force: bool = False,
    ) -> Dict[str, Any]:
        report: Dict[str, Any] = {
            "dry_run": not apply,
            "updated": 0,
            "unchanged": 0,
            "skipped": 0,
            "items": [],
        }
        seen: set[str] = set()
        for item_key in item_keys:
            item_key = str(item_key or "").strip()
            if not item_key or item_key in seen:
                continue
            seen.add(item_key)
            try:
                item = client.fetch_item(item_key)
            except Exception as exc:  # pragma: no cover - network/API failure path
                report["skipped"] += 1
                report["items"].append(
                    {
                        "action": "skipped",
                        "title": item_key,
                        "zotero_key": item_key,
                        "reason": str(exc),
                    }
                )
                continue

            data = deepcopy(item.get("data", item))
            new_data, changed, reason = remove_project_binding_from_item_data(
                data,
                project=project,
                project_collection=project_collection,
                force=force,
            )
            if reason == "skipped-human-gated":
                action = "skipped"
            else:
                action = "updated" if changed else "unchanged"
            if changed and apply:
                client.update_item_data(new_data)
            report[action] += 1
            report["items"].append(
                {
                    "action": action,
                    "title": data.get("title") or item_key,
                    "zotero_key": item_key,
                    "reason": reason,
                    "collections_before": data.get("collections") or [],
                    "collections_after": new_data.get("collections") or [],
                    "tags_before": [str(tag.get("tag") or "") for tag in data.get("tags") or []],
                    "tags_after": [str(tag.get("tag") or "") for tag in new_data.get("tags") or []],
                }
            )
        return report

    def write_card(self, path: Path, record: Dict[str, Any], *, apply: bool) -> Tuple[str, bool]:
        if path.exists():
            existing_text = path.read_text(encoding="utf-8")
            existing_frontmatter, existing_body = parse_frontmatter(existing_text)
            merged = merge_frontmatter(existing_frontmatter, record)
            body = existing_body or new_card_body(merged)
            rendered = render_frontmatter(merged) + body.rstrip() + "\n"
            if rendered == existing_text:
                return "unchanged", False
            if apply:
                path.write_text(rendered, encoding="utf-8")
            return "updated", True

        rendered = render_frontmatter(record) + new_card_body(record)
        if apply:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(rendered, encoding="utf-8")
        return "created", True

    def update_project_inbox(
        self,
        project: str,
        rows: Sequence[Tuple[str, str, str]],
        *,
        apply: bool,
    ) -> int:
        inbox = self.root / f"wiki/projects/{project}/reading-inbox.md"
        if inbox.exists():
            text = inbox.read_text(encoding="utf-8")
        else:
            text = f"# {project} Reading Inbox\n"

        additions: List[str] = []
        for slug, title, zotero_key in rows:
            marker = f"zotero:item:{zotero_key}"
            wikilink_marker = f"[[{slug}"
            if marker in text or wikilink_marker in text:
                continue
            additions.append(f"| [[{slug}|{title}]] | {marker} | candidate | bridge-sync |")

        if not additions:
            return 0

        frontmatter, body = parse_frontmatter(text)
        if frontmatter:
            frontmatter["updated"] = today_string()
            text = render_frontmatter(frontmatter) + body

        section = "\n\n## Zotero Bridge Intake\n\n| Paper | Zotero | Review Status | Notes |\n| --- | --- | --- | --- |\n"
        if "## Zotero Bridge Intake" not in text:
            text = text.rstrip() + section
        else:
            text = text.rstrip() + "\n"
        text += "\n".join(additions) + "\n"

        if apply:
            inbox.parent.mkdir(parents=True, exist_ok=True)
            inbox.write_text(text, encoding="utf-8")
        return len(additions)


def load_input_json(path: Path) -> List[Tuple[Dict[str, Any], Sequence[Dict[str, Any]]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and "items" in payload:
        raw_items = payload["items"]
    else:
        raw_items = payload
    pairs = []
    for entry in raw_items:
        if isinstance(entry, dict) and "item" in entry:
            pairs.append((entry["item"], entry.get("attachments", [])))
        else:
            pairs.append((entry, []))
    return pairs


def format_collection_lines(collections: Sequence[Dict[str, Any]]) -> List[str]:
    lines = []
    for collection in collections:
        data = collection.get("data", collection)
        key = str(data.get("key") or collection.get("key") or "")
        name = str(data.get("name") or "")
        parent = data.get("parentCollection")
        parent_text = "" if parent in (False, None, "") else str(parent)
        lines.append(f"{key}\t{name}\tparent={parent_text}")
    return lines


def fetch_pairs_from_zotero(args: argparse.Namespace) -> List[Tuple[Dict[str, Any], Sequence[Dict[str, Any]]]]:
    client = ZoteroClient(
        library_id=args.library_id,
        library_type=args.library_type,
        api_key=args.api_key or "",
    )
    if args.item:
        item = client.fetch_item(args.item)
        attachments = client.fetch_children(args.item) if args.fetch_attachments else []
        return [(item, attachments)]
    if args.collection:
        items = client.fetch_collection_items(args.collection)
        pairs = []
        for item in items:
            key = item.get("key") or item.get("data", {}).get("key")
            attachments = client.fetch_children(key) if args.fetch_attachments and key else []
            pairs.append((item, attachments))
        return pairs
    raise SystemExit("Provide --item, --collection, or --input-json")


def print_report(report: Dict[str, Any]) -> None:
    mode = "DRY RUN" if report.get("dry_run") else "APPLIED"
    print(f"Zotero Bridge {mode}")
    print(
        "created={created} updated={updated} unchanged={unchanged} skipped={skipped} project_links_added={project_links_added}".format(
            **report
        )
    )
    for item in report["items"]:
        if item["action"] == "skipped":
            print(
                "- skipped: {title} [{zotero_key}] {pdf_status} ({reason})".format(
                    **item
                )
            )
            continue
        print(
            "- {action}: {title} [{zotero_key}] {pdf_status} -> {path}".format(
                **item
            )
        )


def print_status_tag_report(report: Dict[str, Any]) -> None:
    mode = "DRY RUN" if report.get("dry_run") else "APPLIED"
    print(f"Zotero Review/Core Tag Mirror {mode}")
    print(
        "updated={updated} unchanged={unchanged} skipped={skipped}".format(
            **report
        )
    )
    for item in report["items"]:
        if item["action"] == "skipped":
            print(
                "- skipped: {title} [{zotero_key}] {review_status} -> {path} ({reason})".format(
                    **item
                )
            )
            continue
        print(
            "- {action}: {title} [{zotero_key}] {review_status} {tag} -> {path}".format(
                **item
            )
        )


def print_demote_report(report: Dict[str, Any]) -> None:
    mode = "DRY RUN" if report.get("dry_run") else "APPLIED"
    print(f"Zotero Project Candidate Demotion {mode}")
    print("updated={updated} unchanged={unchanged} skipped={skipped}".format(**report))
    for item in report["items"]:
        print(
            "- {action}: {title} [{zotero_key}] ({reason})".format(
                **item
            )
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bridge Zotero metadata into durable wiki paper cards.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ["collections", "inspect", "sync", "mirror-status-tags", "demote-project-candidates"]:
        sub = subparsers.add_parser(name)
        sub.add_argument("--root", default=".", help="Research Pilot root")
        sub.add_argument("--library-id", default=os.environ.get("ZOTERO_LIBRARY_ID", ""))
        sub.add_argument("--library-type", default=os.environ.get("ZOTERO_LIBRARY_TYPE", "users"))
        sub.add_argument("--api-key", default=os.environ.get("ZOTERO_API_KEY", ""))
        if name == "collections":
            sub.add_argument("--contains", default="", help="Filter collection names")
            continue
        if name == "mirror-status-tags":
            sub.add_argument("--apply", action="store_true", help="Write Zotero tags. Default is dry-run.")
            continue
        if name == "demote-project-candidates":
            sub.add_argument("--project", required=True, help="Project name, for example ProjectName")
            sub.add_argument("--project-collection", required=True, help="Zotero project collection key to remove")
            sub.add_argument(
                "--collection",
                action="append",
                default=[],
                help="Zotero collection key whose items should be demoted. Can be repeated.",
            )
            sub.add_argument(
                "--item",
                action="append",
                default=[],
                help="Specific Zotero item key to demote. Can be repeated.",
            )
            sub.add_argument("--force", action="store_true", help="Also demote approved/archived/project-core items.")
            sub.add_argument("--apply", action="store_true", help="Write Zotero changes. Default is dry-run.")
            continue
        sub.add_argument("--collection", help="Zotero collection key")
        sub.add_argument("--item", help="Zotero item key")
        sub.add_argument("--input-json", type=Path, help="Offline Zotero API JSON payload")
        sub.add_argument("--project", default="", help="wiki/projects/<project> to update")
        sub.add_argument(
            "--fetch-attachments",
            action="store_true",
            help="Fetch child attachments from Zotero for PDF status.",
        )
        if name == "sync":
            sub.add_argument("--apply", action="store_true", help="Write files. Default is dry-run.")
            sub.add_argument(
                "--create-durable-cards",
                action="store_true",
                help=(
                    "Create missing wiki/library/papers cards. Default updates existing durable cards only "
                    "and skips ordinary candidates."
                ),
            )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    load_env_file(Path.cwd() / ".env")
    parser = build_parser()
    args = parser.parse_args(argv)
    load_env_file(Path(args.root) / ".env")
    if not args.library_id:
        args.library_id = os.environ.get("ZOTERO_LIBRARY_ID", "")
    if not args.library_type:
        args.library_type = os.environ.get("ZOTERO_LIBRARY_TYPE", "users")
    if not args.api_key:
        args.api_key = os.environ.get("ZOTERO_API_KEY", "")
    if not args.library_id:
        parser.error("--library-id or ZOTERO_LIBRARY_ID is required")

    if args.command == "collections":
        client = ZoteroClient(
            library_id=args.library_id,
            library_type=args.library_type,
            api_key=args.api_key or "",
        )
        collections = client.fetch_collections()
        if args.contains:
            needle = args.contains.lower()
            collections = [
                collection
                for collection in collections
                if needle in str(collection.get("data", {}).get("name") or "").lower()
            ]
        for line in format_collection_lines(collections):
            print(line)
        return 0

    if args.command == "mirror-status-tags":
        client = ZoteroClient(
            library_id=args.library_id,
            library_type=args.library_type,
            api_key=args.api_key or "",
        )
        bridge = ZoteroBridge(
            root=Path(args.root),
            library_id=args.library_id,
            library_type=args.library_type,
        )
        report = bridge.mirror_review_status_tags(client, apply=bool(args.apply))
        print_status_tag_report(report)
        return 0

    if args.command == "demote-project-candidates":
        client = ZoteroClient(
            library_id=args.library_id,
            library_type=args.library_type,
            api_key=args.api_key or "",
        )
        item_keys: List[str] = list(args.item or [])
        for collection_key in args.collection or []:
            collection_items = client.fetch_collection_items(collection_key)
            for item in collection_items:
                key = item.get("key") or item.get("data", {}).get("key")
                if key:
                    item_keys.append(str(key))
        if not item_keys:
            parser.error("demote-project-candidates requires --item or --collection")
        bridge = ZoteroBridge(
            root=Path(args.root),
            library_id=args.library_id,
            library_type=args.library_type,
        )
        report = bridge.demote_project_candidates(
            client,
            item_keys,
            project=args.project,
            project_collection=args.project_collection,
            apply=args.apply,
            force=args.force,
        )
        print_demote_report(report)
        return 0

    if args.input_json:
        pairs = load_input_json(args.input_json)
    else:
        pairs = fetch_pairs_from_zotero(args)

    bridge = ZoteroBridge(
        root=Path(args.root),
        library_id=args.library_id,
        library_type=args.library_type,
    )

    if args.command == "inspect":
        for item, attachments in pairs:
            record = build_record(
                item,
                library_id=args.library_id,
                library_type=args.library_type,
                attachments=attachments,
            )
            print(json.dumps(record, ensure_ascii=False, indent=2))
        return 0

    report = bridge.sync_items(
        pairs,
        project=args.project,
        apply=bool(getattr(args, "apply", False)),
        create_durable_cards=bool(getattr(args, "create_durable_cards", False)),
    )
    print_report(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
