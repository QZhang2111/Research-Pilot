#!/usr/bin/env python3
"""Build disposable read-model JSON for the local Research Browser dashboard."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

THIS_DIR = Path(__file__).resolve().parent
ROOT_DIR = THIS_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

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


def parse_frontmatter(text: str) -> Tuple[Dict[str, Any], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end == -1:
        return {}, text
    raw = text[4:end].strip()
    body = text[text.find("\n", end + 4) + 1 :]
    frontmatter: Dict[str, Any] = {}
    for line in raw.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            frontmatter[key] = [item.strip().strip("\"'") for item in inner.split(",") if item.strip()] if inner else []
        elif value.lower() in {"true", "false"}:
            frontmatter[key] = value.lower() == "true"
        else:
            frontmatter[key] = value.strip("\"'")
    return frontmatter, body


def relpath(path: Path, root: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(resolved)


def resolve_output_path(root: Path, output: str) -> Path:
    output_path = Path(output)
    if output_path.is_absolute():
        return output_path
    return root / output_path


def read_markdown(path: Path) -> Tuple[Dict[str, Any], str]:
    text = path.read_text(encoding="utf-8")
    return parse_frontmatter(text)


def extract_section(text: str, heading: str) -> str:
    target = heading.strip().casefold()
    target_level = 0
    collecting = False
    collected: List[str] = []
    for line in text.splitlines():
        match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if match:
            level = len(match.group(1))
            title = match.group(2).strip().casefold()
            if collecting and level <= target_level:
                break
            if title == target:
                collecting = True
                target_level = level
                continue
        if collecting:
            collected.append(line)
    return "\n".join(collected).strip()


def normalize_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower().strip())
    return re.sub(r"-+", "-", slug).strip("-")


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return slug[:96] or "claim"


def clean_markdown_text(text: str) -> str:
    lines: List[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("```"):
            continue
        stripped = re.sub(r"^[-*]\s+", "", stripped)
        stripped = re.sub(r"^\d+\.\s+", "", stripped)
        lines.append(stripped)
    cleaned = " ".join(lines)
    cleaned = re.sub(r"\*\*(.*?)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"`([^`]*)`", r"\1", cleaned)
    cleaned = re.sub(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", r"\1", cleaned)
    cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def first_sentence(text: str, limit: int = 220) -> str:
    cleaned = clean_markdown_text(text)
    if not cleaned:
        return ""
    sentence_match = re.search(r"(.+?[.!?。！？])(?:\s|$)", cleaned)
    value = sentence_match.group(1) if sentence_match else cleaned
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "…"


def normalize_status(frontmatter: Dict[str, Any]) -> str:
    review_status = str(frontmatter.get("review_status") or "").strip().strip("\"'").lower()
    if review_status in VALID_REVIEW_STATUSES:
        return review_status
    status = str(frontmatter.get("status") or "").strip().strip("\"'").lower()
    if status in VALID_REVIEW_STATUSES:
        return status
    if status == "active":
        return "candidate"
    return "inbox"


def list_value(frontmatter: Dict[str, Any], key: str) -> List[str]:
    value = frontmatter.get(key)
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def scalar(frontmatter: Dict[str, Any], key: str, default: str = "") -> str:
    value = frontmatter.get(key)
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip().strip("\"'")
    return str(value)


def extract_wikilinks(text: str) -> List[str]:
    return sorted({match.group(1).split("|")[0] for match in re.finditer(r"\[\[([^\]]+)\]\]", text)})


def is_table_separator_row(line: str) -> bool:
    trimmed = line.strip()
    if not trimmed.startswith("|"):
        return False
    return bool(re.fullmatch(r"\|\s*:?-{3,}\s*(\|\s*:?-{3,}\s*)+\|?", trimmed))


def infer_family_from_round(project: str, round_name: str, title: str, root: Path) -> str:
    if not project or not round_name:
        return ""
    search_path = (
        root / "wiki" / "projects" / project / "literature-rounds" / round_name / "search-results.md"
    )
    if not search_path.exists():
        return ""
    _, body = read_markdown(search_path)
    for line in body.splitlines():
        if "|" not in line or title not in line:
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) >= 4 and cells[0] == title and cells[3] and cells[3] != "---":
            return cells[3]
    return ""


def collect_core_files(project_dir: Path, root: Path) -> List[Dict[str, Any]]:
    names = [
        "overview.md",
        "questions.md",
        "citation-map.md",
        "claim-register.md",
        "reading-inbox.md",
        "idea-board.md",
        "experiment-log.md",
        "decisions.md",
        "project-understanding-graph.md",
        "project-query-pack.md",
    ]
    files: List[Dict[str, Any]] = []
    for name in names:
        path = project_dir / name
        if not path.exists():
            continue
        frontmatter, _ = read_markdown(path)
        files.append(
            {
                "kind": scalar(frontmatter, "type", name.replace(".md", "")),
                "title": scalar(frontmatter, "title", name.replace(".md", "")),
                "path": relpath(path, root),
                "updated": scalar(frontmatter, "updated"),
            }
        )
    return files


def section_bullets(body: str, heading: str) -> List[str]:
    section = extract_section(body, heading)
    return [
        line.strip("- ").strip()
        for line in section.splitlines()
        if line.strip().startswith("- ") and line.strip("- ").strip()
    ]


def accepted_questions_from_graph(project_id: str, project_graphs: List[Dict[str, Any]]) -> List[str]:
    for graph in project_graphs:
        if graph.get("project") != project_id:
            continue
        questions = []
        for node in graph.get("nodes", []):
            if node.get("kind") != "question":
                continue
            human_review = str(node.get("human_review") or "").lower()
            if human_review in {"accepted", "approved"}:
                label = str(node.get("label") or "").strip()
                if label:
                    questions.append(label)
        return questions
    return []


def collect_projects(root: Path, project_graphs: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    project_graphs = project_graphs or []
    projects_dir = root / "wiki" / "projects"
    if not projects_dir.exists():
        return []
    projects: List[Dict[str, Any]] = []
    for project_dir in sorted(path for path in projects_dir.iterdir() if path.is_dir()):
        overview_file = project_dir / "overview.md"
        query_pack = project_dir / "project-query-pack.md"
        overview_source = overview_file if overview_file.exists() else query_pack
        frontmatter: Dict[str, Any] = {}
        body = ""
        if overview_source.exists():
            frontmatter, body = read_markdown(overview_source)
        direction = first_sentence(extract_section(body, "Project Direction"))
        seed_questions = section_bullets(body, "Seed Questions")
        search_questions = section_bullets(body, "Search Questions")
        accepted_questions = section_bullets(body, "Accepted Questions")
        if not accepted_questions:
            accepted_questions = accepted_questions_from_graph(project_dir.name, project_graphs)
        current_questions = accepted_questions
        if not current_questions:
            current_questions = section_bullets(body, "Current Questions")
        search_contract = first_sentence(
            extract_section(body, "First Search Contract"),
            limit=320,
        )
        projects.append(
            {
                "id": project_dir.name,
                "title": scalar(frontmatter, "display_title") or scalar(frontmatter, "title", project_dir.name),
                "path": relpath(project_dir, root),
                "overview": {
                    "direction": direction,
                    "current_questions": current_questions,
                    "seed_questions": seed_questions,
                    "search_questions": search_questions,
                    "accepted_questions": accepted_questions,
                    "search_contract": search_contract,
                    "human_gates": section_bullets(body, "Human Gates"),
                },
                "core_files": collect_core_files(project_dir, root),
                "stats": {
                    "candidate_papers": 0,
                    "summarized_papers": 0,
                    "approved_papers": 0,
                    "literature_rounds": 0,
                    "claims": 0,
                },
            }
        )
    return projects


def ensure_graph_projects(projects: List[Dict[str, Any]], project_graphs: List[Dict[str, Any]], root: Path) -> None:
    existing = {project["id"] for project in projects}
    for graph in project_graphs:
        project_id = str(graph.get("project") or "").strip()
        if not project_id or project_id in existing:
            continue
        projects.append(
            {
                "id": project_id,
                "title": str(graph.get("title") or project_id),
                "path": relpath(root / "wiki" / "projects" / project_id, root),
                "overview": {
                    "direction": "Graph-only project initialized from graph events.",
                    "current_questions": [],
                    "seed_questions": [],
                    "search_questions": [],
                    "accepted_questions": [],
                    "search_contract": "",
                    "human_gates": ["Graph deltas require explicit human decisions."],
                },
                "core_files": [],
                "stats": {
                    "candidate_papers": 0,
                    "summarized_papers": 0,
                    "approved_papers": 0,
                    "literature_rounds": 0,
                    "claims": 0,
                },
            }
        )
        existing.add(project_id)


def extract_claims_from_memo(body: str) -> List[str]:
    section = extract_section(body, "Claims")
    claims: List[str] = []
    for line in section.splitlines():
        stripped = line.strip()
        if stripped.startswith("- Claim:"):
            claims.append(stripped.replace("- Claim:", "", 1).strip())
        elif stripped.startswith("- 主张："):
            claims.append(stripped.replace("- 主张：", "", 1).strip())
    return claims


def extract_limitations(body: str) -> List[str]:
    section = extract_section(body, "Limitations")
    if not section:
        return []
    limitation_text = first_sentence(section)
    return [limitation_text] if limitation_text else []


def infer_family(frontmatter: Dict[str, Any], project: str, round_name: str, title: str, root: Path) -> str:
    explicit = scalar(frontmatter, "family")
    if explicit:
        return explicit
    return infer_family_from_round(project, round_name, title, root)


def build_paper_record(
    root: Path,
    path: Path,
    frontmatter: Dict[str, Any],
    body: str,
    project: str,
    round_name: str,
    source_type: str,
) -> Dict[str, Any]:
    title = scalar(frontmatter, "title", path.stem)
    zotero_key = scalar(frontmatter, "zotero_key")
    core = extract_section(body, "Core Judgment") or extract_section(body, "Core Contribution")
    why = extract_section(body, f"Why It Matters For {project}") or extract_section(body, "Why It Matters")
    project_core_for = list_value(frontmatter, "project_core_for")
    if source_type == "project-paper" and project and project not in project_core_for:
        project_core_for.append(project)
    return {
        "id": f"zotero:{zotero_key}" if zotero_key else relpath(path, root),
        "zotero_key": zotero_key,
        "title": title,
        "authors": list_value(frontmatter, "authors"),
        "year": frontmatter.get("year", ""),
        "venue": scalar(frontmatter, "venue"),
        "project": project,
        "path": relpath(path, root),
        "source_type": source_type,
        "literature_round": scalar(frontmatter, "literature_round", round_name),
        "review_status": normalize_status(frontmatter),
        "human_review": scalar(frontmatter, "human_review", "pending"),
        "summary_status": scalar(frontmatter, "summary_status"),
        "read_level": scalar(frontmatter, "read_level"),
        "pdf_status": scalar(frontmatter, "pdf_status"),
        "zotero_select": scalar(frontmatter, "zotero_select"),
        "url": scalar(frontmatter, "url"),
        "arxiv": scalar(frontmatter, "arxiv"),
        "doi": scalar(frontmatter, "doi"),
        "project_core_for": project_core_for,
        "family": infer_family(frontmatter, project, round_name, title, root),
        "one_line": first_sentence(core),
        "why_relevant": first_sentence(why, limit=260),
        "key_claims": extract_claims_from_memo(body),
        "limitations": extract_limitations(body),
        "connections": extract_wikilinks(extract_section(body, "Connections")),
    }


def collect_paper_keys(paper: Dict[str, Any]) -> List[str]:
    keys: List[str] = []
    title = str(paper.get("title") or "").strip()
    if title:
        keys.append(title)
        keys.append(title.casefold())
        keys.append(normalize_slug(title))
    path = str(paper.get("path") or "")
    if path:
        stem = Path(path).stem
        name = Path(path).name
        keys.extend([stem, stem.casefold(), name, name.casefold()])
    zotero_key = str(paper.get("zotero_key") or "").strip()
    if zotero_key:
        keys.append(f"zotero:{zotero_key}")
        keys.append(zotero_key)
    return sorted(set(filter(None, keys)))


def build_paper_index(papers: List[Dict[str, Any]]) -> Dict[str, str]:
    index: Dict[str, str] = {}
    for paper in papers:
        paper_id = paper["id"]
        for key in collect_paper_keys(paper):
            index.setdefault(key, paper_id)
    return index


def resolve_supporting_paper_id(link: str, paper_index: Dict[str, str]) -> Optional[str]:
    if not link:
        return None
    trimmed = link.strip()
    candidates = [trimmed, trimmed.casefold(), Path(trimmed).stem, Path(trimmed).stem.casefold(), normalize_slug(trimmed)]
    for candidate in candidates:
        if not candidate:
            continue
        paper_id = paper_index.get(candidate)
        if paper_id:
            return paper_id
    return None


def dedupe_papers(papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    deduped: List[Dict[str, Any]] = []
    seen: Dict[str, bool] = {}
    for paper in papers:
        dedupe_key = str(paper.get("zotero_key") or paper["id"])
        if dedupe_key in seen:
            continue
        seen[dedupe_key] = True
        deduped.append(paper)
    return deduped


def collect_papers(root: Path) -> List[Dict[str, Any]]:
    papers: List[Dict[str, Any]] = []
    project_root = root / "wiki" / "projects"
    if project_root.exists():
        for paper_path in sorted(project_root.glob("*/papers/*/index.md")):
            frontmatter, body = read_markdown(paper_path)
            project = paper_path.relative_to(project_root).parts[0]
            papers.append(
                build_paper_record(
                    root,
                    paper_path,
                    frontmatter,
                    body,
                    project,
                    scalar(frontmatter, "literature_round"),
                    "project-paper",
                )
            )
        for memo_path in sorted(project_root.glob("*/literature-rounds/*/paper-memos/*.md")):
            frontmatter, body = read_markdown(memo_path)
            project = memo_path.relative_to(project_root).parts[0]
            round_name = memo_path.relative_to(project_root).parts[2]
            papers.append(
                build_paper_record(
                    root,
                    memo_path,
                    frontmatter,
                    body,
                    project,
                    round_name,
                    "project-memo",
                )
            )
    library_root = root / "wiki" / "library" / "papers"
    if library_root.exists():
        for card_path in sorted(library_root.glob("*.md")):
            if card_path.name == ".gitkeep":
                continue
            frontmatter, body = read_markdown(card_path)
            projects = list_value(frontmatter, "project_core_for") or list_value(frontmatter, "projects")
            project = projects[0] if projects else ""
            papers.append(
                build_paper_record(
                    root,
                    card_path,
                    frontmatter,
                    body,
                    project,
                    scalar(frontmatter, "literature_round"),
                    "durable-card",
                )
            )
    return papers


def count_search_candidates(search_path: Path) -> int:
    if not search_path.exists():
        return 0
    _, body = read_markdown(search_path)
    section = extract_section(body, "Accepted Candidates")
    count = 0
    for line in section.splitlines():
        if not line.strip().startswith("|"):
            continue
        if is_table_separator_row(line):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if not cells or cells[0].lower() in {"paper", ""}:
            continue
        if len(cells) < 2:
            continue
        count += 1
    return count


def parse_zotero_key(value: str) -> str:
    text = str(value or "").strip()
    if text.startswith("zotero:item:"):
        return text.split("zotero:item:", 1)[1].strip()
    return text


def parse_markdown_table(section: str) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    headers: List[str] = []
    for line in section.splitlines():
        if not line.strip().startswith("|") or is_table_separator_row(line):
            continue
        cells = split_markdown_table_row(line)
        if not headers:
            headers = [normalize_slug(cell).replace("-", "_") for cell in cells]
            continue
        if len(cells) < len(headers):
            cells.extend([""] * (len(headers) - len(cells)))
        rows.append(dict(zip(headers, cells)))
    return rows


def split_markdown_table_row(line: str) -> List[str]:
    text = line.strip()
    if text.startswith("|"):
        text = text[1:]
    if text.endswith("|"):
        text = text[:-1]
    cells: List[str] = []
    current: List[str] = []
    wikilink_depth = 0
    i = 0
    while i < len(text):
        pair = text[i : i + 2]
        if pair == "[[":
            wikilink_depth += 1
            current.append(pair)
            i += 2
            continue
        if pair == "]]" and wikilink_depth:
            wikilink_depth -= 1
            current.append(pair)
            i += 2
            continue
        char = text[i]
        if char == "|" and wikilink_depth == 0:
            cells.append("".join(current).strip())
            current = []
        else:
            current.append(char)
        i += 1
    cells.append("".join(current).strip())
    return cells


def graph_cell_text(value: str) -> str:
    return clean_markdown_text(str(value or ""))


def graph_refs(value: str) -> List[str]:
    text = graph_cell_text(value)
    refs = re.findall(r"\b(?:Q|C|E|W|L|RL|TL)\d+\b", text)
    if refs:
        return refs
    return [
        item.strip()
        for item in re.split(r"[,;，；]\s*", text)
        if item.strip() and item.strip().lower() not in {"none", "n/a"}
    ]


def graph_node(kind: str, row: Dict[str, str]) -> Optional[Dict[str, Any]]:
    node_id = graph_cell_text(row.get("id", ""))
    if not node_id:
        return None
    label_key = {
        "question": "question",
        "claim": "claim",
        "evidence": "evidence",
        "warrant": "warrant",
        "limitation": "limitation",
    }[kind]
    subtitle_key = {
        "question": "role",
        "claim": "status",
        "evidence": "evidence_kind",
        "warrant": "basis",
        "limitation": "severity",
    }[kind]
    return {
        "id": node_id,
        "kind": kind,
        "label": graph_cell_text(row.get(label_key, "")),
        "subtitle": graph_cell_text(row.get(subtitle_key, "")),
        "status": graph_cell_text(row.get("status", "")),
        "confidence": graph_cell_text(row.get("confidence", "")),
        "human_review": graph_cell_text(row.get("human_review", "")),
        "source_refs": graph_cell_text(row.get("source_refs", "")),
        "bounds": graph_refs(row.get("bounds", "")),
    }


def graph_ref_local_id(value: str) -> str:
    text = graph_cell_text(value)
    if text.startswith(("project:", "paper:", "program:")) and ":" in text:
        return text.rsplit(":", 1)[-1]
    return text


def graph_ref_local_ids(values: List[str]) -> List[str]:
    return [item for item in (graph_ref_local_id(value) for value in values) if item]


def snapshot_node_subtitle(node: Dict[str, Any]) -> str:
    kind = str(node.get("node_type") or "").lower()
    metadata = node.get("metadata") if isinstance(node.get("metadata"), dict) else {}
    key = {
        "question": "role",
        "claim": "status",
        "evidence": "evidence_kind",
        "warrant": "basis",
        "limitation": "severity",
    }.get(kind, "")
    if key and metadata.get(key):
        return str(metadata[key])
    return str(node.get("status") or "")


def snapshot_to_project_graph(root: Path, snapshot_path: Path) -> Optional[Dict[str, Any]]:
    if not snapshot_path.name.endswith(".graph.json"):
        return None
    project = snapshot_path.name[: -len(".graph.json")]
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    report_path = root / "wiki" / "projects" / project / "project-understanding-graph.md"
    frontmatter: Dict[str, Any] = {}
    if report_path.exists():
        frontmatter, _ = read_markdown(report_path)
    nodes = [
        {
            "id": graph_ref_local_id(str(node.get("local_id") or node.get("node_id") or "")),
            "kind": str(node.get("node_type") or "").lower(),
            "label": str(node.get("text") or ""),
            "subtitle": snapshot_node_subtitle(node),
            "status": str(node.get("status") or ""),
            "confidence": str(node.get("confidence") or ""),
            "human_review": str(node.get("human_review") or ""),
            "source_refs": ", ".join(str(item) for item in node.get("source_refs", []) if item),
            "bounds": graph_ref_local_ids((node.get("metadata") or {}).get("bounds", [])),
        }
        for node in snapshot.get("nodes", [])
        if node.get("local_id") or node.get("node_id")
    ]
    reasoning_links: List[Dict[str, Any]] = []
    translation_links: List[Dict[str, Any]] = []
    for link in snapshot.get("links", []):
        link_type = link.get("link_type")
        if link_type == "ReasoningLink":
            reasoning_links.append(
                {
                    "id": graph_ref_local_id(str(link.get("local_id") or link.get("link_id") or "")),
                    "premises": graph_ref_local_ids(link.get("from_nodes", [])),
                    "relation": str(link.get("relation") or ""),
                    "target": ", ".join(graph_ref_local_ids(link.get("to_nodes", []))),
                    "warrant": ", ".join(graph_ref_local_ids(link.get("warrant_nodes", []))),
                    "limitations": graph_ref_local_ids(link.get("limitation_nodes", [])),
                    "confidence": str(link.get("confidence") or ""),
                }
            )
        elif link_type == "TranslationLink":
            translation_links.append(
                {
                    "id": graph_ref_local_id(str(link.get("local_id") or link.get("link_id") or "")),
                    "input": str(link.get("source_input") or ", ".join(link.get("from_nodes", []))),
                    "relation": str(link.get("relation") or ""),
                    "project_node": ", ".join(graph_ref_local_ids(link.get("to_nodes", []))),
                    "project_warrant": ", ".join(graph_ref_local_ids(link.get("project_warrant_nodes", []))),
                    "project_limitation": ", ".join(graph_ref_local_ids(link.get("project_limitation_nodes", []))),
                }
            )
    deltas = [
        {
            "id": graph_ref_local_id(str(delta.get("local_id") or delta.get("delta_id") or "")),
            "source_dossier": str(delta.get("source_dossier") or ""),
            "operation": "; ".join(str(item) for item in delta.get("operation", []) if item),
            "change_summary": str(delta.get("summary") or ""),
            "affected": graph_ref_local_ids(delta.get("affected_nodes", [])) + graph_ref_local_ids(delta.get("affected_links", [])),
            "status": str(delta.get("status") or ""),
            "human_review": str(delta.get("human_review") or ""),
        }
        for delta in snapshot.get("deltas", [])
        if delta.get("local_id") or delta.get("delta_id")
    ]
    return {
        "project": project,
        "title": scalar(frontmatter, "title", f"{project} Project Understanding Graph"),
        "path": relpath(snapshot_path, root),
        "report_path": relpath(report_path, root) if report_path.exists() else "",
        "source": "snapshot",
        "updated": str(snapshot.get("generated_at") or scalar(frontmatter, "updated")),
        "nodes": nodes,
        "reasoning_links": [link for link in reasoning_links if link["id"]],
        "translation_links": [link for link in translation_links if link["id"]],
        "deltas": [delta for delta in deltas if delta["id"]],
    }


def collect_project_graphs(root: Path) -> List[Dict[str, Any]]:
    graphs_by_project: Dict[str, Dict[str, Any]] = {}
    snapshots_root = root / "wiki" / "graphs" / "snapshots" / "projects"
    if snapshots_root.exists():
        for snapshot_path in sorted(snapshots_root.glob("*.graph.json")):
            graph = snapshot_to_project_graph(root, snapshot_path)
            if graph:
                graphs_by_project[graph["project"]] = graph
    projects_root = root / "wiki" / "projects"
    if not projects_root.exists():
        return list(graphs_by_project.values())
    node_sections = [
        ("question", "Project Questions"),
        ("claim", "Project Claims"),
        ("evidence", "Evidence"),
        ("warrant", "Warrants"),
        ("limitation", "Limitations"),
    ]
    for graph_path in sorted(projects_root.glob("*/project-understanding-graph.md")):
        project = graph_path.relative_to(projects_root).parts[0]
        if project in graphs_by_project:
            continue
        frontmatter, body = read_markdown(graph_path)
        nodes: List[Dict[str, Any]] = []
        for kind, section_name in node_sections:
            for row in parse_markdown_table(extract_section(body, section_name)):
                node = graph_node(kind, row)
                if node:
                    nodes.append(node)
        reasoning_links = [
            {
                "id": graph_cell_text(row.get("id", "")),
                "premises": graph_refs(row.get("premises", "")),
                "relation": graph_cell_text(row.get("relation", "")),
                "target": graph_cell_text(row.get("target", "")),
                "warrant": graph_cell_text(row.get("warrant", "")),
                "limitations": graph_refs(row.get("limitations", "")),
                "confidence": graph_cell_text(row.get("confidence", "")),
            }
            for row in parse_markdown_table(extract_section(body, "Reasoning Links"))
        ]
        translation_links = [
            {
                "id": graph_cell_text(row.get("id", "")),
                "input": graph_cell_text(row.get("paper_side_or_source_side_input", "")),
                "relation": graph_cell_text(row.get("relation", "")),
                "project_node": graph_cell_text(row.get("project_node", "")),
                "project_warrant": graph_cell_text(row.get("project_warrant", "")),
                "project_limitation": graph_cell_text(row.get("project_limitation", "")),
            }
            for row in parse_markdown_table(extract_section(body, "Translation Links"))
        ]
        deltas = [
            {
                "id": graph_cell_text(row.get("delta_id", "")),
                "source_dossier": graph_cell_text(row.get("source_dossier", "")),
                "operation": graph_cell_text(row.get("operation", "")),
                "change_summary": graph_cell_text(row.get("change_summary", "")),
                "affected": graph_refs(row.get("affected_project_nodes_links", "")),
                "status": graph_cell_text(row.get("status", "")),
                "human_review": graph_cell_text(row.get("human_review", "")),
            }
            for row in parse_markdown_table(extract_section(body, "Graph Delta Inbox"))
        ]
        graphs_by_project[project] = {
            "project": project,
            "title": scalar(frontmatter, "title", f"{project} Project Understanding Graph"),
            "path": relpath(graph_path, root),
            "source": "markdown",
            "updated": scalar(frontmatter, "updated"),
            "nodes": nodes,
            "reasoning_links": [link for link in reasoning_links if link["id"]],
            "translation_links": [link for link in translation_links if link["id"]],
            "deltas": [delta for delta in deltas if delta["id"]],
        }
    return [graphs_by_project[project] for project in sorted(graphs_by_project)]


def load_round_decisions(round_dir: Path) -> Dict[str, Dict[str, str]]:
    decisions_path = round_dir / "review-decisions.md"
    if not decisions_path.exists():
        return {}
    _, body = read_markdown(decisions_path)
    decisions: Dict[str, Dict[str, str]] = {}
    for row in parse_markdown_table(extract_section(body, "Decisions")):
        zotero_key = parse_zotero_key(row.get("zotero", ""))
        if zotero_key:
            decisions[zotero_key] = row
    return decisions


def memo_index_for_round(papers: List[Dict[str, Any]], project: str, round_name: str) -> Dict[str, Dict[str, Any]]:
    index: Dict[str, Dict[str, Any]] = {}
    for paper in papers:
        if paper.get("project") != project or paper.get("literature_round") != round_name:
            continue
        zotero_key = str(paper.get("zotero_key") or "")
        if zotero_key:
            index[zotero_key] = paper
    return index


def collect_rounds(root: Path, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rounds: List[Dict[str, Any]] = []
    rounds_root = root / "wiki" / "projects"
    if not rounds_root.exists():
        return rounds

    for round_dir in sorted(rounds_root.glob("*/literature-rounds/*")):
        if not round_dir.is_dir():
            continue
        project = round_dir.relative_to(rounds_root).parts[0]
        name = round_dir.name
        search_path = round_dir / "search-results.md"
        synthesis_path = round_dir / "evidence-synthesis.md"
        summary = ""
        if search_path.exists():
            _, search_body = read_markdown(search_path)
            summary = first_sentence(extract_section(search_body, "Search Contract"), limit=260)
            if not summary:
                summary = first_sentence(extract_section(search_body, "Summary"), limit=260)
        questions = extract_section(search_body if search_path.exists() else "", "Open Questions")
        if not questions:
            questions = extract_section(search_body if search_path.exists() else "", "Open Questions For Human Gate")
        open_questions = [line.strip("- ").strip() for line in questions.splitlines() if line.strip().startswith("- ")]

        round_papers = [paper for paper in papers if paper["project"] == project and paper["literature_round"] == name]
        rounds.append(
            {
                "id": f"{project}/{name}",
                "project": project,
                "name": name,
                "path": relpath(round_dir, root),
                "search_results_path": relpath(search_path, root) if search_path.exists() else "",
                "synthesis_path": relpath(synthesis_path, root) if synthesis_path.exists() else "",
                "paper_count": count_search_candidates(search_path),
                "deep_read_count": len(round_papers),
                "summary": summary,
                "open_questions": open_questions,
            }
        )
    return rounds


def collect_round_candidates(root: Path, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    candidates: List[Dict[str, Any]] = []
    rounds_root = root / "wiki" / "projects"
    if not rounds_root.exists():
        return candidates
    for round_dir in sorted(rounds_root.glob("*/literature-rounds/*")):
        search_path = round_dir / "search-results.md"
        if not search_path.exists():
            continue
        project = round_dir.relative_to(rounds_root).parts[0]
        round_name = round_dir.name
        _, body = read_markdown(search_path)
        memo_index = memo_index_for_round(papers, project, round_name)
        decisions = load_round_decisions(round_dir)
        for row in parse_markdown_table(extract_section(body, "Accepted Candidates")):
            title = row.get("paper", "")
            zotero_key = parse_zotero_key(row.get("zotero", ""))
            memo = memo_index.get(zotero_key)
            decision = decisions.get(zotero_key, {})
            review_status = (
                decision.get("review_status")
                or (memo or {}).get("review_status")
                or "candidate"
            )
            candidates.append(
                {
                    "id": f"{project}/{round_name}/{zotero_key or normalize_slug(title)}",
                    "project": project,
                    "round": round_name,
                    "title": title,
                    "zotero_key": zotero_key,
                    "zotero": row.get("zotero", ""),
                    "pdf_status": row.get("pdf_status", ""),
                    "year": row.get("year", "") or (memo or {}).get("year", ""),
                    "venue": row.get("venue", "") or (memo or {}).get("venue", ""),
                    "family": row.get("family", ""),
                    "why_relevant": row.get("why_relevant", ""),
                    "relevance": row.get("confidence", ""),
                    "review_status": str(review_status).strip().lower(),
                    "memo_exists": bool(memo),
                    "memo_path": (memo or {}).get("path", ""),
                    "paper_id": (memo or {}).get("id", ""),
                    "project_core": bool((memo or {}).get("project_core_for")),
                }
            )
    return candidates


def collect_claims(root: Path, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    claims: List[Dict[str, Any]] = []
    paper_index = build_paper_index(papers)
    for synthesis_path in sorted((root / "wiki" / "projects").glob("*/literature-rounds/*/evidence-synthesis.md")):
        project = synthesis_path.relative_to(root / "wiki" / "projects").parts[0]
        _, body = read_markdown(synthesis_path)
        table = extract_section(body, "Claim / Evidence Table")
        for line in table.splitlines():
            if not line.strip().startswith("|") or "---" in line or "Project Claim" in line:
                continue
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if len(cells) < 5:
                continue
            claim = cells[0]
            supporting_links = extract_wikilinks(cells[1])
            resolved: List[str] = []
            unresolved: List[str] = []
            for link in supporting_links:
                paper_id = resolve_supporting_paper_id(link, paper_index)
                if paper_id and paper_id not in resolved:
                    resolved.append(paper_id)
                elif not paper_id:
                    unresolved.append(link)
            claims.append(
                {
                    "id": f"{project}:{slugify(claim)}",
                    "project": project,
                    "claim": claim,
                    "evidence_strength": cells[3],
                    "supporting_papers": resolved,
                    "supporting_paper_labels": unresolved,
                    "caveat": cells[2],
                    "source_path": relpath(synthesis_path, root),
                }
            )
    return claims


def attach_project_cards(
    projects: List[Dict[str, Any]],
    papers: List[Dict[str, Any]],
    rounds: List[Dict[str, Any]],
    round_candidates: List[Dict[str, Any]],
) -> None:
    for project in projects:
        project_id = project["id"]
        questions = project.get("overview", {}).get("current_questions", [])
        project_rounds = [item for item in rounds if item["project"] == project_id]
        active_round = sorted(project_rounds, key=lambda item: item["name"], reverse=True)[0] if project_rounds else None
        gate_progress = {status: 0 for status in sorted(VALID_REVIEW_STATUSES)}
        for candidate in round_candidates:
            if candidate["project"] == project_id:
                status = candidate.get("review_status") or "candidate"
                gate_progress[status] = gate_progress.get(status, 0) + 1
        core_papers = [
            {
                "id": paper["id"],
                "title": paper["title"],
                "review_status": paper["review_status"],
                "path": paper["path"],
            }
            for paper in papers
            if project_id in paper.get("project_core_for", [])
        ][:3]
        project["card"] = {
            "working_question": questions[0] if questions else project.get("overview", {}).get("direction", ""),
            "active_round": active_round,
            "gate_progress": gate_progress,
            "core_papers": core_papers,
            "last_updated": max([file.get("updated", "") for file in project.get("core_files", [])] or [""]),
        }


def attach_stats(
    projects: List[Dict[str, Any]],
    papers: List[Dict[str, Any]],
    rounds: List[Dict[str, Any]],
    claims: List[Dict[str, Any]],
) -> None:
    for project in projects:
        project_id = project["id"]
        project_papers = [paper for paper in papers if paper["project"] == project_id]
        project["stats"] = {
            "candidate_papers": sum(
                1 for paper in project_papers if paper["review_status"] in {"candidate", "triaged", "inbox", "reading"}
            ),
            "summarized_papers": sum(1 for paper in project_papers if paper["review_status"] == "summarized"),
            "approved_papers": sum(1 for paper in project_papers if paper["review_status"] == "approved"),
            "literature_rounds": sum(1 for item in rounds if item["project"] == project_id),
            "claims": sum(1 for item in claims if item["project"] == project_id),
        }


def build_index(root: Path) -> Dict[str, Any]:
    root = root.resolve()
    project_graphs = collect_project_graphs(root)
    projects = collect_projects(root, project_graphs)
    ensure_graph_projects(projects, project_graphs, root)
    raw_papers = collect_papers(root)
    papers = dedupe_papers(raw_papers)
    rounds = collect_rounds(root, papers)
    round_candidates = collect_round_candidates(root, raw_papers)
    claims = collect_claims(root, papers)
    attach_stats(projects, papers, rounds, claims)
    attach_project_cards(projects, raw_papers, rounds, round_candidates)
    return {
        "schema_version": "research-browser-v2",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "repo_root": ".",
        "projects": projects,
        "project_graphs": project_graphs,
        "papers": papers,
        "rounds": rounds,
        "round_candidates": round_candidates,
        "claims": claims,
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Build Research Browser dashboard index.")
    parser.add_argument("--repo", default=".", help="Repository root. Default: current directory.")
    parser.add_argument(
        "--output",
        default=".dashboard/index.json",
        help="Output JSON path relative to repo root.",
    )
    args = parser.parse_args(argv)

    root = Path(args.repo).resolve()
    data = build_index(root)
    output_is_absolute = Path(args.output).is_absolute()
    output_path = resolve_output_path(root, args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if output_is_absolute:
        print(f"Wrote {output_path}")
    else:
        print(f"Wrote {output_path.relative_to(root)}")
    print(
        f"Projects: {len(data['projects'])} Papers: {len(data['papers'])} "
        f"Rounds: {len(data['rounds'])} Claims: {len(data['claims'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
