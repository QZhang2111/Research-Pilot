import React, { memo, useCallback, useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Background,
  BackgroundVariant,
  Controls,
  Handle,
  MarkerType,
  MiniMap,
  Position,
  ReactFlow,
  ReactFlowProvider,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import "./workspace-island.css";

const mountedRoots = new WeakMap();
const modes = ["understanding", "literature", "experiments"];
const modeLabels = {
  understanding: "Understanding",
  literature: "Literature",
  experiments: "Experiments",
};

function relationClass(value) {
  return String(value || "related").toLowerCase().replace(/[^a-z0-9_-]+/g, "-") || "related";
}

function shortLabel(value, limit = 116) {
  const text = String(value || "").replace(/\s+/g, " ").trim();
  if (text.length <= limit) return text;
  return `${text.slice(0, limit - 1).trim()}...`;
}

function entityTone(entityType) {
  const type = String(entityType || "").toLowerCase();
  if (type === "question") return "q";
  if (type === "claim" || type === "evaluation_arena" || type === "evaluation_setting") return "c";
  if (type === "evidence" || type === "experiment") return "e";
  if (type === "warrant") return "w";
  if (type === "limitation") return "l";
  if (type === "source" || type === "paper" || type === "literature_lane") return "p";
  if (type === "dataset" || type === "benchmark" || type === "evaluation_context" || type === "protocol") return "p";
  if (type === "model" || type === "metric_family") return "w";
  if (type === "ablation") return "w";
  if (type === "baseline") return "l";
  if (type === "run") return "r";
  return "x";
}

function displayTone(node) {
  return node?.data?.node?.display?.tone || node?.data?.display?.tone || entityTone(node?.data?.entity_type || node?.data?.node?.entity_type);
}

const routePalette = ["#68c7d4", "#9dc66b", "#d6a84f", "#bea0ff", "#e58b83", "#8ec7ff"];

function routeColorIndex(value, fallback = 0) {
  const tone = typeof value === "string" ? value : displayTone({ data: { node: value } });
  const match = String(tone || "").match(/^route-(\d+)$/);
  if (match) return Number(match[1]) % routePalette.length;
  const metadataIndex = Number(value?.metadata?.route_index);
  if (Number.isFinite(metadataIndex)) return metadataIndex % routePalette.length;
  return fallback % routePalette.length;
}

function routeColor(value) {
  const tone = typeof value === "string" ? value : displayTone({ data: { node: value } });
  if (!String(tone || "").match(/^route-\d+$/)) return "";
  return routePalette[routeColorIndex(tone)];
}

function cssTone(tone) {
  if (String(tone || "").match(/^route-\d+$/)) return String(tone);
  return {
    q: "q",
    c: "c",
    e: "e",
    w: "w",
    l: "l",
    p: "p",
    r: "r",
    question: "q",
    claim: "c",
    evidence: "e",
    warrant: "w",
    limitation: "l",
    source: "p",
    run: "r",
  }[tone] || "x";
}

function nodeColor(node) {
  const tone = displayTone(node);
  const routeTone = routeColor(tone);
  if (routeTone) return routeTone;
  return {
    question: "#8ec7ff",
    claim: "#d6a84f",
    evidence: "#70d6a3",
    warrant: "#bea0ff",
    limitation: "#e58b83",
    source: "#68c7d4",
    run: "#9bd7df",
    q: "#8ec7ff",
    c: "#d6a84f",
    e: "#70d6a3",
    w: "#bea0ff",
    l: "#e58b83",
    p: "#68c7d4",
    r: "#9bd7df",
  }[tone] || "#8f98a8";
}

function workspaceNodePosition(node, index, model) {
  if (node.position) return node.position;
  const type = node.entity_type || "";
  const mode = model?.mode || "understanding";
  const layer = model?.layer || "";
  const sameTypeIndex = (model?.canvas?.nodes || []).filter((item, itemIndex) => itemIndex < index && item.entity_type === type).length;
  if (mode === "understanding" && layer === "project_overview") {
    if (type === "question") return { x: sameTypeIndex * 360, y: -180 };
    if (type === "claim") return { x: sameTypeIndex * 390, y: 80 };
  }
  if (mode === "literature") {
    if (type === "literature_lane") return { x: 0, y: sameTypeIndex * 190 };
    return { x: 360 + (sameTypeIndex % 4) * 340, y: Math.floor(sameTypeIndex / 4) * 170 };
  }
  if (mode === "experiments") {
    if (type === "evaluation_arena" || type === "evaluation_setting") return { x: sameTypeIndex * 410, y: -40 };
    if (type === "experiment") return { x: sameTypeIndex * 380, y: 210 };
    if (type === "run") return { x: sameTypeIndex * 340, y: 430 };
  }
  return { x: (index % 4) * 360, y: Math.floor(index / 4) * 180 };
}

function workspaceNodeWidth(node, model) {
  if (model?.mode === "literature") return node.entity_type === "literature_lane" ? 300 : 330;
  if (model?.mode === "experiments") return node.entity_type === "evaluation_arena" || node.entity_type === "evaluation_setting" ? 360 : 330;
  return node.entity_type === "claim" ? 360 : 300;
}

function focusedNodeIds(model) {
  const selectedId = model?.selected_id || model?.focus_id || "";
  const ids = new Set([selectedId].filter(Boolean));
  for (const edge of model?.canvas?.edges || []) {
    if (edge.source === selectedId) ids.add(edge.target);
    if (edge.target === selectedId) ids.add(edge.source);
  }
  return ids;
}

function nodeFocusClass(node, focusedIds, hasFocus) {
  if (!hasFocus) return "";
  if (focusedIds.has(node.id)) return node.id === [...focusedIds][0] ? "is-selected" : "is-neighbor";
  return "is-dimmed";
}

function toFlowNode(node, index, model, focusedIds, onNodeAction) {
  const hasFocus = Boolean(model?.selected_id || model?.focus_id);
  const focusClass = nodeFocusClass(node, focusedIds, hasFocus);
  return {
    id: node.id,
    type: "workspaceKnowledgeNode",
    position: workspaceNodePosition(node, index, model),
    sourcePosition: Position.Bottom,
    targetPosition: Position.Top,
    data: {
      node,
      entity_type: node.entity_type,
      tone: cssTone(node.display?.tone || entityTone(node.entity_type)),
      focusClass,
      onNodeAction,
    },
    style: {
      width: workspaceNodeWidth(node, model),
      minHeight: node.entity_type === "claim" ? 138 : 118,
    },
  };
}

function toFlowEdge(edge, model, focusedIds) {
  const relation = relationClass(edge.relation || edge.label);
  const hasFocus = Boolean(model?.selected_id || model?.focus_id);
  const active = focusedIds.has(edge.source) && focusedIds.has(edge.target);
  const dimmed = hasFocus && !active;
  const color = {
    answers: "#8ec7ff",
    supports: "#d6a84f",
    qualifies: "#68c7d4",
    bounds: "#e58b83",
    cites: "#68c7d4",
    contains: "#8f98a8",
  }[relation] || "#d6a84f";
  return {
    id: edge.id,
    source: edge.source,
    target: edge.target,
    label: active ? edge.label : undefined,
    type: "smoothstep",
    className: `workspace-edge workspace-edge-${relation} ${active ? "is-selected" : ""} ${dimmed ? "is-dimmed" : ""}`.trim(),
    markerEnd: { type: MarkerType.ArrowClosed, color },
    style: {
      stroke: color,
      strokeWidth: active ? 2.4 : 1.2,
      opacity: dimmed ? 0.06 : active ? 0.82 : 0.22,
      strokeDasharray: relation === "bounds" || relation === "cites" ? "7 7" : undefined,
    },
    labelStyle: {
      fill: "var(--text-muted)",
      fontSize: 10,
      fontFamily: "var(--mono)",
      fontWeight: 800,
    },
    labelBgStyle: {
      fill: "var(--surface-1)",
      fillOpacity: 0.82,
    },
    labelBgPadding: [6, 3],
    labelBgBorderRadius: 4,
  };
}

const WorkspaceKnowledgeNode = memo(function WorkspaceKnowledgeNode({ data }) {
  const node = data.node || {};
  const localId = node.local_id || node.subtitle || node.entity_type || "node";
  const canDrill = Boolean(node.drill);
  const className = [
    "workspace-node-card",
    `tone-${data.tone}`,
    data.focusClass,
    canDrill ? "can-drill" : "is-terminal",
  ].filter(Boolean).join(" ");
  const content = (
    <>
      <Handle type="target" position={Position.Top} className="workspace-node-handle" />
      <span>{localId}</span>
      <strong>{shortLabel(node.label, 150)}</strong>
      <em>{node.subtitle || node.status || node.entity_type || ""}</em>
      <Handle type="source" position={Position.Bottom} className="workspace-node-handle" />
    </>
  );
  if (!canDrill && !node.inspector) {
    return <article className={className}>{content}</article>;
  }
  return (
    <button type="button" className={className} onClick={() => data.onNodeAction?.(node)}>
      {content}
    </button>
  );
});

const WorkspaceLaneFrameNode = memo(function WorkspaceLaneFrameNode({ data }) {
  return (
    <section className={`workspace-lane-frame tone-${data.tone || "x"}`}>
      <strong>{data.title}</strong>
      {data.subtitle ? <span>{data.subtitle}</span> : null}
    </section>
  );
});

const WorkspaceRouteFrameNode = memo(function WorkspaceRouteFrameNode({ data }) {
  const node = data.node || {};
  return (
    <article className={`workspace-route-frame-node tone-${data.tone || "x"}`}>
      <strong>{data.title || shortLabel(node.label || node.local_id || "Route", 84)}</strong>
      {data.subtitle ? <span>{data.subtitle}</span> : null}
    </article>
  );
});

const WorkspaceArgumentAtomNode = memo(function WorkspaceArgumentAtomNode({ data }) {
  const node = data.node || {};
  const canInspect = Boolean(node.inspector);
  const content = (
    <>
      <Handle type="source" position={Position.Right} className="workspace-node-handle" />
      <span>{node.local_id || node.subtitle || node.entity_type}</span>
      <strong>{shortLabel(node.label, 128)}</strong>
      <em>{node.subtitle || node.entity_type}</em>
    </>
  );
  if (!canInspect) {
    return <article className={`workspace-argument-atom tone-${data.tone || "x"}`}>{content}</article>;
  }
  return (
    <button type="button" className={`workspace-argument-atom tone-${data.tone || "x"}`} onClick={() => data.onNodeAction?.(node)}>
      {content}
    </button>
  );
});

const WorkspacePaperSourceNode = memo(function WorkspacePaperSourceNode({ data }) {
  const node = data.node || {};
  return (
    <button type="button" className={`workspace-paper-source-node tone-${data.tone || "x"}`} onClick={() => data.onNodeAction?.(node)}>
      <Handle type="target" position={Position.Left} className="workspace-node-handle" />
      <strong className="workspace-paper-source-title">{shortLabel(node.label, 116)}</strong>
    </button>
  );
});

const WorkspaceTimelinePaperNode = memo(function WorkspaceTimelinePaperNode({ data }) {
  const node = data.node || {};
  const year = node.metadata?.sort_year && Number(node.metadata.sort_year) < 9999 ? String(node.metadata.sort_year) : "";
  return (
    <button type="button" className={`workspace-timeline-paper-node tone-${data.tone || "x"}`} onClick={() => data.onNodeAction?.(node)}>
      <Handle type="target" position={Position.Left} className="workspace-node-handle" />
      <strong>{shortLabel(node.label, 104)}</strong>
      {year ? <em>{year}</em> : null}
      <Handle type="source" position={Position.Right} className="workspace-node-handle" />
    </button>
  );
});

function experimentOriginLabel(value) {
  return {
    imported_paper: "Imported Paper",
    local: "Local",
    replication: "Replication",
    external: "External",
  }[value] || shortLabel(value || "Run", 36);
}

const WorkspaceExperimentArenaNode = memo(function WorkspaceExperimentArenaNode({ data }) {
  const node = data.node || {};
  const metadata = node.metadata || {};
  const counts = node.subtitle || `${metadata.experiment_count || 0} experiments / ${metadata.run_count || 0} runs`;
  const metricSummary = (metadata.metric_families || []).join(" / ") || node.subtitle || "";
  const content = (
    <>
      <Handle type="target" position={Position.Left} className="workspace-node-handle" />
      <strong>{shortLabel(node.label || "Evaluation Arena", 56)}</strong>
      <span>{shortLabel(metricSummary, 48)}</span>
      <small>{counts}</small>
      <Handle type="source" position={Position.Right} className="workspace-node-handle" />
    </>
  );
  return (
    <button type="button" className="workspace-experiment-arena-node" onClick={() => data.onNodeAction?.(node)}>
      {content}
    </button>
  );
});

const WorkspaceExperimentContextPanelNode = memo(function WorkspaceExperimentContextPanelNode({ data }) {
  const node = data.node || {};
  const metadata = node.metadata || {};
  const datasets = metadata.datasets || [];
  const benchmarks = metadata.benchmarks || [];
  const metrics = metadata.metric_families || [];
  const countLabel = (count, singular, plural = `${singular}s`) => `${count} ${count === 1 ? singular : plural}`;
  const summary = [
    countLabel(datasets.length, "dataset"),
    countLabel(benchmarks.length, "benchmark"),
    countLabel(metrics.length, "metric family", "metric families"),
  ].join(" · ");
  const rows = [
    ["Datasets", datasets.length],
    ["Benchmarks", benchmarks.length],
    ["Metric families", metrics.length],
  ];
  return (
    <section className="workspace-experiment-context-panel">
      <Handle type="target" position={Position.Left} className="workspace-node-handle" />
      <strong>Evaluation Context</strong>
      <p>{summary} define this arena.</p>
      <dl>
        {rows.map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
      <Handle type="source" position={Position.Right} className="workspace-node-handle" />
    </section>
  );
});

const WorkspaceRunResultNode = memo(function WorkspaceRunResultNode({ data }) {
  const node = data.node || {};
  const origin = experimentOriginLabel(node.metadata?.origin_type);
  const metricText = (node.metadata?.metrics || []).slice(0, 3).map((metric) => `${metric.name} ${metric.value}`).join(" / ");
  return (
    <button type="button" className={`workspace-run-result-node tone-${data.tone || "r"}`} onClick={() => data.onNodeAction?.(node)}>
      <Handle type="target" position={Position.Left} className="workspace-node-handle" />
      <span>{node.local_id || node.entity_type}</span>
      <strong>{shortLabel(node.label, 72)}</strong>
      <em>{shortLabel(metricText || node.subtitle || "", 92)}</em>
      <small>{origin}</small>
    </button>
  );
});

const methodGroupLabels = {
  model: "Models",
  baseline: "Baselines",
  protocol: "Protocol",
  ablation: "Ablations",
};

const methodMetadataKeys = {
  model: "models",
  baseline: "baselines",
  protocol: "protocol",
  ablation: "ablations",
};

function groupExperimentMethodNodes(nodes) {
  const methodNode = (nodes || []).find((node) => node.entity_type === "experiment_method");
  if (methodNode) {
    return Object.entries(methodMetadataKeys)
      .map(([kind, key]) => {
        const values = methodNode.metadata?.[key] || [];
        const selectedId = `${methodNode.id}:${kind}`;
        const items = values.map((value, index) => ({
          id: `${methodNode.id}:${kind}:${index}`,
          label: String(value),
        }));
        return {
          kind,
          label: methodGroupLabels[kind] || kind,
          items,
          target: {
            id: selectedId,
            entity_type: "experiment_method_group",
            label: methodGroupLabels[kind] || kind,
            inspector: { selected_id: `${methodNode.id}:${kind}` },
          },
        };
      })
      .filter((group) => group.items.length);
  }
  const groups = { model: [], baseline: [], protocol: [], ablation: [] };
  for (const node of nodes || []) {
    if (groups[node.entity_type]) groups[node.entity_type].push(node);
  }
  return Object.entries(groups)
    .filter(([, items]) => items.length)
    .map(([kind, items]) => ({ kind, label: methodGroupLabels[kind] || kind, items, target: items[0] }));
}

const WorkspaceExperimentMethodPanelNode = memo(function WorkspaceExperimentMethodPanelNode({ data }) {
  const groups = data.groups || [];
  return (
    <section className="workspace-experiment-method-panel">
      <Handle type="target" position={Position.Left} className="workspace-node-handle" />
      <strong>Design Method</strong>
      <p>Models, baselines, and protocol summarized as experiment recipe.</p>
      <div className="workspace-experiment-method-groups">
        {groups.map((group) => (
          <button
            key={group.kind}
            type="button"
            className="workspace-experiment-method-group-button nodrag"
            onClick={() => data.onNodeAction?.(group.target)}
          >
            <h4>{group.label}</h4>
            <ul>
              {group.items.slice(0, 5).map((item) => (
                <li key={item.id}>{shortLabel(item.label, 72)}</li>
              ))}
              {group.items.length > 5 ? <li>{group.items.length - 5} more</li> : null}
            </ul>
          </button>
        ))}
      </div>
      <Handle type="source" position={Position.Right} className="workspace-node-handle" />
    </section>
  );
});

const WorkspaceExperimentEntityNode = memo(function WorkspaceExperimentEntityNode({ data }) {
  const node = data.node || {};
  const canAct = Boolean(node.drill || node.inspector);
  const content = (
    <>
      <Handle type="target" position={Position.Left} className="workspace-node-handle" />
      <span>{node.local_id || node.subtitle || node.entity_type}</span>
      <strong>{shortLabel(node.label, 96)}</strong>
      <em>{shortLabel(node.subtitle || node.entity_type || "", 58)}</em>
      <Handle type="source" position={Position.Right} className="workspace-node-handle" />
    </>
  );
  const className = `workspace-experiment-entity-node tone-${data.tone || "x"}`;
  if (!canAct) return <article className={className}>{content}</article>;
  return (
    <button type="button" className={className} onClick={() => data.onNodeAction?.(node)}>
      {content}
    </button>
  );
});

const workspaceNodeTypes = {
  workspaceKnowledgeNode: WorkspaceKnowledgeNode,
  workspaceLaneFrameNode: WorkspaceLaneFrameNode,
  workspaceRouteFrameNode: WorkspaceRouteFrameNode,
  workspaceArgumentAtomNode: WorkspaceArgumentAtomNode,
  workspacePaperSourceNode: WorkspacePaperSourceNode,
  workspaceTimelinePaperNode: WorkspaceTimelinePaperNode,
  workspaceExperimentArenaNode: WorkspaceExperimentArenaNode,
  workspaceExperimentContextPanelNode: WorkspaceExperimentContextPanelNode,
  workspaceExperimentMethodPanelNode: WorkspaceExperimentMethodPanelNode,
  workspaceRunResultNode: WorkspaceRunResultNode,
  workspaceExperimentEntityNode: WorkspaceExperimentEntityNode,
};

function normalizeBreadcrumb(model) {
  const crumbs = Array.isArray(model?.breadcrumb) ? model.breadcrumb : [];
  const normalized = crumbs
    .filter((crumb) => crumb && typeof crumb === "object")
    .map((crumb, index) => ({
      label: crumb.label || crumb.layer || crumb.mode || `Layer ${index + 1}`,
      mode: crumb.mode || model?.mode || "understanding",
      layer: crumb.layer || "",
      focus_id: crumb.focus_id || "",
      selected_id: crumb.selected_id || "",
    }));
  if (normalized.length) return normalized;
  return [{
    label: modeLabels[model?.mode] || "Workspace",
    mode: model?.mode || "understanding",
    layer: model?.layer || "",
    focus_id: "",
    selected_id: "",
  }];
}

function WorkspaceBreadcrumb({ model, onNavigate }) {
  const crumbs = normalizeBreadcrumb(model);
  return (
    <nav className="workspace-stage-breadcrumb" aria-label="Workspace layer breadcrumb">
      {crumbs.map((crumb, index) => {
        const isLast = index === crumbs.length - 1;
        return (
          <React.Fragment key={`${crumb.mode}:${crumb.layer}:${crumb.focus_id}:${index}`}>
            {index ? <span className="workspace-breadcrumb-separator">/</span> : null}
            {isLast ? (
              <span className="workspace-breadcrumb-current">{crumb.label}</span>
            ) : (
              <button type="button" onClick={() => onNavigate?.(crumb)}>
                {crumb.label}
              </button>
            )}
          </React.Fragment>
        );
      })}
    </nav>
  );
}

function WorkspaceInspector({ inspector }) {
  const sections = Array.isArray(inspector?.sections) ? inspector.sections : [];
  return (
    <aside className="workspace-inspector" aria-label="Workspace inspector">
      <p className="eyebrow">{inspector?.kind || "Inspector"}</p>
      <h2>{inspector?.title || "Workspace"}</h2>
      {inspector?.summary ? <p>{inspector.summary}</p> : null}
      {sections.map((section, index) => {
        const title = section.title || {
          paper_brief: "Paper Brief",
          paper_node_list: "Paper Argument Nodes",
        }[section.kind] || section.kind || "Section";
        if (section.kind === "paper_brief") {
          return (
            <section key={`${section.kind || "section"}:${index}`} className="workspace-inspector-section workspace-paper-brief-section">
              <h3>{title}</h3>
              {(section.items || []).map((item, itemIndex) => (
                <article key={item.id || item.local_id || item.label || itemIndex} className="workspace-paper-brief-item">
                  <strong>{item.label || item.title || item.kind || "Brief"}</strong>
                  <p>{item.text || item.subtitle || item.impact || ""}</p>
                </article>
              ))}
              {!section.items?.length ? <em>No records.</em> : null}
            </section>
          );
        }
        return (
          <section key={`${section.kind || "section"}:${index}`} className={`workspace-inspector-section workspace-inspector-section-${relationClass(section.kind || "section")}`}>
            <h3>{title}</h3>
            <div className="workspace-inspector-list">
              {(section.items || []).map((item, itemIndex) => (
                <article key={item.id || item.local_id || item.label || itemIndex}>
                  <span>{item.local_id || item.id || item.kind || ""}</span>
                  <strong>{item.label || item.title || item.text || item.target_id || ""}</strong>
                  {item.subtitle || item.impact ? <em>{item.subtitle || item.impact}</em> : null}
                </article>
              ))}
              {!section.items?.length ? <em>No records.</em> : null}
            </div>
          </section>
        );
      })}
      {Array.isArray(inspector?.actions) && inspector.actions.length ? (
        <section>
          <h3>Actions</h3>
          <div className="workspace-inspector-actions">
            {inspector.actions.map((action, index) => (
              <button
                key={action.label || index}
                type="button"
                onClick={() => window.dispatchEvent(new CustomEvent("workspace-island-action", { detail: action.target || action }))}
              >
                {action.label || "Open"}
              </button>
            ))}
          </div>
        </section>
      ) : null}
    </aside>
  );
}

function nodeNavigationTarget(node) {
  if (node?.drill) return node.drill;
  if (node?.inspector) return node.inspector;
  return null;
}

function buildUnderstandingOverviewFlowModel(model, onNavigate) {
  const rawNodes = model?.canvas?.nodes || [];
  const rawEdges = model?.canvas?.edges || [];
  const questions = rawNodes.filter((node) => node.entity_type === "question");
  const claims = rawNodes.filter((node) => node.entity_type === "claim");
  const questionWidth = 300;
  const claimWidth = 360;
  const gap = 36;
  const questionFrameWidth = Math.max(questions.length * (questionWidth + gap) + 70, 720);
  const claimFrameWidth = Math.max(claims.length * (claimWidth + gap) + 70, 980);
  const focusedIds = focusedNodeIds(model);

  const nodes = [
    {
      id: "frame:questions",
      type: "workspaceLaneFrameNode",
      position: { x: -40, y: -250 },
      style: { width: questionFrameWidth, height: 220 },
      draggable: false,
      selectable: false,
      zIndex: 0,
      data: { title: "Questions", subtitle: `${questions.length} project questions`, tone: "q" },
    },
    {
      id: "frame:claims",
      type: "workspaceLaneFrameNode",
      position: { x: -40, y: 20 },
      style: { width: claimFrameWidth, height: 260 },
      draggable: false,
      selectable: false,
      zIndex: 0,
      data: { title: "Claims", subtitle: `${claims.length} project claims`, tone: "c" },
    },
    ...questions.map((node, index) =>
      toFlowNode(
        { ...node, position: { x: index * (questionWidth + gap), y: -180 } },
        index,
        model,
        focusedIds,
        (item) => {
          const target = nodeNavigationTarget(item);
          if (!target) return;
          onNavigate?.(target);
        },
      ),
    ),
    ...claims.map((node, index) =>
      toFlowNode(
        { ...node, position: { x: index * (claimWidth + gap), y: 90 } },
        index,
        model,
        focusedIds,
        (item) => {
          const target = nodeNavigationTarget(item);
          if (!target) return;
          onNavigate?.(target);
        },
      ),
    ),
  ];

  const visibleIds = new Set(rawNodes.map((node) => node.id));
  const edgeFocusIds = focusedIds.size ? focusedIds : visibleIds;
  const edges = rawEdges
    .filter((edge) => visibleIds.has(edge.source) && visibleIds.has(edge.target))
    .map((edge) => toFlowEdge(edge, model, edgeFocusIds));

  return { nodes, edges };
}

function claimFocusFrameHeight(itemCount) {
  return Math.max(190, itemCount * 130 + 92);
}

function buildClaimFocusLaneLayout(rawNodes) {
  const nodeCounts = new Map();
  for (const node of rawNodes) {
    nodeCounts.set(node.entity_type, (nodeCounts.get(node.entity_type) || 0) + 1);
  }

  const laneGap = 72;
  let leftStackY = 20;
  const evidenceHeight = claimFocusFrameHeight((nodeCounts.get("evidence") || 0));
  const evidenceLane = {
    key: "evidence",
    title: "Evidence / Grounds",
    tone: "e",
    x: 720,
    y: leftStackY,
    frameHeight: evidenceHeight,
    relation: "supports",
  };
  leftStackY += evidenceHeight + laneGap;

  return [
    evidenceLane,
    {
      key: "warrant",
      title: "Warrants / Bridges",
      tone: "w",
      x: 720,
      y: leftStackY,
      frameHeight: claimFocusFrameHeight((nodeCounts.get("warrant") || 0)),
      relation: "qualifies",
    },
    {
      key: "limitation",
      title: "Limitations / Boundaries",
      tone: "l",
      x: 1120,
      y: 20,
      frameHeight: claimFocusFrameHeight((nodeCounts.get("limitation") || 0)),
      relation: "bounds",
    },
    {
      key: "source",
      title: "Source Papers",
      tone: "p",
      x: 1540,
      y: 20,
      frameHeight: claimFocusFrameHeight((nodeCounts.get("source") || 0)),
      relation: "cites",
    },
  ];
}

function buildUnderstandingClaimFocusFlowModel(model, onNavigate) {
  const rawNodes = model?.canvas?.nodes || [];
  const focusId = model?.focus_id || rawNodes.find((node) => node.entity_type === "claim")?.id || "";
  const claim = rawNodes.find((node) => node.id === focusId) || rawNodes.find((node) => node.entity_type === "claim");
  if (!claim) return { nodes: [], edges: [] };

  const laneConfig = buildClaimFocusLaneLayout(rawNodes);

  const nodes = [
    {
      ...toFlowNode(
        { ...claim, position: { x: 160, y: 190 } },
        0,
        model,
        new Set([claim.id]),
        () => {},
      ),
      sourcePosition: Position.Right,
      targetPosition: Position.Left,
      style: { width: 420, minHeight: 160 },
      zIndex: 4,
    },
  ];
  const edges = [];

  laneConfig.forEach((lane) => {
    const items = rawNodes.filter((node) => node.entity_type === lane.key);
    const frameHeight = lane.frameHeight || claimFocusFrameHeight(items.length);
    nodes.push({
      id: `frame:${lane.key}`,
      type: "workspaceLaneFrameNode",
      position: { x: lane.x - 28, y: lane.y - 52 },
      style: { width: lane.key === "source" ? 340 : 360, height: frameHeight },
      draggable: false,
      selectable: false,
      zIndex: 0,
      data: { title: lane.title, subtitle: `${items.length} records`, tone: lane.tone },
    });
    items.forEach((node, index) => {
      const nodeId = node.id;
      if (lane.key === "source") {
        nodes.push({
          id: nodeId,
          type: "workspacePaperSourceNode",
          position: { x: lane.x, y: lane.y + index * 126 },
          sourcePosition: Position.Right,
          targetPosition: Position.Left,
          style: { width: 286, minHeight: 96 },
          zIndex: 3,
          data: {
            node,
            tone: cssTone(node.display?.tone || lane.tone),
            onNodeAction: (item) => {
              const target = nodeNavigationTarget(item);
              if (!target) return;
              onNavigate?.(target);
            },
          },
        });
        edges.push({
          id: `claim-focus:${claim.id}:${nodeId}`,
          source: claim.id,
          target: nodeId,
          relation: lane.relation,
          label: lane.relation,
        });
        return;
      }
      nodes.push({
        id: nodeId,
        type: "workspaceArgumentAtomNode",
        position: { x: lane.x, y: lane.y + index * 126 },
        sourcePosition: Position.Right,
        targetPosition: Position.Left,
        style: { width: 310, minHeight: 104 },
        zIndex: 3,
        data: {
          node,
          tone: cssTone(node.display?.tone || lane.tone),
          onNodeAction: (item) => {
            const target = nodeNavigationTarget(item);
            if (!target) return;
            onNavigate?.(target);
          },
        },
      });
      edges.push({
        id: `claim-focus:${nodeId}:${claim.id}`,
        source: nodeId,
        target: claim.id,
        relation: lane.relation,
        label: lane.relation,
      });
    });
  });

  return {
    nodes,
    edges: edges.map((edge) => toFlowEdge(edge, model, new Set([edge.source, edge.target, claim.id]))),
  };
}

function paperFocusLaneHeight(itemCount) {
  return Math.max(180, itemCount * 120 + 86);
}

function buildUnderstandingPaperFocusFlowModel(model, onNavigate) {
  const rawNodes = model?.canvas?.nodes || [];
  const rawEdges = model?.canvas?.edges || [];
  const anchor = rawNodes.find((node) => node.entity_type === "project_claim_anchor");
  const laneSpecs = [
    { key: "paper_question", title: "Paper Questions", tone: "q", x: 560, y: -220, width: 430 },
    { key: "paper_claim", title: "Paper Claims", tone: "c", x: 560, y: 70, width: 430 },
    { key: "paper_evidence", title: "Paper Evidence", tone: "e", x: 1040, y: -140, width: 390 },
    { key: "paper_warrant", title: "Paper Warrants", tone: "w", x: 1040, y: 170, width: 390 },
    { key: "paper_limitation", title: "Paper Limitations", tone: "l", x: 1480, y: 20, width: 390 },
  ];
  const focusedIds = focusedNodeIds(model);
  const nodes = [];
  if (anchor) {
    nodes.push({
      ...toFlowNode(
        { ...anchor, position: { x: 80, y: 80 } },
        0,
        model,
        focusedIds,
        (item) => {
          const target = nodeNavigationTarget(item);
          if (!target) return;
          onNavigate?.(target);
        },
      ),
      sourcePosition: Position.Right,
      targetPosition: Position.Left,
      style: { width: 390, minHeight: 150 },
      zIndex: 4,
    });
  }
  laneSpecs.forEach((lane) => {
    const items = rawNodes.filter((node) => node.entity_type === lane.key);
    if (!items.length) return;
    const frameHeight = paperFocusLaneHeight(items.length);
    nodes.push({
      id: `frame:${lane.key}`,
      type: "workspaceLaneFrameNode",
      position: { x: lane.x - 28, y: lane.y - 52 },
      style: { width: lane.width + 56, height: frameHeight },
      draggable: false,
      selectable: false,
      zIndex: 0,
      data: { title: lane.title, subtitle: `${items.length} records`, tone: lane.tone },
    });
    items.forEach((node, index) => {
      nodes.push({
        ...toFlowNode(
          { ...node, position: { x: lane.x, y: lane.y + index * 120 } },
          index,
          model,
          focusedIds,
          (item) => {
            const target = nodeNavigationTarget(item);
            if (!target) return;
            onNavigate?.(target);
          },
        ),
        sourcePosition: Position.Right,
        targetPosition: Position.Left,
        style: { width: lane.width, minHeight: 104 },
        zIndex: 3,
      });
    });
  });
  const visibleIds = new Set(rawNodes.map((node) => node.id));
  return {
    nodes,
    edges: rawEdges
      .filter((edge) => visibleIds.has(edge.source) && visibleIds.has(edge.target))
      .map((edge) => toFlowEdge(edge, model, focusedIds.size ? focusedIds : visibleIds)),
  };
}

function buildUnderstandingFlowModel(model, onNavigate) {
  if (model?.layer === "claim_focus") {
    return buildUnderstandingClaimFocusFlowModel(model, onNavigate);
  }
  if (model?.layer === "paper_focus" || model?.layer === "literature_paper_focus") {
    return buildUnderstandingPaperFocusFlowModel(model, onNavigate);
  }
  return buildUnderstandingOverviewFlowModel(model, onNavigate);
}

function WorkspaceGraphRenderer({ model, onNavigate, modeClass, providedNodes = null, providedEdges = null }) {
  const focusedIds = useMemo(() => focusedNodeIds(model), [model]);
  const graphKey = `${model?.mode || ""}:${model?.layer || ""}:${model?.focus_id || ""}`;
  const nodes = useMemo(
    () =>
      providedNodes ||
      (model?.canvas?.nodes || []).map((node, index) =>
        toFlowNode(node, index, model, focusedIds, (item) => {
          const target = nodeNavigationTarget(item);
          if (!target) return;
          onNavigate?.(target);
        }),
      ),
    [model, focusedIds, onNavigate, providedNodes],
  );
  const edges = useMemo(
    () => providedEdges || (model?.canvas?.edges || []).map((edge) => toFlowEdge(edge, model, focusedIds)),
    [model, focusedIds, providedEdges],
  );
  const handleNodeClick = useCallback((event, flowNode) => {
    if (flowNode?.type !== "workspaceRouteFrameNode") return;
    const target = nodeNavigationTarget(flowNode?.data?.node);
    if (!target) return;
    onNavigate?.(target);
  }, [onNavigate]);
  return (
    <div className={`workspace-knowledge-canvas ${modeClass || ""}`} aria-label="Workspace graph canvas">
      <WorkspaceBreadcrumb model={model} onNavigate={onNavigate} />
      <ReactFlow
        key={graphKey}
        nodes={nodes}
        edges={edges}
        nodeTypes={workspaceNodeTypes}
        fitView
        fitViewOptions={{ padding: 0.1, maxZoom: 1.12 }}
        minZoom={0.05}
        maxZoom={2.2}
        panOnDrag
        panOnScroll
        zoomOnPinch
        zoomOnScroll
        zoomOnDoubleClick={false}
        nodesDraggable={false}
        elementsSelectable
        onNodeClick={handleNodeClick}
        proOptions={{ hideAttribution: true }}
      >
        <Background variant={BackgroundVariant.Lines} gap={42} size={1} color="var(--workspace-grid-color)" />
        <Controls position="top-right" showInteractive={false} />
        <MiniMap
          position="bottom-right"
          nodeColor={nodeColor}
          pannable
          zoomable
          maskColor="var(--workspace-minimap-mask)"
          className="workspace-minimap"
        />
      </ReactFlow>
    </div>
  );
}

function UnderstandingGraphRenderer({ model, onNavigate }) {
  const { nodes, edges } = useMemo(() => buildUnderstandingFlowModel(model, onNavigate), [model, onNavigate]);
  return (
    <WorkspaceGraphRenderer
      model={model}
      onNavigate={onNavigate}
      modeClass="is-understanding"
      providedNodes={nodes}
      providedEdges={edges}
    />
  );
}

function sortLiteraturePapersByTime(papers) {
  return [...papers].sort((left, right) => {
    const leftYear = Number(left.metadata?.sort_year || 9999);
    const rightYear = Number(right.metadata?.sort_year || 9999);
    if (leftYear !== rightYear) return leftYear - rightYear;
    const leftMonth = Number(left.metadata?.sort_month || 12);
    const rightMonth = Number(right.metadata?.sort_month || 12);
    if (leftMonth !== rightMonth) return leftMonth - rightMonth;
    return String(left.label || "").localeCompare(String(right.label || ""));
  });
}

function buildLiteratureOverviewFlowModel(model, onNavigate) {
  const rawNodes = model?.canvas?.nodes || [];
  const routeNodes = rawNodes
    .filter((node) => node.entity_type === "literature_lane")
    .sort((left, right) => Number(left.metadata?.route_index || 0) - Number(right.metadata?.route_index || 0));
  const paperNodes = rawNodes.filter((node) => node.entity_type !== "literature_lane");
  const routes = routeNodes.length ? routeNodes : [{ id: "route:all", label: "Literature", metadata: { route_key: "all", route_index: 0 }, display: { tone: "route-0" } }];
  const laneHeight = 185;
  const paperGap = 38;
  const paperWidth = 246;
  const nodes = [];
  routes.forEach((route, routeOrder) => {
    const routeKey = route.metadata?.route_key || route.local_id || route.id;
    const routePapers = sortLiteraturePapersByTime(
      paperNodes.filter((paper) => routeNodes.length === 0 || paper.metadata?.route_key === routeKey),
    );
    const tone = `route-${routeColorIndex(route, routeOrder)}`;
    const laneY = routeOrder * laneHeight;
    const frameWidth = Math.max(980, 310 + routePapers.length * (paperWidth + paperGap));
    nodes.push({
      id: `frame:${route.id}`,
      type: "workspaceRouteFrameNode",
      position: { x: -40, y: laneY - 42 },
      style: { width: frameWidth, height: 150 },
      draggable: false,
      selectable: false,
      zIndex: 2,
      data: {
        node: route,
        title: route.label || route.local_id || "Route",
        subtitle: `${routePapers.length} papers`,
        tone,
        onNodeAction: (item) => {
          const target = nodeNavigationTarget(item);
          if (!target) return;
          onNavigate?.(target);
        },
      },
    });
    routePapers.forEach((paper, index) => {
      nodes.push({
        id: paper.id,
        type: "workspaceTimelinePaperNode",
        position: { x: 300 + index * (paperWidth + paperGap), y: laneY },
        sourcePosition: Position.Right,
        targetPosition: Position.Left,
        style: { width: paperWidth, minHeight: 100 },
        zIndex: 3,
        data: {
          node: paper,
          tone,
          onNodeAction: (item) => {
            const target = nodeNavigationTarget(item);
            if (!target) return;
            onNavigate?.(target);
          },
        },
      });
    });
  });
  return {
    nodes,
    edges: [],
  };
}

function buildLiteratureRouteFocusFlowModel(model, onNavigate) {
  return buildLiteratureOverviewFlowModel(model, onNavigate);
}

function LiteratureGraphRenderer({ model, onNavigate }) {
  const overviewLayer = model?.layer === "literature_overview";
  const routeLayer = model?.layer === "literature_route_focus";
  const paperLayer = model?.layer === "literature_paper_focus";
  const flow = useMemo(
    () => {
      if (paperLayer) return buildUnderstandingPaperFocusFlowModel(model, onNavigate);
      if (routeLayer) return buildLiteratureRouteFocusFlowModel(model, onNavigate);
      if (overviewLayer) return buildLiteratureOverviewFlowModel(model, onNavigate);
      return null;
    },
    [model, onNavigate, paperLayer, routeLayer, overviewLayer],
  );
  if (!overviewLayer && !routeLayer && !paperLayer) {
    return <WorkspaceGraphRenderer model={model} onNavigate={onNavigate} modeClass="is-literature" />;
  }
  return (
    <WorkspaceGraphRenderer
      model={model}
      onNavigate={onNavigate}
      modeClass="is-literature"
      providedNodes={flow.nodes}
      providedEdges={flow.edges}
    />
  );
}

function experimentsNodeAction(onNavigate) {
  return (item) => {
    const target = nodeNavigationTarget(item);
    if (!target) return;
    onNavigate?.(target);
  };
}

function toExperimentEntityNode(node, index, model, focusedIds, onNavigate, options = {}) {
  return {
    id: node.id,
    type: "workspaceExperimentEntityNode",
    position: options.position || workspaceNodePosition(node, index, model),
    sourcePosition: Position.Right,
    targetPosition: Position.Left,
    style: { width: options.width || 300, minHeight: options.minHeight || 96 },
    zIndex: options.zIndex || 3,
    data: {
      node,
      tone: cssTone(options.tone || node.display?.tone || entityTone(node.entity_type)),
      onNodeAction: experimentsNodeAction(onNavigate),
    },
  };
}

function toExperimentEdge(edge) {
  const relation = relationClass(edge.relation || edge.label);
  const color = {
    defines: "#d6a84f",
    uses: "#d6a84f",
    "measured-by": "#68c7d4",
    "used-by": "#70d6a3",
    produces: "#70d6a3",
  }[relation] || "#d6a84f";
  return {
    id: edge.id,
    source: edge.source,
    target: edge.target,
    type: "smoothstep",
    className: `workspace-edge workspace-edge-${relation}`.trim(),
    markerEnd: { type: MarkerType.ArrowClosed, color },
    style: {
      stroke: color,
      strokeWidth: 1.8,
      opacity: 0.46,
      strokeDasharray: relation === "measured-by" ? "7 7" : undefined,
    },
  };
}

function buildExperimentsArenaOverviewFlowModel(model, onNavigate) {
  const arenas = model?.canvas?.nodes || [];
  const cardWidth = 360;
  const cardHeight = 118;
  const gapX = 76;
  const gapY = 54;
  const nodes = arenas.map((node, index) => ({
    id: node.id,
    type: "workspaceExperimentArenaNode",
    position: { x: (index % 2) * (cardWidth + gapX), y: Math.floor(index / 2) * (cardHeight + gapY) },
    sourcePosition: Position.Right,
    targetPosition: Position.Left,
    style: { width: cardWidth, minHeight: cardHeight },
    zIndex: 3,
    data: {
      node,
      onNodeAction: experimentsNodeAction(onNavigate),
    },
  }));
  return { nodes, edges: [] };
}

function buildExperimentsArenaFocusFlowModel(model, onNavigate) {
  const rawNodes = model?.canvas?.nodes || [];
  const contextNodes = rawNodes.filter((node) => node.entity_type === "evaluation_context");
  const experimentNodes = rawNodes.filter((node) => node.entity_type === "experiment");
  const focusedIds = focusedNodeIds(model);
  const nodes = [
    {
      id: "frame:arena-context",
      type: "workspaceLaneFrameNode",
      position: { x: 36, y: -44 },
      style: { width: 470, height: Math.max(330, contextNodes.length * 104 + 92) },
      draggable: false,
      selectable: false,
      zIndex: 0,
      data: { title: "Evaluation Context", subtitle: "dataset, benchmark, metric", tone: "p" },
    },
    {
      id: "frame:arena-designs",
      type: "workspaceLaneFrameNode",
      position: { x: 590, y: -44 },
      style: { width: 560, height: Math.max(330, experimentNodes.length * 126 + 92) },
      draggable: false,
      selectable: false,
      zIndex: 0,
      data: { title: "Experiment Designs", subtitle: `${experimentNodes.length} designs`, tone: "e" },
    },
  ];
  contextNodes.forEach((node, index) => {
    nodes.push({
      id: node.id,
      type: "workspaceExperimentContextPanelNode",
      position: { x: 76, y: 34 + index * 150 },
      sourcePosition: Position.Right,
      targetPosition: Position.Left,
      style: { width: 390, minHeight: 136 },
      zIndex: 4,
      data: { node, tone: "p" },
    });
  });
  experimentNodes.forEach((node, index) => {
    nodes.push(
      toExperimentEntityNode(node, index, model, focusedIds, onNavigate, {
        position: { x: 630, y: 28 + index * 126 },
        width: 470,
        minHeight: 100,
        tone: "e",
      }),
    );
  });
  return {
    nodes,
    edges: [],
  };
}

function buildExperimentsDesignFocusFlowModel(model, onNavigate) {
  const rawNodes = model?.canvas?.nodes || [];
  const rawEdges = model?.canvas?.edges || [];
  const experiment = rawNodes.find((node) => node.entity_type === "experiment");
  const methodNode = rawNodes.find((node) => node.entity_type === "experiment_method");
  const methodGroups = groupExperimentMethodNodes(rawNodes);
  const runNodes = rawNodes.filter((node) => node.entity_type === "run");
  const focusedIds = focusedNodeIds(model);
  const runNodeStep = 152;
  const runNodeHeight = 112;
  const nodes = [
    {
      id: "frame:design-method",
      type: "workspaceLaneFrameNode",
      position: { x: 500, y: -48 },
      style: { width: 500, height: 520 },
      draggable: false,
      selectable: false,
      zIndex: 0,
      data: { title: "Design Method", subtitle: "models, baselines, protocol", tone: "p" },
    },
    {
      id: "frame:design-runs",
      type: "workspaceLaneFrameNode",
      position: { x: 980, y: -48 },
      style: { width: 430, height: Math.max(330, runNodes.length * runNodeStep + 92) },
      draggable: false,
      selectable: false,
      zIndex: 0,
      data: { title: "Runs / Results", subtitle: `${runNodes.length} runs`, tone: "r" },
    },
  ];
  if (experiment) {
    nodes.push(
      toExperimentEntityNode(experiment, 0, model, focusedIds, onNavigate, {
        position: { x: 40, y: 72 },
        width: 400,
        minHeight: 112,
        tone: "e",
      }),
    );
  }
  nodes.push({
    id: methodNode?.id || "method-panel",
    type: "workspaceExperimentMethodPanelNode",
    position: { x: 540, y: 24 },
    sourcePosition: Position.Right,
    targetPosition: Position.Left,
    style: { width: 420, minHeight: 432 },
    zIndex: 4,
    data: { groups: methodGroups, node: methodNode, onNodeAction: experimentsNodeAction(onNavigate) },
  });
  runNodes.forEach((node, index) => {
    nodes.push({
      id: node.id,
      type: "workspaceRunResultNode",
      position: { x: 1020, y: 24 + index * runNodeStep },
      sourcePosition: Position.Right,
      targetPosition: Position.Left,
      style: { width: 350, minHeight: runNodeHeight },
      zIndex: 4,
      data: { node, tone: "r", onNodeAction: experimentsNodeAction(onNavigate) },
    });
  });
  const visibleIds = new Set(nodes.map((node) => node.id));
  return {
    nodes,
    edges: rawEdges
      .filter((edge) => visibleIds.has(edge.source) && visibleIds.has(edge.target))
      .map((edge) => toExperimentEdge(edge)),
  };
}

function buildExperimentsOverviewFlowModel(model, onNavigate) {
  return buildExperimentsArenaOverviewFlowModel(model, onNavigate);
}

function buildExperimentsFlowModel(model, onNavigate) {
  if (model?.layer === "evaluation_overview") return buildExperimentsArenaOverviewFlowModel(model, onNavigate);
  if (model?.layer === "evaluation_arena_focus" || model?.layer === "evaluation_setting_focus") return buildExperimentsArenaFocusFlowModel(model, onNavigate);
  if (model?.layer === "experiment_design_focus") return buildExperimentsDesignFocusFlowModel(model, onNavigate);
  return { nodes: [], edges: [] };
}

function ExperimentsGraphRenderer({ model, onNavigate }) {
  const { nodes, edges } = useMemo(() => buildExperimentsFlowModel(model, onNavigate), [model, onNavigate]);
  return (
    <WorkspaceGraphRenderer
      model={model}
      onNavigate={onNavigate}
      modeClass="is-experiments"
      providedNodes={nodes}
      providedEdges={edges}
    />
  );
}

function ModeGraphRenderer({ model, onNavigate }) {
  if (model?.mode === "understanding") return <UnderstandingGraphRenderer model={model} onNavigate={onNavigate} />;
  if (model?.mode === "literature") return <LiteratureGraphRenderer model={model} onNavigate={onNavigate} />;
  if (model?.mode === "experiments") return <ExperimentsGraphRenderer model={model} onNavigate={onNavigate} />;
  return <UnderstandingGraphRenderer model={model} onNavigate={onNavigate} />;
}

function WorkspaceIslandApp({ model, onNavigate }) {
  const [activeMode, setActiveMode] = useState(model?.mode || "understanding");
  const [isImmersive, setIsImmersive] = useState(false);
  useEffect(() => {
    setActiveMode(model?.mode || "understanding");
  }, [model?.mode]);
  useEffect(() => {
    document.body.classList.toggle("workspace-island-immersive-active", isImmersive);
    return () => document.body.classList.remove("workspace-island-immersive-active");
  }, [isImmersive]);
  useEffect(() => {
    const handler = (event) => onNavigate?.(event.detail || {});
    window.addEventListener("workspace-island-action", handler);
    return () => window.removeEventListener("workspace-island-action", handler);
  }, [onNavigate]);
  useEffect(() => {
    const handler = (event) => {
      if (event.key !== "Escape") return;
      if (isImmersive) {
        event.preventDefault();
        setIsImmersive(false);
        return;
      }
      const crumbs = normalizeBreadcrumb(model);
      if (crumbs.length < 2) return;
      event.preventDefault();
      onNavigate?.(crumbs[crumbs.length - 2]);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [isImmersive, model, onNavigate]);
  return (
    <ReactFlowProvider>
      <section className={`workspace-island-shell ${isImmersive ? "is-immersive" : ""}`}>
        <header className="workspace-island-toolbar">
          <nav aria-label="Workspace modes">
            {modes.map((mode) => (
              <button
                key={mode}
                type="button"
                className={mode === activeMode ? "is-active" : ""}
                onClick={() => {
                  setActiveMode(mode);
                  onNavigate?.({ mode });
                }}
              >
                {modeLabels[mode]}
              </button>
            ))}
          </nav>
          <button
            type="button"
            className="workspace-island-focus-button"
            aria-pressed={isImmersive ? "true" : "false"}
            onClick={() => setIsImmersive((value) => !value)}
          >
            {isImmersive ? "Exit" : "Focus"}
          </button>
        </header>
        <div className="workspace-island-body">
          <ModeGraphRenderer model={model} onNavigate={onNavigate} />
          <WorkspaceInspector inspector={model?.inspector || {}} />
        </div>
      </section>
    </ReactFlowProvider>
  );
}

function mount(root, props) {
  if (!root) return null;
  const previous = mountedRoots.get(root);
  if (previous) {
    previous.render(<WorkspaceIslandApp {...props} />);
    return previous;
  }
  const reactRoot = createRoot(root);
  reactRoot.render(<WorkspaceIslandApp {...props} />);
  mountedRoots.set(root, reactRoot);
  return reactRoot;
}

window.ResearchBrowserWorkspaceIsland = { mount, WorkspaceIslandApp };
