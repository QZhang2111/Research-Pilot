import React, { memo, useEffect, useMemo, useState } from "react";
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
  if (type === "claim" || type === "evaluation_setting") return "c";
  if (type === "evidence" || type === "experiment") return "e";
  if (type === "warrant") return "w";
  if (type === "limitation") return "l";
  if (type === "source" || type === "paper" || type === "literature_lane") return "p";
  if (type === "run") return "r";
  return "x";
}

function displayTone(node) {
  return node?.data?.node?.display?.tone || node?.data?.display?.tone || entityTone(node?.data?.entity_type || node?.data?.node?.entity_type);
}

function cssTone(tone) {
  return {
    question: "q",
    claim: "c",
    evidence: "e",
    warrant: "w",
    limitation: "l",
    source: "p",
    run: "r",
  }[tone] || tone || "x";
}

function nodeColor(node) {
  const tone = displayTone(node);
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
    if (type === "evaluation_setting") return { x: sameTypeIndex * 410, y: -40 };
    if (type === "experiment") return { x: sameTypeIndex * 380, y: 210 };
    if (type === "run") return { x: sameTypeIndex * 340, y: 430 };
  }
  return { x: (index % 4) * 360, y: Math.floor(index / 4) * 180 };
}

function workspaceNodeWidth(node, model) {
  if (model?.mode === "literature") return node.entity_type === "literature_lane" ? 300 : 330;
  if (model?.mode === "experiments") return node.entity_type === "evaluation_setting" ? 360 : 330;
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

function DisplayBadges({ display }) {
  const badges = Array.isArray(display?.badges) ? display.badges : [];
  if (!badges.length) return null;
  return (
    <span className="workspace-node-badges">
      {badges.map((badge) => (
        <small key={`${badge.key || "badge"}:${badge.label}`} data-tone={badge.tone || display?.tone || "unknown"}>
          {badge.label}
        </small>
      ))}
    </span>
  );
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
      <DisplayBadges display={node.display} />
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

const WorkspaceArgumentAtomNode = memo(function WorkspaceArgumentAtomNode({ data }) {
  const node = data.node || {};
  return (
    <article className={`workspace-argument-atom tone-${data.tone || "x"}`}>
      <Handle type="source" position={Position.Right} className="workspace-node-handle" />
      <span>{node.local_id || node.subtitle || node.entity_type}</span>
      <strong>{shortLabel(node.label, 128)}</strong>
      <em>{node.subtitle || node.entity_type}</em>
      <DisplayBadges display={node.display} />
    </article>
  );
});

const WorkspacePaperSourceNode = memo(function WorkspacePaperSourceNode({ data }) {
  const node = data.node || {};
  return (
    <button type="button" className="workspace-paper-source-node" onClick={() => data.onNodeAction?.(node)}>
      <Handle type="target" position={Position.Left} className="workspace-node-handle" />
      <span>{node.local_id || node.source_id || "paper"}</span>
      <strong>{shortLabel(node.label, 96)}</strong>
      <em>{node.subtitle || "paper/source"}</em>
      <DisplayBadges display={node.display} />
    </button>
  );
});

const workspaceNodeTypes = {
  workspaceKnowledgeNode: WorkspaceKnowledgeNode,
  workspaceLaneFrameNode: WorkspaceLaneFrameNode,
  workspaceArgumentAtomNode: WorkspaceArgumentAtomNode,
  workspacePaperSourceNode: WorkspacePaperSourceNode,
};

function isTopLevelWorkspaceLayer(layer) {
  return (
    layer === "project_overview" ||
    layer === "literature_overview" ||
    layer === "evaluation_overview"
  );
}

function breadcrumbLabelForTarget(target) {
  const raw = target?.selected_id || target?.focus_id || target?.layer || target?.mode || "Workspace";
  const text = String(raw).replace(/^[^:]+:/, "").replace(/_/g, " ").trim();
  return text || "Workspace";
}

function currentBreadcrumbTarget(model) {
  const layer = model?.layer || "";
  const focus_id = model?.focus_id || "";
  const selected_id = model?.selected_id || "";
  if (!layer && !focus_id && !selected_id) return null;
  if (isTopLevelWorkspaceLayer(layer) && !focus_id) return null;
  if (!focus_id && selected_id) return null;
  const target = {
    label: "",
    mode: model?.mode || "understanding",
    layer,
    focus_id,
    selected_id: model?.selected_id || "",
  };
  target.label = breadcrumbLabelForTarget(target);
  return target;
}

function sameBreadcrumbTarget(left, right) {
  return Boolean(left && right)
    && left.mode === right.mode
    && left.layer === right.layer
    && left.focus_id === right.focus_id
    && left.selected_id === right.selected_id;
}

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
  const currentTarget = currentBreadcrumbTarget(model);
  if (currentTarget && !sameBreadcrumbTarget(normalized[normalized.length - 1], currentTarget)) {
    normalized.push(currentTarget);
  }
  if (normalized.length) return normalized;
  return [{
    label: "Workspace",
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
      {sections.map((section, index) => (
        <section key={`${section.kind || "section"}:${index}`}>
          <h3>{section.title || section.kind || "Section"}</h3>
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
      ))}
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

function buildUnderstandingClaimFocusFlowModel(model, onNavigate) {
  const rawNodes = model?.canvas?.nodes || [];
  const focusId = model?.focus_id || rawNodes.find((node) => node.entity_type === "claim")?.id || "";
  const claim = rawNodes.find((node) => node.id === focusId) || rawNodes.find((node) => node.entity_type === "claim");
  if (!claim) return { nodes: [], edges: [] };

  const laneConfig = [
    { key: "evidence", title: "Evidence / Grounds", tone: "e", x: 720, y: 20, relation: "supports" },
    { key: "warrant", title: "Warrants / Bridges", tone: "w", x: 720, y: 310, relation: "qualifies" },
    { key: "limitation", title: "Limitations / Boundaries", tone: "l", x: 1120, y: 165, relation: "bounds" },
    { key: "source", title: "Source Papers", tone: "p", x: 1540, y: 20, relation: "cites" },
  ];

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
    const frameHeight = Math.max(190, items.length * 130 + 92);
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
        data: { node, tone: cssTone(node.display?.tone || lane.tone) },
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

function buildUnderstandingFlowModel(model, onNavigate) {
  if (model?.layer === "claim_focus") {
    return buildUnderstandingClaimFocusFlowModel(model, onNavigate);
  }
  return buildUnderstandingOverviewFlowModel(model, onNavigate);
}

function WorkspaceGraphRenderer({ model, onNavigate, modeClass, providedNodes = null, providedEdges = null }) {
  const focusedIds = useMemo(() => focusedNodeIds(model), [model]);
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
  return (
    <div className={`workspace-knowledge-canvas ${modeClass || ""}`} aria-label="Workspace graph canvas">
      <WorkspaceBreadcrumb model={model} onNavigate={onNavigate} />
      <ReactFlow
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

function LiteratureGraphRenderer(props) {
  return <WorkspaceGraphRenderer {...props} modeClass="is-literature" />;
}

function ExperimentsGraphRenderer(props) {
  return <WorkspaceGraphRenderer {...props} modeClass="is-experiments" />;
}

function ModeGraphRenderer({ model, onNavigate }) {
  if (model?.mode === "understanding") return <UnderstandingGraphRenderer model={model} onNavigate={onNavigate} />;
  if (model?.mode === "literature") return <LiteratureGraphRenderer model={model} onNavigate={onNavigate} />;
  if (model?.mode === "experiments") return <ExperimentsGraphRenderer model={model} onNavigate={onNavigate} />;
  return <UnderstandingGraphRenderer model={model} onNavigate={onNavigate} />;
}

function WorkspaceIslandApp({ model, onNavigate }) {
  const [activeMode, setActiveMode] = useState(model?.mode || "understanding");
  useEffect(() => {
    setActiveMode(model?.mode || "understanding");
  }, [model?.mode]);
  useEffect(() => {
    const handler = (event) => onNavigate?.(event.detail || {});
    window.addEventListener("workspace-island-action", handler);
    return () => window.removeEventListener("workspace-island-action", handler);
  }, [onNavigate]);
  useEffect(() => {
    const handler = (event) => {
      if (event.key !== "Escape") return;
      const crumbs = normalizeBreadcrumb(model);
      if (crumbs.length < 2) return;
      event.preventDefault();
      onNavigate?.(crumbs[crumbs.length - 2]);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [model, onNavigate]);
  return (
    <ReactFlowProvider>
      <section className="workspace-island-shell">
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
  if (previous) previous.unmount();
  const reactRoot = createRoot(root);
  reactRoot.render(<WorkspaceIslandApp {...props} />);
  mountedRoots.set(root, reactRoot);
  return reactRoot;
}

window.ResearchBrowserWorkspaceIsland = { mount, WorkspaceIslandApp };
