#!/usr/bin/env python3
"""Read-only experiment proposal generator for Project Understanding Graph claims."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

THIS_DIR = Path(__file__).resolve().parent
ROOT_DIR = THIS_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from tools.graph_store import graph_id_for_project, project_ref, relpath
from tools.project_gap_cli import detect_gaps


INACTIVE_LIFECYCLES = {"retired", "superseded", "merged"}
SUPPORT_RELATIONS = {"supports", "answers", "strengthens"}


def resolve_repo(value: str) -> Path:
    return Path(value).resolve()


def db_path(root: Path) -> Path:
    return root / "wiki" / "graphs" / "graph.db"


def connect(root: Path) -> sqlite3.Connection:
    db = db_path(root)
    if not db.exists():
        raise FileNotFoundError(f"graph database not found: {relpath(db, root)}")
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    return conn


def parse_json(value: str, fallback: Any) -> Any:
    try:
        return json.loads(value or "")
    except json.JSONDecodeError:
        return fallback


def local_id(value: str) -> str:
    return str(value or "").rsplit(":", 1)[-1]


def normalize_ref(project_id: str, value: str) -> str:
    text = str(value or "").strip()
    if text.startswith("project:"):
        return text
    return project_ref(project_id, text)


def active_node(row: sqlite3.Row) -> bool:
    lifecycle = str(row["lifecycle_status"] or "").lower()
    status = str(row["status"] or "").lower()
    return lifecycle not in INACTIVE_LIFECYCLES and status not in {"archived", "rejected", "retired"}


def positioned_values(conn: sqlite3.Connection, table: str, owner_column: str, owner_id: str, value_column: str) -> List[str]:
    rows = conn.execute(
        f"select {value_column} from {table} where {owner_column} = ? order by position",
        (owner_id,),
    ).fetchall()
    return [str(row[0]) for row in rows]


def node_record(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "id": local_id(row["node_id"]),
        "kind": row["node_type"],
        "text": row["text"],
        "confidence": row["confidence"],
        "lifecycle_status": row["lifecycle_status"],
        "human_review": row["human_review"],
        "metadata": parse_json(row["metadata_json"], {}),
    }


def load_node(conn: sqlite3.Connection, project_id: str, record_id: str) -> Optional[sqlite3.Row]:
    return conn.execute(
        "select * from nodes where graph_id = ? and node_id = ?",
        (graph_id_for_project(project_id), normalize_ref(project_id, record_id)),
    ).fetchone()


def load_nodes(conn: sqlite3.Connection, node_ids: Sequence[str]) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for node_id in node_ids:
        row = conn.execute("select * from nodes where node_id = ?", (node_id,)).fetchone()
        if row and active_node(row):
            records.append(node_record(row))
    return records


def link_node_ids(conn: sqlite3.Connection, table: str, link_id: str) -> List[str]:
    return positioned_values(conn, table, "link_id", link_id, "node_id")


def incoming_support_links(conn: sqlite3.Connection, project_id: str, node_id: str) -> List[Dict[str, Any]]:
    rows = conn.execute(
        """
        select links.*
        from links
        join link_to_nodes on link_to_nodes.link_id = links.link_id
        where links.graph_id = ? and link_to_nodes.node_id = ?
        order by links.local_id
        """,
        (graph_id_for_project(project_id), node_id),
    ).fetchall()
    links: List[Dict[str, Any]] = []
    for row in rows:
        if str(row["relation"] or "") not in SUPPORT_RELATIONS:
            continue
        link_id = row["link_id"]
        links.append(
            {
                "id": row["local_id"],
                "kind": row["link_type"],
                "relation": row["relation"],
                "confidence": row["confidence"],
                "from_nodes": load_nodes(conn, link_node_ids(conn, "link_from_nodes", link_id)),
                "to_nodes": load_nodes(conn, link_node_ids(conn, "link_to_nodes", link_id)),
                "warrant_nodes": load_nodes(
                    conn,
                    link_node_ids(conn, "link_warrants", link_id) + link_node_ids(conn, "link_project_warrants", link_id),
                ),
                "limitation_nodes": load_nodes(
                    conn,
                    link_node_ids(conn, "link_limitations", link_id)
                    + link_node_ids(conn, "link_project_limitations", link_id),
                ),
                "source_refs": positioned_values(conn, "link_sources", "link_id", link_id, "source_ref"),
                "payload": parse_json(row["payload_json"], {}),
            }
        )
    return links


def target_gap(root: Path, project_id: str, target_id: str) -> Dict[str, Any]:
    gaps = detect_gaps(root, project_id).get("gaps", [])
    for item in gaps:
        if item.get("target", {}).get("id") == target_id:
            return item
    return {
        "gap_type": "experiment_need",
        "severity": "medium",
        "target": {"id": target_id, "kind": "Claim"},
        "why": "Claim needs project-owned evidence before stronger use.",
        "evidence_need": "Produce direct experimental evidence that tests the claim under project-relevant conditions.",
        "current_support": [],
        "blocking_limitations": [],
        "suggested_action": "Design minimal experiment before strengthening or broadening the claim.",
    }


def combined_text(*parts: Any) -> str:
    values: List[str] = []
    for part in parts:
        if isinstance(part, str):
            values.append(part)
        elif isinstance(part, dict):
            values.extend(str(value) for value in part.values() if isinstance(value, str))
        elif isinstance(part, list):
            values.extend(str(item.get("text", "")) for item in part if isinstance(item, dict))
    return " ".join(values).lower()


def dataset_candidates(text: str) -> List[str]:
    candidates: List[str] = []
    if any(term in text for term in ["agd20k", "affordance", "localization", "grounding"]):
        candidates.extend(["AGD20K", "UMD affordance dataset"])
    if any(term in text for term in ["3d", "planning", "execution", "robot", "embodied"]):
        candidates.extend(["robot manipulation benchmark", "3D affordance / interaction benchmark"])
    if any(term in text for term in ["attention", "vlm", "generative", "image generation"]):
        candidates.append("action-conditioned VLM / generative-model probe set")
    if not candidates:
        candidates.append("small project-owned benchmark or ablation set")
    return list(dict.fromkeys(candidates))


def metric_candidates(text: str) -> List[str]:
    metrics: List[str] = []
    if any(term in text for term in ["localization", "grounding", "region", "heatmap", "mask"]):
        metrics.extend(["KLD / SIM / NSS", "IoU or pointing-game accuracy"])
    if any(term in text for term in ["execution", "planning", "robot", "embodied"]):
        metrics.extend(["task success rate", "action-conditioned success prediction"])
    if any(term in text for term in ["attention", "probe", "feature"]):
        metrics.append("linear probe / attention-to-region alignment")
    if not metrics:
        metrics.append("claim-specific pass/fail metric")
    return list(dict.fromkeys(metrics))


def comparison(text: str) -> str:
    if "geometry" in text and "interaction" in text:
        return "Compare geometry-only, interaction-only, and fused variants under the same benchmark and metric."
    if "attention" in text:
        return "Compare raw attention/probe signal against controlled baselines and shuffled action/object prompts."
    if "dino" in text or "feature" in text:
        return "Compare target representation against frozen-feature baselines and ablations that remove spatial alignment."
    return "Compare the claim method against a minimal baseline and one ablation that removes the claimed causal cue."


def experiment_type(text: str) -> Dict[str, str]:
    if any(term in text for term in ["geometry", "interaction", "fusion", "ablation", "agd20k"]):
        return {
            "type": "benchmark_ablation",
            "label": "Benchmark ablation",
            "rationale": "The claim depends on whether a component or cue improves measured behavior over a comparable baseline.",
        }
    if any(term in text for term in ["attention", "probe", "feature", "representation", "encode", "encoded"]):
        return {
            "type": "mechanism_probe",
            "label": "Mechanism probe",
            "rationale": "The claim depends on whether an internal signal or representation carries the proposed information.",
        }
    if any(term in text for term in ["execution", "planning", "robot", "embodied"]):
        return {
            "type": "embodied_validation",
            "label": "Embodied validation",
            "rationale": "The claim is bounded by execution, planning, or embodied-use limitations.",
        }
    if any(term in text for term in ["3d", "dataset", "benchmark", "out-of-domain", "generalization"]):
        return {
            "type": "benchmark_extension",
            "label": "Benchmark extension",
            "rationale": "The claim needs a benchmark condition beyond current evidence coverage.",
        }
    return {
        "type": "controlled_comparison",
        "label": "Controlled comparison",
        "rationale": "The claim needs direct evidence against a minimal baseline or counterfactual.",
    }


def decomposition_type(testability: Dict[str, Any]) -> Dict[str, str]:
    return {
        "type": "claim_decomposition",
        "label": "Claim decomposition",
        "rationale": testability["reason"],
    }


def minimal_viable_experiment(testability: Dict[str, Any]) -> str:
    if testability["recommendation"] == "split_before_experiment":
        return (
            "Do not run a direct experiment for this claim yet. First split it into directly testable child claims; "
            "then create one Evidence Production proposal per child claim."
        )
    return (
        "Run the smallest controlled comparison that tests the target claim against its strongest current limitation; "
        "record setup, metric, and failure cases before proposing any graph update."
    )


def evidence_value_score(
    *,
    source_gap: Dict[str, Any],
    experiment_kind: Dict[str, str],
    support_links: Sequence[Dict[str, Any]],
    limitations: Sequence[Dict[str, Any]],
    warrants: Sequence[Dict[str, Any]],
    context_limitations: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    score = 4
    reasons: List[str] = ["Targets an active project claim."]
    if limitations:
        score += 2
        reasons.append("Directly addresses blocking limitations.")
    if warrants:
        score += 1
        reasons.append("Can test an explicit project warrant.")
    if support_links:
        score += 1
        reasons.append("Builds on existing support instead of starting cold.")
    if source_gap.get("severity") == "high":
        score += 1
        reasons.append("Source gap has high severity.")
    if experiment_kind["type"] in {"benchmark_ablation", "mechanism_probe"}:
        score += 1
        reasons.append("Experiment type can usually produce interpretable graph evidence.")
    if context_limitations:
        reasons.append("Translation context exists but should not count as direct support.")
    score = max(1, min(10, score))
    if score >= 8:
        level = "high"
    elif score >= 5:
        level = "medium"
    else:
        level = "low"
    return {
        "score": score,
        "level": level,
        "cost": "medium",
        "risk": "medium",
        "reasons": reasons,
    }


def claim_testability(claim: Dict[str, Any], support_links: Sequence[Dict[str, Any]], text: str) -> Dict[str, Any]:
    supporting_claims = sorted(
        {
            node["id"]
            for link in support_links
            for node in link["from_nodes"]
            if node.get("kind") == "Claim"
        }
    )
    evidence_supports = sorted(
        {
            node["id"]
            for link in support_links
            for node in link["from_nodes"]
            if node.get("kind") == "Evidence"
        }
    )
    broad_markers = ["useful for", "understanding", "reasoning", "factorization", "decomposition", "framework"]
    measurable_markers = ["improves", "outperforms", "metric", "metrics", "accuracy", "kld", "sim", "nss", "iou"]
    if supporting_claims and len(supporting_claims) >= 2:
        return {
            "status": "synthesis_only",
            "reason": "Claim is currently supported by multiple claim premises, so it is better treated as synthesis over child claims.",
            "recommendation": "split_before_experiment",
            "supporting_claims": supporting_claims,
            "supporting_evidence": evidence_supports,
            "suggested_child_claims": [
                f"Make each premise claim directly testable before using it to support {claim['id']}.",
                f"Use {claim['id']} as synthesis only after child claims have direct evidence.",
            ],
        }
    if any(marker in text for marker in broad_markers) and not any(marker in text for marker in measurable_markers):
        return {
            "status": "needs_split",
            "reason": "Claim uses broad conceptual language without a clear measurable proof target.",
            "recommendation": "split_before_experiment",
            "supporting_claims": supporting_claims,
            "supporting_evidence": evidence_supports,
            "suggested_child_claims": [
                "Split into one performance claim, one mechanism/probe claim, or one boundary claim before experiment design."
            ],
        }
    return {
        "status": "directly_testable",
        "reason": "Claim has a focused enough proof target for one experiment proposal.",
        "recommendation": "proceed_to_experiment",
        "supporting_claims": supporting_claims,
        "supporting_evidence": evidence_supports,
        "suggested_child_claims": [],
    }


def expected_evidence_id(target_id: str) -> str:
    return f"E_for_{target_id}"


def build_proposal(root: Path, project_id: str, target_id: str) -> Dict[str, Any]:
    conn = connect(root)
    try:
        row = load_node(conn, project_id, target_id)
        if not row or not active_node(row) or row["node_type"] != "Claim":
            return {"valid": False, "project": project_id, "error": f"target must be an active Claim: {target_id}"}
        claim = node_record(row)
        incoming_links = incoming_support_links(conn, project_id, row["node_id"])
        support_links = [link for link in incoming_links if link["kind"] == "ReasoningLink"]
        translation_links = [link for link in incoming_links if link["kind"] == "TranslationLink"]
        limitations = []
        warrants = []
        evidence = []
        for link in support_links:
            limitations.extend(link["limitation_nodes"])
            warrants.extend(link["warrant_nodes"])
            evidence.extend([node for node in link["from_nodes"] if node["kind"] == "Evidence"])
        context_limitations = []
        for link in translation_links:
            context_limitations.extend(link["limitation_nodes"])
        limitation_by_id = {item["id"]: item for item in limitations}
        warrant_by_id = {item["id"]: item for item in warrants}
        evidence_by_id = {item["id"]: item for item in evidence}
        context_limitation_by_id = {item["id"]: item for item in context_limitations}
    finally:
        conn.close()

    source_gap = target_gap(root, project_id, target_id)
    text = combined_text(claim, list(limitation_by_id.values()), list(warrant_by_id.values()), list(evidence_by_id.values()))
    testability = claim_testability(claim, support_links, text)
    kind = experiment_type(text) if testability["recommendation"] == "proceed_to_experiment" else decomposition_type(testability)
    proposal = {
        "target_claim": claim,
        "source_gap": {
            "gap_type": source_gap["gap_type"],
            "severity": source_gap["severity"],
            "why": source_gap["why"],
            "evidence_need": source_gap["evidence_need"],
        },
        "current_support": [
            {
                "id": link["id"],
                "kind": link["kind"],
                "relation": link["relation"],
                "from": [node["id"] for node in link["from_nodes"]],
                "warrants": [node["id"] for node in link["warrant_nodes"]],
                "limitations": [node["id"] for node in link["limitation_nodes"]],
            }
            for link in support_links
        ],
        "translation_context": [
            {
                "id": link["id"],
                "kind": link["kind"],
                "relation": link["relation"],
                "from": [node["id"] for node in link["from_nodes"]],
                "warrants": [node["id"] for node in link["warrant_nodes"]],
                "limitations": [node["id"] for node in link["limitation_nodes"]],
            }
            for link in translation_links
        ],
        "blocking_limitations": list(limitation_by_id.values()),
        "context_limitations": list(context_limitation_by_id.values()),
        "warrant_to_test": list(warrant_by_id.values())
        or [
            {
                "id": "implicit_warrant",
                "kind": "Warrant",
                "text": "The experiment must make explicit why the measured result supports the target claim.",
                "confidence": "low",
            }
        ],
        "experiment_type": kind,
        "claim_testability": testability,
        "evidence_value_score": evidence_value_score(
            source_gap=source_gap,
            experiment_kind=kind,
            support_links=support_links,
            limitations=list(limitation_by_id.values()),
            warrants=list(warrant_by_id.values()),
            context_limitations=list(context_limitation_by_id.values()),
        ),
        "missing_evidence": [
            source_gap["evidence_need"],
            "Project-owned experiment that can close, weaken, or sharpen the blocking limitation instead of only adding another paper citation.",
        ],
        "hypothesis": f"If the project claim is correct, a controlled experiment should produce new evidence supporting {target_id} under its current limitations.",
        "intervention_or_comparison": comparison(text),
        "dataset_or_benchmark": dataset_candidates(text),
        "metric": metric_candidates(text),
        "minimal_viable_experiment": minimal_viable_experiment(testability),
        "expected_graph_update": {
            "node_types": ["Evidence"],
            "link_types": ["ReasoningLink"],
            "candidate_evidence_id": expected_evidence_id(target_id),
            "possible_delta": "add evidence, strengthen warrant, refine claim, or add limitation depending on outcome",
        },
        "possible_outcomes": {
            "supports": f"Add {expected_evidence_id(target_id)} and a supports RL to {target_id}; optionally raise confidence.",
            "weakens": f"Add limitation or challenge link; demote or refine {target_id}.",
            "refines": f"Split or narrow {target_id} so the claim only covers the supported condition.",
        },
        "required_resources": ["source data or benchmark split", "baseline implementation", "metric script", "result table"],
        "risks": [
            "Experiment may only measure proxy behavior rather than the claimed mechanism.",
            "Benchmark may reproduce existing limitation instead of closing it.",
        ],
        "human_decision": {
            "options": ["accept_as_experiment_idea", "park", "revise", "reject", "run_paper_search_first"],
            "default": "revise",
        },
    }
    return {
        "valid": True,
        "project": project_id,
        "experiment_proposal": proposal,
        "effects": {"writes": [], "graph_events": [], "experiment_runs": []},
    }


def artifact_dir(root: Path, project_id: str) -> Path:
    return root / "wiki" / "projects" / project_id / "experiment-proposals"


def render_artifact(result: Dict[str, Any]) -> str:
    proposal = result["experiment_proposal"]
    target = proposal["target_claim"]["id"]
    now = datetime.now(timezone.utc).date().isoformat()
    return "\n".join(
        [
            "---",
            f'title: "Evidence Production Proposal - {target}"',
            "type: artifact",
            f"created: {now}",
            f"updated: {now}",
            "domains: [generative-models, embodied-intelligence, scene-understanding]",
            "tags: [evidence-production, experiment-proposal, project-understanding-graph]",
            "aliases: []",
            "sources:",
            f"  - \"project:{result['project']}:{target}\"",
            "status: candidate",
            "human_review: pending",
            "confidence: medium",
            "---",
            "",
            "# Evidence Production Proposal",
            "",
            f"Project: {result['project']}",
            f"target: {target}",
            "",
            "Boundary: this artifact does not append graph events, run experiments, or update Q/C/E/W/L/RL/TL truth.",
            "State: planned / pending / not yet graph evidence.",
            "",
            "## Target Claim",
            "",
            f"{target}: {proposal['target_claim']['text']}",
            "",
            "## Blocking Limitations",
            "",
            *(
                [f"- {item['id']}: {item['text']}" for item in proposal["blocking_limitations"]]
                or ["- None listed."]
            ),
            "",
            "## Missing Evidence",
            "",
            *[f"- {item}" for item in proposal["missing_evidence"]],
            "",
            "## Experiment Type",
            "",
            f"- Type: `{proposal['experiment_type']['type']}`",
            f"- Rationale: {proposal['experiment_type']['rationale']}",
            "",
            "## Claim Testability",
            "",
            f"- Status: `{proposal['claim_testability']['status']}`",
            f"- Recommendation: `{proposal['claim_testability']['recommendation']}`",
            f"- Reason: {proposal['claim_testability']['reason']}",
            "",
            "## Evidence Value Score",
            "",
            f"- Score: {proposal['evidence_value_score']['score']}/10",
            f"- Level: {proposal['evidence_value_score']['level']}",
            f"- Cost: {proposal['evidence_value_score']['cost']}",
            f"- Risk: {proposal['evidence_value_score']['risk']}",
            "",
            "## Hypothesis",
            "",
            proposal["hypothesis"],
            "",
            "## Minimal Viable Experiment",
            "",
            proposal["minimal_viable_experiment"],
            "",
            "## Comparison",
            "",
            proposal["intervention_or_comparison"],
            "",
            "## Dataset / Benchmark",
            "",
            *[f"- {item}" for item in proposal["dataset_or_benchmark"]],
            "",
            "## Metric",
            "",
            *[f"- {item}" for item in proposal["metric"]],
            "",
            "## Expected Graph Update",
            "",
            f"- Candidate evidence id: `{proposal['expected_graph_update']['candidate_evidence_id']}`",
            f"- Possible delta: {proposal['expected_graph_update']['possible_delta']}",
            "",
        ]
    )


def save_artifact(root: Path, project_id: str, result: Dict[str, Any]) -> Dict[str, str]:
    target = result["experiment_proposal"]["target_claim"]["id"].lower()
    today = datetime.now(timezone.utc).date().isoformat()
    out_dir = artifact_dir(root, project_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{today}-{target}-evidence-production.md"
    path.write_text(render_artifact(result), encoding="utf-8")
    return {"path": relpath(path, root)}


def command_suggest(args: argparse.Namespace) -> Tuple[int, Dict[str, Any]]:
    root = resolve_repo(args.repo)
    try:
        result = build_proposal(root, args.project, args.target)
        if result.get("valid") and args.save_artifact:
            artifact = save_artifact(root, args.project, result)
            result["artifact"] = artifact
            result["effects"]["writes"] = [artifact["path"]]
    except FileNotFoundError as exc:
        result = {"valid": False, "project": args.project, "error": str(exc)}
    return (0 if result.get("valid") else 1), result


def print_result(result: Dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate read-only experiment proposals from graph claims.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    suggest = subparsers.add_parser("suggest", help="Suggest a minimal evidence-production experiment for a claim.")
    suggest.add_argument("--repo", default=".")
    suggest.add_argument("--project", required=True)
    suggest.add_argument("--target", required=True)
    suggest.add_argument("--save-artifact", action="store_true")
    suggest.add_argument("--json", action="store_true")
    return parser


def dispatch(args: argparse.Namespace) -> Tuple[int, Dict[str, Any]]:
    if args.command == "suggest":
        return command_suggest(args)
    return 2, {"valid": False, "error": f"unsupported command: {args.command}"}


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    code, result = dispatch(args)
    print_result(result, bool(getattr(args, "json", False)))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
