import React, { memo, useCallback, useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Background,
  BackgroundVariant,
  Controls,
  Handle,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  MarkerType,
  Position,
  useReactFlow,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import "./project-graph.css";

const mountedRoots = new WeakMap();

function relationClass(value) {
  return String(value || "supports").toLowerCase().replace(/[^a-z0-9_-]+/g, "-");
}

function relationLabel(value) {
  const labels = {
    supports: "supports",
    qualifies: "qualifies",
    bounds: "bounds",
    motivates: "motivates",
    answers: "answers",
  };
  return labels[String(value || "").toLowerCase()] || String(value || "related");
}

function nodeColor(node) {
  const kind = node?.data?.kind || "";
  if (kind === "question") return "#8ec7ff";
  if (kind === "claim") return "#d6a84f";
  return "#8f98a8";
}

function projectGraphNodeClasses(base, data) {
  return [
    base,
    data.isSelected ? "is-selected" : "",
    data.isNeighbor ? "is-neighbor" : "",
    data.isDimmed ? "is-dimmed" : "",
  ].filter(Boolean).join(" ");
}

function flowSafeId(value) {
  return String(value || "node").replace(/[^a-zA-Z0-9_-]+/g, "-").replace(/^-+|-+$/g, "") || "node";
}

function shortLabel(value, limit = 118) {
  const text = String(value || "").replace(/\s+/g, " ").trim();
  if (text.length <= limit) return text;
  return `${text.slice(0, limit - 1).trim()}...`;
}

const ProjectGraphQuestionNode = memo(function ProjectGraphQuestionNode({ data }) {
  return (
    <button
      type="button"
      className={projectGraphNodeClasses("project-graph-question-node", data)}
      onClick={() => data.onNodeClick(data.id, "question")}
    >
      <Handle type="target" position={Position.Top} className="project-graph-handle" />
      <span>{data.id}</span>
      <strong>{data.label}</strong>
      <em>{data.claimIds?.length ? `${data.claimIds.length} claims` : "no claim"}</em>
      <Handle type="source" position={Position.Bottom} className="project-graph-handle" />
    </button>
  );
});

const ProjectGraphClaimNode = memo(function ProjectGraphClaimNode({ data }) {
  return (
    <button
      type="button"
      className={projectGraphNodeClasses("project-graph-claim-node", data)}
      data-prominence={data.prominence}
      onClick={() => data.onNodeClick(data.id, "claim")}
    >
      <Handle type="target" position={Position.Top} className="project-graph-handle" />
      <span>{data.id}</span>
      <strong>{data.label}</strong>
      <em>{data.subtitle || "project claim"}</em>
      <small>
        S{data.stats.supportClaims} E{data.stats.evidence} W{data.stats.warrants} L{data.stats.limitations}
      </small>
      <Handle type="source" position={Position.Bottom} className="project-graph-handle" />
    </button>
  );
});

const ProjectGraphPaperSourceNode = memo(function ProjectGraphPaperSourceNode({ data }) {
  return (
    <button
      type="button"
      className={projectGraphNodeClasses("project-graph-paper-source-node", data)}
      onClick={() => data.onOpenPaper?.(data.path)}
    >
      <Handle type="target" position={Position.Left} className="project-graph-handle" />
      <span>{data.id}</span>
      <strong>{data.label}</strong>
      <em>{data.subtitle || "paper source"}</em>
      <small>{data.linkCount || 1} project links</small>
      <Handle type="source" position={Position.Right} className="project-graph-handle" />
    </button>
  );
});

const ProjectGraphPaperPortalNode = memo(function ProjectGraphPaperPortalNode({ data }) {
  return (
    <button
      type="button"
      className={projectGraphNodeClasses("project-graph-paper-portal-node", data)}
      onClick={() => data.onOpenPaper?.(data.path, data.sourceNodeId)}
    >
      <Handle type="target" position={Position.Left} className="project-graph-handle" />
      <span>{data.id}</span>
      <strong>{data.label}</strong>
      <em>{data.subtitle || "paper dossier"}</em>
      <small>{data.linkCount || 1} source link</small>
      <Handle type="source" position={Position.Right} className="project-graph-handle" />
    </button>
  );
});

const ProjectGraphPaperContainerNode = memo(function ProjectGraphPaperContainerNode({ data }) {
  return (
    <section className={projectGraphNodeClasses("project-graph-paper-container-node", data)}>
      <Handle type="target" position={Position.Left} className="project-graph-handle" />
      <p className="eyebrow">Paper Argument</p>
      <strong>{data.label}</strong>
      <span>{data.subtitle}</span>
      <small>{data.stats}</small>
      <Handle type="source" position={Position.Right} className="project-graph-handle" />
    </section>
  );
});

const ProjectGraphPaperArgumentNode = memo(function ProjectGraphPaperArgumentNode({ data }) {
  return (
    <button
      type="button"
      className={projectGraphNodeClasses(`project-graph-paper-argument-node is-${data.kind}`, data)}
      onClick={() => data.onNodeClick?.(data.id, data.kind)}
    >
      <Handle type="target" position={Position.Left} className="project-graph-handle" />
      <span>{data.id}</span>
      <strong>{data.label}</strong>
      <em>{data.subtitle || paperKindLabels[data.kind] || "paper node"}</em>
      <Handle type="source" position={Position.Right} className="project-graph-handle" />
    </button>
  );
});

const nodeTypes = {
  questionNode: ProjectGraphQuestionNode,
  claimNode: ProjectGraphClaimNode,
  paperSourceNode: ProjectGraphPaperSourceNode,
  paperPortalNode: ProjectGraphPaperPortalNode,
  paperContainerNode: ProjectGraphPaperContainerNode,
  paperArgumentNode: ProjectGraphPaperArgumentNode,
};

function normalizePaperSources(claims, selectedClaimId = "") {
  const byPath = new Map();
  for (const claim of claims || []) {
    if (selectedClaimId && claim.id !== selectedClaimId) continue;
    for (const source of claim.sources || []) {
      if (!source?.path) continue;
      const existing = byPath.get(source.path) || {
        id: `P${byPath.size + 1}`,
        path: source.path,
        label: source.label || source.path.split("/").pop(),
        claimIds: new Set(),
        linkCount: 0,
      };
      existing.claimIds.add(claim.id);
      existing.linkCount += 1;
      byPath.set(source.path, existing);
    }
  }
  return Array.from(byPath.values()).map((source) => ({
    ...source,
    claimIds: Array.from(source.claimIds),
  }));
}

function edgeColorForRelation(relation) {
  const rel = relationClass(relation);
  if (rel === "answers") return "#8ec7ff";
  if (rel === "qualifies") return "#68c7d4";
  if (rel === "bounds") return "#e58b83";
  if (rel === "motivates") return "#70d6a3";
  if (rel === "paper-source") return "#c7a052";
  if (rel === "paper-argument") return "#8f98a8";
  if (rel === "translationbridgeedge") return "#70d6c7";
  return "#d6a84f";
}

function decorateFlowEdge(edge, { focusedIds = new Set(), activeNodeId = "", selectedClaimId = "", hasFocus = false } = {}) {
  const rel = relationClass(edge.data?.relation);
  const isAnswer = rel === "answers";
  const selected = activeNodeId && (edge.source === activeNodeId || edge.target === activeNodeId);
  const neighbor = selectedClaimId && (edge.source === selectedClaimId || edge.target === selectedClaimId);
  const active = selected || neighbor || edge.data?.isActive;
  const dimmed = hasFocus && !focusedIds.has(edge.source) && !focusedIds.has(edge.target) && !edge.data?.forceVisible;
  const color = edgeColorForRelation(edge.data?.relation);
  return {
    ...edge,
    label: active && edge.data?.relation !== "answers" ? edge.rawLabel : undefined,
    className: `project-graph-edge project-graph-edge-${rel} ${active ? "is-selected" : ""} ${dimmed ? "is-dimmed" : ""}`.trim(),
    animated: Boolean(active && rel !== "answers"),
    markerEnd: {
      type: MarkerType.ArrowClosed,
      color,
    },
    style: {
      stroke: color,
      strokeWidth: active ? (isAnswer ? 1.7 : 2.6) : (isAnswer ? 0.85 : rel === "translationbridgeedge" ? 1.7 : 1.2),
      opacity: dimmed ? 0.05 : active ? (isAnswer ? 0.42 : 0.88) : (isAnswer ? 0.08 : rel === "paper-argument" ? 0.18 : 0.28),
      strokeDasharray: rel === "bounds" || rel === "paper-source" || rel === "translationbridgeedge" ? "7 7" : undefined,
    },
    labelStyle: {
      fill: "var(--text-muted)",
      fontSize: 10,
      fontFamily: "var(--mono)",
      fontWeight: 800,
    },
    labelBgStyle: {
      fill: "var(--surface-1)",
      fillOpacity: active ? 0.92 : 0.74,
    },
    labelBgPadding: [6, 3],
    labelBgBorderRadius: 4,
  };
}

function buildProjectGraphFlowModel(payload, activeNodeId, selectedClaimId, onNodeClick, onOpenPaper) {
  const questions = payload?.questions || [];
  const claims = payload?.claims || [];
  const claimEdges = payload?.edges || [];
  const selectedClaim = claims.find((claim) => claim.id === selectedClaimId) || claims[0] || null;
  const paperSources = selectedClaim ? normalizePaperSources(claims, selectedClaim.id) : [];
  const questionWidth = 174;
  const questionGap = 18;
  const questionY = -190;
  const questionOffset = Math.max(0, ((claims.length || 1) * 208 - questions.length * (questionWidth + questionGap)) / 2);

  const adjacency = new Map();
  const addNeighbor = (a, b) => {
    if (!adjacency.has(a)) adjacency.set(a, new Set());
    adjacency.get(a).add(b);
  };
  for (const edge of claimEdges) {
    addNeighbor(edge.source, edge.target);
    addNeighbor(edge.target, edge.source);
  }
  for (const question of questions) {
    for (const claimId of question.claimIds || []) {
      addNeighbor(question.id, claimId);
      addNeighbor(claimId, question.id);
    }
  }
  if (selectedClaim) {
    for (const source of paperSources) {
      const sourceId = `paper-source:${flowSafeId(source.path)}`;
      addNeighbor(selectedClaim.id, sourceId);
      addNeighbor(sourceId, selectedClaim.id);
    }
  }

  const focusedIds = new Set([activeNodeId, selectedClaimId].filter(Boolean));
  for (const id of [...focusedIds]) {
    for (const neighbor of adjacency.get(id) || []) focusedIds.add(neighbor);
  }
  const hasFocus = Boolean(activeNodeId || selectedClaimId);

  const nodes = [
    ...questions.map((question, index) => ({
      id: question.id,
      type: "questionNode",
      position: { x: questionOffset + index * (questionWidth + questionGap), y: questionY },
      sourcePosition: Position.Bottom,
      targetPosition: Position.Top,
      style: {
        width: questionWidth,
        minHeight: 96,
      },
      data: {
        ...question,
        kind: "question",
        onNodeClick,
        isSelected: activeNodeId === question.id,
        isNeighbor: activeNodeId !== question.id && focusedIds.has(question.id),
        isDimmed: hasFocus && !focusedIds.has(question.id),
      },
    })),
    ...claims.map((claim) => ({
      id: claim.id,
      type: "claimNode",
      position: { x: claim.x, y: claim.y },
      sourcePosition: Position.Bottom,
      targetPosition: Position.Top,
      data: {
        ...claim,
        kind: "claim",
        onNodeClick,
        isSelected: selectedClaimId === claim.id,
        isNeighbor: selectedClaimId !== claim.id && focusedIds.has(claim.id),
        isDimmed: hasFocus && !focusedIds.has(claim.id),
      },
      style: {
        width: claim.width,
        minHeight: claim.height,
      },
    })),
    ...paperSources.map((source, index) => {
      const sourceId = `paper-source:${flowSafeId(source.path)}`;
      const anchor = selectedClaim || { x: 0, y: 0 };
      return {
        id: sourceId,
        type: "paperSourceNode",
        position: { x: anchor.x + 450, y: anchor.y - 96 + index * 124 },
        sourcePosition: Position.Right,
        targetPosition: Position.Left,
        style: {
          width: 260,
          minHeight: 96,
        },
        data: {
          ...source,
          kind: "paper-source",
          id: source.id,
          label: shortLabel(source.label, 86),
          subtitle: "click to expand paper graph",
          onOpenPaper,
          isSelected: activeNodeId === sourceId,
          isNeighbor: activeNodeId !== sourceId && focusedIds.has(sourceId),
          isDimmed: hasFocus && !focusedIds.has(sourceId),
        },
      };
    }),
  ];

  const edges = [
    ...questions.flatMap((question) => (question.claimIds || []).map((claimId) => ({
      id: `answers:${question.id}:${claimId}`,
      source: question.id,
      target: claimId,
      type: "smoothstep",
      rawLabel: "answers",
      data: { relation: "answers" },
    }))),
    ...claimEdges.map((edge) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      type: "smoothstep",
      rawLabel: `${edge.linkId} ${relationLabel(edge.relation)}`,
      data: { relation: edge.relation },
    })),
    ...(selectedClaim ? paperSources.map((source) => {
      const sourceId = `paper-source:${flowSafeId(source.path)}`;
      return {
        id: `claim-paper:${selectedClaim.id}:${flowSafeId(source.path)}`,
        source: selectedClaim.id,
        target: sourceId,
        type: "smoothstep",
        rawLabel: `${source.linkCount || 1} paper links`,
        data: { relation: "paper-source" },
      };
    }) : []),
  ].map((edge) => decorateFlowEdge(edge, { focusedIds, activeNodeId, selectedClaimId, hasFocus }));

  return { nodes, edges };
}

function ClaimInspector({ claim, onOpenPaperGraph }) {
  if (!claim) {
    return (
      <aside className="project-graph-inspector">
        <p className="eyebrow">Selected Claim Detail</p>
        <h3>No claim</h3>
      </aside>
    );
  }
  return (
    <aside className="project-graph-inspector" aria-label="Selected claim Toulmin detail">
      <div className="project-graph-inspector-head">
        <p className="eyebrow">Selected Claim Detail</p>
        <h3>{claim.id} evidence / warrant / limitation</h3>
        <strong>{claim.label}</strong>
        <span>{claim.subtitle || "project claim"}</span>
      </div>
      <InspectorLane title="Supporting Claims" items={claim.supportClaims} empty="No supporting claim." />
      <InspectorLane title="Evidence / Grounds" items={claim.evidence} empty="No evidence." />
      <InspectorLane title="Warrant / Bridge" items={claim.warrants} empty="No explicit warrant." />
      <InspectorLane title="Limitations / Rebuttal" items={claim.limitations} empty="No limitation." />
      <section className="project-graph-source-lane">
        <p className="eyebrow">Source papers</p>
        <div>
          {(claim.sources || []).map((source) => (
            <button key={source.path || source.label} type="button" onClick={() => onOpenPaperGraph?.(source.path)}>
              {source.label}
            </button>
          ))}
          {!claim.sources?.length ? <em>No paper source.</em> : null}
        </div>
      </section>
    </aside>
  );
}

function InspectorLane({ title, items, empty }) {
  return (
    <section className="project-graph-inspector-lane">
      <p className="eyebrow">{title}</p>
      <div>
        {(items || []).map((item) => (
          <article key={item.id}>
            <span>{item.id}</span>
            <strong>{item.label}</strong>
            {item.subtitle ? <em>{item.subtitle}</em> : null}
          </article>
        ))}
        {!items?.length ? <em>{empty}</em> : null}
      </div>
    </section>
  );
}

const paperKindLabels = {
  question: "P-Q",
  claim: "P-C",
  evidence: "P-E",
  warrant: "P-W",
  limitation: "P-L",
};

function normalizePaperKind(value, id = "") {
  const raw = String(value || "").toLowerCase().replace(/^paper[-_\s]*/, "").replace(/[_\s]+/g, "-");
  if (["question", "claim", "evidence", "warrant", "limitation"].includes(raw)) return raw;
  const prefix = String(id || "").toUpperCase().match(/^P-([QCEWL])\d+/)?.[1];
  return {
    Q: "question",
    C: "claim",
    E: "evidence",
    W: "warrant",
    L: "limitation",
  }[prefix] || raw || "unknown";
}

function textValue(...values) {
  for (const value of values) {
    const text = String(value || "").trim();
    if (text) return text;
  }
  return "";
}

function listValue(value) {
  if (Array.isArray(value)) return value.filter(Boolean).map(String);
  return String(value || "").split(/[;,]/).map((item) => item.trim()).filter(Boolean);
}

function unique(values) {
  return [...new Set((values || []).filter(Boolean).map(String))];
}

function compactPaperNode(node) {
  const id = textValue(node?.id, node?.local_id, node?.node_id);
  const kind = normalizePaperKind(node?.kind || node?.node_type, id);
  return {
    ...node,
    id,
    kind,
    label: textValue(node?.label, node?.text, node?.question, node?.claim, node?.evidence, node?.warrant, node?.limitation, id),
    subtitle: textValue(node?.role, node?.source_locus, node?.status, node?.confidence),
  };
}

function paperNodeRows(ids, nodeById) {
  return unique(ids).map((id) => nodeById.get(id)).filter(Boolean);
}

function buildPaperContributionModel(graph) {
  const nodes = (Array.isArray(graph?.nodes) ? graph.nodes : []).map(compactPaperNode).filter((node) => node.id);
  const nodeById = new Map(nodes.map((node) => [node.id, node]));
  const groups = nodes.reduce((result, node) => {
    if (!result[node.kind]) result[node.kind] = [];
    result[node.kind].push(node);
    return result;
  }, { question: [], claim: [], evidence: [], warrant: [], limitation: [] });
  const links = (Array.isArray(graph?.paper_links) ? graph.paper_links : []).map((link) => ({
    id: textValue(link.id),
    relation: textValue(link.relation, "supports"),
    premises: listValue(link.premises),
    target: textValue(link.target),
    warrant: textValue(link.warrant),
    limitations: listValue(link.limitations),
  })).filter((link) => link.id || link.target);
  const translations = Array.isArray(graph?.translations) ? graph.translations : [];
  const deltas = Array.isArray(graph?.deltas) ? graph.deltas : [];
  const claimModels = groups.claim.map((claim) => {
    const claimLinks = links.filter((link) => link.target === claim.id || link.premises.includes(claim.id));
    const premiseIds = unique(claimLinks.flatMap((link) => link.premises));
    const warrantIds = unique([
      ...claimLinks.map((link) => link.warrant),
      ...premiseIds.filter((id) => normalizePaperKind("", id) === "warrant"),
    ]);
    const limitationIds = unique(claimLinks.flatMap((link) => [
      ...link.limitations,
      ...(link.relation === "bounds" ? link.premises : []),
    ]));
    const evidenceIds = unique(premiseIds.filter((id) => normalizePaperKind("", id) === "evidence"));
    const supportClaimIds = unique(premiseIds.filter((id) => normalizePaperKind("", id) === "claim"));
    const relatedIds = unique([claim.id, ...premiseIds, ...warrantIds, ...limitationIds]);
    return {
      ...claim,
      links: claimLinks,
      relatedIds,
      supportClaims: paperNodeRows(supportClaimIds, nodeById),
      evidence: paperNodeRows(evidenceIds, nodeById),
      warrants: paperNodeRows(warrantIds, nodeById),
      limitations: paperNodeRows(limitationIds, nodeById),
    };
  });
  return {
    graph,
    nodes,
    groups,
    links,
    translations,
    deltas,
    claims: claimModels,
    counts: {
      nodes: nodes.length,
      links: links.length,
      translations: translations.length,
      deltas: deltas.length,
    },
  };
}

function paperFlowNodeId(paperPath, nodeId) {
  return `paper:${flowSafeId(paperPath)}:${flowSafeId(nodeId)}`;
}

function claimById(payload, claimId) {
  return (payload?.claims || []).find((claim) => claim.id === claimId) || payload?.claims?.[0] || null;
}

function itemTone(kind) {
  if (kind === "support-claim") return "claim";
  if (kind === "limitation") return "limitation";
  if (kind === "warrant") return "warrant";
  if (kind === "evidence") return "evidence";
  return "claim";
}

function projectAtomNode(item, kind, position, handlers, options = {}) {
  return {
    id: options.nodeId || item.id,
    type: kind === "support-claim" ? "claimNode" : "paperArgumentNode",
    position,
    sourcePosition: Position.Right,
    targetPosition: Position.Left,
    style: {
      width: options.width || (kind === "support-claim" ? 300 : 318),
      minHeight: options.height || 108,
    },
    data: {
      ...item,
      id: item.id,
      kind: itemTone(kind),
      label: shortLabel(item.label, options.labelLimit || 112),
      subtitle: item.subtitle || kind,
      stats: item.stats || { supportClaims: 0, evidence: 0, warrants: 0, limitations: 0 },
      onNodeClick: handlers.onNodeClick,
      isSelected: options.activeNodeId === item.id,
      isNeighbor: true,
      isDimmed: false,
    },
  };
}

function sourceKey(source) {
  return source?.path || source?.label || "";
}

function collectClaimSources(claim) {
  const byPath = new Map();
  const add = (source, ownerId = "") => {
    if (!source?.path) return;
    const key = sourceKey(source);
    const current = byPath.get(key) || {
      id: `P${byPath.size + 1}`,
      path: source.path,
      label: source.label || source.path.split("/").pop(),
      owners: new Set(),
      linkCount: 0,
    };
    if (ownerId) current.owners.add(ownerId);
    current.linkCount += 1;
    byPath.set(key, current);
  };
  for (const source of claim?.sources || []) add(source, claim?.id || "");
  for (const item of [
    ...(claim?.supportClaims || []),
    ...(claim?.evidence || []),
    ...(claim?.warrants || []),
    ...(claim?.limitations || []),
  ]) {
    for (const source of item.sources || []) add(source, item.id);
  }
  return Array.from(byPath.values()).map((source) => ({
    ...source,
    owners: Array.from(source.owners),
  }));
}

function buildProjectOverviewFlowModel(payload, activeNodeId, selectedClaimId, handlers) {
  const questions = payload?.questions || [];
  const claims = payload?.claims || [];
  const claimEdges = payload?.edges || [];
  const width = Math.max(1280, questions.length * 260);
  const questionGap = 28;
  const questionWidth = 232;
  const questionStart = 0;
  const claimSlots = new Map();
  const claimRowByQuestion = new Map();

  for (const claim of claims) {
    const qid = claim.questionIds?.[0] || questions.find((question) => question.claimIds?.includes(claim.id))?.id || questions[0]?.id || "";
    const qIndex = Math.max(0, questions.findIndex((question) => question.id === qid));
    const row = claimRowByQuestion.get(qIndex) || 0;
    claimRowByQuestion.set(qIndex, row + 1);
    claimSlots.set(claim.id, {
      qIndex,
      row,
      x: questionStart + qIndex * (questionWidth + questionGap),
      y: 260 + row * 154,
    });
  }

  const adjacency = new Map();
  const addNeighbor = (a, b) => {
    if (!adjacency.has(a)) adjacency.set(a, new Set());
    adjacency.get(a).add(b);
  };
  for (const question of questions) {
    for (const claimId of question.claimIds || []) {
      addNeighbor(question.id, claimId);
      addNeighbor(claimId, question.id);
    }
  }
  for (const edge of claimEdges) {
    addNeighbor(edge.source, edge.target);
    addNeighbor(edge.target, edge.source);
  }
  const focusedIds = new Set([activeNodeId, selectedClaimId].filter(Boolean));
  for (const id of [...focusedIds]) {
    for (const neighbor of adjacency.get(id) || []) focusedIds.add(neighbor);
  }
  const hasFocus = Boolean(activeNodeId || selectedClaimId);

  const nodes = [
    ...questions.map((question, index) => ({
      id: question.id,
      type: "questionNode",
      position: { x: questionStart + index * (questionWidth + questionGap), y: 0 },
      sourcePosition: Position.Bottom,
      targetPosition: Position.Top,
      style: { width: questionWidth, minHeight: 118 },
      data: {
        ...question,
        kind: "question",
        label: shortLabel(question.fullLabel || question.label, 92),
        onNodeClick: handlers.onNodeClick,
        isSelected: activeNodeId === question.id,
        isNeighbor: activeNodeId !== question.id && focusedIds.has(question.id),
        isDimmed: hasFocus && !focusedIds.has(question.id),
      },
    })),
    ...claims.map((claim) => {
      const slot = claimSlots.get(claim.id) || { x: width / 2, y: 260 };
      return {
        id: claim.id,
        type: "claimNode",
        position: { x: slot.x, y: slot.y },
        sourcePosition: Position.Bottom,
        targetPosition: Position.Top,
        style: { width: claim.prominence === "primary" ? 330 : 278, minHeight: claim.prominence === "primary" ? 136 : 116 },
        data: {
          ...claim,
          kind: "claim",
          onNodeClick: handlers.onNodeClick,
          isSelected: selectedClaimId === claim.id,
          isNeighbor: selectedClaimId !== claim.id && focusedIds.has(claim.id),
          isDimmed: hasFocus && !focusedIds.has(claim.id),
        },
      };
    }),
  ];

  const edges = [
    ...questions.flatMap((question) => (question.claimIds || []).map((claimId) => ({
      id: `answers:${question.id}:${claimId}`,
      source: question.id,
      target: claimId,
      type: "smoothstep",
      rawLabel: "answers",
      data: { relation: "answers" },
    }))),
    ...claimEdges.map((edge) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      type: "smoothstep",
      rawLabel: `${edge.linkId} ${relationLabel(edge.relation)}`,
      data: { relation: edge.relation },
    })),
  ].map((edge) => decorateFlowEdge(edge, { focusedIds, activeNodeId, selectedClaimId, hasFocus }));

  return { nodes, edges };
}

function buildClaimFocusFlowModel(payload, selectedClaimId, activeNodeId, handlers) {
  const selectedClaim = claimById(payload, selectedClaimId);
  if (!selectedClaim) return { nodes: [], edges: [] };
  const claims = payload?.claims || [];
  const focusedIds = new Set([selectedClaim.id]);
  const nodes = [];
  const edges = [];
  const pushEdge = (edge) => {
    edges.push(decorateFlowEdge(edge, {
      focusedIds,
      activeNodeId,
      selectedClaimId: selectedClaim.id,
      hasFocus: true,
    }));
  };

  nodes.push({
    id: selectedClaim.id,
    type: "claimNode",
    position: { x: 420, y: 360 },
    sourcePosition: Position.Right,
    targetPosition: Position.Left,
    style: { width: 420, minHeight: 158 },
    data: {
      ...selectedClaim,
      kind: "claim",
      prominence: "primary",
      onNodeClick: handlers.onNodeClick,
      isSelected: true,
      isNeighbor: false,
      isDimmed: false,
    },
  });

  const supportClaims = selectedClaim.supportClaims || [];
  const evidence = selectedClaim.evidence || [];
  const warrants = selectedClaim.warrants || [];
  const limitations = selectedClaim.limitations || [];
  const lanes = [
    { kind: "support-claim", items: supportClaims, x: -40, y: 210, relation: "supports" },
    { kind: "evidence", items: evidence, x: 960, y: 150, relation: "supports" },
    { kind: "warrant", items: warrants, x: 960, y: 430, relation: "qualifies" },
    { kind: "limitation", items: limitations, x: 1320, y: 290, relation: "bounds" },
  ];

  for (const lane of lanes) {
    lane.items.forEach((item, index) => {
      const y = lane.y + index * 132;
      nodes.push(projectAtomNode(item, lane.kind, { x: lane.x, y }, handlers, { activeNodeId }));
      focusedIds.add(item.id);
      pushEdge({
        id: `claim-focus:${item.id}:${selectedClaim.id}:${lane.relation}`,
        source: item.id,
        target: selectedClaim.id,
        type: "smoothstep",
        rawLabel: lane.relation,
        data: { relation: lane.relation, isActive: true, forceVisible: true },
      });
    });
  }

  const sourceList = collectClaimSources(selectedClaim);
  sourceList.slice(0, 8).forEach((source, index) => {
    const nodeId = `paper-source:${flowSafeId(source.path)}`;
    nodes.push({
      id: nodeId,
      type: "paperPortalNode",
      position: { x: 1720, y: 170 + index * 118 },
      sourcePosition: Position.Right,
      targetPosition: Position.Left,
      style: { width: 286, minHeight: 96 },
      data: {
        ...source,
        kind: "paper-source",
        label: shortLabel(source.label, 86),
        subtitle: "click to enter paper layer",
        sourceNodeId: source.owners[0] || selectedClaim.id,
        onOpenPaper: handlers.onOpenPaper,
        isSelected: activeNodeId === nodeId,
        isNeighbor: true,
        isDimmed: false,
      },
    });
    focusedIds.add(nodeId);
    pushEdge({
      id: `claim-source:${selectedClaim.id}:${flowSafeId(source.path)}`,
      source: selectedClaim.id,
      target: nodeId,
      type: "smoothstep",
      rawLabel: `${source.linkCount || 1} source`,
      data: { relation: "paper-source", forceVisible: true },
    });
  });

  const relatedClaims = unique((payload?.edges || [])
    .filter((edge) => edge.source === selectedClaim.id || edge.target === selectedClaim.id)
    .flatMap((edge) => [edge.source, edge.target]))
    .filter((id) => id !== selectedClaim.id)
    .map((id) => claims.find((claim) => claim.id === id))
    .filter(Boolean)
    .slice(0, 4);
  relatedClaims.forEach((claim, index) => {
    nodes.push({
      id: `related:${claim.id}`,
      type: "claimNode",
      position: { x: 360 + index * 300, y: 620 },
      style: { width: 260, minHeight: 104 },
      data: {
        ...claim,
        id: claim.id,
        kind: "claim",
        label: shortLabel(claim.label, 86),
        onNodeClick: handlers.onNodeClick,
        isSelected: false,
        isNeighbor: false,
        isDimmed: true,
      },
    });
  });

  return { nodes, edges };
}

function buildPaperFocusFlowModel(payload, paperGraph, selectedClaimId, selectedPaperPath, handlers) {
  const selectedClaim = claimById(payload, selectedClaimId);
  const model = buildPaperContributionModel(paperGraph);
  const paperNodeIds = new Set(model.nodes.map((node) => paperFlowNodeId(selectedPaperPath, node.id)));
  const focusedIds = new Set([`project-anchor:${selectedClaimId}`, ...paperNodeIds]);
  const laneX = {
    question: 260,
    evidence: 630,
    warrant: 990,
    claim: 1350,
    limitation: 1710,
  };
  const laneRows = { question: 0, evidence: 0, warrant: 0, claim: 0, limitation: 0, unknown: 0 };
  const nodes = [
    {
      id: `project-anchor:${selectedClaimId}`,
      type: "claimNode",
      position: { x: -150, y: 310 },
      sourcePosition: Position.Right,
      targetPosition: Position.Left,
      style: { width: 300, minHeight: 128 },
      data: {
        ...(selectedClaim || {}),
        id: selectedClaimId,
        kind: "claim",
        label: shortLabel(selectedClaim?.label || selectedClaimId, 96),
        subtitle: "project claim anchor",
        stats: selectedClaim?.stats || { supportClaims: 0, evidence: 0, warrants: 0, limitations: 0 },
        prominence: "support",
        onNodeClick: handlers.onNodeClick,
        isSelected: false,
        isNeighbor: true,
        isDimmed: false,
      },
    },
    {
      id: `paper-header:${flowSafeId(selectedPaperPath)}`,
      type: "paperPortalNode",
      position: { x: 260, y: -40 },
      style: { width: 720, minHeight: 88 },
      data: {
        id: "paper",
        kind: "paper-source",
        label: shortLabel(paperGraph?.title || paperGraph?.paper || "paper graph", 128),
        subtitle: "single paper argument layer",
        linkCount: model.counts.translations,
        isSelected: true,
        isNeighbor: false,
        isDimmed: false,
      },
    },
    ...model.nodes.map((node) => {
      const row = laneRows[node.kind] ?? 0;
      laneRows[node.kind] = row + 1;
      return {
        id: paperFlowNodeId(selectedPaperPath, node.id),
        type: "paperArgumentNode",
        position: {
          x: laneX[node.kind] ?? 1350,
          y: 140 + row * 142,
        },
        sourcePosition: Position.Right,
        targetPosition: Position.Left,
        style: { width: node.kind === "claim" ? 330 : 310, minHeight: node.kind === "claim" ? 118 : 100 },
        data: {
          ...node,
          id: node.id,
          label: shortLabel(node.label, node.kind === "claim" ? 126 : 108),
          subtitle: node.subtitle || paperKindLabels[node.kind] || "paper node",
          onNodeClick: handlers.onNodeClick,
          isSelected: false,
          isNeighbor: true,
          isDimmed: false,
        },
      };
    }),
  ];

  const edges = [];
  const seen = new Set();
  const push = (edge) => {
    const key = `${edge.source}->${edge.target}:${edge.data?.relation || ""}`;
    if (seen.has(key)) return;
    seen.add(key);
    edges.push(decorateFlowEdge(edge, {
      focusedIds,
      activeNodeId: `project-anchor:${selectedClaimId}`,
      selectedClaimId: `project-anchor:${selectedClaimId}`,
      hasFocus: true,
    }));
  };

  for (const link of model.links) {
    const target = paperFlowNodeId(selectedPaperPath, link.target);
    for (const premise of link.premises || []) {
      const source = paperFlowNodeId(selectedPaperPath, premise);
      if (paperNodeIds.has(source) && paperNodeIds.has(target)) {
        push({
          id: `paper-link:${link.id}:${premise}:${link.target}`,
          source,
          target,
          type: "smoothstep",
          rawLabel: `${link.id || "paper link"} ${relationLabel(link.relation)}`,
          data: { relation: "paper-argument", forceVisible: true },
        });
      }
    }
    if (link.warrant) {
      const source = paperFlowNodeId(selectedPaperPath, link.warrant);
      if (paperNodeIds.has(source) && paperNodeIds.has(target)) {
        push({
          id: `paper-warrant:${link.id}:${link.warrant}:${link.target}`,
          source,
          target,
          type: "smoothstep",
          rawLabel: `${link.id || "paper link"} warrant`,
          data: { relation: "paper-argument", forceVisible: true },
        });
      }
    }
    for (const limitation of link.limitations || []) {
      const source = paperFlowNodeId(selectedPaperPath, limitation);
      if (paperNodeIds.has(source) && paperNodeIds.has(target)) {
        push({
          id: `paper-limit:${link.id}:${limitation}:${link.target}`,
          source,
          target,
          type: "smoothstep",
          rawLabel: `${link.id || "paper link"} bounds`,
          data: { relation: "bounds", forceVisible: true },
        });
      }
    }
  }

  for (const item of model.translations || []) {
    for (const paperId of listValue(item.paper_nodes)) {
      const source = paperFlowNodeId(selectedPaperPath, paperId);
      if (!paperNodeIds.has(source)) continue;
      push({
        id: `translation:${item.id || "TL"}:${paperId}:${selectedClaimId}`,
        source,
        target: `project-anchor:${selectedClaimId}`,
        type: "smoothstep",
        rawLabel: `${item.id || "TL"} bridge`,
        data: { relation: "translationBridgeEdge", isActive: true, forceVisible: true },
      });
    }
  }

  return { nodes, edges };
}

function PaperContributionApp({ graph }) {
  const model = useMemo(() => buildPaperContributionModel(graph), [graph]);
  const fallbackClaimId = model.claims[0]?.id || "";
  const [activeClaimId, setActiveClaimId] = useState(fallbackClaimId);

  useEffect(() => {
    setActiveClaimId(fallbackClaimId);
  }, [fallbackClaimId]);

  if (!graph) {
    return (
      <div className="paper-contribution-panel is-empty">
        <div>
          <p className="eyebrow">Paper Contribution</p>
          <h3>Select a paper source</h3>
          <span>Select a paper in claim detail to inspect Paper Argument -&gt; Project Impact.</span>
        </div>
      </div>
    );
  }

  const selectedClaim = model.claims.find((claim) => claim.id === activeClaimId) || model.claims[0] || null;
  const relatedIds = new Set(selectedClaim?.relatedIds || []);
  const relevantTranslations = model.translations.filter((item) => listValue(item.paper_nodes).some((id) => relatedIds.has(id)));
  const relevantDeltas = model.deltas.filter((item) => listValue(item.source_paper_nodes).some((id) => relatedIds.has(id)));

  return (
    <div className="paper-contribution-panel">
      <header className="paper-contribution-head">
        <div>
          <p className="eyebrow">Paper Contribution</p>
          <h3>{graph.title || graph.paper || "paper graph"}</h3>
          <span>Paper Argument -&gt; Project Impact</span>
        </div>
        <dl>
          <div><dt>nodes</dt><dd>{model.counts.nodes}</dd></div>
          <div><dt>links</dt><dd>{model.counts.links}</dd></div>
          <div><dt>TL</dt><dd>{model.counts.translations}</dd></div>
          <div><dt>D</dt><dd>{model.counts.deltas}</dd></div>
        </dl>
      </header>

      <PaperQuestionThread questions={model.groups.question} />

      <div className="paper-contribution-grid">
        <PaperClaimList claims={model.claims} selectedClaimId={selectedClaim?.id || ""} onSelectClaim={setActiveClaimId} />
        <PaperClaimDetail claim={selectedClaim} />
        <TranslationBridge translations={model.translations} relevantTranslations={relevantTranslations} />
      </div>

      <PaperImpactLedger deltas={model.deltas} relevantDeltas={relevantDeltas} />
    </div>
  );
}

function PaperQuestionThread({ questions }) {
  return (
    <section className="paper-question-thread" aria-label="Paper questions">
      <p className="eyebrow">Paper Questions</p>
      <div>
        {(questions || []).map((question) => (
          <article key={question.id}>
            <span>{question.id}</span>
            <strong>{question.label}</strong>
          </article>
        ))}
        {!questions?.length ? <em>No paper questions extracted.</em> : null}
      </div>
    </section>
  );
}

function PaperClaimList({ claims, selectedClaimId, onSelectClaim }) {
  return (
    <aside className="paper-contribution-claim-list" aria-label="Paper claim spine">
      <p className="eyebrow">Paper Claim Spine</p>
      <div>
        {(claims || []).map((claim) => (
          <button
            key={claim.id}
            type="button"
            className={claim.id === selectedClaimId ? "is-selected" : ""}
            onClick={() => onSelectClaim(claim.id)}
          >
            <span>{claim.id}</span>
            <strong>{claim.label}</strong>
            <em>E{claim.evidence.length} W{claim.warrants.length} L{claim.limitations.length}</em>
          </button>
        ))}
        {!claims?.length ? <em>No paper claims extracted.</em> : null}
      </div>
    </aside>
  );
}

function PaperClaimDetail({ claim }) {
  if (!claim) {
    return (
      <section className="paper-claim-detail-panel">
        <p className="eyebrow">Selected Paper Claim</p>
        <h3>No claim</h3>
      </section>
    );
  }
  return (
    <section className="paper-claim-detail-panel" aria-label="Selected paper claim detail">
      <div className="paper-claim-detail-hero">
        <span>{claim.id}</span>
        <h3>{claim.label}</h3>
        {claim.subtitle ? <em>{claim.subtitle}</em> : null}
      </div>
      <div className="paper-claim-support-grid">
        <PaperSupportLane title="Supporting Claims" tone="claim" items={claim.supportClaims} empty="No supporting claim." />
        <PaperSupportLane title="Evidence / Grounds" tone="evidence" items={claim.evidence} empty="No evidence." />
        <PaperSupportLane title="Warrant / Bridge" tone="warrant" items={claim.warrants} empty="No warrant." />
        <PaperSupportLane title="Limitations / Boundary" tone="limitation" items={claim.limitations} empty="No limitation." />
      </div>
    </section>
  );
}

function PaperSupportLane({ title, tone, items, empty }) {
  return (
    <section className="paper-support-lane" data-tone={tone}>
      <p>{title}</p>
      <div>
        {(items || []).map((item) => (
          <article key={item.id}>
            <span>{item.id}</span>
            <strong>{item.label}</strong>
            {item.subtitle ? <em>{item.subtitle}</em> : null}
          </article>
        ))}
        {!items?.length ? <em>{empty}</em> : null}
      </div>
    </section>
  );
}

function TranslationBridge({ translations, relevantTranslations }) {
  const rows = relevantTranslations.length ? relevantTranslations : translations;
  return (
    <aside className="translation-bridge-panel" aria-label="Translation bridge">
      <div>
        <p className="eyebrow">Translation Bridge</p>
        <h3>Paper -&gt; Project</h3>
        <span>{relevantTranslations.length ? "Current claim bridges" : "All bridges"}</span>
      </div>
      <div className="translation-bridge-list">
        {(rows || []).map((item) => (
          <article key={item.id || `${item.paper_nodes}-${item.project_nodes}`}>
            <strong>{item.id || "TL"}</strong>
            <span>{listValue(item.paper_nodes).join(", ") || "paper nodes"} -&gt; {listValue(item.project_nodes).join(", ") || "project nodes"}</span>
            {item.interpretation ? <p>{item.interpretation}</p> : null}
            {item.caveat ? <em>{item.caveat}</em> : null}
          </article>
        ))}
        {!rows?.length ? <em>No translation bridge extracted.</em> : null}
      </div>
    </aside>
  );
}

function PaperImpactLedger({ deltas, relevantDeltas }) {
  const rows = relevantDeltas.length ? relevantDeltas : deltas;
  return (
    <section className="paper-impact-ledger" aria-label="Delta and Human Gate status">
      <div>
        <p className="eyebrow">Delta / Human Gate</p>
        <h3>Project impact audit</h3>
        <span>{relevantDeltas.length ? "Current claim deltas" : "All deltas"}</span>
      </div>
      <div>
        {(rows || []).map((item) => (
          <article key={item.id || item.project_delta}>
            <strong>{item.project_delta || item.id || "delta"}</strong>
            <span>{item.operation || "operation"} · {item.status || "proposed"} · {item.human_review || "pending"}</span>
            <em>{listValue(item.source_paper_nodes).join(", ") || "paper nodes"} =&gt; {listValue(item.affected).join(", ") || "project graph"}</em>
            {item.proposed_change ? <p>{item.proposed_change}</p> : null}
          </article>
        ))}
        {!rows?.length ? <em>No delta.</em> : null}
      </div>
    </section>
  );
}

function ProjectGraphBreadcrumb({ viewMode, selectedClaimId, paperTitle, onBackToProject, onBackToClaim }) {
  return (
    <nav className="project-graph-breadcrumb" aria-label="Project graph breadcrumb">
      <button type="button" onClick={onBackToProject}>Project</button>
      {viewMode === "claim" || viewMode === "paper" ? <button type="button" onClick={onBackToClaim}>{selectedClaimId}</button> : null}
      {viewMode === "paper" && paperTitle ? <span>{paperTitle}</span> : null}
    </nav>
  );
}

function ProjectGraphFitView({ focusKey, viewMode }) {
  const { fitView } = useReactFlow();
  useEffect(() => {
    const timer = window.setTimeout(() => {
      fitView({
        duration: 420,
        padding: viewMode === "paper" ? 0.14 : viewMode === "claim" ? 0.2 : 0.16,
        minZoom: 0.04,
        maxZoom: viewMode === "project" ? 1 : 1.18,
      });
    }, 60);
    return () => window.clearTimeout(timer);
  }, [focusKey, viewMode, fitView]);
  return null;
}

function ProjectGraphApp({ payload, callbacks = {} }) {
  const fallbackClaim = payload?.selectedClaimId || payload?.primaryClaimId || payload?.claims?.[0]?.id || "";
  const [activeNodeId, setActiveNodeId] = useState(fallbackClaim);
  const [selectedClaimId, setSelectedClaimId] = useState(fallbackClaim);
  const [viewMode, setViewMode] = useState("project");
  const [selectedPaperPath, setSelectedPaperPath] = useState("");
  const [selectedPaperSourceNodeId, setSelectedPaperSourceNodeId] = useState("");
  const [loadedPaperGraphs, setLoadedPaperGraphs] = useState({});
  const [paperGraphError, setPaperGraphError] = useState("");

  useEffect(() => {
    const next = payload?.selectedClaimId || payload?.primaryClaimId || payload?.claims?.[0]?.id || "";
    setActiveNodeId(next);
    setSelectedClaimId(next);
    setViewMode("project");
    setSelectedPaperPath("");
    setSelectedPaperSourceNodeId("");
    setPaperGraphError("");
  }, [payload]);

  const onNodeClick = useCallback((nodeId, kind) => {
    setActiveNodeId(nodeId);
    if (kind === "claim") {
      setSelectedClaimId(nodeId);
      setViewMode("claim");
      setSelectedPaperPath("");
      callbacks.onSelectNode?.(nodeId);
      return;
    }
    const question = (payload?.questions || []).find((item) => item.id === nodeId);
    const firstClaim = question?.claimIds?.[0];
    if (firstClaim) {
      setSelectedClaimId(firstClaim);
      setViewMode("project");
      setSelectedPaperPath("");
      callbacks.onSelectNode?.(firstClaim);
    }
  }, [callbacks, payload]);

  const onOpenPaper = useCallback(async (path, sourceNodeId = "") => {
    if (!path) return;
    setPaperGraphError("");
    setActiveNodeId(`paper-source:${flowSafeId(path)}`);
    setSelectedPaperPath(path);
    setSelectedPaperSourceNodeId(sourceNodeId);
    setViewMode("paper");
    if (loadedPaperGraphs[path]) return;
    try {
      const graph = await callbacks.loadProjectGraphPaper?.(path);
      if (!graph) {
        setPaperGraphError("Paper graph unavailable. Source artifact still remains unchanged.");
        return;
      }
      setLoadedPaperGraphs((current) => ({ ...current, [path]: graph }));
    } catch (error) {
      setPaperGraphError(error instanceof Error ? error.message : String(error));
    }
  }, [callbacks, loadedPaperGraphs]);

  const { nodes, edges } = useMemo(
    () => {
      if (viewMode === "paper") {
        const paperGraph = selectedPaperPath ? loadedPaperGraphs[selectedPaperPath] : null;
        if (paperGraph) {
          return buildPaperFocusFlowModel(payload, paperGraph, selectedClaimId, selectedPaperPath, {
            onNodeClick,
            onOpenPaper,
          });
        }
        return buildClaimFocusFlowModel(payload, selectedClaimId, activeNodeId, {
          onNodeClick,
          onOpenPaper,
        });
      }
      if (viewMode === "claim") {
        return buildClaimFocusFlowModel(payload, selectedClaimId, activeNodeId, {
          onNodeClick,
          onOpenPaper,
        });
      }
      return buildProjectOverviewFlowModel(payload, activeNodeId, selectedClaimId, {
        onNodeClick,
        onOpenPaper,
      });
    },
    [payload, viewMode, activeNodeId, selectedClaimId, onNodeClick, onOpenPaper, selectedPaperPath, loadedPaperGraphs],
  );
  const selectedPaperGraph = selectedPaperPath ? loadedPaperGraphs[selectedPaperPath] : null;
  const selectedPaperTitle = selectedPaperGraph?.title || selectedPaperGraph?.paper || "";
  const focusKey = `${viewMode}:${selectedClaimId}:${selectedPaperPath}:${selectedPaperSourceNodeId}:${Boolean(selectedPaperGraph)}`;
  const backToProject = useCallback(() => {
    const next = payload?.primaryClaimId || payload?.claims?.[0]?.id || "";
    setActiveNodeId(next);
    setSelectedClaimId(next);
    setViewMode("project");
    setSelectedPaperPath("");
    setSelectedPaperSourceNodeId("");
    setPaperGraphError("");
  }, [payload]);
  const backToClaim = useCallback(() => {
    setActiveNodeId(selectedClaimId);
    setViewMode("claim");
    setSelectedPaperPath("");
    setSelectedPaperSourceNodeId("");
    setPaperGraphError("");
  }, [selectedClaimId]);

  return (
    <ReactFlowProvider>
      <div className={`project-graph-shell is-${viewMode}-view`}>
        {viewMode === "paper" && selectedPaperPath && !selectedPaperGraph && !paperGraphError ? (
          <div className="project-graph-loading">Loading paper graph...</div>
        ) : null}
        {paperGraphError ? <div className="project-graph-loading is-error">{paperGraphError}</div> : null}
        <section className="project-graph-flow" aria-label="Project argument backbone">
          <ProjectGraphBreadcrumb
            viewMode={viewMode}
            selectedClaimId={selectedClaimId}
            paperTitle={selectedPaperTitle}
            onBackToProject={backToProject}
            onBackToClaim={backToClaim}
          />
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            fitView
            fitViewOptions={{ padding: 0.08, maxZoom: 1.18 }}
            minZoom={0.06}
            maxZoom={2.2}
            panOnDrag
            panOnScroll
            zoomOnPinch
            zoomOnScroll
            zoomOnDoubleClick={false}
            nodesDraggable={false}
            elementsSelectable
            proOptions={{ hideAttribution: true }}
            onInit={(instance) => {
              instance.fitView({ padding: 0.08, maxZoom: 1.18 });
            }}
          >
            <ProjectGraphFitView focusKey={focusKey} viewMode={viewMode} />
            <Background variant={BackgroundVariant.Lines} gap={42} size={1} color="var(--graph-grid-color)" />
            <Controls position="top-right" showInteractive={false} />
            <MiniMap
              position="bottom-right"
              nodeColor={nodeColor}
              pannable
              zoomable
              maskColor="var(--graph-minimap-mask)"
              className="project-graph-minimap"
            />
          </ReactFlow>
        </section>
      </div>
    </ReactFlowProvider>
  );
}

function mount(root, props) {
  if (!root) return null;
  const previous = mountedRoots.get(root);
  if (previous) previous.unmount();
  const reactRoot = createRoot(root);
  reactRoot.render(<ProjectGraphApp {...props} />);
  mountedRoots.set(root, reactRoot);
  return reactRoot;
}

function mountPaperContribution(root, props) {
  if (!root) return null;
  const previous = mountedRoots.get(root);
  if (previous) previous.unmount();
  const reactRoot = createRoot(root);
  reactRoot.render(<PaperContributionApp {...props} />);
  mountedRoots.set(root, reactRoot);
  return reactRoot;
}

window.ResearchBrowserProjectGraph = {
  mount,
  mountPaperContribution,
  ProjectGraphApp,
  PaperContributionApp,
  buildProjectGraphFlowModel,
  buildProjectOverviewFlowModel,
  buildClaimFocusFlowModel,
  buildPaperFocusFlowModel,
  buildPaperContributionModel,
};
