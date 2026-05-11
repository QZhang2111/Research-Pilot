#!/usr/bin/env python3
"""Build small search contracts from Project Understanding Graph gaps."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

THIS_DIR = Path(__file__).resolve().parent
ROOT_DIR = THIS_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from tools.project_gap_cli import detect_gaps


STOPWORDS = {
    "about",
    "active",
    "add",
    "and",
    "answer",
    "answerable",
    "answers",
    "claim",
    "claims",
    "can",
    "directly",
    "does",
    "evidence",
    "evaluation",
    "exposed",
    "find",
    "for",
    "from",
    "have",
    "into",
    "link",
    "links",
    "mechanism",
    "method",
    "model",
    "models",
    "need",
    "needs",
    "question",
    "reasoning",
    "should",
    "subquestions",
    "support",
    "supports",
    "that",
    "this",
    "what",
    "when",
    "where",
    "which",
    "with",
}

DOMAIN_EXPANSION_RULES = [
    (
        {"generative", "generation"},
        [
            "image generation",
            "video generation",
            "generative world model",
            "world knowledge",
        ],
    ),
    (
        {"interaction", "action", "affordance"},
        [
            "action-conditioned",
            "affordance grounding",
            "interaction prior",
            "object affordance",
        ],
    ),
    (
        {"robot", "embodied", "affordance", "interaction"},
        [
            "robot control",
            "robot manipulation",
            "embodied reasoning",
            "under-specified tasks",
        ],
    ),
    (
        {"vision", "visual", "image", "video"},
        [
            "vision-language model",
            "visual representation",
            "dense visual feature",
        ],
    ),
]


def resolve_repo(value: str) -> Path:
    return Path(value).resolve()


def compact_space(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def keywords(value: str, limit: int = 10) -> List[str]:
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9-]{2,}", value.lower())
    seen: set[str] = set()
    result: List[str] = []
    for token in tokens:
        token = token.strip("-")
        if token in STOPWORDS or token in seen:
            continue
        seen.add(token)
        result.append(token)
        if len(result) >= limit:
            break
    return result


def normalized_tokens(value: str) -> set[str]:
    return set(keywords(value, limit=200))


def unique_values(values: Iterable[str]) -> List[str]:
    seen: set[str] = set()
    result: List[str] = []
    for value in values:
        text = compact_space(value)
        key = text.lower()
        if not text or key in seen:
            continue
        seen.add(key)
        result.append(text)
    return result


def infer_domain_expansions(text: str) -> List[str]:
    token_set = normalized_tokens(text)
    expansions: List[str] = []
    for triggers, values in DOMAIN_EXPANSION_RULES:
        if token_set.intersection(triggers):
            expansions.extend(values)
    return unique_values(expansions)


def infer_required_match_groups(text: str) -> List[List[str]]:
    token_set = normalized_tokens(text)
    groups: List[List[str]] = []
    if "generative" in token_set or "generation" in token_set:
        groups.append(["generative", "image generation", "video generation", "generative world model", "world knowledge", "robot control"])
    elif "affordance" in token_set and ("interaction" in token_set or "action" in token_set):
        groups.append(["affordance", "affordance grounding", "action-conditioned", "interaction prior", "object affordance"])
    return groups


def find_gap(root: Path, project: str, target_id: str, gap_type: str = "") -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    report = detect_gaps(root, project, limit=0)
    if not report.get("valid"):
        return None, report
    for item in report.get("gaps", []):
        if item.get("target", {}).get("id") != target_id:
            continue
        if gap_type and item.get("gap_type") != gap_type:
            continue
        return item, report
    return None, report


def build_queries(gap: Dict[str, Any]) -> List[Dict[str, str]]:
    target = gap["target"]
    target_text = compact_space(target.get("text", ""))
    evidence_need = compact_space(gap.get("evidence_need", ""))
    terms = keywords(f"{target_text} {evidence_need}", limit=8)
    expansions = infer_domain_expansions(f"{target_text} {evidence_need}")
    compact_terms = " ".join(terms)
    compact_expansions = " ".join(expansions[:5])
    queries = [
        {
            "family": "direct-gap",
            "query": target_text,
            "why": "Search directly for papers addressing the target Q/C gap.",
        },
        {
            "family": "evidence-need",
            "query": f"{compact_terms} evidence benchmark",
            "why": "Find papers likely to supply evidence, benchmark, or empirical support.",
        },
        {
            "family": "method-or-mechanism",
            "query": f"{compact_terms} method mechanism evaluation",
            "why": "Find methods or mechanisms that could close the gap.",
        },
        {
            "family": "domain-expanded",
            "query": f"{compact_terms} {compact_expansions}",
            "why": "Use project-domain expansions to reduce generic keyword noise.",
        },
    ]
    return [item for item in queries if item["query"].strip()]


def build_search_contract(root: Path, project: str, target_id: str, gap_type: str = "", target_count: int = 5) -> Dict[str, Any]:
    gap, report = find_gap(root, project, target_id, gap_type=gap_type)
    if not gap:
        return {
            "valid": False,
            "project": project,
            "error": f"gap not found for target: {target_id}",
            "gap_report_valid": bool(report.get("valid")),
        }
    target = gap["target"]
    seed_text = f"{target.get('text', '')} {gap.get('evidence_need', '')}"
    domain_expansions = infer_domain_expansions(seed_text)
    contract = {
        "contract_name": f"Gap Search Contract: {target['id']} {gap['gap_type']}",
        "mode": "targeted-gap",
        "purpose": f"Use this Evidence Need to find papers or experiments that close graph gap {target['id']}.",
        "source_gap": gap,
        "search_families": ["direct-gap", "evidence-need", "method-or-mechanism", "domain-expanded"],
        "queries": build_queries(gap),
        "seed_terms": keywords(seed_text, limit=12),
        "domain_expansions": domain_expansions,
        "required_match_groups": infer_required_match_groups(seed_text),
        "known_seeds": [],
        "exclude_or_deprioritize": ["keyword-only matches", "papers without stable identity"],
        "target_count": target_count,
        "success_signal": "At least one verified paper or experiment can supply evidence, warrant, limitation-closing result, or a reason to revise the target graph node/link.",
        "do_not_assume": [
            "A search lead is not a project-core paper.",
            "A search lead is not a graph update.",
            "A paper result must pass deep-read and delta human gate before changing Q/C/E/W/L/RL/TL.",
        ],
        "next_skill": "paper-discovery-intake",
    }
    return {"valid": True, "project": project, "search_contract": contract, "effects": {"writes": [], "graph_events": []}}


def arxiv_id_from_url(value: str) -> str:
    match = re.search(r"/abs/([^/]+)$", value)
    if not match:
        return ""
    return re.sub(r"v\d+$", "", match.group(1))


def parse_arxiv_feed(feed_text: str, source_query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    root = ET.fromstring(feed_text)
    ns = {"a": "http://www.w3.org/2005/Atom"}
    leads: List[Dict[str, Any]] = []
    for entry in root.findall("a:entry", ns):
        title = compact_space(entry.findtext("a:title", default="", namespaces=ns))
        summary = compact_space(entry.findtext("a:summary", default="", namespaces=ns))
        published = entry.findtext("a:published", default="", namespaces=ns)
        entry_id = entry.findtext("a:id", default="", namespaces=ns)
        authors = [compact_space(node.findtext("a:name", default="", namespaces=ns)) for node in entry.findall("a:author", ns)]
        authors = [author for author in authors if author]
        url = entry_id
        pdf_url = ""
        for link in entry.findall("a:link", ns):
            href = link.attrib.get("href", "")
            if link.attrib.get("type") == "application/pdf":
                pdf_url = href
            elif link.attrib.get("rel") == "alternate":
                url = href
        leads.append(
            {
                "title": title,
                "authors": authors,
                "year": published[:4],
                "venue": "arXiv",
                "doi": "",
                "arxiv": arxiv_id_from_url(entry_id),
                "url": url,
                "pdf_url": pdf_url,
                "source": "arxiv",
                "source_query": source_query,
                "why_relevant": "Matches gap-driven search query; requires Candidate Triage Pass before Zotero intake.",
                "relevance_confidence": "low",
                "triage_status": "lead",
                "human_review": "pending",
                "abstract": summary,
            }
        )
        if len(leads) >= max_results:
            break
    return leads


def content_value(content: Dict[str, Any], key: str, fallback: Any = "") -> Any:
    value = content.get(key, fallback)
    if isinstance(value, dict) and "value" in value:
        return value.get("value", fallback)
    return value


def parse_openreview_notes(data: Dict[str, Any], source_query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    leads: List[Dict[str, Any]] = []
    for note in data.get("notes", []):
        content = note.get("content") or {}
        title = compact_space(content_value(content, "title", ""))
        abstract = compact_space(content_value(content, "abstract", ""))
        authors = content_value(content, "authors", [])
        if isinstance(authors, str):
            authors = [authors]
        venue = compact_space(content_value(content, "venue", content_value(content, "venueid", "OpenReview")))
        year = ""
        cdate = note.get("cdate")
        if isinstance(cdate, int) and cdate > 0:
            year = dt.datetime.fromtimestamp(cdate / 1000, tz=dt.UTC).strftime("%Y")
        forum = note.get("forum") or note.get("id") or ""
        leads.append(
            {
                "title": title,
                "authors": [compact_space(author) for author in authors if compact_space(author)],
                "year": year,
                "venue": venue or "OpenReview",
                "doi": "",
                "arxiv": "",
                "openreview_id": note.get("id") or "",
                "url": f"https://openreview.net/forum?id={forum}" if forum else "",
                "pdf_url": "",
                "source": "openreview",
                "source_query": source_query,
                "why_relevant": "Matches gap-driven OpenReview query; requires Candidate Triage Pass before Zotero intake.",
                "relevance_confidence": "low",
                "triage_status": "lead",
                "human_review": "pending",
                "abstract": abstract,
            }
        )
        if len(leads) >= max_results:
            break
    return leads


def build_arxiv_query(query: str, *, operator: str = "AND", max_terms: int = 5) -> str:
    terms = keywords(query, limit=max_terms)
    if not terms:
        return f'all:"{query}"'
    return f" {operator} ".join(f"all:{term}" for term in terms)


def fetch_arxiv_query(search_query: str, source_query: str, max_results: int) -> List[Dict[str, Any]]:
    params = urllib.parse.urlencode(
        {
            "search_query": search_query,
            "start": 0,
            "max_results": max_results,
            "sortBy": "relevance",
            "sortOrder": "descending",
        }
    )
    url = f"https://export.arxiv.org/api/query?{params}"
    request = urllib.request.Request(url, headers={"User-Agent": "Research Pilot/0.1"})
    with urllib.request.urlopen(request, timeout=15) as response:
        return parse_arxiv_feed(response.read().decode("utf-8"), source_query=source_query, max_results=max_results)


def search_arxiv(query: str, max_results: int = 3) -> List[Dict[str, Any]]:
    leads = fetch_arxiv_query(build_arxiv_query(query, operator="AND", max_terms=5), query, max_results)
    if leads:
        return leads
    return fetch_arxiv_query(build_arxiv_query(query, operator="OR", max_terms=5), query, max_results)


def fetch_json(url: str) -> Dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": "Research Pilot/0.1"})
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def search_openreview(query: str, max_results: int = 3) -> List[Dict[str, Any]]:
    params = urllib.parse.urlencode({"term": query, "content": "all", "source": "forum", "limit": max_results})
    url = f"https://api2.openreview.net/notes/search?{params}"
    return parse_openreview_notes(fetch_json(url), source_query=query, max_results=max_results)


def lead_text(lead: Dict[str, Any]) -> str:
    return f"{lead.get('title', '')} {lead.get('abstract', '')}".lower()


def score_lead(lead: Dict[str, Any], contract: Dict[str, Any]) -> Dict[str, Any]:
    text = lead_text(lead)
    seed_terms = [term for term in contract.get("seed_terms", []) if len(term) >= 4]
    expansion_terms = list(contract.get("domain_expansions", []))
    matched_seed = [term for term in seed_terms if term.lower() in text]
    matched_expansions = [term for term in expansion_terms if term.lower() in text]
    matched_terms = unique_values([*matched_seed, *matched_expansions])
    missing_terms = [term for term in seed_terms[:8] if term not in matched_seed]
    required_groups = contract.get("required_match_groups") or []
    missing_required_groups = [
        group
        for group in required_groups
        if not any(str(term).lower() in text for term in group)
    ]
    score = len(matched_seed) + (2 * len(matched_expansions))
    result = dict(lead)
    result["fit_score"] = score
    result["matched_terms"] = matched_terms
    result["missing_terms"] = missing_terms
    result["missing_required_groups"] = missing_required_groups
    if score >= 6:
        result["relevance_confidence"] = "high"
    elif score >= 3:
        result["relevance_confidence"] = "medium"
    else:
        result["relevance_confidence"] = "low"
    if missing_required_groups:
        result["triage_status"] = "noise"
        result["reject_reason"] = "Missing required anchor term group for this gap."
    elif score < 3:
        result["triage_status"] = "noise"
        result["reject_reason"] = "Too few matched project/domain terms; likely keyword noise."
    else:
        result["triage_status"] = "lead"
        result["reject_reason"] = ""
    return result


def dedupe_key(lead: Dict[str, Any]) -> str:
    title = compact_space(str(lead.get("title") or "")).lower()
    if title:
        return re.sub(r"[^a-z0-9]+", " ", title).strip()
    return str(lead.get("url") or lead.get("arxiv") or lead.get("openreview_id") or "")


def dedupe_leads(leads: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    best: Dict[str, Dict[str, Any]] = {}
    for lead in leads:
        key = dedupe_key(lead)
        if not key:
            continue
        current = best.get(key)
        if current is None or int(lead.get("fit_score") or 0) > int(current.get("fit_score") or 0):
            best[key] = dict(lead)
    return list(best.values())


def rank_and_filter_leads(leads: Sequence[Dict[str, Any]], contract: Dict[str, Any], include_noise: bool = False) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    scored = dedupe_leads([score_lead(lead, contract) for lead in leads])
    scored.sort(key=lambda item: (-int(item.get("fit_score") or 0), item.get("title", "")))
    kept = [lead for lead in scored if include_noise or lead.get("triage_status") != "noise"]
    discarded = [lead for lead in scored if lead.get("triage_status") == "noise"]
    return kept, discarded


def project_fit_from_score(score: int) -> str:
    if score >= 6:
        return "high"
    if score >= 3:
        return "medium"
    return "low"


def recommendation_from_fit(project_fit: str) -> str:
    if project_fit == "high":
        return "deep-read"
    if project_fit == "medium":
        return "keep-candidate"
    return "later"


def first_sentence(value: str, limit: int = 240) -> str:
    text = compact_space(value)
    parts = re.split(r"(?<=[.!?])\s+", text, maxsplit=1)
    sentence = parts[0] if parts else text
    return sentence[:limit].rstrip()


def candidate_record_from_lead(lead: Dict[str, Any], contract: Dict[str, Any], project: str) -> Dict[str, Any]:
    score = int(lead.get("fit_score") or 0)
    project_fit = project_fit_from_score(score)
    recommendation = recommendation_from_fit(project_fit)
    matched_terms = list(lead.get("matched_terms") or [])
    one_line = first_sentence(str(lead.get("abstract") or ""))
    title = str(lead.get("title") or "")
    source_gap = contract.get("source_gap") or {}
    target = source_gap.get("target") or {}
    source = str(lead.get("source") or "")
    return {
        "title": title,
        "authors": list(lead.get("authors") or []),
        "year": str(lead.get("year") or ""),
        "venue": str(lead.get("venue") or ""),
        "doi": str(lead.get("doi") or ""),
        "arxiv": str(lead.get("arxiv") or ""),
        "openreview_id": str(lead.get("openreview_id") or ""),
        "url": str(lead.get("url") or ""),
        "pdf_url": str(lead.get("pdf_url") or ""),
        "source": source,
        "source_query": str(lead.get("source_query") or ""),
        "contract_name": str(contract.get("contract_name") or ""),
        "project": project,
        "source_gap_target": str(target.get("id") or ""),
        "source_gap_type": str(source_gap.get("gap_type") or ""),
        "why_found": f"Gap-driven search lead from {source}; matched terms: {', '.join(matched_terms) or 'none'}.",
        "why_relevant": str(lead.get("why_relevant") or "Matches gap-driven search contract."),
        "triage_status": "needs-triage",
        "triage_read_level": "metadata-only",
        "one_line_contribution": one_line,
        "project_fit": project_fit,
        "method_family": "",
        "evidence_type": "paper-lead-for-evidence-need",
        "why_deep_read": "高匹配度线索，可能直接回答当前 Evidence Need。" if recommendation == "deep-read" else "",
        "why_not_deep_read": "需要 Candidate Triage Pass 验证，不应仅凭关键词进入深读。" if recommendation != "deep-read" else "",
        "risk": "metadata-only lead; requires identity verification, duplicate check, and Candidate Triage Pass before Zotero intake.",
        "recommendation": recommendation,
        "seed_link": str(target.get("id") or ""),
        "relevance_confidence": str(lead.get("relevance_confidence") or "low"),
        "suggested_topics": matched_terms,
        "suggested_roles": ["gap-evidence-candidate"],
        "duplicate_check": "pending",
        "human_review": "pending",
        "fit_score": score,
    }


def build_discovery_handoff(search_result: Dict[str, Any]) -> Dict[str, Any]:
    if not search_result.get("valid"):
        return search_result
    project = str(search_result.get("project") or "")
    contract = search_result.get("search_contract") or {}
    records = [candidate_record_from_lead(lead, contract, project) for lead in search_result.get("candidate_leads", [])]
    return {
        "valid": True,
        "project": project,
        "search_contract": contract,
        "candidate_records": records,
        "discarded_leads": list(search_result.get("discarded_leads") or []),
        "counts": {"candidate_records": len(records), "discarded_leads": len(search_result.get("discarded_leads") or [])},
        "next_skill": "paper-discovery-intake",
        "effects": {"writes": [], "zotero_writes": [], "graph_events": []},
    }


def frontmatter_title(text: str, fallback: str) -> str:
    match = re.search(r"^title:\s*[\"']?(.+?)[\"']?\s*$", text, re.MULTILINE)
    return compact_space(match.group(1)) if match else fallback


def frontmatter_year(text: str) -> str:
    match = re.search(r"^year:\s*[\"']?(\d{4})[\"']?\s*$", text, re.MULTILINE)
    return match.group(1) if match else ""


def memory_candidate_allowed(path: Path, text: str) -> bool:
    lowered_name = path.name.lower()
    lowered_text = text[:1200].lower()
    if lowered_name in {"gap-search.md", "paper-discovery-handoff.md"}:
        return False
    if "gap-driven-search" in lowered_text or "paper-discovery-intake" in lowered_text:
        if re.search(r"^type:\s*artifact\s*$", text, re.MULTILINE):
            return False
    return True


def search_existing_memory(root: Path, project: str, contract: Dict[str, Any], max_results: int = 5) -> List[Dict[str, Any]]:
    roots = [
        root / "wiki" / "library" / "papers",
        root / "wiki" / "projects" / project / "papers",
        root / "wiki" / "projects" / project / "literature-rounds",
    ]
    raw_leads: List[Dict[str, Any]] = []
    for base in roots:
        if not base.exists():
            continue
        for path in sorted(base.rglob("*.md")):
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if not memory_candidate_allowed(path, text):
                continue
            lead = {
                "title": frontmatter_title(text, path.stem.replace("-", " ")),
                "authors": [],
                "year": frontmatter_year(text),
                "venue": "wiki",
                "doi": "",
                "arxiv": "",
                "url": str(path.relative_to(root)),
                "pdf_url": "",
                "source": "wiki-memory",
                "source_query": contract.get("contract_name", ""),
                "why_relevant": "Existing wiki memory matched gap-driven search terms.",
                "relevance_confidence": "low",
                "triage_status": "lead",
                "human_review": "pending",
                "abstract": compact_space(text[:2000]),
            }
            raw_leads.append(lead)
    kept, _ = rank_and_filter_leads(raw_leads, contract)
    return kept[:max_results]


def preferred_search_query(contract: Dict[str, Any]) -> str:
    queries = contract.get("queries", [])
    for item in queries:
        if item.get("family") == "domain-expanded":
            return str(item.get("query") or "")
    for item in queries:
        if item.get("family") == "evidence-need":
            return str(item.get("query") or "")
    return str(queries[0].get("query") or "") if queries else ""


def artifact_slug(contract: Dict[str, Any]) -> str:
    target = contract.get("source_gap", {}).get("target", {}).get("id", "gap")
    return f"{dt.date.today().isoformat()}-gap-{target.lower()}-search"


def render_search_artifact(result: Dict[str, Any]) -> str:
    contract = result.get("search_contract", {})
    leads = result.get("candidate_leads", [])
    discarded = result.get("discarded_leads", [])
    return "\n".join(
        [
            "---",
            f"title: \"Gap-Driven Search Artifact - {contract.get('contract_name', '')}\"",
            "type: artifact",
            f"created: {dt.date.today().isoformat()}",
            f"updated: {dt.date.today().isoformat()}",
            "domains: [generative-models, embodied-intelligence, scene-understanding]",
            "tags: [gap-driven-search, evidence-need]",
            "aliases: []",
            "sources: []",
            "status: candidate",
            "human_review: pending",
            "confidence: medium",
            "---",
            "",
            "# Gap-Driven Search Artifact",
            "",
            "## Search Contract",
            "",
            "```json",
            json.dumps(contract, ensure_ascii=False, indent=2, sort_keys=True),
            "```",
            "",
            "## Candidate Leads",
            "",
            "```json",
            json.dumps(leads, ensure_ascii=False, indent=2, sort_keys=True),
            "```",
            "",
            "## Discarded Leads",
            "",
            "```json",
            json.dumps(discarded, ensure_ascii=False, indent=2, sort_keys=True),
            "```",
            "",
            "## Boundary",
            "",
            "This artifact is not graph truth and not Zotero intake. Use `paper-discovery-intake` for real candidate intake.",
            "",
        ]
    )


def render_discovery_handoff_artifact(result: Dict[str, Any]) -> str:
    contract = result.get("search_contract", {})
    records = result.get("candidate_records", [])
    discarded = result.get("discarded_leads", [])
    return "\n".join(
        [
            "---",
            f"title: \"Paper Discovery Intake Handoff - {contract.get('contract_name', '')}\"",
            "type: artifact",
            f"created: {dt.date.today().isoformat()}",
            f"updated: {dt.date.today().isoformat()}",
            "domains: [generative-models, embodied-intelligence, scene-understanding]",
            "tags: [gap-driven-search, paper-discovery-intake, candidate-triage]",
            "aliases: []",
            "sources: []",
            "status: candidate",
            "human_review: pending",
            "confidence: medium",
            "---",
            "",
            "# Paper Discovery Intake Handoff",
            "",
            "This artifact converts kept gap-search leads into paper-discovery candidate records.",
            "",
            "Zotero writes: none",
            "Graph events: none",
            "Next skill: `paper-discovery-intake`",
            "",
            "## Search Contract",
            "",
            "```json",
            json.dumps(contract, ensure_ascii=False, indent=2, sort_keys=True),
            "```",
            "",
            "## Candidate Records",
            "",
            "```json",
            json.dumps(records, ensure_ascii=False, indent=2, sort_keys=True),
            "```",
            "",
            "## Discarded Leads",
            "",
            "```json",
            json.dumps(discarded, ensure_ascii=False, indent=2, sort_keys=True),
            "```",
            "",
            "## Boundary",
            "",
            "`triage_status: needs-triage` means the lead is ready for Candidate Triage Pass, not Zotero intake or project approval.",
            "",
        ]
    )


def save_search_artifact(root: Path, project: str, result: Dict[str, Any]) -> str:
    contract = result.get("search_contract", {})
    out_dir = root / "wiki" / "projects" / project / "literature-rounds" / artifact_slug(contract)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "gap-search.md"
    out_path.write_text(render_search_artifact(result), encoding="utf-8")
    return str(out_path.relative_to(root))


def save_discovery_handoff_artifact(root: Path, project: str, result: Dict[str, Any]) -> str:
    contract = result.get("search_contract", {})
    out_dir = root / "wiki" / "projects" / project / "literature-rounds" / artifact_slug(contract)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "paper-discovery-handoff.md"
    out_path.write_text(render_discovery_handoff_artifact(result), encoding="utf-8")
    return str(out_path.relative_to(root))


def search_from_contract(contract_result: Dict[str, Any], source: str, max_results: int, *, include_noise: bool = False, root: Optional[Path] = None) -> Dict[str, Any]:
    if not contract_result.get("valid"):
        return contract_result
    contract = contract_result["search_contract"]
    query = preferred_search_query(contract)
    raw_leads: List[Dict[str, Any]] = []
    search_error = ""
    if source in {"memory", "all"}:
        if root is not None:
            raw_leads.extend(search_existing_memory(root, contract_result["project"], contract, max_results=max_results))
    if source in {"arxiv", "all"}:
        try:
            raw_leads.extend(search_arxiv(query, max_results=max_results))
        except Exception as exc:  # pragma: no cover - network failures are runtime environment.
            search_error = str(exc)
    if source in {"openreview", "all"}:
        try:
            raw_leads.extend(search_openreview(query, max_results=max_results))
        except Exception as exc:  # pragma: no cover - network failures are runtime environment.
            search_error = "; ".join(item for item in [search_error, str(exc)] if item)
    elif source not in {"none", "memory", "arxiv", "all"}:
        return {"valid": False, "project": contract_result["project"], "error": f"unsupported source: {source}"}
    leads, discarded = rank_and_filter_leads(raw_leads, contract, include_noise=include_noise)
    leads = leads[:max_results]
    result = dict(contract_result)
    result["candidate_leads"] = leads
    result["discarded_leads"] = discarded
    result["search"] = {
        "source": source,
        "query": query,
        "max_results": max_results,
        "search_error": search_error,
        "include_noise": include_noise,
        "writes": [],
        "zotero_intake": [],
        "graph_events": [],
    }
    return result


def print_result(result: Dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))


def command_contract(args: argparse.Namespace) -> Tuple[int, Dict[str, Any]]:
    result = build_search_contract(resolve_repo(args.repo), args.project, args.target, gap_type=args.gap_type, target_count=args.target_count)
    return (0 if result.get("valid") else 1), result


def command_search(args: argparse.Namespace) -> Tuple[int, Dict[str, Any]]:
    root = resolve_repo(args.repo)
    contract = build_search_contract(root, args.project, args.target, gap_type=args.gap_type, target_count=args.max_results)
    result = search_from_contract(contract, source=args.source, max_results=args.max_results, include_noise=args.include_noise, root=root)
    if result.get("valid") and args.save_artifact:
        artifact_path = save_search_artifact(root, args.project, result)
        result.setdefault("effects", {}).setdefault("writes", []).append(artifact_path)
        result.setdefault("search", {}).setdefault("writes", []).append(artifact_path)
    return (0 if result.get("valid") else 1), result


def command_handoff(args: argparse.Namespace) -> Tuple[int, Dict[str, Any]]:
    root = resolve_repo(args.repo)
    contract = build_search_contract(root, args.project, args.target, gap_type=args.gap_type, target_count=args.max_results)
    search_result = search_from_contract(contract, source=args.source, max_results=args.max_results, include_noise=args.include_noise, root=root)
    result = build_discovery_handoff(search_result)
    if result.get("valid"):
        artifact_path = save_discovery_handoff_artifact(root, args.project, result)
        result.setdefault("effects", {}).setdefault("writes", []).append(artifact_path)
    return (0 if result.get("valid") else 1), result


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--repo", default=".")
    parser.add_argument("--project", required=True)
    parser.add_argument("--target", required=True, help="Gap target local id, e.g. Q7 or C2.")
    parser.add_argument("--gap-type", default="")
    parser.add_argument("--json", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build and lightly run search contracts from graph gap reports.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    contract = subparsers.add_parser("contract", help="Build a read-only search contract from a graph gap.")
    add_common(contract)
    contract.add_argument("--target-count", type=int, default=5)
    search = subparsers.add_parser("search", help="Run a tiny search from a gap-derived contract.")
    add_common(search)
    search.add_argument("--source", choices=["arxiv", "openreview", "memory", "all", "none"], default="arxiv")
    search.add_argument("--max-results", type=int, default=3)
    search.add_argument("--include-noise", action="store_true")
    search.add_argument("--save-artifact", action="store_true")
    handoff = subparsers.add_parser("handoff", help="Write a paper-discovery-intake handoff artifact from kept leads.")
    add_common(handoff)
    handoff.add_argument("--source", choices=["arxiv", "openreview", "memory", "all", "none"], default="all")
    handoff.add_argument("--max-results", type=int, default=5)
    handoff.add_argument("--include-noise", action="store_true")
    return parser


def dispatch(args: argparse.Namespace) -> Tuple[int, Dict[str, Any]]:
    if args.command == "contract":
        return command_contract(args)
    if args.command == "search":
        return command_search(args)
    if args.command == "handoff":
        return command_handoff(args)
    return 2, {"valid": False, "error": f"unsupported command: {args.command}"}


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    code, result = dispatch(args)
    print_result(result, bool(getattr(args, "json", False)))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
