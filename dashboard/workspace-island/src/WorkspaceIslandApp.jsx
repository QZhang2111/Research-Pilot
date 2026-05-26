import React, { useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
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

function nodeColor(node) {
  const type = node?.data?.entity_type || "";
  if (type === "question") return "#8ec7ff";
  if (type === "claim" || type === "evaluation_setting") return "#d6a84f";
  if (type === "experiment" || type === "run") return "#70d6a3";
  if (type === "source") return "#68c7d4";
  return "#8f98a8";
}

function toFlowNode(node, index, onNodeAction) {
  return {
    id: node.id,
    type: "default",
    position: node.position || { x: (index % 4) * 340, y: Math.floor(index / 4) * 180 },
    data: {
      label: (
        <button type="button" className="workspace-node-button" onClick={() => onNodeAction(node)}>
          <span>{node.local_id || node.entity_type}</span>
          <strong>{node.label}</strong>
          {node.subtitle ? <em>{node.subtitle}</em> : null}
        </button>
      ),
      entity_type: node.entity_type,
    },
    style: { width: node.entity_type === "source" ? 320 : 300, minHeight: 112 },
  };
}

function toFlowEdge(edge) {
  return {
    id: edge.id,
    source: edge.source,
    target: edge.target,
    label: edge.label,
    type: "smoothstep",
  };
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
    </aside>
  );
}

function WorkspaceIslandApp({ model, onNavigate }) {
  const [activeMode, setActiveMode] = useState(model?.mode || "understanding");
  const nodes = useMemo(
    () =>
      (model?.canvas?.nodes || []).map((node, index) =>
        toFlowNode(node, index, (item) => onNavigate?.(item.drill || item.inspector || { selected_id: item.id })),
      ),
    [model, onNavigate],
  );
  const edges = useMemo(() => (model?.canvas?.edges || []).map(toFlowEdge), [model]);
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
          <div className="workspace-canvas" aria-label="Workspace graph canvas">
            <ReactFlow nodes={nodes} edges={edges} fitView minZoom={0.05} maxZoom={2} proOptions={{ hideAttribution: true }}>
              <Background variant={BackgroundVariant.Lines} gap={42} size={1} />
              <Controls position="top-right" showInteractive={false} />
              <MiniMap position="bottom-right" nodeColor={nodeColor} pannable zoomable />
            </ReactFlow>
          </div>
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
