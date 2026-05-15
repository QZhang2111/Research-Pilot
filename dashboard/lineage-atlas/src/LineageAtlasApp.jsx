import React, { useMemo } from "react";
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
import "./lineage-atlas.css";

const mountedRoots = new WeakMap();
const ROUTE_COLORS = ["#d6a84f", "#70d6a3", "#8ec7ff", "#d2a6ff", "#e58b83", "#68c7d4", "#f2a6c7", "#a8d66d"];

function firstNonEmptyText(...values) {
  for (const value of values) {
    const text = String(value || "").replace(/\s+/g, " ").trim();
    if (text) return text;
  }
  return "";
}

function safeExternalSourceUrl(value) {
  const raw = String(value || "").trim();
  if (!raw) return "";
  try {
    const url = new URL(raw);
    return ["http:", "https:"].includes(url.protocol) ? url.href : "";
  } catch (_error) {
    return "";
  }
}

export function lineageTopicName(map = {}, project = {}) {
  return firstNonEmptyText(
    map.topic_name,
    map.display?.topic_name,
    cleanLineageTitle(map.title),
    project.title,
    project.name,
    project.id,
    "Lineage Atlas"
  );
}

function sanitizeLineageItems(items = []) {
  return items.filter((item) => item && typeof item === "object" && !Array.isArray(item));
}

function flowSafeId(prefix, value) {
  return `${prefix}:${encodeURIComponent(String(value || prefix))}`;
}

function flowIndexedId(prefix, index, value) {
  return `${prefix}:${index}:${encodeURIComponent(String(value || prefix))}`;
}

function cleanLineageTitle(value) {
  const text = String(value || "").replace(/\s+/g, " ").trim();
  return text.replace(/\s+(related work lineage|lineage atlas)$/i, "").trim() || text;
}

function shortLabel(value, limit = 54) {
  const text = String(value || "").replace(/\s+/g, " ").trim();
  if (text.length <= limit) return text;
  return `${text.slice(0, limit - 1).trim()}...`;
}

function sortedPaperEntries(paperEntries = []) {
  return [...paperEntries].sort((a, b) => {
    const paperA = a.paper;
    const paperB = b.paper;
    const yearA = Number(paperA.year || 9999);
    const yearB = Number(paperB.year || 9999);
    if (yearA !== yearB) return yearA - yearB;
    const monthA = Number(paperA.month || 99);
    const monthB = Number(paperB.month || 99);
    if (monthA !== monthB) return monthA - monthB;
    return String(paperA.title || "").localeCompare(String(paperB.title || ""));
  });
}

function sortedPapers(papers = []) {
  return sortedPaperEntries(
    papers.map((paper, index) => ({
      paper,
      index,
    }))
  ).map((entry) => entry.paper);
}

function uniqueLineageRoutes(sourceRoutes = [], papers = []) {
  const seenRouteIds = new Set();
  const routes = [];

  sourceRoutes.forEach((route, index) => {
    const id = String(route.id || `missing-route-${index}`);
    if (seenRouteIds.has(id)) return;
    seenRouteIds.add(id);
    routes.push({
      ...route,
      id,
      label: route.label || id,
    });
  });

  const missingRouteIds = [
    ...new Set(
      papers
        .map((paper) => String(paper.route || "unassigned"))
        .filter((routeId) => !seenRouteIds.has(routeId))
    ),
  ];

  return [
    ...routes,
    ...missingRouteIds.map((routeId) => ({
      id: routeId,
      label: routeId === "unassigned" ? "Unassigned" : routeId,
      review_status: "candidate",
    })),
  ];
}

function LineageTopicNode({ data }) {
  return (
    <div className="lineage-atlas-topic-node">
      <Handle type="source" position={Position.Right} className="lineage-atlas-handle" />
      <button type="button" className="lineage-atlas-node-button" onClick={() => data.onSelect?.({ type: "map" })}>
        <span>Topic</span>
        <strong>{data.label}</strong>
        <em>{data.subtitle}</em>
      </button>
    </div>
  );
}

function LineageRouteNode({ data }) {
  return (
    <div
      className={`lineage-atlas-route-node ${data.selected ? "is-selected" : ""}`}
      style={{ "--route-color": data.color }}
    >
      <Handle type="target" position={Position.Left} className="lineage-atlas-handle" />
      <button
        type="button"
        className="lineage-atlas-node-button"
        onClick={() => data.onSelect?.({ type: "route", route: data.route })}
      >
        <span>{data.reviewStatus || "candidate"}</span>
        <strong>{data.label}</strong>
        <em>{data.paperCount} papers</em>
      </button>
      <Handle type="source" position={Position.Right} className="lineage-atlas-handle" />
    </div>
  );
}

function LineagePaperNode({ data }) {
  return (
    <div
      className={`lineage-atlas-paper-node ${data.isBaseline ? "is-baseline" : ""} ${data.selected ? "is-selected" : ""}`}
      style={{ "--route-color": data.color }}
    >
      <Handle type="target" position={Position.Left} className="lineage-atlas-handle" />
      <button
        type="button"
        className="lineage-atlas-node-button"
        onClick={() => data.onSelect?.({ type: "paper", paper: data.paper })}
      >
        <span>{data.date || "n.d."}</span>
        <strong>{data.label}</strong>
        <em>{data.roles || data.status}</em>
      </button>
      <Handle type="source" position={Position.Right} className="lineage-atlas-handle" />
    </div>
  );
}

const nodeTypes = {
  topicNode: LineageTopicNode,
  routeNode: LineageRouteNode,
  paperNode: LineagePaperNode,
};

export function buildLineageAtlasModel(map = {}, project = {}, options = {}) {
  const topic = lineageTopicName(map, project);
  const selected = options.selected || { type: "map" };
  const onSelect = options.onSelect || (() => {});
  const showEdges = Boolean(options.showEdges);
  const routeFilter = String(options.routeFilter || "");
  const statusFilter = String(options.statusFilter || "");
  const query = String(options.query || "").trim().toLowerCase();
  const sourceRoutes = Array.isArray(map.routes) ? sanitizeLineageItems(map.routes) : [];
  const papers = Array.isArray(map.papers) ? sanitizeLineageItems(map.papers) : [];
  const paperEntries = papers.map((paper, index) => ({
    paper,
    index,
    rawId: paper.id,
    rawIdOrFallback: paper.id || `missing-paper-${index}`,
  }));
  const explicitEdges = Array.isArray(map.explicit_edges) ? sanitizeLineageItems(map.explicit_edges) : [];
  const routes = uniqueLineageRoutes(sourceRoutes, papers);
  const routeMap = new Map(
    routes.map((route, index) => [route.id, { ...route, color: ROUTE_COLORS[index % ROUTE_COLORS.length] }])
  );
  const visibleRouteIds = routes
    .map((route) => route.id)
    .filter((routeId) => !routeFilter || routeId === routeFilter);
  const nodes = [
    {
      id: "topic",
      type: "topicNode",
      position: { x: 0, y: 0 },
      data: {
        label: topic,
        subtitle: `${routes.length} routes / ${papers.length} papers`,
        onSelect,
      },
    },
  ];
  const edges = [];
  const paperNodeIdByRawId = new Map();
  const radiusX = 420;
  const radiusY = 260;
  const startAngle = -Math.PI * 0.78;
  const endAngle = Math.PI * 0.78;
  const angleStep = visibleRouteIds.length > 1 ? (endAngle - startAngle) / (visibleRouteIds.length - 1) : 0;

  visibleRouteIds.forEach((routeId, routeIndex) => {
    const route = routeMap.get(routeId);
    if (!route) return;
    const routeText = [route.label, route.description, route.id].join(" ").toLowerCase();
    const routeMatchesQuery = query && routeText.includes(query);
    const angle = visibleRouteIds.length === 1 ? 0 : startAngle + angleStep * routeIndex;
    const routeX = Math.cos(angle) * radiusX;
    const routeY = Math.sin(angle) * radiusY;
    const color = route.color;
    const routePapers = sortedPaperEntries(
      paperEntries.filter((paperEntry) => {
        const paper = paperEntry.paper;
        if (String(paper.route || "unassigned") !== routeId) return false;
        if (statusFilter && String(paper.review_status || "candidate") !== statusFilter) return false;
        if (!query || routeMatchesQuery) return true;
        const roles = Array.isArray(paper.roles) ? paper.roles : [];
        return [paper.title, paper.summary, paper.source_evidence, paper.field_position, paper.method_setting, ...roles]
          .join(" ")
          .toLowerCase()
          .includes(query);
      })
    );
    if (query && !routeMatchesQuery && routePapers.length === 0) return;

    const routeNodeId = flowSafeId("route", route.id);

    nodes.push({
      id: routeNodeId,
      type: "routeNode",
      position: { x: routeX, y: routeY },
      data: {
        route,
        label: route.label || route.id,
        reviewStatus: route.review_status || "candidate",
        paperCount: routePapers.length,
        color,
        selected: selected.type === "route" && selected.route?.id === route.id,
        onSelect,
      },
    });
    edges.push({
      id: `topic-route:${routeNodeId}`,
      source: "topic",
      target: routeNodeId,
      type: "smoothstep",
      className: "lineage-atlas-route-edge",
      style: { stroke: color, strokeWidth: 3 },
    });

    const directionX = Math.cos(angle);
    const directionY = Math.sin(angle);
    const tangentX = -directionY;
    const tangentY = directionX;
    routePapers.forEach((paperEntry, paperIndex) => {
      const paper = paperEntry.paper;
      const distance = 260 + paperIndex * 170;
      const alternate = paperIndex % 2 === 0 ? -1 : 1;
      const offset = alternate * 52;
      const paperId = flowIndexedId("paper", paperEntry.index, paperEntry.rawIdOrFallback);
      const date = [paper.year, paper.month].filter(Boolean).join("-");
      const roles = Array.isArray(paper.roles) ? paper.roles : [];
      const isBaseline = roles.includes("baseline");
      if (paperEntry.rawId && !paperNodeIdByRawId.has(paperEntry.rawId)) {
        paperNodeIdByRawId.set(paperEntry.rawId, paperId);
      }
      nodes.push({
        id: paperId,
        type: "paperNode",
        position: {
          x: routeX + directionX * distance + tangentX * offset,
          y: routeY + directionY * distance + tangentY * offset,
        },
        data: {
          paper,
          label: shortLabel(paper.title || paper.id, 46),
          date,
          roles: roles.slice(0, 2).join(", "),
          status: paper.review_status || "candidate",
          isBaseline,
          color,
          selected: selected.type === "paper" && selected.paper?.id === paper.id,
          onSelect,
        },
      });
      edges.push({
        id: `route-paper:${routeNodeId}:${paperId}`,
        source: routeNodeId,
        target: paperId,
        type: "smoothstep",
        className: "lineage-atlas-paper-edge",
        style: { stroke: color, strokeWidth: isBaseline ? 2.8 : 1.6 },
      });
    });
  });

  if (showEdges) {
    explicitEdges.forEach((edge, edgeIndex) => {
      const source = paperNodeIdByRawId.get(edge.source);
      const target = paperNodeIdByRawId.get(edge.target);
      if (!source || !target) return;
      edges.push({
        id: `explicit:${edgeIndex}:${source}:${target}:${flowSafeId("relation", edge.relation)}`,
        source,
        target,
        type: "smoothstep",
        label: edge.relation || "related",
        className: "lineage-atlas-explicit-edge",
        markerEnd: { type: MarkerType.ArrowClosed, color: "#d6a84f" },
        data: { edge },
      });
    });
  }

  return {
    topic,
    nodes,
    edges,
    routes,
    papers,
  };
}

function LineageInspector({ map = {}, project = {}, selected = { type: "map" }, model }) {
  if (selected?.type === "paper" && selected.paper && typeof selected.paper === "object") {
    const paper = selected.paper;
    const roles = Array.isArray(paper.roles) ? paper.roles.filter(Boolean) : [];
    const date = firstNonEmptyText([paper.year, paper.month].filter(Boolean).join("-"), paper.date, paper.published_at);
    const sourceUrl = safeExternalSourceUrl(firstNonEmptyText(paper.source_url, paper.url));

    return (
      <aside className="lineage-atlas-inspector" aria-live="polite">
        <p className="eyebrow">Paper</p>
        <h2>{paper.title || paper.id || "Untitled paper"}</h2>
        <dl>
          <div>
            <dt>Date</dt>
            <dd>{date || "n.d."}</dd>
          </div>
          <div>
            <dt>Route</dt>
            <dd>{paper.route || "unassigned"}</dd>
          </div>
          <div>
            <dt>Status</dt>
            <dd>{paper.review_status || "candidate"}</dd>
          </div>
        </dl>
        <p>{paper.summary || paper.field_position || "No summary."}</p>
        {roles.length ? (
          <div className="lineage-atlas-tagrow">
            {roles.map((role, index) => (
              <span key={`${role}:${index}`}>{role}</span>
            ))}
          </div>
        ) : null}
        {sourceUrl ? (
          <a className="lineage-atlas-source-link" href={sourceUrl} target="_blank" rel="noopener noreferrer">
            Open source
          </a>
        ) : null}
        <details>
          <summary>source evidence</summary>
          <p>{paper.source_evidence || "No source evidence."}</p>
        </details>
      </aside>
    );
  }

  if (selected?.type === "route" && selected.route && typeof selected.route === "object") {
    const route = selected.route;
    const routePapers = Array.isArray(model?.papers)
      ? model.papers.filter((paper) => String(paper.route || "unassigned") === route.id)
      : [];

    return (
      <aside className="lineage-atlas-inspector" aria-live="polite">
        <p className="eyebrow">Route</p>
        <h2>{route.label || route.id || "Unassigned"}</h2>
        <dl>
          <div>
            <dt>Status</dt>
            <dd>{route.review_status || "candidate"}</dd>
          </div>
          <div>
            <dt>Papers</dt>
            <dd>{routePapers.length}</dd>
          </div>
        </dl>
        <p>{route.description || "No route description."}</p>
        {routePapers.length ? (
          <ol>
            {sortedPapers(routePapers)
              .slice(0, 8)
              .map((paper, index) => (
                <li key={`${paper.id || paper.title || "paper"}:${index}`}>{paper.title || paper.id || "Untitled paper"}</li>
              ))}
          </ol>
        ) : null}
      </aside>
    );
  }

  const papers = Array.isArray(model?.papers) ? model.papers : [];
  const baseline = papers.find((paper) => {
    const roles = Array.isArray(paper.roles) ? paper.roles : [];
    return roles.includes("baseline");
  });

  return (
    <aside className="lineage-atlas-inspector" aria-live="polite">
      <p className="eyebrow">Topic</p>
      <h2>{model?.topic || lineageTopicName(map, project)}</h2>
      <dl>
        <div>
          <dt>Status</dt>
          <dd>{map.status || "candidate"}</dd>
        </div>
        <div>
          <dt>Routes</dt>
          <dd>{Array.isArray(model?.routes) ? model.routes.length : 0}</dd>
        </div>
        <div>
          <dt>Papers</dt>
          <dd>{papers.length}</dd>
        </div>
      </dl>
      {baseline ? <p><strong>Baseline:</strong> {baseline.title || baseline.id}</p> : null}
      <p>{map.positioning_note || project.description || "Paper-only related-work atlas."}</p>
      <p className="lineage-atlas-boundary">Paper-only lineage. Not Project Understanding Graph truth.</p>
    </aside>
  );
}

export function LineageAtlasApp({ map = {}, project = {} }) {
  const [selected, setSelected] = React.useState({ type: "map" });
  const [query, setQuery] = React.useState("");
  const [routeFilter, setRouteFilter] = React.useState("");
  const [statusFilter, setStatusFilter] = React.useState("");
  const [showEdges, setShowEdges] = React.useState(false);
  const model = useMemo(
    () =>
      buildLineageAtlasModel(map, project, {
        selected,
        onSelect: setSelected,
        query,
        routeFilter,
        statusFilter,
        showEdges,
      }),
    [map, project, selected, query, routeFilter, statusFilter, showEdges]
  );
  const statusOptions = Array.from(
    new Set((Array.isArray(model.papers) ? model.papers : []).map((paper) => paper.review_status || "candidate"))
  );
  const inspectorSelection = useMemo(() => {
    const visibleNodeIds = new Set(model.nodes.map((node) => node.id));

    if (selected?.type === "paper" && selected.paper && typeof selected.paper === "object") {
      const visiblePaperNode = model.nodes.find((node) => {
        const paper = node.data?.paper;
        return (
          node.type === "paperNode" &&
          (paper === selected.paper || (paper?.id && selected.paper?.id && paper.id === selected.paper.id))
        );
      });
      if (!visiblePaperNode || !visibleNodeIds.has(visiblePaperNode.id)) return { type: "map" };
      return selected;
    }

    if (selected?.type === "route" && selected.route && typeof selected.route === "object") {
      const visibleRouteNode = model.nodes.find((node) => {
        const route = node.data?.route;
        return (
          node.type === "routeNode" &&
          (route === selected.route || (route?.id && selected.route?.id && route.id === selected.route.id))
        );
      });
      if (!visibleRouteNode || !visibleNodeIds.has(visibleRouteNode.id)) return { type: "map" };
      return selected;
    }

    return selected || { type: "map" };
  }, [model.nodes, selected]);

  return (
    <ReactFlowProvider>
      <section className="lineage-atlas-shell">
        <div className="lineage-atlas-main">
          <div className="lineage-atlas-controlbar">
            <input
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search papers and routes"
              aria-label="Search papers and routes"
            />
            <select value={routeFilter} onChange={(event) => setRouteFilter(event.target.value)} aria-label="Filter route">
              <option value="">All routes</option>
              {model.routes.map((route) => (
                <option key={route.id} value={route.id}>
                  {route.label || route.id}
                </option>
              ))}
            </select>
            <select
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value)}
              aria-label="Filter paper status"
            >
              <option value="">All statuses</option>
              {statusOptions.map((status) => (
                <option key={status} value={status}>
                  {status}
                </option>
              ))}
            </select>
            <label>
              <input type="checkbox" checked={showEdges} onChange={(event) => setShowEdges(event.target.checked)} />
              Show edges
            </label>
            <button type="button" onClick={() => setSelected({ type: "map" })}>
              Overview
            </button>
          </div>
          <div className="lineage-atlas-flow" aria-label="Related work lineage atlas">
            <ReactFlow
              nodes={model.nodes}
              edges={model.edges}
              nodeTypes={nodeTypes}
              fitView
              fitViewOptions={{ padding: 0.22, maxZoom: 1.05 }}
              minZoom={0.08}
              maxZoom={1.8}
              panOnDrag
              panOnScroll
              zoomOnPinch
              zoomOnScroll
              zoomOnDoubleClick={false}
              nodesDraggable={false}
              elementsSelectable
              proOptions={{ hideAttribution: true }}
            >
              <Background variant={BackgroundVariant.Dots} gap={28} size={1} color="var(--graph-grid-color)" />
              <Controls position="bottom-left" showInteractive={false} />
              <MiniMap position="bottom-right" pannable zoomable className="lineage-atlas-minimap" />
            </ReactFlow>
          </div>
        </div>
        <LineageInspector map={map} project={project} selected={inspectorSelection} model={model} />
      </section>
    </ReactFlowProvider>
  );
}

export function mount(element, propsOrMap = {}, maybeProject = {}) {
  if (!element) return null;
  const props =
    propsOrMap && ("map" in propsOrMap || "project" in propsOrMap)
      ? propsOrMap
      : { map: propsOrMap, project: maybeProject };
  let root = mountedRoots.get(element);
  if (!root) {
    root = createRoot(element);
    mountedRoots.set(element, root);
  }
  root.render(<LineageAtlasApp {...props} />);
  return root;
}

window.ResearchBrowserLineageAtlas = {
  mount,
  LineageAtlasApp,
  buildLineageAtlasModel,
  lineageTopicName,
};
