const STATUS_ORDER = ["inbox", "candidate", "reading", "summarized", "approved", "rejected", "archived"];
const DASHBOARD_PAGE_VERSION = "english-dashboard-20260523";
const STATUS_LABELS = {
  inbox: "Inbox",
  candidate: "Candidate",
  triaged: "Triaged",
  reading: "Reading",
  summarized: "Summarized",
  approved: "Approved",
  rejected: "Rejected",
  archived: "Archived",
  unknown: "Unknown",
};
const FAMILY_LABELS = {
  direct: "Direct",
  probing: "Representation probing",
  capability: "Capability evaluation",
  unknown: "Unknown",
};
const RELEVANCE_LABELS = {
  high: "High",
  medium: "Medium",
  low: "Low",
  unscored: "Unscored",
};
const PAPER_STATE_ORDER = ["candidate", "reading", "summarized", "approved", "project-core", "rejected", "archived"];
const PAPER_STATE_LABELS = {
  inbox: "Inbox",
  candidate: "Needs triage",
  reading: "Reading requested",
  summarized: "Deep read complete",
  approved: "Added to project",
  "project-core": "Project core",
  rejected: "Rejected",
  archived: "Archived",
  unknown: "Unknown",
};
const PAPER_READ_FILTER_LABELS = {
  "deep-read": "Deep read / memo available",
};
const MEMO_SECTION_LABELS = {
  "Memo overview": "Memo Overview",
  "Core Contribution": "Core Contribution",
  "Why It Matters For Target Project": "Why It Matters for the Target Project",
  "Interpretive Deep Read": "Interpretive Deep Read",
  "Teaching-Grade Deep Read": "Teaching-Grade Deep Read",
  Evidence: "Evidence",
  Claims: "Claims",
  Limitations: "Limitations",
  "Project Role Assessment": "Project Role Assessment",
  "Open Questions": "Open Questions",
  "Problem Setting": "Problem Setting",
  Method: "Method",
  Connections: "Connections",
  "Human Notes": "Human Notes",
  "Read Provenance": "Read Provenance",
  "Source Identity": "Source Identity",
  "1. Paper's real question": "1. Paper real question",
  "2. Background tension": "2. Background tension",
  "3. Author's core hypothesis": "3. Author core hypothesis",
  "4. Paper structure": "4. Paper structure",
  "5. Method mechanism": "5. Method mechanism",
  "6. Experiment logic": "6. Experiment logic",
  "7. True insight": "7. Core insight",
  "8. Position for the target project": "8. Position for the target project",
  "8. Position for the target project": "8. Position for the target project",
  "9. What not to learn": "9. What not to learn",
};

const THEME_STORAGE_KEY = "research-browser-theme";
const THEME_LABELS = {
  dark: "Dark",
  light: "Light",
};

const GRAPH_PAN_DRAG_THRESHOLD = 5;
const GRAPH_PAN_INERTIA_DECAY = 0.91;
const GRAPH_PAN_MIN_VELOCITY = 0.18;
const GRAPH_PAN_MAX_VELOCITY = 36;
let graphPanMomentumFrame = 0;

const state = {
  data: null,
  page: document.body.dataset.page || "projects",
  projectId: "",
  roundId: "",
  paperId: "",
  focusedCandidateKey: "",
  selectedGraphNodeId: "",
  paperGraphCache: {},
  activePaperGraphPath: "",
  graphZoom: 0.82,
  graphMaintenance: null,
  projectUnderstanding: null,
  selectedGraphDeltaId: "",
};

function normalizeTheme(value) {
  return value === "light" ? "light" : "dark";
}

function storedTheme() {
  try {
    return normalizeTheme(window.localStorage.getItem(THEME_STORAGE_KEY));
  } catch (_error) {
    return "dark";
  }
}

function applyTheme(theme, { persist = false } = {}) {
  const nextTheme = normalizeTheme(theme);
  document.documentElement.dataset.theme = nextTheme;
  document.body.dataset.theme = nextTheme;
  if (persist) {
    try {
      window.localStorage.setItem(THEME_STORAGE_KEY, nextTheme);
    } catch (_error) {
      // Theme should still switch even when localStorage is unavailable.
    }
  }
  updateThemeToggle();
}

function mountThemeToggle() {
  const topbar = document.querySelector(".topbar");
  if (!topbar || topbar.querySelector("[data-theme-toggle]")) return;
  const button = document.createElement("button");
  button.type = "button";
  button.className = "theme-toggle";
  button.dataset.themeToggle = "";
  button.innerHTML = `
    <span class="theme-toggle-mark" aria-hidden="true"></span>
    <span class="theme-toggle-text"></span>
  `;
  button.addEventListener("click", () => {
    const nextTheme = document.body.dataset.theme === "light" ? "dark" : "light";
    applyTheme(nextTheme, { persist: true });
  });
  topbar.append(button);
  updateThemeToggle();
}

function updateThemeToggle() {
  const button = document.querySelector("[data-theme-toggle]");
  if (!button) return;
  const theme = normalizeTheme(document.body.dataset.theme);
  const nextTheme = theme === "light" ? "dark" : "light";
  button.setAttribute("aria-label", `Toggle to ${THEME_LABELS[nextTheme]} mode`);
  button.setAttribute("aria-pressed", theme === "light" ? "true" : "false");
  button.dataset.activeTheme = theme;
  const text = button.querySelector(".theme-toggle-text");
  if (text) text.textContent = THEME_LABELS[theme];
}

applyTheme(storedTheme());

const el = {
  title: document.getElementById("page-title"),
  subtitle: document.getElementById("page-subtitle"),
  kicker: document.getElementById("page-kicker"),
  content: document.getElementById("page-content"),
  projectNav: document.getElementById("project-nav"),
};

function params(search = window.location.search) {
  try {
    return new URLSearchParams(search);
  } catch (_error) {
    return new URLSearchParams();
  }
}

function normalizeToken(value) {
  return String(value || "").trim().toLowerCase();
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function escapeAttr(value) {
  return escapeHtml(value);
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

function statusPill(value) {
  const status = normalizeToken(value) || "unknown";
  return `<span class="status-pill status-${escapeAttr(status.replace(/[^a-z0-9_-]+/g, "-"))}">${escapeHtml(STATUS_LABELS[status] || status)}</span>`;
}

function renderDemoBadge(project) {
  return project?.demo ? '<span class="demo-badge">Demo</span>' : "";
}

function displayFamily(value) {
  const family = normalizeToken(value) || "unknown";
  return FAMILY_LABELS[family] || String(value || "").trim() || FAMILY_LABELS.unknown;
}

function displayRelevance(value) {
  const relevance = normalizeToken(value) || "unscored";
  return RELEVANCE_LABELS[relevance] || String(value || "").trim() || RELEVANCE_LABELS.unscored;
}

function displayMemoSectionTitle(title) {
  return MEMO_SECTION_LABELS[title] || title;
}

function displayProjectTitle(project) {
  return String(project?.title || project?.id || "").replace(/ Project Query Pack$/, "");
}

function paperCurrentState(paper) {
  const projectCoreFor = Array.isArray(paper?.project_core_for) ? paper.project_core_for : [];
  if (projectCoreFor.length) {
    return { key: "project-core", label: PAPER_STATE_LABELS["project-core"] };
  }
  const status = normalizeToken(paper?.review_status || "candidate");
  return { key: status, label: PAPER_STATE_LABELS[status] || status || PAPER_STATE_LABELS.unknown };
}

function projectById(projectId = state.projectId) {
  return (state.data?.projects || []).find((project) => project.id === projectId) || state.data?.projects?.[0] || null;
}

function projectGraphForProject(projectId = state.projectId) {
  return (state.data?.project_graphs || []).find((graph) => graph.project === projectId) || null;
}

async function loadProjectGraphFromApi(projectId = state.projectId) {
  if (!projectId) return null;
  try {
    const response = await fetch(`/api/project-graph?project=${encodeURIComponent(projectId)}`, { cache: "no-store" });
    if (!response.ok) return projectGraphForProject(projectId);
    const graph = await response.json();
    const graphs = (state.data.project_graphs || []).filter((item) => item.project !== projectId);
    state.data.project_graphs = [...graphs, graph];
    return graph;
  } catch {
    return projectGraphForProject(projectId);
  }
}

async function loadProjectGraphMaintenanceFromApi(projectId = state.projectId) {
  if (!projectId) return null;
  try {
    const response = await fetch(`/api/project-graph-maintenance?project=${encodeURIComponent(projectId)}`, { cache: "no-store" });
    if (!response.ok) return state.graphMaintenance;
    const maintenance = await response.json();
    state.graphMaintenance = maintenance;
    return maintenance;
  } catch {
    return state.graphMaintenance;
  }
}

async function loadProjectUnderstandingFromApi(projectId = state.projectId) {
  if (!projectId) return null;
  try {
    const response = await fetch(`/api/project-understanding?project=${encodeURIComponent(projectId)}`, { cache: "no-store" });
    if (!response.ok) return null;
    const understanding = await response.json();
    state.projectUnderstanding = understanding;
    return understanding;
  } catch {
    return null;
  }
}

async function loadPaperGraphFromApi(path) {
  const graphPath = normalizePaperDossierPath(path);
  if (!graphPath) return null;
  if (state.paperGraphCache[graphPath]) return state.paperGraphCache[graphPath];
  try {
    const response = await fetch(`/api/paper-graph?path=${encodeURIComponent(graphPath)}`, { cache: "no-store" });
    if (!response.ok) return null;
    const graph = await response.json();
    state.paperGraphCache[graphPath] = graph;
    return graph;
  } catch {
    return null;
  }
}

async function loadProjectGraphPaper(path) {
  return loadPaperGraphFromApi(path);
}

function emptyExperimentsModel(projectId = state.projectId) {
  return {
    schema_version: "experiments-v1",
    project_id: projectId || "",
    mutating: false,
    summary: {},
    experiments: [],
    runs: [],
    next_moves: [],
    legacy_proposals: { found: false, count: 0, path: projectId ? `wiki/projects/${projectId}/experiment-proposals` : "" },
    empty_message: "No experiments recorded yet.",
  };
}

async function loadExperimentsFromApi(projectId) {
  if (!projectId) return emptyExperimentsModel(projectId);
  try {
    const response = await fetch(`/api/experiments?project=${encodeURIComponent(projectId)}`, { cache: "no-store" });
    if (!response.ok) return emptyExperimentsModel(projectId);
    const model = await response.json();
    return model && typeof model === "object" ? model : emptyExperimentsModel(projectId);
  } catch {
    return emptyExperimentsModel(projectId);
  }
}

function normalizePaperDossierPath(path) {
  const value = String(path || "").trim();
  if (!value) return "";
  if (value.endsWith(".md")) return value;
  if (value.endsWith("/index")) return `${value}.md`;
  return value;
}

function roundsForProject(projectId = state.projectId) {
  return (state.data?.rounds || [])
    .filter((round) => round.project === projectId)
    .sort((a, b) => normalizeToken(b.name).localeCompare(normalizeToken(a.name)));
}

function latestRound(projectId = state.projectId) {
  const rounds = roundsForProject(projectId);
  return rounds.find((round) => Number(round.paper_count || 0) > 0 || candidatesForRoundName(projectId, round.name).length > 0) || rounds[0] || null;
}

function papersForProject(projectId = state.projectId) {
  return (state.data?.papers || []).filter((paper) => paper.project === projectId);
}

function lineageMapsForProject(projectId = state.projectId) {
  return (state.data?.lineage_maps || [])
    .filter((map) => map.project === projectId)
    .sort((a, b) => normalizeToken(b.round).localeCompare(normalizeToken(a.round)));
}

function paperKey(paper) {
  return String(paper?.zotero_key || paper?.zotero || paper?.id || paper?.title || "").replace("zotero:item:", "").replace("zotero:", "");
}

function paperByKey(key) {
  const target = normalizeToken(String(key || "").replace("zotero:item:", "").replace("zotero:", ""));
  return (state.data?.papers || []).find((paper) => normalizeToken(paperKey(paper)) === target) || null;
}

function roundByName(roundName = state.roundId, projectId = state.projectId) {
  const target = normalizeToken(roundName);
  return roundsForProject(projectId).find((round) => normalizeToken(round.name) === target || normalizeToken(round.id) === target) || latestRound(projectId);
}

function candidateId(candidate) {
  return String(candidate?.id || candidate?.paper_id || candidate?.zotero_key || candidate?.zotero || candidate?.title || "");
}

function candidatesForRound(projectId = state.projectId, roundName = state.roundId) {
  const round = roundByName(roundName, projectId);
  if (!round) return [];
  return candidatesForRoundName(projectId, round.name).map((candidate) => enrichCandidate(candidate));
}

function candidatesForRoundName(projectId, roundName) {
  return (state.data?.round_candidates || [])
    .filter((candidate) => candidate.project === projectId && candidate.round === roundName);
}

function enrichCandidate(candidate) {
  const paper = paperByKey(candidate.zotero_key || candidate.zotero);
  return {
    ...(paper || {}),
    ...candidate,
    one_line: candidate.one_line || paper?.one_line || "",
    why_relevant: candidate.why_relevant || paper?.why_relevant || "",
    key_claims: paper?.key_claims || [],
    limitations: paper?.limitations || [],
    path: paper?.path || candidate.memo_path || "",
    human_review: paper?.human_review || "pending",
    read_level: paper?.read_level || "",
    literature_round: candidate.round || paper?.literature_round || "",
  };
}

function deepReadPapers(projectId = state.projectId) {
  return papersForProject(projectId)
    .filter((paper) => (
      paper.read_level === "full-text"
      || ["reading", "summarized"].includes(paper.review_status)
      || Boolean(paper.path)
    ))
    .sort((a, b) => STATUS_ORDER.indexOf(a.review_status) - STATUS_ORDER.indexOf(b.review_status));
}

function setHeader(kicker, title, subtitle = "") {
  el.kicker.textContent = kicker;
  el.title.textContent = title;
  el.subtitle.textContent = subtitle;
  el.subtitle.className = "";
}

function setPaperDetailHeader(project, paper) {
  setHeader("Paper", paper.title || "Untitled", "");
  el.subtitle.className = "paper-title-meta";
  el.subtitle.innerHTML = `
    <span>${escapeHtml(displayProjectTitle(project))}</span>
    ${statusPill(paper.review_status || "candidate")}
    <span>${escapeHtml(paperPublicationLine(paper))}</span>
  `;
}

function dashboardPageUrl(pageName, params = {}) {
  const search = new URLSearchParams({ v: DASHBOARD_PAGE_VERSION });
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") search.set(key, value);
  });
  return `./${pageName}.html?${search.toString()}`;
}

function projectUrl(projectId) {
  return dashboardPageUrl("project", { project: projectId });
}

function roundUrl(projectId, roundName) {
  return dashboardPageUrl("round", { project: projectId, round: roundName || "" });
}

function papersUrl(projectId, filters = {}) {
  return dashboardPageUrl("papers", { project: projectId, ...filters });
}

function paperUrl(projectId, paperId, roundName = "") {
  return dashboardPageUrl("paper", { project: projectId, paper: paperId, round: roundName });
}

function experimentsUrl(projectId) {
  return dashboardPageUrl("experiments", { project: projectId });
}

function lineageUrl(projectId, roundName) {
  return dashboardPageUrl("lineage", { project: projectId, round: roundName });
}

function renderProjectNav(project) {
  if (!el.projectNav || !project) return;
  const current = state.page;
  const projectCurrent = current === "project" ? ' aria-current="page"' : "";
  const papersCurrent = ["papers", "round", "paper", "deep-reads"].includes(current) ? ' aria-current="page"' : "";
  const lineageCurrent = current === "lineage" ? ' aria-current="page"' : "";
  const experimentsCurrent = current === "experiments" ? ' aria-current="page"' : "";
  el.projectNav.innerHTML = `
    <a href="${escapeAttr(projectUrl(project.id))}"${projectCurrent}>Project</a>
    <a href="${escapeAttr(papersUrl(project.id))}"${papersCurrent}>Papers</a>
    <a href="${escapeAttr(lineageUrl(project.id))}"${lineageCurrent}>Technical Lineage</a>
    <a href="${escapeAttr(experimentsUrl(project.id))}"${experimentsCurrent}>Experiments</a>
  `;
}

function renderProjectsIndex() {
  setHeader("Project", "Project", "Select a project to inspect project papers, search status, and graph state.");
  el.content.innerHTML = `
    <div class="project-entry-list">
      ${(state.data.projects || []).map((project) => {
        const round = latestRound(project.id);
        const paperCount = allPapersForProject(project.id).length;
        const stats = project.stats || {};
        return `
          <article class="project-entry">
            <div>
              <p class="eyebrow">Project</p>
              <h2><a href="${escapeAttr(projectUrl(project.id))}">${escapeHtml(displayProjectTitle(project))}</a>${renderDemoBadge(project)}</h2>
              <p class="project-question">${escapeHtml(project.card?.working_question || project.overview?.direction || "No project question yet.")}</p>
            </div>
            <dl class="metric-row">
              <div><dt>Candidate</dt><dd>${stats.candidate_papers || 0}</dd></div>
              <div><dt>ProjectPaper</dt><dd>${stats.summarized_papers || 0}</dd></div>
              <div><dt>paper_count</dt><dd>${paperCount || round?.paper_count || 0}</dd></div>
              <div><dt>Rounds</dt><dd>${stats.literature_rounds || 0}</dd></div>
              <div><dt>Claims</dt><dd>${stats.claims || 0}</dd></div>
            </dl>
            <div class="entry-actions">
              <span class="latest-round-label">Latest status ${escapeHtml(projectStatusLine(project, round))}</span>
              <a class="primary-action" href="${escapeAttr(projectUrl(project.id))}">OpenProject</a>
              <a class="primary-action review-action" href="${escapeAttr(papersUrl(project.id))}">Papers</a>
            </div>
          </article>
        `;
      }).join("")}
    </div>
  `;
}

async function renderProjectWorkspace() {
  const project = projectById();
  if (!project) {
    renderEmpty("Project not found.");
    return;
  }
  renderProjectNav(project);
  const [graph, understanding] = await Promise.all([
    loadProjectGraphFromApi(project.id),
    loadProjectUnderstandingFromApi(project.id),
  ]);
  setHeader("Project", displayProjectTitle(project), project.overview?.direction || "");
  if (project.demo && el.subtitle) {
    el.subtitle.className = "project-title-meta";
    el.subtitle.innerHTML = `
      ${renderDemoBadge(project)}
      <span>${escapeHtml(project.overview?.direction || "")}</span>
    `;
  }
  el.content.innerHTML = `
    ${renderProjectUnderstandingPanel(understanding)}
    <section class="section-block project-graph-panel" id="project-graph">
      <div class="section-head">
        <div>
          <p class="eyebrow">Understanding Graph</p>
          <h2>Project Understanding Graph</h2>
        </div>
      </div>
      ${renderProjectGraphView(graph)}
    </section>
  `;
  wireClickableRows();
  wireGraphStudio(graph);
}

function hasProjectUnderstanding(model) {
  return Boolean(
    model
    && (
      (Array.isArray(model.recent_changes) && model.recent_changes.length)
      || (Array.isArray(model.next_moves) && model.next_moves.length)
      || (Array.isArray(model.sources) && model.sources.length)
      || (Array.isArray(model.claims) && model.claims.length)
      || (Array.isArray(model.gaps) && model.gaps.length)
    )
  );
}

function renderProjectUnderstandingPanel(model) {
  if (!hasProjectUnderstanding(model)) return "";
  const recentChanges = [...(model.recent_changes || [])].slice(-3).reverse();
  const nextMoves = [...(model.next_moves || [])].slice(0, 3);
  return `
    <section class="section-block project-understanding-panel" aria-label="Project Understanding Updates">
      <div class="section-head">
        <div>
          <p class="eyebrow">Project Understanding</p>
          <h2>Recent Understanding</h2>
          <p class="section-note">Read-only agent update projection. Keep acting through chat.</p>
        </div>
        <dl class="status-strip understanding-counts">
          <div><dt>sources</dt><dd>${(model.sources || []).length}</dd></div>
          <div><dt>claims</dt><dd>${(model.claims || []).length}</dd></div>
          <div><dt>gaps</dt><dd>${(model.gaps || []).length}</dd></div>
          <div><dt>moves</dt><dd>${(model.next_moves || []).length}</dd></div>
        </dl>
      </div>
      <div class="understanding-grid">
        <article>
          <h3>Recent Understanding</h3>
          <ul class="understanding-list">
            ${recentChanges.map((change) => `
              <li>
                <strong>${escapeHtml(change.summary || change.task?.summary || "Understanding updated.")}</strong>
                <span>${escapeHtml([change.task?.kind, change.confidence, change.created_at].filter(Boolean).join(" · "))}</span>
              </li>
            `).join("") || "<li><strong>No recent understanding changes.</strong></li>"}
          </ul>
        </article>
        <article>
          <h3>Next Moves</h3>
          <ul class="understanding-list">
            ${nextMoves.map((move) => `
              <li>
                <strong>${escapeHtml(move.text || "Next move")}</strong>
                <span>${escapeHtml(move.suggested_prompt || move.rationale || move.type || "")}</span>
              </li>
            `).join("") || "<li><strong>No next moves.</strong></li>"}
          </ul>
        </article>
      </div>
    </section>
  `;
}

function renderProjectGraphView(graph) {
  if (!graph) return `<div class="empty-state">No Project Understanding Graph yet.</div>`;
  return `
    <div id="project-graph-explorer">
      ${renderGraphStudio(graph)}
    </div>
  `;
}

function renderGraphStudio(graph) {
  const model = buildGraphStudioModel(graph);
  const counts = graphStudioCounts(model);
  return `
    <div class="graph-summary-strip">
      <div><dt>Q</dt><dd>${counts.question}</dd></div>
      <div><dt>C</dt><dd>${counts.claim}</dd></div>
      <div><dt>E</dt><dd>${counts.evidence}</dd></div>
      <div><dt>W</dt><dd>${counts.warrant}</dd></div>
      <div><dt>L</dt><dd>${counts.limitation}</dd></div>
      <div><dt>RL/TL/D</dt><dd>${counts.reasoningLink}/${counts.translationLink}/${counts.delta}</dd></div>
    </div>
    <section class="graph-studio" aria-label="Project Argument Map">
      <div class="graph-studio-toolbar">
        <div>
          <p class="eyebrow">Project Argument Map</p>
          <h3>GSN / Toulmin Argument Map</h3>
          <span>Questions define project problems; claims are argument units; evidence, warrants, and limitations stay inside claims.</span>
        </div>
        <div class="graph-legend" aria-label="Legend">
          <span data-legend-kind="question">Q</span>
          <span data-legend-kind="claim">C</span>
          <span data-legend-kind="evidence">E</span>
          <span data-legend-kind="warrant">W</span>
          <span data-legend-kind="limitation">L</span>
        </div>
      </div>
      <div class="graph-studio-canvas-shell">
        ${renderGraphCanvas(model)}
      </div>
    </section>
  `;
}

function renderHumanGatePanel(maintenance) {
  const model = maintenance || {};
  const openDeltas = Array.isArray(model.open_deltas) ? model.open_deltas : [];
  const selected = selectedGraphDelta(model);
  const acceptedHistory = Array.isArray(model.accepted_history) ? model.accepted_history : [];
  const paperContributions = Array.isArray(model.paper_contributions) ? model.paper_contributions : [];
  const reviewQueue = model.review_queue || {};
  const claimPaths = Array.isArray(model.claim_paths) ? model.claim_paths : [];
  return `
    <section class="human-gate-panel" id="human-gate-panel" aria-label="Human Gate Delta Inbox">
      <div class="human-gate-head">
        <div>
          <p class="eyebrow">Delta Review Ledger</p>
          <h3>Read-only delta state</h3>
          <span>Dashboard is a read-only projection. Use agent chat or CLI to decide or apply this item.</span>
        </div>
        <dl class="human-gate-metrics">
          <div><dt>open_deltas</dt><dd>${openDeltas.length}</dd></div>
          <div><dt>accepted_history</dt><dd>${acceptedHistory.length}</dd></div>
          <div><dt>paper_contributions</dt><dd>${paperContributions.length}</dd></div>
          <div><dt>review_queue</dt><dd>${reviewQueueCount(reviewQueue)}</dd></div>
          <div><dt>claim_paths</dt><dd>${claimPaths.length}</dd></div>
        </dl>
      </div>
      <div class="human-gate-grid">
        ${renderDeltaInbox(openDeltas)}
        ${renderDeltaDetail(selected, model)}
      </div>
    </section>
  `;
}

function selectedGraphDelta(maintenance) {
  const deltas = Array.isArray(maintenance?.open_deltas) ? maintenance.open_deltas : [];
  if (!deltas.length) return null;
  const selected = deltas.find((delta) => graphDeltaId(delta) === state.selectedGraphDeltaId);
  const fallback = selected || deltas[0];
  state.selectedGraphDeltaId = graphDeltaId(fallback);
  return fallback;
}

function reviewQueueCount(reviewQueue) {
  return ["nodes", "links", "deltas"].reduce((sum, key) => sum + (Array.isArray(reviewQueue?.[key]) ? reviewQueue[key].length : 0), 0);
}

function graphDeltaId(delta) {
  return String(delta?.id || delta?.local_id || delta?.global_id || "");
}

function renderDeltaInbox(openDeltas) {
  return `
    <aside class="delta-inbox" aria-label="open_deltas">
      <div class="delta-inbox-head">
        <p class="eyebrow">open_deltas</p>
        <strong>${openDeltas.length}</strong>
      </div>
      <div class="delta-card-list">
        ${openDeltas.map((delta) => renderDeltaInboxCard(delta)).join("") || `<div class="empty-state">No open deltas. Accepted history remains available through the maintenance model.</div>`}
      </div>
    </aside>
  `;
}

function renderDeltaInboxCard(delta) {
  const id = graphDeltaId(delta);
  const selected = id && id === state.selectedGraphDeltaId;
  return `
    <button type="button" class="delta-card${selected ? " is-selected" : ""}" data-delta-id="${escapeAttr(id)}" aria-selected="${selected ? "true" : "false"}">
      <span class="delta-card-topline">
        <strong>${escapeHtml(id || "delta")}</strong>
        <em>${escapeHtml(delta.lifecycle_status || delta.status || "proposed")}</em>
      </span>
      <span class="delta-summary">${escapeHtml(delta.summary || "No summary.")}</span>
      <span class="delta-meta-line">${escapeHtml(deltaSourceLabel(delta))}</span>
      <span class="delta-chip-row">
        ${renderMiniChip("operation", deltaOperationLabel(delta))}
        ${renderMiniChip("effect", delta.epistemic_effect || "unknown effect")}
        ${renderMiniChip("human", delta.human_review || "pending")}
      </span>
      <span class="delta-affects">${escapeHtml([...(delta.affected_nodes || []), ...(delta.affected_links || [])].join(", ") || "No affected graph records")}</span>
    </button>
  `;
}

function renderDeltaDetail(delta, maintenance) {
  if (!delta) {
    return `
      <section class="delta-detail" aria-label="Delta Detail">
        <div class="delta-detail-empty">
          <p class="eyebrow">Delta Detail</p>
          <h3>No pending delta</h3>
          <p>Maintenance model loaded. Dashboard only displays the delta lifecycle.</p>
        </div>
      </section>
    `;
  }
  const id = graphDeltaId(delta);
  const validation = delta.dry_run || delta.dry_run_result || delta.validation || null;
  return `
    <section class="delta-detail" aria-label="Delta Detail" data-active-delta-id="${escapeAttr(id)}">
      <div class="delta-detail-head">
        <div>
          <p class="eyebrow">Delta Detail</p>
          <h3>${escapeHtml(id)}</h3>
        </div>
        <span class="delta-state-pill">${escapeHtml(delta.lifecycle_status || delta.status || "proposed")} / ${escapeHtml(delta.human_review || "pending")}</span>
      </div>
      <p class="delta-detail-summary">${escapeHtml(delta.summary || "No summary.")}</p>
      <div class="delta-fact-grid">
        ${renderDeltaFact("source", deltaSourceLabel(delta))}
        ${renderDeltaFact("operation", deltaOperationLabel(delta))}
        ${renderDeltaFact("epistemic_effect", delta.epistemic_effect || "missing")}
        ${renderDeltaFact("lifecycle_status", delta.lifecycle_status || "proposed")}
        ${renderDeltaFact("human_review", delta.human_review || "pending")}
        ${renderDeltaFact("decision", delta.decision || "pending")}
      </div>
      <div class="delta-detail-grid">
        <section>
          <h4>source refs</h4>
          ${renderDeltaList(deltaSourceRefs(delta), "No source refs.")}
        </section>
        <section>
          <h4>affected graph records</h4>
          ${renderDeltaList([...(delta.affected_nodes || []), ...(delta.affected_links || [])], "No affected graph records.")}
        </section>
      </div>
      <section class="delta-patch-ops">
        <h4>patch_ops</h4>
        ${renderDeltaPatchOps(delta.patch_ops)}
      </section>
      ${renderDeltaDryRunPreview(validation)}
      ${renderDeltaAlerts(validation)}
      ${renderAgentCommandHint(`review ${id}`, "Use agent chat / CLI to decide or apply this item.")}
    </section>
  `;
}

function renderDeltaFact(label, value) {
  return `<div><dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value || "missing")}</dd></div>`;
}

function deltaOperationLabel(delta) {
  const operation = delta?.operation_type || delta?.operation || [];
  return Array.isArray(operation) ? operation.join(", ") : String(operation || "");
}

function deltaSourceLabel(delta) {
  return delta?.source_dossier || delta?.source_graph_id || (delta?.source_refs || [])[0] || "unknown source";
}

function deltaSourceRefs(delta) {
  return uniqueStrings([
    delta?.source_dossier,
    delta?.source_graph_id,
    ...(Array.isArray(delta?.source_refs) ? delta.source_refs : []),
    ...(Array.isArray(delta?.source_paper_nodes) ? delta.source_paper_nodes : []),
  ]);
}

function renderMiniChip(label, value) {
  return `<span><b>${escapeHtml(label)}</b>${escapeHtml(value || "missing")}</span>`;
}

function renderAgentCommandHint(command, message = "Use agent chat / CLI to decide or apply this item.") {
  return `
    <aside class="agent-command-hint" aria-label="Agent command hint">
      <p>${escapeHtml(message)}</p>
      <code>Ask agent: ${escapeHtml(command || "review this item")}</code>
    </aside>
  `;
}

function renderDeltaList(items, emptyText) {
  const values = uniqueStrings((Array.isArray(items) ? items : []).map((item) => String(item || "")).filter(Boolean));
  if (!values.length) return `<p class="graph-inspector-empty">${escapeHtml(emptyText)}</p>`;
  return `<ul>${values.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;
}

function renderDeltaPatchOps(patchOps) {
  const ops = Array.isArray(patchOps) ? patchOps : [];
  if (!ops.length) return `<div class="delta-alert is-warning">No patch_ops in this delta. Dry-run will report invalid payload until API/model supplies patch_ops.</div>`;
  return `
    <div class="delta-patch-list">
      ${ops.map((op, index) => `
        <article>
          <strong>${escapeHtml(op.op || `op-${index + 1}`)}</strong>
          <pre>${escapeHtml(JSON.stringify(op, null, 2))}</pre>
        </article>
      `).join("")}
    </div>
  `;
}

function renderDeltaDryRunPreview(dryRun) {
  const preview = dryRun?.preview || {};
  const buckets = ["added_nodes", "updated_nodes", "retired_nodes", "added_links", "updated_links", "retired_links"];
  return `
    <section class="delta-preview" aria-label="Dry-run Preview">
      <div class="delta-preview-head">
        <h4>Dry-run Preview</h4>
        <span>${dryRun ? (dryRun.valid ? "valid=true" : "valid=false") : "not run"}</span>
      </div>
      ${dryRun?.summary ? `<p>${escapeHtml(dryRun.summary)}</p>` : ""}
      <div class="delta-preview-grid">
        ${buckets.map((bucket) => renderDeltaPreviewBucket(bucket, preview[bucket])).join("")}
      </div>
    </section>
  `;
}

function renderDeltaPreviewBucket(label, items) {
  const values = Array.isArray(items) ? items : [];
  return `
    <div>
      <dt>${escapeHtml(label)}</dt>
      <dd>${values.length}</dd>
      ${values.length ? `<pre>${escapeHtml(JSON.stringify(values, null, 2))}</pre>` : ""}
    </div>
  `;
}

function renderDeltaAlerts(dryRun, applyResult) {
  const warnings = [...(dryRun?.warnings || []), ...(applyResult?.warnings || [])];
  const errors = [...(dryRun?.errors || []), ...(applyResult?.errors || [])];
  const result = applyResult ? `<div class="delta-alert ${applyResult.valid === false ? "is-error" : "is-success"}">${escapeHtml(JSON.stringify(applyResult, null, 2))}</div>` : "";
  return `
    <section class="delta-alerts" aria-label="warnings/errors">
      ${warnings.map((warning) => `<div class="delta-alert is-warning">${escapeHtml(warning)}</div>`).join("")}
      ${errors.map((error) => `<div class="delta-alert is-error">${escapeHtml(error)}</div>`).join("")}
      ${result}
    </section>
  `;
}


function buildGraphStudioModel(graph) {
  const rawNodes = Array.isArray(graph?.nodes) ? graph.nodes : [];
  const reasoningLinks = projectReasoningLinks(graph);
  const reasoningModels = graphReasoningLinkModels(reasoningLinks);
  const translationLinks = projectTranslationLinks(graph);
  const deltas = Array.isArray(graph?.deltas) ? graph.deltas : [];
  const nodes = [];
  const nodeById = new Map();
  const addNode = (node) => {
    if (!node?.id || nodeById.has(node.id)) return;
    if (!["question", "claim", "evidence", "warrant", "limitation"].includes(node.kind)) return;
    const next = {
      radius: 24,
      sourcePath: "",
      payload: null,
      ...node,
    };
    nodes.push(next);
    nodeById.set(next.id, next);
  };

  rawNodes.forEach((node) => {
    const id = compactGraphId(node.id || node.local_id || node.node_id);
    if (!id) return;
    addNode({
      id,
      kind: normalizeGraphKind(node.kind || node.node_type),
      label: node.label || node.text || id,
      subtitle: node.subtitle || node.status || node.metadata?.role || "",
      sourcePath: firstPaperPath(node.source_refs || node.sourceRefs || ""),
      payload: node,
    });
  });

  const edges = [];
  const addEdge = (source, target, relation, linkId = "", role = "premise", claimId = "") => {
    if (!source || !target || !nodeById.has(source) || !nodeById.has(target)) return;
    edges.push({ id: `${source}->${target}:${relation}:${edges.length}`, source, target, relation, linkId, role, claimId });
  };

  reasoningModels.forEach((link) => {
    const claimId = graphPrimaryClaimIds(link, nodeById)[0] || link.targets[0] || "";
    link.premises.forEach((sourceId) => {
      link.targets.forEach((targetId) => addEdge(sourceId, targetId, link.relation, link.id, "premise", claimId || targetId));
    });
    link.warrants.forEach((warrantId) => {
      const bridgeSources = link.premises.length ? link.premises : link.targets;
      bridgeSources.forEach((sourceId) => addEdge(sourceId, warrantId, "warrant", link.id, "premise-to-warrant", claimId));
      link.targets.forEach((targetId) => addEdge(warrantId, targetId, "warrant", link.id, "warrant-to-claim", claimId || targetId));
    });
    link.limitations.forEach((sourceId) => {
      link.targets.forEach((targetId) => addEdge(sourceId, targetId, "bounds", link.id, "limitation", claimId || targetId));
    });
  });

  const degreeMap = graphDegreeMap(nodes, edges);
  const maxDegree = Math.max(1, ...nodes.map((node) => degreeMap.get(node.id) || 0));
  const kindTotals = nodes.reduce((totals, node) => {
    totals[node.kind] = (totals[node.kind] || 0) + 1;
    return totals;
  }, {});
  const kindIndexes = {};
  nodes.forEach((node) => {
    const index = kindIndexes[node.kind] || 0;
    kindIndexes[node.kind] = index + 1;
    node.degree = degreeMap.get(node.id) || 0;
    node.radius = graphNodeRadius(node, maxDegree);
    node.prominence = graphNodeProminence(node, maxDegree);
    const position = atlasNodePosition(node, index, kindTotals[node.kind] || 1, maxDegree);
    node.x = position.x;
    node.y = position.y;
  });

  const width = 1800;
  const height = 1180;
  placeClaimNeighborhoodNodes(nodes, nodeById, reasoningModels, width, height);
  placeWarrantBridgeNodes(nodes, nodeById, reasoningModels, width, height);
  placeLimitationBoundaryNodes(nodes, nodeById, reasoningModels, width, height);
  const neighborhoods = graphClaimNeighborhoods(nodes, nodeById, reasoningModels);
  const clusters = claimClusterHulls(neighborhoods, nodes, width, height);
  return { graph, nodes, nodeById, edges, width, height, clusters, neighborhoods, reasoningLinks, reasoningModels, translationLinks, deltas, degreeMap };
}

function graphDegreeMap(nodes, edges) {
  const degree = new Map(nodes.map((node) => [node.id, 0]));
  edges.forEach((edge) => {
    degree.set(edge.source, (degree.get(edge.source) || 0) + 1);
    degree.set(edge.target, (degree.get(edge.target) || 0) + 1);
  });
  return degree;
}

function graphNodeRadius(node, maxDegree) {
  const degreeRatio = Math.sqrt((node.degree || 0) / Math.max(1, maxDegree));
  const ranges = {
    claim: [30, 66],
    question: [24, 46],
    evidence: [13, 27],
    warrant: [13, 24],
    limitation: [13, 25],
  };
  const [min, max] = ranges[node.kind] || [14, 28];
  return Math.round(min + (max - min) * degreeRatio);
}

function graphNodeProminence(node, maxDegree) {
  const degree = node.degree || 0;
  if (node.kind === "claim" && degree >= Math.max(4, maxDegree * 0.34)) return "primary";
  if (node.kind === "question" && degree >= 2) return "major";
  if (degree >= Math.max(2, maxDegree * 0.18)) return "major";
  if (degree > 0) return "minor";
  return "low";
}

function atlasNodePosition(node, index, total, maxDegree) {
  const spread = total <= 1 ? 0 : index / (total - 1);
  const wave = Math.sin((index + 1) * 1.7) * 28;
  if (node.kind === "claim") {
    const claimSlots = {
      C0: { x: 900, y: 560 },
      C1: { x: 1260, y: 330 },
      C2: { x: 1295, y: 690 },
      C3: { x: 900, y: 925 },
      C4: { x: 525, y: 790 },
      C5: { x: 440, y: 480 },
      C6: { x: 900, y: 250 },
    };
    const fallbackSlots = [
      { x: 900, y: 560 },
      { x: 1260, y: 330 },
      { x: 1295, y: 690 },
      { x: 900, y: 925 },
      { x: 525, y: 790 },
      { x: 440, y: 480 },
      { x: 900, y: 250 },
    ];
    const slot = claimSlots[node.id] || fallbackSlots[index % fallbackSlots.length];
    const pull = Math.min(1, (node.degree || 0) / Math.max(1, maxDegree));
    const centerPull = node.id === "C0" ? 0.18 : 0;
    return {
      x: slot.x + (900 - slot.x) * centerPull * pull,
      y: slot.y + (560 - slot.y) * centerPull * pull,
    };
  }
  if (node.kind === "question") {
    return { x: 160 + spread * 1480, y: 130 + wave * 0.32 };
  }
  if (node.kind === "evidence") {
    return { x: 160 + (index % 4) * 165, y: 445 + Math.floor(index / 4) * 190 + wave * 0.26 };
  }
  if (node.kind === "warrant") {
    return { x: 1140 + (index % 3) * 145, y: 360 + Math.floor(index / 3) * 170 + wave * 0.22 };
  }
  if (node.kind === "limitation") {
    return { x: 1160 + (index % 4) * 128, y: 760 + Math.floor(index / 4) * 146 + wave * 0.22 };
  }
  return { x: 900, y: 560 };
}

function graphReasoningLinkModels(reasoningLinks) {
  return (Array.isArray(reasoningLinks) ? reasoningLinks : []).map((link, index) => ({
    id: compactGraphId(link.id) || `RL${index + 1}`,
    premises: splitGraphIds(link.premises),
    relation: String(link.relation || "supports").trim() || "supports",
    targets: splitGraphIds(link.target),
    warrants: splitGraphIds(link.warrant),
    limitations: splitGraphIds(link.limitations),
  }));
}

function graphPrimaryClaimIds(link, nodeById) {
  const targetClaims = link.targets.filter((id) => nodeById.get(id)?.kind === "claim");
  if (targetClaims.length) return targetClaims;
  return link.premises.filter((id) => nodeById.get(id)?.kind === "claim");
}

function placeClaimNeighborhoodNodes(nodes, nodeById, reasoningModels, width, height) {
  const desired = new Map();
  const ordinal = new Map();
  const addDesired = (id, x, y, role = "claim-neighbor", weight = 1) => {
    const node = nodeById.get(id);
    if (!node || node.kind !== "evidence") return;
    const current = desired.get(id) || { x: 0, y: 0, weight: 0, role };
    current.x += x * weight;
    current.y += y * weight;
    current.weight += weight;
    desired.set(id, current);
  };
  const nextOrdinal = (key) => {
    const value = ordinal.get(key) || 0;
    ordinal.set(key, value + 1);
    return value;
  };

  reasoningModels.forEach((link) => {
    graphPrimaryClaimIds(link, nodeById).forEach((claimId) => {
      const claim = nodeById.get(claimId);
      if (!claim) return;
      link.premises.forEach((premiseId) => {
        const premise = nodeById.get(premiseId);
        if (!premise || premise.kind !== "evidence") return;
        const index = nextOrdinal(`${claimId}:evidence`);
        const angle = claimEvidenceAngle(claimId, index);
        const distance = (claim.radius || 34) + 190 + (index % 2) * 28;
        addDesired(
          premiseId,
          clampGraphCoordinate(claim.x + Math.cos(angle) * distance, 72, width - 72),
          clampGraphCoordinate(claim.y + Math.sin(angle) * distance, 72, height - 72),
          "claim-neighbor",
          1.5,
        );
      });
    });
  });

  desired.forEach((target, id) => {
    const node = nodeById.get(id);
    if (!node || !target.weight) return;
    node.x = target.x / target.weight;
    node.y = target.y / target.weight;
    node.role = target.role;
  });
}

function placeWarrantBridgeNodes(nodes, nodeById, reasoningModels, width, height) {
  const desired = new Map();
  reasoningModels.forEach((link, linkIndex) => {
    graphPrimaryClaimIds(link, nodeById).forEach((claimId) => {
      const claim = nodeById.get(claimId);
      if (!claim) return;
      const premiseNodes = link.premises.map((id) => nodeById.get(id)).filter(Boolean);
      const centroid = graphNodeCentroid(premiseNodes.length ? premiseNodes : [claim]);
      const dx = claim.x - centroid.x;
      const dy = claim.y - centroid.y;
      const length = Math.max(1, Math.hypot(dx, dy));
      const px = -dy / length;
      const py = dx / length;
      link.warrants.forEach((warrantId, warrantIndex) => {
        const node = nodeById.get(warrantId);
        if (!node || node.kind !== "warrant") return;
        const offset = ((warrantIndex % 2 === 0 ? 1 : -1) * 34) + ((linkIndex % 3) - 1) * 14;
        const x = centroid.x * 0.52 + claim.x * 0.48 + px * offset;
        const y = centroid.y * 0.52 + claim.y * 0.48 + py * offset;
        const current = desired.get(warrantId) || { x: 0, y: 0, weight: 0 };
        current.x += clampGraphCoordinate(x, 72, width - 72) * 2;
        current.y += clampGraphCoordinate(y, 72, height - 72) * 2;
        current.weight += 2;
        desired.set(warrantId, current);
      });
    });
  });
  desired.forEach((target, id) => {
    const node = nodeById.get(id);
    if (!node || !target.weight) return;
    node.x = target.x / target.weight;
    node.y = target.y / target.weight;
    node.role = "bridge";
  });
}

function placeLimitationBoundaryNodes(nodes, nodeById, reasoningModels, width, height) {
  const desired = new Map();
  const ordinal = new Map();
  const nextOrdinal = (key) => {
    const value = ordinal.get(key) || 0;
    ordinal.set(key, value + 1);
    return value;
  };
  reasoningModels.forEach((link) => {
    graphPrimaryClaimIds(link, nodeById).forEach((claimId) => {
      const claim = nodeById.get(claimId);
      if (!claim) return;
      link.limitations.forEach((limitationId) => {
        const node = nodeById.get(limitationId);
        if (!node || node.kind !== "limitation") return;
        const index = nextOrdinal(`${claimId}:limitation`);
        const angle = claimLimitationAngle(claimId, index);
        const distance = (claim.radius || 34) + 220 + (index % 2) * 34;
        const current = desired.get(limitationId) || { x: 0, y: 0, weight: 0 };
        current.x += clampGraphCoordinate(claim.x + Math.cos(angle) * distance, 72, width - 72);
        current.y += clampGraphCoordinate(claim.y + Math.sin(angle) * distance, 72, height - 72);
        current.weight += 1;
        desired.set(limitationId, current);
      });
    });
  });
  desired.forEach((target, id) => {
    const node = nodeById.get(id);
    if (!node || !target.weight) return;
    node.x = target.x / target.weight;
    node.y = target.y / target.weight;
    node.role = "boundary";
  });
}

function graphClaimNeighborhoods(nodes, nodeById, reasoningModels) {
  const byClaim = new Map();
  const ensure = (claimId) => {
    const claim = nodeById.get(claimId);
    if (!claim || claim.kind !== "claim") return null;
    if (!byClaim.has(claimId)) {
      byClaim.set(claimId, { claimId, label: `${displayStudioNodeId(claimId)} argument`, nodeIds: new Set([claimId]), linkIds: [] });
    }
    return byClaim.get(claimId);
  };
  reasoningModels.forEach((link) => {
    graphPrimaryClaimIds(link, nodeById).forEach((claimId) => {
      const neighborhood = ensure(claimId);
      if (!neighborhood) return;
      neighborhood.linkIds.push(link.id);
      [...link.targets, ...link.premises, ...link.warrants, ...link.limitations].forEach((id) => {
        if (nodeById.has(id)) neighborhood.nodeIds.add(id);
      });
    });
  });
  return [...byClaim.values()]
    .map((item) => ({ ...item, nodeIds: [...item.nodeIds] }))
    .filter((item) => item.nodeIds.length > 1)
    .sort((a, b) => (nodeById.get(b.claimId)?.degree || 0) - (nodeById.get(a.claimId)?.degree || 0));
}

function claimClusterHulls(neighborhoods, nodes, width, height) {
  const nodeById = new Map(nodes.map((node) => [node.id, node]));
  return neighborhoods
    .map((neighborhood) => {
      const members = neighborhood.nodeIds.map((id) => nodeById.get(id)).filter(Boolean);
      if (!members.length) return null;
      const claim = nodeById.get(neighborhood.claimId);
      const padding = claim?.prominence === "primary" ? 54 : 38;
      const minX = Math.min(...members.map((node) => node.x - node.radius)) - padding;
      const maxX = Math.max(...members.map((node) => node.x + node.radius)) + padding;
      const minY = Math.min(...members.map((node) => node.y - node.radius)) - padding;
      const maxY = Math.max(...members.map((node) => node.y + node.radius)) + padding;
      const x = Math.max(18, minX);
      const y = Math.max(18, minY);
      const right = Math.min(width - 18, maxX);
      const bottom = Math.min(height - 18, maxY);
      return {
        claimId: neighborhood.claimId,
        label: neighborhood.label,
        linkIds: neighborhood.linkIds,
        x,
        y,
        width: Math.max(124, right - x),
        height: Math.max(92, bottom - y),
      };
    })
    .filter(Boolean);
}

function graphNodeCentroid(nodes) {
  if (!nodes.length) return { x: 590, y: 360 };
  return {
    x: nodes.reduce((sum, node) => sum + node.x, 0) / nodes.length,
    y: nodes.reduce((sum, node) => sum + node.y, 0) / nodes.length,
  };
}

function claimEvidenceAngle(claimId, index) {
  const bases = {
    C0: Math.PI * 0.96,
    C1: Math.PI * 1.18,
    C2: Math.PI * 1.16,
    C3: Math.PI * 1.05,
    C4: Math.PI * 1.32,
    C5: Math.PI * 0.82,
    C6: Math.PI * 1.42,
  };
  return (bases[claimId] || Math.PI) + (index - 0.5) * 0.34;
}

function claimLimitationAngle(claimId, index) {
  const bases = {
    C0: Math.PI * 0.22,
    C1: Math.PI * 0.36,
    C2: Math.PI * 0.42,
    C3: Math.PI * 0.64,
    C4: Math.PI * 0.74,
    C5: Math.PI * 0.88,
    C6: Math.PI * 0.1,
  };
  return (bases[claimId] || Math.PI * 0.35) + (index - 0.5) * 0.32;
}

function clampGraphCoordinate(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function graphZoomValue() {
  return clampGraphZoom(state.graphZoom);
}

function clampGraphZoom(value) {
  const zoom = Number(value);
  if (!Number.isFinite(zoom)) return 0.82;
  return Math.max(0.35, Math.min(1.8, zoom));
}

function projectReasoningLinks(graph) {
  if (Array.isArray(graph?.reasoning_links)) return graph.reasoning_links;
  return (graph?.links || [])
    .filter((link) => normalizeToken(link.link_type || link.type) === "reasoninglink")
    .map((link) => ({
      id: compactGraphId(link.local_id || link.link_id || link.id),
      premises: link.source || link.premises || [],
      relation: link.relation || "",
      target: link.target || "",
      warrant: link.warrant || "",
      limitations: link.limitations || [],
      confidence: link.confidence || "",
    }));
}

function projectTranslationLinks(graph) {
  if (Array.isArray(graph?.translation_links)) return graph.translation_links;
  return (graph?.links || [])
    .filter((link) => normalizeToken(link.link_type || link.type) === "translationlink")
    .map((link) => ({
      id: compactGraphId(link.local_id || link.link_id || link.id),
      input: link.input || "",
      relation: link.relation || "",
      project_node: link.project_node || link.target || "",
      project_warrant: link.project_warrant || "",
      project_limitation: link.project_limitation || "",
    }));
}

function compactGraphId(value) {
  const text = String(value || "").trim();
  if (!text) return "";
  const match = text.match(/\b(?:Q|C|E|W|L|RL|TL|D)\d+\b/);
  return match ? match[0] : text;
}

function normalizeGraphKind(kind) {
  const value = normalizeToken(kind).replace(/[_\s-]+/g, "-");
  return {
    question: "question",
    claim: "claim",
    evidence: "evidence",
    warrant: "warrant",
    limitation: "limitation",
    reasoninglink: "reasoning-link",
    "reasoning-link": "reasoning-link",
    translationlink: "translation-link",
    "translation-link": "translation-link",
    delta: "delta",
    projectdelta: "delta",
    paper: "paper-source",
    "paper-source": "paper-source",
  }[value] || value || "unknown";
}

function splitGraphIds(value) {
  const values = Array.isArray(value) ? value : String(value || "").split(/[;,]/);
  const ids = [];
  values.forEach((item) => {
    const matches = String(item || "").match(/\b(?:Q|C|E|W|L|RL|TL|D)\d+\b/g) || [];
    matches.forEach((match) => {
      if (!ids.includes(match)) ids.push(match);
    });
  });
  return ids;
}

function paperPathFromText(value) {
  const text = String(value || "");
  const match = text.match(/wiki\/projects\/[^\s,;|]+\/papers\/[^\s,;|]+\/index(?:\.md)?/);
  return normalizePaperDossierPath(match ? match[0] : "");
}

function firstPaperPath(value) {
  if (Array.isArray(value)) {
    return value.map((item) => paperPathFromText(item)).find(Boolean) || "";
  }
  return paperPathFromText(value);
}

function paperTitleFromPath(path) {
  const parts = String(path || "").split("/");
  const index = parts.indexOf("papers");
  return index >= 0 && parts[index + 1] ? parts[index + 1].replaceAll("-", " ") : "paper dossier";
}

function graphRelationLabel(value) {
  return String(value || "").replaceAll("_", " ").trim() || "relates";
}

function isOpenDelta(delta) {
  const status = normalizeToken(delta?.status || delta?.payload?.status || "");
  if (!status) return true;
  if (["proposed", "pending", "parked", "revised", "open"].includes(status)) return true;
  return !["accepted", "rejected", "integrated", "partially_integrated", "closed"].includes(status);
}

function graphNodeMeta(node) {
  const payload = node.payload || {};
  const parts = [
    payload.status || node.status || "",
    payload.confidence || node.confidence || "",
    payload.human_review || node.human_review || "",
  ].filter(Boolean);
  return uniqueStrings(parts).slice(0, 2).join(" · ");
}

function graphStudioCounts(model) {
  return {
    question: model.nodes.filter((node) => node.kind === "question").length,
    claim: model.nodes.filter((node) => node.kind === "claim").length,
    evidence: model.nodes.filter((node) => node.kind === "evidence").length,
    warrant: model.nodes.filter((node) => node.kind === "warrant").length,
    limitation: model.nodes.filter((node) => node.kind === "limitation").length,
    reasoningLink: model.reasoningLinks.length,
    translationLink: model.translationLinks.length,
    delta: model.deltas.length,
  };
}

function renderGraphCanvas(model) {
  return renderProjectGraphReactMount(model);
}

function renderProjectGraphReactMount(_model) {
  return `
    <div
      id="project-graph-react-root"
      class="project-graph-react-root"
      data-project-graph-react-root
      aria-label="Project argument graph canvas"
    ></div>
  `;
}

function buildProjectGraphReactPayload(model) {
  const argumentMap = buildProjectArgumentMap(model);
  const backbone = buildProjectArgumentBackbone(model, argumentMap);
  const selectedNode = model.nodeById.get(state.selectedGraphNodeId || "");
  const selectedClaimId = selectedNode?.kind === "claim"
    ? selectedNode.id
    : backbone.primaryClaimId || argumentMap.claims[0]?.claim.id || "";
  const claimMaxDegree = Math.max(1, ...argumentMap.claims.map((section) => section.claim.degree || 0));
  const claimPayloads = backbone.claims.map((section) => {
    const position = backbone.positions.get(section.claim.id) || {
      x: 0,
      y: 0,
      width: 260,
      height: 118,
      prominence: "secondary",
    };
    const questionIds = backbone.questions
      .filter((question) => question.claimIds.includes(section.claim.id))
      .map((question) => question.id);
    return {
      id: section.claim.id,
      label: truncateText(section.claim.label, position.prominence === "primary" ? 132 : 96),
      fullLabel: section.claim.label,
      subtitle: section.claim.subtitle || "",
      degree: section.claim.degree || 0,
      radius: graphNodeRadius(section.claim, claimMaxDegree),
      prominence: position.prominence,
      x: Math.round(position.x - position.width / 2),
      y: Math.round(position.y + 140 - position.height / 2),
      width: position.width,
      height: position.height,
      questionIds,
      stats: {
        supportClaims: section.supportClaims.length,
        evidence: section.evidence.length,
        warrants: section.warrants.length,
        limitations: section.limitations.length,
        links: section.links.length,
        sources: section.sources.length,
      },
      supportClaims: projectGraphReactNodeRows(model, section.supportClaims),
      evidence: projectGraphReactNodeRows(model, section.evidence),
      warrants: projectGraphReactNodeRows(model, section.warrants),
      limitations: projectGraphReactNodeRows(model, section.limitations),
      links: section.links.map((link) => ({
        id: link.id,
        relation: link.relation,
        premises: link.premises,
        targets: link.targets,
        warrants: link.warrants,
        limitations: link.limitations,
      })),
      sources: section.sources.map((source) => ({
        path: source,
        label: argumentSourceLabel(source),
      })),
    };
  });
  return {
    project: model.graph?.project || state.projectId,
    counts: graphStudioCounts(model),
    primaryClaimId: backbone.primaryClaimId,
    selectedClaimId,
    questions: backbone.questions.map((question) => ({
      id: question.id,
      label: truncateText(question.label, 104),
      fullLabel: question.label,
      claimIds: question.claimIds,
    })),
    claims: claimPayloads,
    edges: backbone.claimEdges.map((edge) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      relation: edge.relation || "supports",
      linkId: edge.linkId,
    })),
  };
}

function projectGraphReactNodeRows(model, nodes) {
  return nodes.map((node) => ({
    id: node.id,
    kind: node.kind,
    label: node.label,
    subtitle: node.subtitle || "",
    sources: paperSourcesForGraphNode(model, node).map((source) => ({
      path: source,
      label: argumentSourceLabel(source),
    })),
  }));
}

function mountProjectGraphReactIsland(graphOrModel) {
  const root = document.querySelector("[data-project-graph-react-root]");
  if (!root) return false;
  const model = graphOrModel?.nodeById ? graphOrModel : buildGraphStudioModel(graphOrModel);
  const mountApi = window.ResearchBrowserProjectGraph;
  if (!mountApi?.mount) {
    root.innerHTML = renderProjectArgumentMap(model);
    return false;
  }
  mountApi.mount(root, {
    payload: buildProjectGraphReactPayload(model),
    callbacks: {
      onSelectNode: (nodeId) => {
        state.selectedGraphNodeId = nodeId;
      },
      loadProjectGraphPaper: (path) => {
        return loadProjectGraphPaper(path);
      },
    },
  });
  return true;
}

function mountPaperContributionReactIsland(graph) {
  const root = document.querySelector("[data-paper-contribution-react-root]");
  if (!root) return false;
  const mountApi = window.ResearchBrowserProjectGraph;
  if (!mountApi?.mountPaperContribution) {
    root.innerHTML = renderPaperContributionFallback(graph);
    return false;
  }
  mountApi.mountPaperContribution(root, { graph });
  return true;
}

function buildProjectArgumentMap(model) {
  const questions = model.nodes
    .filter((node) => node.kind === "question")
    .sort((a, b) => a.id.localeCompare(b.id, undefined, { numeric: true }));
  const claims = model.nodes
    .filter((node) => node.kind === "claim")
    .sort((a, b) => (b.degree || 0) - (a.degree || 0) || a.id.localeCompare(b.id, undefined, { numeric: true }))
    .map((claim) => claimArgumentSections(model, claim));
  return { questions, claims };
}

function claimArgumentSections(model, claim) {
  const links = model.reasoningModels.filter((link) => graphPrimaryClaimIds(link, model.nodeById).includes(claim.id));
  const supportClaimIds = [];
  const evidenceIds = [];
  const warrantIds = [];
  const limitationIds = [];
  links.forEach((link) => {
    link.premises.forEach((id) => {
      if (id !== claim.id && model.nodeById.get(id)?.kind === "claim") supportClaimIds.push(id);
      if (model.nodeById.get(id)?.kind === "evidence") evidenceIds.push(id);
    });
    link.warrants.forEach((id) => warrantIds.push(id));
    link.limitations.forEach((id) => limitationIds.push(id));
  });
  const supportClaims = argumentNodesForIds(model, supportClaimIds);
  const evidence = argumentNodesForIds(model, evidenceIds);
  const warrants = argumentNodesForIds(model, warrantIds);
  const limitations = argumentNodesForIds(model, limitationIds);
  const sources = uniqueStrings([
    ...paperSourcesForGraphNode(model, claim),
    ...supportClaims.flatMap((node) => paperSourcesForGraphNode(model, node)),
    ...evidence.flatMap((node) => paperSourcesForGraphNode(model, node)),
    ...warrants.flatMap((node) => paperSourcesForGraphNode(model, node)),
    ...limitations.flatMap((node) => paperSourcesForGraphNode(model, node)),
  ]).slice(0, 6);
  return { claim, links, supportClaims, evidence, warrants, limitations, sources };
}

function argumentNodesForIds(model, ids) {
  return uniqueStrings(ids)
    .map((id) => model.nodeById.get(id))
    .filter(Boolean)
    .sort((a, b) => a.id.localeCompare(b.id, undefined, { numeric: true }));
}

function renderProjectArgumentMap(model) {
  const argumentMap = buildProjectArgumentMap(model);
  return `
    <div class="project-argument-map" aria-label="Project Argument Map">
      <div class="argument-map-header">
        <div>
          <p class="eyebrow">Argument Backbone</p>
          <h3>Question -> Claim -> Claim</h3>
        </div>
        <span>Toulmin detail on selection</span>
      </div>
      ${renderProjectArgumentBackbone(model, argumentMap)}
      ${renderSelectedClaimDetail(model, argumentMap)}
    </div>
  `;
}

function buildProjectArgumentBackbone(model, argumentMap) {
  const claimById = new Map(argumentMap.claims.map((section) => [section.claim.id, section]));
  const questionClaimIds = new Map(argumentMap.questions.map((question) => [question.id, []]));
  const claimEdges = [];
  model.reasoningModels.forEach((link) => {
    const premiseClaims = link.premises.filter((id) => model.nodeById.get(id)?.kind === "claim");
    const premiseQuestions = link.premises.filter((id) => model.nodeById.get(id)?.kind === "question");
    const targetClaims = link.targets.filter((id) => model.nodeById.get(id)?.kind === "claim");
    const targetQuestions = link.targets.filter((id) => model.nodeById.get(id)?.kind === "question");
    targetQuestions.forEach((questionId) => {
      const current = questionClaimIds.get(questionId) || [];
      premiseClaims.forEach((claimId) => current.push(claimId));
      questionClaimIds.set(questionId, uniqueStrings(current));
    });
    premiseQuestions.forEach((questionId) => {
      const current = questionClaimIds.get(questionId) || [];
      targetClaims.forEach((claimId) => current.push(claimId));
      questionClaimIds.set(questionId, uniqueStrings(current));
    });
    targetClaims.forEach((targetId) => {
      premiseClaims.forEach((sourceId) => {
        if (sourceId === targetId) return;
        claimEdges.push({
          id: `${link.id}:${sourceId}:${targetId}`,
          source: sourceId,
          target: targetId,
          relation: link.relation,
          linkId: link.id,
        });
      });
    });
  });
  const primaryClaimId = claimById.has("C0") ? "C0" : argumentMap.claims[0]?.claim.id || "";
  const questions = argumentMap.questions.map((question, index) => ({
    ...question,
    claimIds: argumentQuestionClaimIds(question, argumentMap.claims, questionClaimIds.get(question.id) || [], primaryClaimId, index),
  }));
  const directSupportIds = uniqueStrings(claimEdges.filter((edge) => edge.target === primaryClaimId).map((edge) => edge.source));
  const placed = new Set();
  const width = 1480;
  const height = 700;
  const positions = new Map();
  const addPosition = (claimId, x, y) => {
    const section = claimById.get(claimId);
    if (!section || placed.has(claimId)) return;
    const prominence = claimId === primaryClaimId ? "primary" : directSupportIds.includes(claimId) ? "support" : "secondary";
    const radius = graphNodeRadius(section.claim, Math.max(1, argumentMap.claims[0]?.claim.degree || 1));
    positions.set(claimId, {
      id: claimId,
      x,
      y,
      width: prominence === "primary" ? 360 : prominence === "support" ? 280 : 240,
      height: prominence === "primary" ? 142 : 116,
      prominence,
      radius,
    });
    placed.add(claimId);
  };
  if (primaryClaimId) addPosition(primaryClaimId, width / 2, 160);
  directSupportIds.forEach((claimId, index) => {
    const spread = directSupportIds.length <= 1 ? 0.5 : index / (directSupportIds.length - 1);
    addPosition(claimId, 350 + spread * 780, 430);
  });
  const questionClaimSlots = new Map();
  questions.forEach((question, questionIndex) => {
    question.claimIds.forEach((claimId) => {
      if (claimId === primaryClaimId || directSupportIds.includes(claimId)) return;
      const current = questionClaimSlots.get(claimId) ?? questionIndex;
      questionClaimSlots.set(claimId, Math.min(current, questionIndex));
    });
  });
  [...questionClaimSlots.entries()].forEach(([claimId, questionIndex], index) => {
    const fallbackSpread = questionClaimSlots.size <= 1 ? 0.5 : index / (questionClaimSlots.size - 1);
    const questionSpread = questions.length <= 1 ? fallbackSpread : questionIndex / (questions.length - 1);
    addPosition(claimId, 180 + questionSpread * 1120, 245);
  });
  const remaining = argumentMap.claims.map((section) => section.claim.id).filter((id) => !placed.has(id));
  remaining.forEach((claimId, index) => {
    const spread = remaining.length <= 1 ? 0.5 : index / (remaining.length - 1);
    addPosition(claimId, 220 + spread * 1040, 610);
  });
  return {
    width,
    height,
    primaryClaimId,
    questions,
    claims: argumentMap.claims,
    claimById,
    claimEdges,
    positions,
  };
}

function argumentQuestionClaimIds(question, claimSections, explicitIds, primaryClaimId, questionIndex) {
  const ids = uniqueStrings(explicitIds);
  if (!ids.length && questionIndex === 0 && primaryClaimId) ids.push(primaryClaimId);
  const questionTokens = argumentTextTokens(question.label);
  const scored = claimSections
    .filter((section) => !ids.includes(section.claim.id))
    .map((section) => {
      const claimTokens = argumentTextTokens(`${section.claim.label} ${section.claim.subtitle || ""}`);
      const overlap = questionTokens.filter((token) => claimTokens.includes(token)).length;
      return { id: section.claim.id, overlap, degree: section.claim.degree || 0 };
    })
    .filter((item) => item.overlap > 0)
    .sort((a, b) => b.overlap - a.overlap || b.degree - a.degree || a.id.localeCompare(b.id, undefined, { numeric: true }))
    .slice(0, ids.length ? 1 : 3)
    .map((item) => item.id);
  return uniqueStrings([...ids, ...scored]).slice(0, 4);
}

function argumentTextTokens(value) {
  const stop = new Set(["what", "does", "this", "that", "with", "from", "mean", "means", "project", "claim", "side", "object", "regions", "useful", "current"]);
  return uniqueStrings(String(value || "").toLowerCase().match(/[a-z0-9]+/g) || [])
    .filter((token) => token.length > 3 && !stop.has(token));
}

function renderProjectArgumentBackbone(model, argumentMap) {
  const backbone = buildProjectArgumentBackbone(model, argumentMap);
  return `
    <section class="argument-backbone-map" aria-label="Project argument backbone">
      ${renderBackboneQuestionRail(backbone)}
      ${renderBackboneClaimMap(backbone)}
    </section>
  `;
}

function renderBackboneQuestionRail(backbone) {
  return `
    <div class="argument-question-rail" aria-label="Question to claim map">
      ${backbone.questions.map((question) => `
        <article class="argument-question-card" data-backbone-question-id="${escapeAttr(question.id)}" data-argument-node-id="${escapeAttr(question.id)}" data-studio-node-id="${escapeAttr(question.id)}">
          <header>
            <span>${escapeHtml(question.id)}</span>
            <strong>${escapeHtml(truncateText(question.label, 92))}</strong>
          </header>
          <div>
            ${question.claimIds.map((claimId) => `<button type="button" data-backbone-claim-id="${escapeAttr(claimId)}" data-argument-node-id="${escapeAttr(claimId)}" data-studio-node-id="${escapeAttr(claimId)}">${escapeHtml(claimId)}</button>`).join("") || `<em>No claim</em>`}
          </div>
        </article>
      `).join("") || `<div class="empty-state">No question。</div>`}
    </div>
  `;
}

function renderBackboneClaimMap(backbone) {
  return `
    <div class="argument-claim-map" style="height:${backbone.height}px;min-width:${backbone.width}px">
      <svg class="argument-claim-edge-layer" viewBox="0 0 ${backbone.width} ${backbone.height}" aria-hidden="true">
        ${renderBackboneClaimEdges(backbone)}
      </svg>
      <div class="argument-claim-node-layer">
        ${backbone.claims.map((section) => renderBackboneClaimNode(section, backbone)).join("")}
      </div>
    </div>
  `;
}

function renderBackboneClaimEdges(backbone) {
  return backbone.claimEdges.map((edge) => {
    const source = backbone.positions.get(edge.source);
    const target = backbone.positions.get(edge.target);
    if (!source || !target) return "";
    const d = backboneEdgePath(source, target);
    const label = backboneEdgeLabelPosition(source, target);
    const relation = String(edge.relation || "supports").replace(/[^a-z0-9_-]+/gi, "-");
    return `
      <path class="argument-claim-edge argument-claim-edge-${escapeAttr(relation)}" data-source-id="${escapeAttr(edge.source)}" data-target-id="${escapeAttr(edge.target)}" data-link-id="${escapeAttr(edge.linkId)}" data-relation="${escapeAttr(edge.relation)}" d="${d}"></path>
      <text class="argument-claim-edge-label" x="${label.x.toFixed(1)}" y="${label.y.toFixed(1)}">${escapeHtml(edge.linkId)} ${escapeHtml(graphRelationLabel(edge.relation))}</text>
    `;
  }).join("");
}

function backboneEdgePath(source, target) {
  const dx = target.x - source.x;
  const dy = target.y - source.y;
  const length = Math.max(1, Math.hypot(dx, dy));
  const ux = dx / length;
  const uy = dy / length;
  const sx = source.x + ux * (source.width * 0.42);
  const sy = source.y + uy * (source.height * 0.38);
  const tx = target.x - ux * (target.width * 0.42);
  const ty = target.y - uy * (target.height * 0.38);
  const midY = (sy + ty) / 2;
  return `M ${sx.toFixed(1)} ${sy.toFixed(1)} C ${sx.toFixed(1)} ${midY.toFixed(1)}, ${tx.toFixed(1)} ${midY.toFixed(1)}, ${tx.toFixed(1)} ${ty.toFixed(1)}`;
}

function backboneEdgeLabelPosition(source, target) {
  return {
    x: source.x * 0.52 + target.x * 0.48,
    y: source.y * 0.52 + target.y * 0.48 - 8,
  };
}

function renderBackboneClaimNode(section, backbone) {
  const { claim, supportClaims, evidence, warrants, limitations, links, sources } = section;
  const position = backbone.positions.get(claim.id);
  if (!position) return "";
  const questionIds = backbone.questions.filter((question) => question.claimIds.includes(claim.id)).map((question) => question.id);
  return `
    <button type="button" class="argument-claim-node" data-backbone-claim-id="${escapeAttr(claim.id)}" data-argument-node-id="${escapeAttr(claim.id)}" data-studio-node-id="${escapeAttr(claim.id)}" data-claim-prominence="${escapeAttr(position.prominence)}" style="left:${(position.x - position.width / 2).toFixed(1)}px;top:${(position.y - position.height / 2).toFixed(1)}px;width:${position.width}px;min-height:${position.height}px">
      <span class="argument-node-token">${escapeHtml(claim.id)}</span>
      <strong>${escapeHtml(truncateText(claim.label, position.prominence === "primary" ? 140 : 92))}</strong>
      <em>${escapeHtml(claim.subtitle || "project claim")}</em>
      <span class="argument-claim-badges">
        <i>S${supportClaims.length}</i><i>E${evidence.length}</i><i>W${warrants.length}</i><i>L${limitations.length}</i><i>RL${links.length}</i><i>P${sources.length}</i>
      </span>
      ${questionIds.length ? `<small>answers ${escapeHtml(questionIds.join(", "))}</small>` : ""}
    </button>
  `;
}

function selectedClaimSection(argumentMap) {
  const selected = argumentMap.claims.find((section) => section.claim.id === state.selectedGraphNodeId);
  return selected || argumentMap.claims[0] || null;
}

function renderSelectedClaimDetail(model, argumentMap) {
  const section = selectedClaimSection(argumentMap);
  if (!section) return `<section class="selected-claim-detail" id="selected-claim-detail"><div class="empty-state">No claim detail。</div></section>`;
  return `
    <section class="selected-claim-detail" id="selected-claim-detail" aria-label="Selected claim Toulmin detail">
      <div class="selected-claim-detail-head">
        <div>
          <p class="eyebrow">Selected Claim Detail</p>
          <h3>${escapeHtml(section.claim.id)} evidence / warrant / limitation</h3>
        </div>
        <span>Select a claim above to switch</span>
      </div>
      ${renderArgumentClaimRegion(section)}
    </section>
  `;
}

function renderArgumentQuestionSpine(questions) {
  return `
    <section class="argument-question-spine" aria-label="Project questions">
      <div>
        <p class="eyebrow">Question Spine</p>
        <strong>Project question layer</strong>
      </div>
      <div class="argument-question-list">
        ${questions.map((question) => `
          <button type="button" data-argument-node-id="${escapeAttr(question.id)}" data-studio-node-id="${escapeAttr(question.id)}">
            <span>${escapeHtml(question.id)}</span>
            <strong>${escapeHtml(truncateText(question.label, 92))}</strong>
          </button>
        `).join("") || `<p class="graph-inspector-empty">No question。</p>`}
      </div>
    </section>
  `;
}

function renderArgumentClaimRegion(section) {
  const { claim, supportClaims, evidence, warrants, limitations, sources, links } = section;
  return `
    <article class="argument-claim-region" data-argument-claim-id="${escapeAttr(claim.id)}" data-studio-node-id="${escapeAttr(claim.id)}" tabindex="0">
      <header class="argument-claim-head">
        <div>
          <span class="argument-node-token">Claim ${escapeHtml(claim.id)}</span>
          <h4>${escapeHtml(claim.label)}</h4>
          ${claim.subtitle ? `<p>${escapeHtml(claim.subtitle)}</p>` : ""}
        </div>
        <dl>
          <div><dt>Support</dt><dd>${supportClaims.length}</dd></div>
          <div><dt>Evidence</dt><dd>${evidence.length}</dd></div>
          <div><dt>Warrant</dt><dd>${warrants.length}</dd></div>
          <div><dt>Limit</dt><dd>${limitations.length}</dd></div>
          <div><dt>RL</dt><dd>${links.length}</dd></div>
        </dl>
      </header>
      <div class="argument-flow-grid">
        <section class="argument-lane argument-support-lane">
          <p class="eyebrow">Supporting Claims</p>
          ${renderArgumentNodeRows(supportClaims, "No supporting claim.")}
        </section>
        <section class="argument-lane argument-evidence-lane">
          <p class="eyebrow">Evidence / Grounds</p>
          ${renderArgumentNodeRows(evidence, "No evidence.")}
        </section>
        <section class="argument-lane argument-warrant-lane">
          <p class="eyebrow">Warrant / Bridge</p>
          <div class="argument-warrant-bridge">
            ${renderArgumentNodeRows(warrants, "No explicit warrant.")}
          </div>
        </section>
        <section class="argument-lane argument-limitation-lane">
          <p class="eyebrow">Limitations / Rebuttal</p>
          ${renderArgumentNodeRows(limitations, "No limitation.")}
        </section>
      </div>
      <div class="argument-source-strip">
        <span>Source papers</span>
        ${sources.map((source) => `<button type="button" data-paper-graph-path="${escapeAttr(source)}">${escapeHtml(argumentSourceLabel(source))}</button>`).join("") || `<em>No paper source.</em>`}
      </div>
    </article>
  `;
}

function renderArgumentNodeRows(nodes, emptyText) {
  if (!nodes.length) return `<p class="graph-inspector-empty">${escapeHtml(emptyText)}</p>`;
  return `
    <div class="argument-node-list">
      ${nodes.map((node) => `
        <button type="button" class="argument-node-row" data-argument-node-id="${escapeAttr(node.id)}" data-studio-node-id="${escapeAttr(node.id)}" data-node-kind="${escapeAttr(node.kind)}">
          <span>${escapeHtml(node.id)}</span>
          <strong>${escapeHtml(node.label)}</strong>
          ${node.subtitle ? `<em>${escapeHtml(node.subtitle)}</em>` : ""}
        </button>
      `).join("")}
    </div>
  `;
}

function argumentSourceLabel(source) {
  const title = paperTitleFromPath(source);
  return title === "paper dossier" ? truncateText(source, 42) : truncateText(title, 42);
}

function renderProjectClaimAtlas(model) {
  const zoom = graphZoomValue();
  const scaledWidth = Math.ceil(model.width * zoom);
  const scaledHeight = Math.ceil(model.height * zoom);
  return `
    <div class="claim-atlas" aria-label="Project Claim Atlas" data-graph-interaction="pan-zoom" data-graph-zoom="${zoom.toFixed(2)}" tabindex="0">
      <div class="claim-atlas-zoom-space" style="width:${scaledWidth}px;height:${scaledHeight}px">
        <div class="claim-atlas-board" style="width:${model.width}px;height:${model.height}px;--graph-zoom:${zoom.toFixed(2)}">
          <svg class="graph-edge-layer" viewBox="0 0 ${model.width} ${model.height}" aria-hidden="true">
            ${renderClaimClusterHulls(model)}
            ${renderGraphSvgEdges(model)}
          </svg>
          <div class="graph-node-layer">
            ${model.nodes.map((node) => renderGraphCanvasNode(node)).join("")}
          </div>
        </div>
      </div>
    </div>
  `;
}

function renderGraphZoomControls() {
  return `
    <div class="graph-zoom-controls" aria-label="Canvas zoom">
      <button type="button" data-zoom-command="out" title="Zoom out">-</button>
      <span class="graph-zoom-value" data-graph-zoom-value>${Math.round(graphZoomValue() * 100)}%</span>
      <button type="button" data-zoom-command="in" title="Zoom in">+</button>
      <button type="button" data-zoom-command="reset" title="Reset to 100%">100%</button>
      <button type="button" data-zoom-command="fit" title="Fit viewport">Fit</button>
    </div>
  `;
}

function renderClaimClusterHulls(model) {
  const hulls = (model.clusters || []).map((cluster) => `
    <g class="claim-cluster-hull" data-cluster-claim="${escapeAttr(cluster.claimId)}">
      <rect x="${cluster.x.toFixed(1)}" y="${cluster.y.toFixed(1)}" width="${cluster.width.toFixed(1)}" height="${cluster.height.toFixed(1)}" rx="46"></rect>
      <text class="claim-cluster-label" x="${(cluster.x + 18).toFixed(1)}" y="${(cluster.y + 23).toFixed(1)}">${escapeHtml(cluster.label)}</text>
    </g>
  `).join("");
  return hulls ? `<g class="claim-cluster-layer">${hulls}</g>` : "";
}

function renderGraphSvgEdges(model) {
  const paths = model.edges.map((edge) => {
    const source = model.nodeById.get(edge.source);
    const target = model.nodeById.get(edge.target);
    if (!source || !target) return "";
    const vx = target.x - source.x;
    const vy = target.y - source.y;
    const distance = Math.max(1, Math.hypot(vx, vy));
    const ux = vx / distance;
    const uy = vy / distance;
    const sx = source.x + ux * (source.radius + 4);
    const sy = source.y + uy * (source.radius + 4);
    const tx = target.x - ux * (target.radius + 6);
    const ty = target.y - uy * (target.radius + 6);
    const route = graphEdgeRoute(model, edge, { sx, sy, tx, ty, ux, uy });
    const roleClass = String(edge.role || "edge").replace(/[^a-z0-9_-]+/gi, "-");
    const relationClass = edge.relation.replace(/[^a-z0-9_-]+/gi, "-");
    const attrs = `data-graph-edge-id="${escapeAttr(edge.id)}" data-source-id="${escapeAttr(edge.source)}" data-target-id="${escapeAttr(edge.target)}" data-link-id="${escapeAttr(edge.linkId)}" data-relation="${escapeAttr(edge.relation)}" data-edge-role="${escapeAttr(edge.role || "edge")}" data-claim-id="${escapeAttr(edge.claimId || "")}"`;
    return `
      <path class="graph-edge graph-edge-${escapeAttr(relationClass)} graph-edge-role-${escapeAttr(roleClass)}" ${attrs} d="${route.d}"></path>
      ${renderGraphArrowHead(edge, { tx, ty, ux: route.arrowUx, uy: route.arrowUy, relationClass, roleClass, attrs })}
    `;
  }).join("");
  return paths;
}

function graphEdgeRoute(model, edge, geometry) {
  const claim = model.nodeById.get(edge.claimId || "");
  const waypoint = graphEdgeWaypoint(edge, claim, geometry);
  if (!waypoint) {
    const fromRight = geometry.sx <= geometry.tx;
    const dx = Math.max(90, Math.abs(geometry.tx - geometry.sx) * 0.48);
    const c1x = fromRight ? geometry.sx + dx : geometry.sx - dx;
    const c2x = fromRight ? geometry.tx - dx : geometry.tx + dx;
    return {
      d: `M ${geometry.sx} ${geometry.sy} C ${c1x} ${geometry.sy}, ${c2x} ${geometry.ty}, ${geometry.tx} ${geometry.ty}`,
      arrowUx: geometry.ux,
      arrowUy: geometry.uy,
    };
  }
  const firstCx = geometry.sx + (waypoint.x - geometry.sx) * 0.62;
  const firstCy = geometry.sy + (waypoint.y - geometry.sy) * 0.18;
  const secondCx = geometry.tx + (waypoint.x - geometry.tx) * 0.62;
  const secondCy = geometry.ty + (waypoint.y - geometry.ty) * 0.18;
  const dx = geometry.tx - waypoint.x;
  const dy = geometry.ty - waypoint.y;
  const length = Math.max(1, Math.hypot(dx, dy));
  return {
    d: `M ${geometry.sx} ${geometry.sy} C ${firstCx.toFixed(1)} ${firstCy.toFixed(1)}, ${waypoint.x.toFixed(1)} ${waypoint.y.toFixed(1)}, ${waypoint.x.toFixed(1)} ${waypoint.y.toFixed(1)} C ${waypoint.x.toFixed(1)} ${waypoint.y.toFixed(1)}, ${secondCx.toFixed(1)} ${secondCy.toFixed(1)}, ${geometry.tx} ${geometry.ty}`,
    arrowUx: dx / length,
    arrowUy: dy / length,
  };
}

function graphEdgeWaypoint(edge, claim, geometry) {
  if (!claim) return null;
  const dx = geometry.tx - geometry.sx;
  const dy = geometry.ty - geometry.sy;
  const length = Math.max(1, Math.hypot(dx, dy));
  const ux = dx / length;
  const uy = dy / length;
  const px = -uy;
  const py = ux;
  const edgeIndex = Number(String(edge.id || "").match(/:(\d+)$/)?.[1] || 0);
  const stagger = ((edgeIndex % 5) - 2) * 8;
  const roleOffset = {
    premise: 0,
    "premise-to-warrant": -32,
    "warrant-to-claim": 22,
    limitation: 44,
  }[edge.role] || 0;
  if (edge.target === claim.id) {
    return {
      x: claim.x - ux * ((claim.radius || 36) + 96) + px * (roleOffset + stagger),
      y: claim.y - uy * ((claim.radius || 36) + 96) + py * (roleOffset + stagger),
    };
  }
  if (edge.role === "premise-to-warrant") {
    return {
      x: geometry.sx * 0.42 + geometry.tx * 0.42 + claim.x * 0.16 + px * (roleOffset + stagger),
      y: geometry.sy * 0.42 + geometry.ty * 0.42 + claim.y * 0.16 + py * (roleOffset + stagger),
    };
  }
  return null;
}

function renderGraphArrowHead(edge, geometry) {
  const size = geometry.roleClass === "warrant-to-claim" ? 10 : 8;
  const wing = size * 0.48;
  const baseX = geometry.tx - geometry.ux * size;
  const baseY = geometry.ty - geometry.uy * size;
  const leftX = baseX + -geometry.uy * wing;
  const leftY = baseY + geometry.ux * wing;
  const rightX = baseX - -geometry.uy * wing;
  const rightY = baseY - geometry.ux * wing;
  const d = [
    `M ${geometry.tx.toFixed(1)} ${geometry.ty.toFixed(1)}`,
    `L ${leftX.toFixed(1)} ${leftY.toFixed(1)}`,
    `L ${rightX.toFixed(1)} ${rightY.toFixed(1)}`,
    "Z",
  ].join(" ");
  return `<path class="graph-arrow-head graph-arrow-head-${escapeAttr(geometry.relationClass)} graph-arrow-role-${escapeAttr(geometry.roleClass)}" ${geometry.attrs} data-arrow-role="${escapeAttr(edge.role || "edge")}" d="${d}"></path>`;
}

function renderGraphCanvasNode(node) {
  const sourceAttr = node.sourcePath ? ` data-paper-graph-path="${escapeAttr(node.sourcePath)}"` : "";
  const meta = graphNodeMeta(node);
  const size = node.radius * 2;
  const roleAttr = node.role ? ` data-node-role="${escapeAttr(node.role)}"` : "";
  return `
    <button type="button" class="claim-atlas-node" data-node-kind="${escapeAttr(node.kind)}" data-studio-node-id="${escapeAttr(node.id)}" data-node-degree="${escapeAttr(node.degree || 0)}" data-node-radius="${escapeAttr(node.radius)}" data-node-prominence="${escapeAttr(node.prominence || "low")}"${roleAttr}${sourceAttr} style="left:${node.x - node.radius}px;top:${node.y - node.radius}px;width:${size}px;height:${size}px">
      <span class="graph-node-id">${escapeHtml(displayStudioNodeId(node.id))}</span>
      <strong class="claim-atlas-label">${escapeHtml(truncateText(node.label, node.prominence === "primary" ? 92 : 54))}</strong>
      ${meta ? `<span class="graph-node-meta">${escapeHtml(meta)}</span>` : ""}
    </button>
  `;
}

function renderGraphInspector(model) {
  return `<aside class="graph-inspector" id="graph-inspector">${renderGraphInspectorBody(model)}</aside>`;
}

function renderGraphInspectorBody(model) {
  const node = graphStudioSelectedNode(model);
  if (!node) return `<div class="empty-state">Select a node to inspect relationships.</div>`;
  const connected = graphConnectionsForNode(model, node.id);
  return `
    <div class="graph-inspector-head">
      <p class="eyebrow">${escapeHtml(graphKindDisplay(node.kind))}</p>
      <h3>${escapeHtml(displayStudioNodeId(node.id))}</h3>
    </div>
    <p class="graph-inspector-label">${escapeHtml(node.label)}</p>
    ${node.subtitle ? `<p class="graph-inspector-subtitle">${escapeHtml(node.subtitle)}</p>` : ""}
    ${node.sourcePath ? `<button type="button" class="paper-graph-button" data-paper-graph-path="${escapeAttr(node.sourcePath)}">Open paper graph</button>` : ""}
    <dl class="graph-inspector-facts">
      <div><dt>kind</dt><dd>${escapeHtml(node.kind)}</dd></div>
      <div><dt>degree</dt><dd>${connected.length}</dd></div>
    </dl>
    ${renderGraphAuditTrail(model, node)}
    <div class="graph-connection-list">
      <p class="eyebrow">Connected edges</p>
      ${connected.map((edge) => `
        <button type="button" data-studio-node-id="${escapeAttr(edge.source === node.id ? edge.target : edge.source)}">
          <span>${escapeHtml(displayStudioNodeId(edge.source))} ${escapeHtml(edge.source === node.id ? "->" : "<-")} ${escapeHtml(displayStudioNodeId(edge.target))}</span>
          <strong>${escapeHtml(graphRelationLabel(edge.relation))}</strong>
        </button>
      `).join("") || `<p class="graph-inspector-empty">No connections.</p>`}
    </div>
  `;
}

function renderGraphAuditTrail(model, node) {
  const audit = graphAuditForNode(model, node);
  return `
    <div class="graph-audit-trail" aria-label="Graph audit trail">
      <section class="graph-audit-section">
        <h4>Why it exists</h4>
        <p>${escapeHtml(audit.why)}</p>
      </section>
      <section class="graph-audit-section">
        <h4>What supports it</h4>
        ${renderGraphAuditItems(audit.supportedBy, "No direct support path.")}
      </section>
      <section class="graph-audit-section">
        <h4>What limits it</h4>
        ${renderGraphAuditItems(audit.limitedBy, "No explicit limitation.")}
      </section>
      <section class="graph-audit-section">
        <h4>Source papers</h4>
        ${renderGraphAuditItems(audit.paperSources, "No paper source path.")}
      </section>
      <section class="graph-audit-section">
        <h4>pending delta</h4>
        ${renderGraphAuditItems(audit.pendingDeltas, "No pending delta.")}
      </section>
    </div>
  `;
}

function renderGraphAuditItems(items, emptyText) {
  if (!items.length) return `<p class="graph-inspector-empty">${escapeHtml(emptyText)}</p>`;
  return `
    <ul>
      ${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}
    </ul>
  `;
}

function graphAuditForNode(model, node) {
  return {
    why: graphWhyExists(model, node),
    supportedBy: graphSupportItems(model, node.id),
    limitedBy: graphLimitationItems(model, node.id),
    paperSources: paperSourcesForGraphNode(model, node).map((path) => paperTitleFromPath(path)),
    pendingDeltas: pendingDeltasForGraphNode(model, node.id).map((delta) => `${delta.id}: ${delta.change_summary || delta.operation || delta.status || "pending"}`),
  };
}

function graphWhyExists(model, node) {
  if (node.kind === "reasoning-link") {
    const link = model.reasoningLinks.find((item) => item.id === node.id);
    return link ? `${link.id} connects ${splitGraphIds(link.premises).join(", ") || "premise"} through ${graphRelationLabel(link.relation)} to ${splitGraphIds(link.target).join(", ") || link.target || "target"}。` : "Reasoning link nodes store explicit reasoning relations.";
  }
  if (node.kind === "translation-link") return "TranslationLink records how a paper-side graph enters the project graph.";
  if (node.kind === "delta") return "Delta records proposed deltas or historical changes from papers, experiments, or discussion.";
  if (node.kind === "paper-source") return "Paper source nodes trace project-level claims back to paper dossiers.";
  const role = node.payload?.metadata?.role || node.payload?.status || node.subtitle;
  return role ? `${displayStudioNodeId(node.id)} is ${role}。` : `${displayStudioNodeId(node.id)} is a project graph ${graphKindDisplay(node.kind)} node.`;
}

function graphSupportItems(model, nodeId) {
  const items = [];
  model.reasoningLinks.forEach((link) => {
    const targetIds = splitGraphIds(link.target);
    const premiseIds = splitGraphIds(link.premises);
    const warrantIds = splitGraphIds(link.warrant);
    if (targetIds.includes(nodeId)) {
      items.push(`${link.id}: ${premiseIds.join(", ") || "premise"} -> ${targetIds.join(", ")} (${graphRelationLabel(link.relation)})`);
      if (warrantIds.length) items.push(`${link.id} warrant: ${warrantIds.join(", ")}`);
    } else if (premiseIds.includes(nodeId)) {
      items.push(`${link.id}: supports ${targetIds.join(", ") || link.target || "target"}`);
    } else if (warrantIds.includes(nodeId)) {
      items.push(`${link.id}: warrant for ${targetIds.join(", ") || link.target || "target"}`);
    } else if (link.id === nodeId) {
      items.push(`${premiseIds.join(", ") || "premise"} -> ${targetIds.join(", ") || link.target || "target"}`);
      if (warrantIds.length) items.push(`warrant: ${warrantIds.join(", ")}`);
    }
  });
  return uniqueStrings(items);
}

function graphLimitationItems(model, nodeId) {
  const items = [];
  model.reasoningLinks.forEach((link) => {
    const targetIds = splitGraphIds(link.target);
    const limitationIds = splitGraphIds(link.limitations);
    if (targetIds.includes(nodeId) || link.id === nodeId || limitationIds.includes(nodeId)) {
      limitationIds.forEach((id) => items.push(`${link.id}: ${id}`));
    }
  });
  return uniqueStrings(items);
}

function paperSourcesForGraphNode(model, node) {
  const paths = [];
  if (node.sourcePath) paths.push(node.sourcePath);
  collectPaperPaths(node.payload?.source_refs, paths);
  collectPaperPaths(node.payload?.sourceRefs, paths);
  model.translationLinks.forEach((link) => {
    if (splitGraphIds(link.project_node).includes(node.id) || link.id === node.id) collectPaperPaths(link.input, paths);
  });
  model.deltas.forEach((delta) => {
    if (splitGraphIds(delta.affected).includes(node.id) || delta.id === node.id) collectPaperPaths(delta.source_dossier, paths);
  });
  return uniqueStrings(paths.filter(Boolean));
}

function collectPaperPaths(value, paths) {
  const values = Array.isArray(value) ? value : [value];
  values.forEach((item) => {
    const path = paperPathFromText(item || "");
    if (path) paths.push(path);
  });
}

function pendingDeltasForGraphNode(model, nodeId) {
  return model.deltas.filter((delta) => isOpenDelta(delta) && splitGraphIds(delta.affected).includes(nodeId));
}

function uniqueStrings(values) {
  return [...new Set(values.filter(Boolean))];
}

function displayStudioNodeId(id) {
  const value = String(id || "");
  if (!value.startsWith("paper:")) return value;
  const title = paperTitleFromPath(value.slice("paper:".length));
  const firstToken = title.split(/\s+/).find(Boolean) || "paper";
  return `PAPER:${firstToken}`;
}

function graphStudioSelectedNode(model) {
  const preferred = state.selectedGraphNodeId && model.nodeById.get(state.selectedGraphNodeId);
  return preferred || model.nodeById.get("C0") || model.nodes.find((node) => node.kind === "claim") || model.nodes[0] || null;
}

function graphConnectionsForNode(model, nodeId) {
  return model.edges.filter((edge) => edge.source === nodeId || edge.target === nodeId);
}

function graphFocusClaimIdsForNode(model, nodeId) {
  const node = model.nodeById.get(nodeId);
  const focusClaimIds = new Set();
  if (!node) return focusClaimIds;
  if (node.kind === "claim") {
    focusClaimIds.add(node.id);
    return focusClaimIds;
  }
  graphConnectionsForNode(model, nodeId).forEach((edge) => {
    if (edge.claimId && model.nodeById.get(edge.claimId)?.kind === "claim") focusClaimIds.add(edge.claimId);
    const source = model.nodeById.get(edge.source);
    const target = model.nodeById.get(edge.target);
    if (source?.kind === "claim") focusClaimIds.add(source.id);
    if (target?.kind === "claim") focusClaimIds.add(target.id);
  });
  return focusClaimIds;
}

function graphFocusEdgesForNode(model, nodeId) {
  const node = model.nodeById.get(nodeId);
  const directEdges = graphConnectionsForNode(model, nodeId)
    .filter((edge) => node?.kind !== "claim" || edge.claimId === node.id);
  const focusClaimIds = graphFocusClaimIdsForNode(model, nodeId);
  const directEdgeIds = new Set(directEdges.map((edge) => edge.id));
  const focusEdges = model.edges.filter((edge) => directEdgeIds.has(edge.id) || focusClaimIds.has(edge.claimId));
  return { focusEdges, directEdges, focusClaimIds };
}

function graphKindDisplay(kind) {
  return {
    question: "Question",
    claim: "Claim",
    evidence: "Evidence",
    warrant: "Warrant",
    limitation: "Limitation",
    "reasoning-link": "Reasoning Link",
    "translation-link": "Translation Link",
    delta: "Graph Delta",
    "paper-source": "Paper Dossier",
  }[kind] || kind;
}

function renderPaperGraphDrilldown(graph) {
  return `
    <section class="paper-drilldown" id="paper-drilldown" aria-label="Paper Drilldown">
      <div
        class="paper-contribution-react-root"
        data-paper-contribution-react-root
        aria-label="Paper Argument -> Project Impact"
      >
        ${renderPaperContributionFallback(graph)}
      </div>
    </section>
  `;
}

function renderPaperContributionFallback(graph) {
  if (!graph) {
    return `
      <div class="paper-drilldown-empty">
        Select a claim paper source to inspect Paper Argument -> Project Impact.
      </div>
    `;
  }
  return `
    <div class="paper-drilldown-empty">
      Preparing ${escapeHtml(graph.title || graph.paper || "paper graph")} paper contribution.
    </div>
  `;
}

function renderPaperTranslationRows(translations) {
  return translations.map((item) => `
    <article class="paper-link-row">
      <strong>${escapeHtml(item.id)}</strong>
      <span>${escapeHtml((item.paper_nodes || []).join(", "))} -> ${escapeHtml((item.project_nodes || []).join(", "))}</span>
      <em>${escapeHtml(graphRelationLabel(item.relation))}</em>
    </article>
  `).join("") || `<div class="empty-state">No translations extracted.</div>`;
}

function renderPaperDeltaRows(deltas) {
  return deltas.map((item) => `
    <article class="paper-link-row paper-delta-row">
      <strong>${escapeHtml(item.id)}</strong>
      <span>${escapeHtml((item.source_paper_nodes || []).join(", "))} => ${escapeHtml((item.affected || []).join(", "))}</span>
      <em>${escapeHtml(item.status || "delta")}</em>
    </article>
  `).join("") || `<div class="empty-state">No proposed deltas.</div>`;
}

function renderPaperMiniLane(kind, nodes) {
  const labels = {
    "paper-question": "P-Q",
    "paper-claim": "P-C",
    "paper-evidence": "P-E",
    "paper-warrant": "P-W",
    "paper-limitation": "P-L",
  };
  const targetKind = kind.replace(/^paper-/, "");
  const items = nodes.filter((node) => {
    const nodeKind = normalizeGraphKind(node.kind);
    return nodeKind === kind || nodeKind === targetKind;
  });
  return `
    <div class="paper-mini-lane" data-paper-node-kind="${escapeAttr(kind)}">
      <h4>${escapeHtml(labels[kind] || kind)}</h4>
      ${items.map((node) => `
        <article class="paper-mini-node">
          <strong>${escapeHtml(node.id)}</strong>
          <span>${escapeHtml(truncateText(node.label, 110))}</span>
        </article>
      `).join("") || `<p>None</p>`}
    </div>
  `;
}

function wireHumanGatePanel() {
  document.querySelectorAll("[data-delta-id]").forEach((button) => {
    if (button.dataset.deltaWired === "1") return;
    button.dataset.deltaWired = "1";
    button.addEventListener("click", () => {
      const deltaId = button.dataset.deltaId || "";
      if (!deltaId) return;
      state.selectedGraphDeltaId = deltaId;
      rerenderHumanGatePanel();
    });
  });
}

function rerenderHumanGatePanel() {
  const panel = document.getElementById("human-gate-panel");
  if (!panel) return;
  panel.outerHTML = renderHumanGatePanel(state.graphMaintenance);
  wireHumanGatePanel();
}

function graphDeltaById(deltaId) {
  const openDeltas = Array.isArray(state.graphMaintenance?.open_deltas) ? state.graphMaintenance.open_deltas : [];
  return openDeltas.find((delta) => graphDeltaId(delta) === deltaId) || null;
}

function wireGraphStudio(graph) {
  if (!graph) return;
  const model = buildGraphStudioModel(graph);
  if (mountProjectGraphReactIsland(model)) {
    mountPaperContributionReactIsland(null);
    wirePaperGraphButtons();
    return;
  }
  document.querySelectorAll("[data-studio-node-id]").forEach((node) => {
    node.addEventListener("click", () => selectGraphStudioNode(node.dataset.studioNodeId || "", model));
    node.addEventListener("mouseenter", () => previewGraphStudioNode(node.dataset.studioNodeId || "", model));
    node.addEventListener("mouseleave", () => clearGraphStudioPreview(model));
    node.addEventListener("focus", () => previewGraphStudioNode(node.dataset.studioNodeId || "", model));
    node.addEventListener("blur", () => clearGraphStudioPreview(model));
  });
  wireGraphZoomControls(model);
  wireGraphWheelZoom(model);
  wireGraphDragPan();
  mountPaperContributionReactIsland(null);
  wirePaperGraphButtons();
  state.selectedGraphNodeId ? selectGraphStudioNode(state.selectedGraphNodeId, model) : applyGraphFocusState(model, "", { clear: true });
}

function wireGraphZoomControls(model) {
  document.querySelectorAll("[data-zoom-command]").forEach((button) => {
    button.addEventListener("click", () => {
      const command = button.dataset.zoomCommand || "";
      if (command === "in") setGraphZoom(state.graphZoom + 0.12, model);
      if (command === "out") setGraphZoom(state.graphZoom - 0.12, model);
      if (command === "reset") setGraphZoom(1, model);
      if (command === "fit") fitGraphZoom(model);
    });
  });
}

function setGraphZoom(value, model) {
  setGraphZoomAtPoint(value, model);
}

function setGraphZoomAtPoint(value, model, point = null) {
  const nextZoom = clampGraphZoom(value);
  const atlas = document.querySelector(".claim-atlas");
  const board = document.querySelector(".claim-atlas-board");
  const zoomSpace = document.querySelector(".claim-atlas-zoom-space");
  const valueLabel = document.querySelector("[data-graph-zoom-value]");
  if (atlas) cancelGraphPanMomentum(atlas);
  const previousZoom = graphZoomValue();
  const rect = atlas ? atlas.getBoundingClientRect() : null;
  const localX = atlas && point ? point.clientX - rect.left : atlas?.clientWidth / 2 || 0;
  const localY = atlas && point ? point.clientY - rect.top : atlas?.clientHeight / 2 || 0;
  const anchorX = atlas ? (atlas.scrollLeft + localX) / previousZoom : 0;
  const anchorY = atlas ? (atlas.scrollTop + localY) / previousZoom : 0;
  state.graphZoom = nextZoom;
  if (atlas) atlas.dataset.graphZoom = nextZoom.toFixed(2);
  if (board) board.style.setProperty("--graph-zoom", nextZoom.toFixed(2));
  if (zoomSpace && model) {
    zoomSpace.style.width = `${Math.ceil(model.width * nextZoom)}px`;
    zoomSpace.style.height = `${Math.ceil(model.height * nextZoom)}px`;
  }
  if (valueLabel) valueLabel.textContent = `${Math.round(nextZoom * 100)}%`;
  if (atlas) {
    atlas.scrollLeft = Math.max(0, anchorX * nextZoom - localX);
    atlas.scrollTop = Math.max(0, anchorY * nextZoom - localY);
  }
}

function wireGraphWheelZoom(model) {
  const atlas = document.querySelector(".claim-atlas");
  if (!atlas) return;
  atlas.addEventListener("wheel", (event) => {
    if (!event.ctrlKey) return;
    cancelGraphPanMomentum(atlas);
    event.preventDefault();
    const factor = Math.exp(-event.deltaY * 0.0024);
    setGraphZoomAtPoint(graphZoomValue() * factor, model, event);
  }, { passive: false });
}

function cancelGraphPanMomentum(atlas) {
  if (graphPanMomentumFrame) cancelAnimationFrame(graphPanMomentumFrame);
  graphPanMomentumFrame = 0;
  if (atlas) atlas.classList.remove("is-pan-inertia");
}

function startGraphPanMomentum(atlas, velocityX, velocityY) {
  cancelGraphPanMomentum(atlas);
  let vx = Math.max(-GRAPH_PAN_MAX_VELOCITY, Math.min(GRAPH_PAN_MAX_VELOCITY, velocityX));
  let vy = Math.max(-GRAPH_PAN_MAX_VELOCITY, Math.min(GRAPH_PAN_MAX_VELOCITY, velocityY));
  if (Math.hypot(vx, vy) < GRAPH_PAN_MIN_VELOCITY) return;
  atlas.classList.add("is-pan-inertia");
  const stepMomentum = () => {
    const beforeLeft = atlas.scrollLeft;
    const beforeTop = atlas.scrollTop;
    atlas.scrollLeft -= vx;
    atlas.scrollTop -= vy;
    if (atlas.scrollLeft === beforeLeft) vx = 0;
    if (atlas.scrollTop === beforeTop) vy = 0;
    vx *= GRAPH_PAN_INERTIA_DECAY;
    vy *= GRAPH_PAN_INERTIA_DECAY;
    if (Math.hypot(vx, vy) > GRAPH_PAN_MIN_VELOCITY) {
      graphPanMomentumFrame = requestAnimationFrame(stepMomentum);
      return;
    }
    cancelGraphPanMomentum(atlas);
  };
  graphPanMomentumFrame = requestAnimationFrame(stepMomentum);
}

function wireGraphDragPan() {
  const atlas = document.querySelector(".claim-atlas");
  if (!atlas) return;
  let panState = null;
  let suppressClick = false;
  const stopPan = () => {
    panState = null;
    atlas.classList.remove("is-panning");
  };
  atlas.addEventListener("pointerdown", (event) => {
    if (window.PointerEvent && !(event instanceof PointerEvent)) return;
    if (event.button !== 0) return;
    const control = event.target.closest("a, input, select, textarea, [data-zoom-command]");
    const nonNodeButton = event.target.closest("button:not(.claim-atlas-node)");
    if (control || nonNodeButton) return;
    cancelGraphPanMomentum(atlas);
    panState = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      lastX: event.clientX,
      lastY: event.clientY,
      lastTime: performance.now(),
      scrollLeft: atlas.scrollLeft,
      scrollTop: atlas.scrollTop,
      velocityX: 0,
      velocityY: 0,
      dragStarted: false,
    };
  });
  atlas.addEventListener("pointermove", (event) => {
    if (!panState || event.pointerId !== panState.pointerId) return;
    const dx = event.clientX - panState.startX;
    const dy = event.clientY - panState.startY;
    if (!panState.dragStarted && Math.hypot(dx, dy) < GRAPH_PAN_DRAG_THRESHOLD) return;
    if (!panState.dragStarted) {
      panState.dragStarted = true;
      atlas.classList.add("is-panning");
      atlas.setPointerCapture(event.pointerId);
    }
    const now = performance.now();
    const dt = Math.max(8, now - panState.lastTime);
    const frameVelocityX = ((event.clientX - panState.lastX) / dt) * 16;
    const frameVelocityY = ((event.clientY - panState.lastY) / dt) * 16;
    panState.velocityX = panState.velocityX * 0.35 + frameVelocityX * 0.65;
    panState.velocityY = panState.velocityY * 0.35 + frameVelocityY * 0.65;
    panState.lastX = event.clientX;
    panState.lastY = event.clientY;
    panState.lastTime = now;
    atlas.scrollLeft = panState.scrollLeft - dx;
    atlas.scrollTop = panState.scrollTop - dy;
    event.preventDefault();
  });
  atlas.addEventListener("pointerup", (event) => {
    if (!panState || event.pointerId !== panState.pointerId) return;
    const wasDragging = panState.dragStarted;
    const velocityX = panState.velocityX;
    const velocityY = panState.velocityY;
    stopPan();
    if (wasDragging) {
      suppressClick = true;
      window.setTimeout(() => { suppressClick = false; }, 120);
      startGraphPanMomentum(atlas, velocityX, velocityY);
    }
  });
  atlas.addEventListener("click", (event) => {
    if (!suppressClick) return;
    suppressClick = false;
    event.preventDefault();
    event.stopPropagation();
  }, true);
  atlas.addEventListener("pointercancel", () => {
    cancelGraphPanMomentum(atlas);
    stopPan();
  });
  atlas.addEventListener("lostpointercapture", stopPan);
}

function fitGraphZoom(model) {
  const atlas = document.querySelector(".claim-atlas");
  if (!atlas || !model) return;
  const widthZoom = (atlas.clientWidth - 28) / model.width;
  const heightZoom = (atlas.clientHeight - 28) / model.height;
  setGraphZoom(Math.min(widthZoom, heightZoom, 1), model);
}

function selectGraphStudioNode(nodeId, model) {
  const selectedNode = model.nodeById.get(nodeId) || graphStudioSelectedNode(model);
  if (!selectedNode) return;
  state.selectedGraphNodeId = selectedNode.id;
  applyGraphFocusState(model, selectedNode.id);
  const detail = document.getElementById("selected-claim-detail");
  if (detail && selectedNode.kind === "claim") {
    detail.outerHTML = renderSelectedClaimDetail(model, buildProjectArgumentMap(model));
    wireArgumentDetailEvents(model);
  }
  const inspector = document.getElementById("graph-inspector");
  if (inspector) {
    inspector.innerHTML = renderGraphInspectorBody(model);
    inspector.querySelectorAll("[data-studio-node-id]").forEach((button) => {
      button.addEventListener("click", () => selectGraphStudioNode(button.dataset.studioNodeId || "", model));
    });
  }
  wirePaperGraphButtons();
}

function wireArgumentDetailEvents(model) {
  const detail = document.getElementById("selected-claim-detail");
  if (!detail) return;
  detail.querySelectorAll("[data-studio-node-id]").forEach((node) => {
    node.addEventListener("click", () => selectGraphStudioNode(node.dataset.studioNodeId || "", model));
    node.addEventListener("mouseenter", () => previewGraphStudioNode(node.dataset.studioNodeId || "", model));
    node.addEventListener("mouseleave", () => clearGraphStudioPreview(model));
    node.addEventListener("focus", () => previewGraphStudioNode(node.dataset.studioNodeId || "", model));
    node.addEventListener("blur", () => clearGraphStudioPreview(model));
  });
  wirePaperGraphButtons();
}

function previewGraphStudioNode(nodeId, model) {
  if (!nodeId) return;
  applyGraphFocusState(model, nodeId, { preview: true });
}

function clearGraphStudioPreview(model) {
  const fallbackId = state.selectedGraphNodeId || "";
  if (fallbackId) {
    applyGraphFocusState(model, fallbackId);
    return;
  }
  applyGraphFocusState(model, "", { clear: true });
}

function applyGraphFocusState(model, nodeId, options = {}) {
  const selectedNode = model.nodeById.get(nodeId);
  const focus = selectedNode && !options.clear ? graphFocusEdgesForNode(model, selectedNode.id) : {
    focusEdges: [],
    directEdges: [],
    focusClaimIds: new Set(),
  };
  const focusEdgeIds = new Set(focus.focusEdges.map((edge) => edge.id));
  const directEdgeIds = new Set(focus.directEdges.map((edge) => edge.id));
  const neighborIds = new Set(selectedNode ? [selectedNode.id] : []);
  focus.focusEdges.forEach((edge) => {
    neighborIds.add(edge.source);
    neighborIds.add(edge.target);
  });
  focus.focusClaimIds.forEach((claimId) => neighborIds.add(claimId));
  document.querySelectorAll(".claim-atlas-node").forEach((node) => {
    const id = node.dataset.studioNodeId || "";
    node.classList.toggle("is-selected", Boolean(selectedNode) && id === selectedNode.id);
    node.classList.toggle("is-preview", Boolean(options.preview) && id === selectedNode?.id);
    node.classList.toggle("is-neighbor", Boolean(selectedNode) && id !== selectedNode.id && neighborIds.has(id));
    node.classList.toggle("is-dimmed", Boolean(selectedNode) && !neighborIds.has(id));
  });
  document.querySelectorAll(".argument-claim-region").forEach((region) => {
    const claimId = region.dataset.argumentClaimId || "";
    const active = Boolean(selectedNode) && focus.focusClaimIds.has(claimId);
    region.classList.toggle("is-selected", active && selectedNode?.id === claimId);
    region.classList.toggle("is-neighbor", active && selectedNode?.id !== claimId);
    region.classList.toggle("is-dimmed", Boolean(selectedNode) && !active);
  });
  document.querySelectorAll("[data-argument-node-id]").forEach((node) => {
    const id = node.dataset.argumentNodeId || "";
    node.classList.toggle("is-selected", Boolean(selectedNode) && id === selectedNode.id);
    node.classList.toggle("is-neighbor", Boolean(selectedNode) && id !== selectedNode.id && neighborIds.has(id));
    node.classList.toggle("is-dimmed", Boolean(selectedNode) && !neighborIds.has(id));
  });
  document.querySelectorAll(".argument-claim-edge").forEach((edge) => {
    const sourceId = edge.dataset.sourceId || "";
    const targetId = edge.dataset.targetId || "";
    const direct = Boolean(selectedNode) && (sourceId === selectedNode.id || targetId === selectedNode.id);
    const active = Boolean(selectedNode) && neighborIds.has(sourceId) && neighborIds.has(targetId);
    edge.classList.toggle("is-selected", direct);
    edge.classList.toggle("is-neighbor", active && !direct);
    edge.classList.toggle("is-dimmed", Boolean(selectedNode) && !active);
  });
  document.querySelectorAll(".graph-edge, .graph-arrow-head").forEach((edge) => {
    const edgeId = edge.dataset.graphEdgeId || "";
    const active = focusEdgeIds.has(edgeId);
    const direct = directEdgeIds.has(edgeId);
    const claimFocus = edge.dataset.claimId && focus.focusClaimIds.has(edge.dataset.claimId);
    edge.classList.toggle("is-selected", active);
    edge.classList.toggle("is-path-focus", direct);
    edge.classList.toggle("is-cluster-focus", active && !direct && claimFocus);
    edge.classList.toggle("is-background", Boolean(selectedNode) && !active);
    edge.classList.toggle("is-dimmed", Boolean(selectedNode) && !active);
  });
  document.querySelectorAll(".claim-cluster-hull").forEach((cluster) => {
    const claimId = cluster.dataset.clusterClaim || "";
    cluster.classList.toggle("is-selected", Boolean(selectedNode) && focus.focusClaimIds.has(claimId));
    cluster.classList.toggle("is-neighbor", Boolean(selectedNode) && claimId !== selectedNode.id && neighborIds.has(claimId));
  });
}

async function openPaperGraphDrilldown(path) {
  const graphPath = normalizePaperDossierPath(path);
  if (!graphPath) return;
  const panel = document.getElementById("paper-drilldown");
  if (panel) panel.innerHTML = `<div class="paper-drilldown-empty">Loading ${escapeHtml(graphPath)}...</div>`;
  const graph = await loadPaperGraphFromApi(graphPath);
  state.activePaperGraphPath = graphPath;
  document.querySelectorAll("[data-paper-graph-path]").forEach((item) => {
    item.classList.toggle("is-active-paper", normalizePaperDossierPath(item.dataset.paperGraphPath) === state.activePaperGraphPath);
  });
  const nextPanel = document.getElementById("paper-drilldown");
  if (nextPanel) nextPanel.outerHTML = renderPaperGraphDrilldown(graph);
}

function wirePaperGraphButtons() {
  document.querySelectorAll("[data-paper-graph-path]").forEach((button) => {
    if (button.dataset.paperGraphWired === "1") return;
    button.dataset.paperGraphWired = "1";
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      openPaperGraphDrilldown(button.dataset.paperGraphPath || "");
    });
  });
}

function projectStatusLine(project, round) {
  const gate = project.card?.gate_progress || {};
  const waiting = Number(gate.candidate || 0) + Number(gate.reading || 0);
  if (!round) return "No search record";
  return `${waiting} pending · ${Number(gate.summarized || 0)} summarized`;
}

function searchStatusTitle(project, round) {
  if (!round) return "Search not started";
  const gate = project.card?.gate_progress || {};
  const waiting = Number(gate.candidate || 0) + Number(gate.reading || 0);
  return waiting ? `${waiting} papers are pending` : "No pending papers";
}

function searchStatusSummary(project, round) {
  if (!round) return "Project has no search record yet. Next step should be paper discovery.";
  const gate = project.card?.gate_progress || {};
  const total = Object.values(gate).reduce((sum, value) => sum + Number(value || 0), 0);
  return `Papers contains ${total || round.paper_count || 0} relevant papers. Dashboard shows status, deep-read memos, and provenance only; decisions stay in agent chat or CLI.`;
}

function paperRank(paper) {
  const status = normalizeToken(paper.review_status);
  if (status === "approved") return 0;
  if (status === "summarized") return 1;
  if (status === "reading") return 2;
  return 3;
}

function renderPaperSummaryRows(items, projectId, roundName = "") {
  if (!items.length) return `<div class="empty-state">Paper not found.</div>`;
  return `
    <div class="table-scroll">
      <table class="paper-summary-table project-core-table">
        <thead>
          <tr>
            <th>Paper</th>
            <th>Compressed Judgment</th>
            <th>Status</th>
            <th>Open</th>
          </tr>
        </thead>
        <tbody>
          ${items.map((paper) => {
            const key = paperKey(paper) || candidateId(paper);
            const href = paperUrl(projectId, key, roundName);
            return `
              <tr class="clickable-row" data-row-href="${href}" tabindex="0" role="link" aria-label="OpenPaper ${escapeAttr(paper.title || "Untitled")}">
                <td>
                  <strong>${escapeHtml(paper.title || "Untitled")}</strong>
                  <span>${escapeHtml(paperPublicationLine(paper))}</span>
                </td>
                <td class="evidence-cell">${escapeHtml(paper.one_line || paper.why_relevant || "No compressed summary yet.")}</td>
                <td>${statusPill(paper.review_status || "candidate")}</td>
                <td><a class="detail-link" href="${href}">Details</a></td>
              </tr>
            `;
          }).join("")}
        </tbody>
      </table>
    </div>
  `;
}

function renderProjectPapersPage() {
  const project = projectById();
  if (!project) {
    renderEmpty("Project not found.");
    return;
  }
  renderProjectNav(project);
  const papers = allPapersForProject(project.id);
  const filters = paperFiltersFromParams();
  const visiblePapers = applyPaperFilters(papers, filters);
  setHeader("Papers", "Papers", `${displayProjectTitle(project)} · ${visiblePapers.length}/${papers.length} papers`);
  el.content.innerHTML = `
    <section class="paper-library-shell">
      <form class="paper-library-filters" data-paper-filter-form>
        <label for="paper-search-filter">
          <span>Search</span>
          <input id="paper-search-filter" name="q" value="${escapeAttr(filters.q)}" placeholder="Title, summary, project judgment" />
        </label>
        <label for="paper-status-filter">
          <span>Current Status</span>
          ${renderPaperFilterSelect("paper-status-filter", "status", filters.status, paperStatusOptions(papers), PAPER_STATE_LABELS)}
        </label>
        <label for="paper-read-filter">
          <span>Reading</span>
          ${renderPaperFilterSelect("paper-read-filter", "filter", filters.filter, paperReadFilterOptions(papers), PAPER_READ_FILTER_LABELS)}
        </label>
        <button type="submit">Filter</button>
      </form>
      ${renderPaperLibraryRows(visiblePapers, project.id)}
    </section>
  `;
  wirePaperFilters();
  wireClickableRows();
}

function allPapersForProject(projectId = state.projectId) {
  const byKey = new Map();
  const addPaper = (paper) => {
    const key = normalizeToken(paperKey(paper) || candidateId(paper));
    if (!key) return;
    byKey.set(key, mergePaperRecords(byKey.get(key) || {}, paper));
  };
  (state.data?.round_candidates || [])
    .filter((candidate) => candidate.project === projectId)
    .map((candidate) => enrichCandidate(candidate))
    .forEach(addPaper);
  papersForProject(projectId).forEach(addPaper);
  return Array.from(byKey.values())
    .sort((a, b) => paperRank(a) - paperRank(b) || String(a.title || "").localeCompare(String(b.title || "")));
}

function mergePaperRecords(base, next) {
  const merged = { ...base };
  Object.entries(next || {}).forEach(([key, value]) => {
    if (hasPaperValue(value) || !hasPaperValue(merged[key])) {
      merged[key] = value;
    }
  });
  return merged;
}

function hasPaperValue(value) {
  if (Array.isArray(value)) return value.length > 0;
  return value !== undefined && value !== null && String(value).trim() !== "";
}

function paperFiltersFromParams() {
  const query = params();
  return {
    q: query.get("q") || "",
    status: query.get("status") || "",
    filter: query.get("filter") || "",
  };
}

function applyPaperFilters(papers, filters) {
  const q = normalizeToken(filters.q);
  const readFilter = normalizeToken(filters.filter);
  return papers.filter((paper) => {
    const state = paperCurrentState(paper);
    const haystack = normalizeToken([
      paper.title,
      paper.one_line,
      paper.why_relevant,
      paper.literature_round,
      paper.round,
    ].join(" "));
    return (!filters.status || state.key === normalizeToken(filters.status))
      && (!readFilter || (readFilter === "deep-read" && isDeepReadPaper(paper)))
      && (!q || haystack.includes(q));
  });
}

function isDeepReadPaper(paper) {
  return paper.read_level === "full-text"
    || ["reading", "summarized", "approved"].includes(normalizeToken(paper.review_status))
    || Boolean(paper.path || paper.memo_path);
}

function renderPaperLibraryRows(items, projectId) {
  if (!items.length) return `<div class="empty-state">No papers match the current filter.</div>`;
  return `
    <div class="table-scroll paper-library-scroll">
      <table class="paper-library-table paper-review-table">
        <thead>
          <tr>
            <th>Paper</th>
            <th>Compressed Judgment</th>
            <th>Current Status</th>
          </tr>
        </thead>
        <tbody>
          ${items.map((paper) => {
            const key = paperKey(paper) || candidateId(paper);
            const state = paperCurrentState(paper);
            const href = paperUrl(projectId, key, paper.round || paper.literature_round || "");
            return `
              <tr class="clickable-row" data-row-href="${escapeAttr(href)}" tabindex="0" role="link" aria-label="OpenPaper ${escapeAttr(paper.title || "Untitled")}">
                <td>
                  <strong>${escapeHtml(paper.title || "Untitled")}</strong>
                  <span>${escapeHtml(paperPublicationLine(paper))}</span>
                </td>
                <td class="evidence-cell">
                  <p>${escapeHtml(paper.one_line || paper.why_relevant || "No compressed summary yet.")}</p>
                </td>
                <td class="state-cell"><span class="paper-state paper-state-${escapeAttr(state.key)}">${escapeHtml(state.label)}</span></td>
              </tr>
            `;
          }).join("")}
        </tbody>
      </table>
    </div>
  `;
}

function paperPublicationLine(paper) {
  const year = paper?.year || "Year unknown";
  const venue = String(paper?.venue || "").trim() || "arXiv";
  return `${year} · ${venue}`;
}

function renderPaperFilterSelect(id, name, currentValue, options, labels) {
  return `
    <select id="${escapeAttr(id)}" name="${escapeAttr(name)}">
      <option value="">All</option>
      ${options.map((value) => `
        <option value="${escapeAttr(value)}"${normalizeToken(currentValue) === normalizeToken(value) ? " selected" : ""}>${escapeHtml(labels[normalizeToken(value)] || value)}</option>
      `).join("")}
    </select>
  `;
}

function paperStatusOptions(papers) {
  const present = new Set(papers.map((paper) => paperCurrentState(paper).key).filter(Boolean));
  ["approved", "project-core"].forEach((status) => present.add(status));
  return PAPER_STATE_ORDER.filter((status) => present.has(status));
}

function paperReadFilterOptions(papers) {
  return papers.some((paper) => isDeepReadPaper(paper)) ? ["deep-read"] : [];
}

function wirePaperFilters() {
  document.querySelectorAll("[data-paper-filter-form]").forEach((form) => {
    const submitFilters = (event) => {
      event.preventDefault();
      const formData = new FormData(form);
      const next = new URLSearchParams({ project: state.projectId });
      ["q", "status", "filter"].forEach((key) => {
        const value = String(formData.get(key) || "").trim();
        if (value) next.set(key, value);
      });
      window.location.href = papersUrl(state.projectId, {
        q: next.get("q") || "",
        status: next.get("status") || "",
        filter: next.get("filter") || "",
      });
    };
    form.addEventListener("submit", submitFilters);
    form.querySelectorAll("select").forEach((select) => {
      select.addEventListener("change", () => form.requestSubmit());
    });
  });
}

function wireClickableRows() {
  document.querySelectorAll("[data-row-href]").forEach((row) => {
    const navigate = (event) => {
      if (event.target.closest("a, button, input, select, summary")) return;
      const href = row.dataset.rowHref || "";
      if (!href) return;
      if (event.metaKey || event.ctrlKey) {
        window.open(href, "_blank", "noopener");
        return;
      }
      window.location.href = href;
    };
    row.addEventListener("click", navigate);
    row.addEventListener("keydown", (event) => {
      if (event.key !== "Enter" && event.key !== " ") return;
      event.preventDefault();
      navigate(event);
    });
  });
}

function renderRoundReviewPage() {
  const project = projectById();
  const round = roundByName();
  if (!project || !round) {
    renderEmpty("Round not found.");
    return;
  }
  renderProjectNav(project);
  state.roundId = round.name;
  const candidates = candidatesForRound(project.id, round.name);
  if (!candidates.some((candidate) => paperKey(candidate) === state.focusedCandidateKey)) {
    state.focusedCandidateKey = paperKey(candidates[0] || {}) || "";
  }
  setHeader("Round Review", round.name, `${displayProjectTitle(project)} · ${candidates.length} candidate papers. Dashboard is a read-only viewer.`);
  el.content.innerHTML = `
    <section class="round-review-grid">
      <div class="review-main">
        <div class="section-head">
          <div>
            <p class="eyebrow">Read-only</p>
            <h2>Search Results</h2>
          </div>
          <span>${candidates.length} papers</span>
        </div>
        <div class="table-scroll round-review-scroll">
        <table class="paper-review-table round-review-table">
          <thead>
            <tr>
              <th>Paper</th>
              <th>Compressed Judgment</th>
              <th>Status</th>
              <th>Agent</th>
            </tr>
          </thead>
          <tbody>
            ${candidates.map((candidate) => renderCandidateReviewRow(candidate, project.id, round.name)).join("")}
          </tbody>
        </table>
        </div>
      </div>
      <aside class="decision-side">
        ${renderFocusedCandidatePanel(candidates, project.id, round.name)}
      </aside>
    </section>
  `;
  wireReviewRowFocus();
}

function renderCandidateReviewRow(candidate, projectId, roundName) {
  const key = paperKey(candidate) || candidate.zotero_key || candidateId(candidate);
  const focused = key === state.focusedCandidateKey;
  const href = paperUrl(projectId, key, roundName);
  return `
    <tr class="review-row ${focused ? "is-focused" : ""}" data-candidate-id="${escapeAttr(candidateId(candidate))}" data-focus-key="${escapeAttr(key)}" data-row-href="${href}" tabindex="0" aria-selected="${focused ? "true" : "false"}">
      <td>
        <strong><a href="${href}">${escapeHtml(candidate.title || "Untitled")}</a></strong>
        <span>${escapeHtml(paperPublicationLine(candidate))}</span>
        <span class="paper-provenance-line provenance-code">zotero ${escapeHtml(candidate.zotero || candidate.zotero_key || "none")} · round ${escapeHtml(roundName || candidate.round || "unknown")} · memo ${escapeHtml(candidate.memo_path || "none")}</span>
      </td>
      <td class="evidence-cell">
        <p>${escapeHtml(candidate.one_line || "No compressed summary yet.")}</p>
        <small>${escapeHtml(candidate.why_relevant || "No relevance note yet.")}</small>
      </td>
      <td>${statusPill(candidate.review_status || "candidate")}</td>
      <td>
        ${renderAgentCommandHint(`review paper ${key}`)}
      </td>
    </tr>
  `;
}

function renderFocusedCandidatePanel(candidates, projectId, roundName) {
  const candidate = candidates.find((item) => paperKey(item) === state.focusedCandidateKey) || candidates[0] || null;
  if (!candidate) {
    return `<section class="focus-preview"><p class="eyebrow">Current Paper</p><p>No paper selected.</p></section>`;
  }
  const key = paperKey(candidate) || candidate.zotero_key || candidateId(candidate);
  return `
    <section class="focus-preview issue-panel" aria-label="Current Paper">
      <p class="eyebrow">Current Paper</p>
      <h2>${escapeHtml(candidate.title || "Untitled")}</h2>
      <p class="focus-summary">${escapeHtml(candidate.one_line || "No compressed summary yet.")}</p>
      <p class="focus-relevance">${escapeHtml(candidate.why_relevant || "No relevance note yet.")}</p>
      <p class="paper-provenance-line provenance-code">zotero ${escapeHtml(candidate.zotero || candidate.zotero_key || "none")} · round ${escapeHtml(roundName || candidate.round || "unknown")} · memo ${escapeHtml(candidate.memo_path || "none")}</p>
      <dl class="focus-facts">
        <div><dt>Status</dt><dd>${statusPill(candidate.review_status || "candidate")}</dd></div>
        <div><dt>Zotero</dt><dd class="provenance-code">${escapeHtml(candidate.zotero || candidate.zotero_key || "none")}</dd></div>
        <div><dt>Round</dt><dd class="provenance-code">${escapeHtml(roundName || candidate.round || "unknown")}</dd></div>
        <div><dt>Memo</dt><dd class="provenance-code">${escapeHtml(candidate.memo_path || "none")}</dd></div>
      </dl>
      ${renderAgentCommandHint(`review paper ${key}`)}
      <a class="secondary-action detail-link" href="${escapeAttr(paperUrl(projectId, key, roundName))}">Open detailed memo</a>
    </section>
  `;
}

async function renderPaperDetailPage() {
  const project = projectById();
  if (!project) {
    renderEmpty("Project not found.");
    return;
  }
  renderProjectNav(project);
  const paper = resolveCurrentPaper(project.id);
  if (!paper) {
    renderEmpty("Paper not found.");
    return;
  }
  const roundName = state.roundId || paper.literature_round || "";
  setPaperDetailHeader(project, paper);
  el.content.innerHTML = renderPaperDetailShell(paper, project.id, roundName, "Loading detailed memo...");
  const memoPath = paper.path || paper.memo_path || "";
  if (memoPath) {
    const memo = await fetchMemoContent(memoPath);
    const sections = parseMemoSections(memo.content || "");
    const memoTarget = document.getElementById("memo-content");
    const mapTarget = document.getElementById("insight-map");
    if (memoTarget) memoTarget.innerHTML = renderStructuredMemo(sections, paper, project.id);
    if (mapTarget) mapTarget.innerHTML = renderPaperInsightMap(paper, sections);
  }
}

function resolveCurrentPaper(projectId) {
  const key = state.paperId;
  return paperByKey(key)
    || candidatesForRound(projectId, state.roundId).find((candidate) => normalizeToken(candidateId(candidate)) === normalizeToken(key) || normalizeToken(paperKey(candidate)) === normalizeToken(key))
    || papersForProject(projectId)[0]
    || null;
}

function renderPaperDetailShell(paper, projectId, roundName, memoPlaceholder) {
  const key = paperKey(paper) || candidateId(paper);
  return `
    <section class="paper-decision-shell">
      <section class="paper-readonly-strip" aria-label="PaperStatus">
        ${renderPaperReadOnlyStatusPanel(paper)}
        ${renderAgentCommandHint(`review paper ${key}`)}
      </section>
      <section class="paper-detail-flow">
        <article class="paper-brief project-fit-panel">
          <p class="eyebrow">Project Fit Brief</p>
          <div class="fit-summary-grid">
            <section>
              <h3>Why this matters</h3>
              <p>${escapeHtml(paper.why_relevant || "No project relevance note yet.")}</p>
            </section>
            <section>
              <h3>What to learn</h3>
              <ul>${(paper.key_claims || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("") || "<li>No claims extracted yet.</li>"}</ul>
            </section>
            <section>
              <h3>What not to overlearn</h3>
              <ul>${(paper.limitations || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("") || "<li>No limitations listed yet.</li>"}</ul>
            </section>
          </div>
        </article>
        <article class="visual-panel">
          <p class="eyebrow">Visual Understanding</p>
          <div id="insight-map">${renderPaperInsightMap(paper, [])}</div>
        </article>
        <article class="memo-panel deep-read-panel">
          <p class="eyebrow">Core Contribution</p>
          <div id="memo-content" class="memo-document structured-memo">${escapeHtml(memoPlaceholder)}</div>
        </article>
      </section>
      ${renderProvenanceDisclosure(paper, roundName)}
    </section>
  `;
}

function renderPaperReadOnlyStatusPanel(paper) {
  const stateInfo = paperCurrentState(paper);
  return `
    <section class="paper-readonly-status" aria-label="Read-only paper state">
      <p class="eyebrow">Read-only Paper State</p>
      <dl class="paper-status-grid">
        <div><dt>review_status</dt><dd>${escapeHtml(paper.review_status || "candidate")}</dd></div>
        <div><dt>current_state</dt><dd>${escapeHtml(stateInfo.label)}</dd></div>
        <div><dt>read_level</dt><dd>${escapeHtml(paper.read_level || "unknown")}</dd></div>
        <div><dt>summary_status</dt><dd>${escapeHtml(paper.summary_status || "unknown")}</dd></div>
        <div><dt>human_review</dt><dd>${escapeHtml(paper.human_review || "pending")}</dd></div>
        <div><dt>project_core_for</dt><dd>${escapeHtml((paper.project_core_for || []).join(", ") || "none")}</dd></div>
        <div><dt>global_core</dt><dd>${paper.global_core ? "true" : "false"}</dd></div>
      </dl>
    </section>
  `;
}

function renderProvenanceDisclosure(paper, roundName) {
  return `
    <details class="provenance-disclosure">
      <summary>Metadata and Sources</summary>
      <dl class="source-list">
        <div><dt>Zotero</dt><dd>${escapeHtml(paper.zotero || paper.zotero_key || "None")}</dd></div>
        <div><dt>Memo</dt><dd>${escapeHtml(paper.path || paper.memo_path || "None")}</dd></div>
        <div><dt>PDF</dt><dd>${escapeHtml(paper.pdf_status || "Unknown")}</dd></div>
        <div><dt>Rounds</dt><dd>${escapeHtml(roundName || "unknown")}</dd></div>
      </dl>
    </details>
  `;
}

function renderPaperInsightMap(paper, sections = []) {
  const generatedAsset = paperVisualizationAsset(paper);
  if (generatedAsset) {
    return `
      <figure class="generated-visual">
        <img src="${escapeAttr(generatedAsset.src)}" alt="${escapeAttr(generatedAsset.alt)}" loading="lazy" decoding="async" />
        <figcaption>${escapeHtml(generatedAsset.caption)}</figcaption>
      </figure>
    `;
  }
  const nodes = [
    ["Paper Question", sectionExcerpt(sections, ["Problem Setting", "Core Contribution"]) || paper.one_line || paper.why_relevant],
    ["Method View", sectionExcerpt(sections, ["Method", "Method mechanism"]) || "Method details are in the deep-read memo."],
    ["Evidence", sectionExcerpt(sections, ["Evidence", "Experiment logic"]) || firstListItem(paper.key_claims) || "No evidence extracted yet."],
    ["Evidence Boundary", sectionExcerpt(sections, ["Limitations", "What not to learn"]) || firstListItem(paper.limitations) || "No limitations extracted yet."],
    ["Project Consequence", sectionExcerpt(sections, ["Why It Matters", "Project Role Assessment", "Position for the target project"]) || paper.why_relevant || "No project consequence extracted yet."],
  ];
  return `
    <div class="argument-map" aria-label="PaperArgument Map">
      ${nodes.map(([label, text], index) => `
        <section class="insight-node">
          <span>${index + 1}</span>
          <h3>${escapeHtml(label)}</h3>
          <p>${escapeHtml(truncateText(text, 220))}</p>
        </section>
      `).join("")}
    </div>
  `;
}

function paperVisualizationAsset(paper) {
  const key = normalizeToken(paperKey(paper));
  const title = normalizeToken(paper?.title);
  if (key === "kiagpczh" || title.includes("beyond surface statistics: scene representations in a latent diffusion model")) {
    return {
      src: "./assets/paper-visualizations/chen2023-beyond-surface-statistics.png",
      alt: "Generated technical diagram of denoising activations, linear probes, saliency, relative depth, activation intervention, and generation changes.",
      caption: "API-generated graph：denoising activations -> saliency/depth probes -> activation intervention -> generation changes。",
    };
  }
  return null;
}

function parseMemoSections(markdown) {
  const clean = stripFrontmatter(markdown);
  const sections = [];
  let current = { title: "Memo overview", depth: 1, lines: [] };
  for (const line of clean.split(/\r?\n/)) {
    const heading = line.trim().match(/^(#{1,6})\s+(.+)$/);
    if (heading) {
      if (current.lines.join("\n").trim()) sections.push(current);
      current = {
        title: heading[2].trim(),
        depth: heading[1].length,
        lines: [],
      };
    } else {
      current.lines.push(line);
    }
  }
  if (current.lines.join("\n").trim()) sections.push(current);
  return sections.map((section) => ({
    ...section,
    markdown: section.lines.join("\n").trim(),
  }));
}

function renderStructuredMemo(sections, paper, projectId) {
  if (!sections.length) {
    return renderMemoDocument(paper.one_line || "Detailed memo unavailable.");
  }
  const preferred = [
    "Core Contribution",
    `Why It Matters For ${projectId}`,
    "Interpretive Deep Read",
    "Teaching-Grade Deep Read",
    "Evidence",
    "Claims",
    "Limitations",
    "Project Role Assessment",
    "Open Questions",
  ];
  const chosen = [];
  preferred.forEach((name) => {
    const section = findMemoSection(sections, [name]);
    if (section && !chosen.includes(section)) chosen.push(section);
  });
  sections.slice(0, 8).forEach((section) => {
    if (chosen.length < 8 && !chosen.includes(section) && !/^source identity$/i.test(section.title)) chosen.push(section);
  });
  return chosen.map((section) => `
    <section class="memo-section">
      <h3>${escapeHtml(displayMemoSectionTitle(section.title))}</h3>
      ${renderMemoDocument(section.markdown)}
    </section>
  `).join("");
}

function findMemoSection(sections, titleNeedles) {
  return sections.find((section) => titleNeedles.some((needle) => normalizeToken(section.title).includes(normalizeToken(needle))));
}

function sectionExcerpt(sections, titleNeedles) {
  const section = findMemoSection(sections, titleNeedles);
  if (!section) return "";
  return plainMemoText(section.markdown).split(/\n+/).find(Boolean) || "";
}

function plainMemoText(markdown) {
  return String(markdown || "")
    .replace(/^[-*]\s+/gm, "")
    .replace(/\*\*/g, "")
    .replace(/`/g, "")
    .trim();
}

function firstListItem(items) {
  return Array.isArray(items) && items.length ? items[0] : "";
}

function truncateText(text, limit) {
  const value = String(text || "").replace(/\s+/g, " ").trim();
  if (value.length <= limit) return value;
  return `${value.slice(0, limit - 1).trim()}...`;
}

async function fetchMemoContent(path) {
  const response = await fetch(`/api/wiki-page?path=${encodeURIComponent(path)}`);
  if (!response.ok) {
    return { path, content: "Memo content unavailable." };
  }
  return response.json();
}

function renderMemoDocument(markdown) {
  const clean = stripFrontmatter(markdown);
  const lines = clean.split(/\r?\n/);
  const html = [];
  let inList = false;
  let inCode = false;
  const codeLines = [];
  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed.startsWith("```")) {
      if (inList) {
        html.push("</ul>");
        inList = false;
      }
      if (inCode) {
        html.push(`<pre><code>${escapeHtml(codeLines.join("\n"))}</code></pre>`);
        codeLines.length = 0;
        inCode = false;
      } else {
        inCode = true;
      }
      continue;
    }
    if (inCode) {
      codeLines.push(line);
      continue;
    }
    if (!trimmed) {
      if (inList) {
        html.push("</ul>");
        inList = false;
      }
      continue;
    }
    const heading = trimmed.match(/^(#{1,6})\s+(.+)$/);
    if (heading) {
      if (inList) {
        html.push("</ul>");
        inList = false;
      }
      const level = Math.min(4, Math.max(2, heading[1].length + 1));
      html.push(`<h${level}>${escapeHtml(displayMemoSectionTitle(heading[2]))}</h${level}>`);
    } else if (trimmed.startsWith("- ")) {
      if (!inList) {
        html.push("<ul>");
        inList = true;
      }
      html.push(`<li>${renderInlineMarkdown(trimmed.slice(2))}</li>`);
    } else {
      if (inList) {
        html.push("</ul>");
        inList = false;
      }
      html.push(`<p>${renderInlineMarkdown(trimmed)}</p>`);
    }
  }
  if (inList) html.push("</ul>");
  if (inCode) html.push(`<pre><code>${escapeHtml(codeLines.join("\n"))}</code></pre>`);
  return html.join("");
}

function renderInlineMarkdown(text) {
  return escapeHtml(text).replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
}

function stripFrontmatter(markdown) {
  if (markdown.startsWith("---")) {
    const end = markdown.indexOf("\n---", 3);
    if (end !== -1) return markdown.slice(end + 4).trim();
  }
  return markdown.trim();
}

function renderDeepReadsPage() {
  const project = projectById();
  if (!project) {
    renderEmpty("Project not found.");
    return;
  }
  renderProjectNav(project);
  const libraryHref = papersUrl(project.id, { filter: "deep-read" });
  setHeader("Papers", "Deep Reads Moved to Papers", `${displayProjectTitle(project)} · Dashboard keeps one paper entry point.`);
  el.content.innerHTML = `
    <section class="section-block deep-read-merged-shell">
      <div class="section-head">
        <div>
          <p class="eyebrow">Compatibility Entry</p>
          <h2>Deep Reads Moved to Papers</h2>
          <p class="section-note">Dashboard keeps one paper entry point.Deep-read memos, paper detail, status, and provenance are all in Papers.</p>
        </div>
        <a class="primary-action review-action" href="${escapeAttr(libraryHref)}">OpenPapers</a>
      </div>
    </section>
  `;
}

function renderLineageAtlasFallback(map) {
  const routes = Array.isArray(map?.routes)
    ? map.routes.filter((route) => route && typeof route === "object" && !Array.isArray(route))
    : [];
  const papers = Array.isArray(map?.papers)
    ? map.papers.filter((paper) => paper && typeof paper === "object" && !Array.isArray(paper))
    : [];
  const topic = map?.topic_name || map?.display?.topic_name || map?.title || "Related Work Lineage";
  const routeIds = routes.map((route) => route.id).filter(Boolean);
  papers.forEach((paper) => {
    const routeId = paper.route || "unassigned";
    if (!routeIds.includes(routeId)) routeIds.push(routeId);
  });

  return `
    <section class="lineage-atlas-fallback" aria-label="Lineage atlas fallback">
      <header>
        <p class="eyebrow">Lineage Atlas</p>
        <h2>${escapeHtml(topic)}</h2>
      </header>
      <div class="lineage-lanes">
        ${routeIds.length ? routeIds.map((routeId) => {
          const route = routes.find((item) => item.id === routeId) || { id: routeId, label: routeId, description: "" };
          const routePapers = sortedLineagePapers(papers.filter((paper) => (paper.route || "unassigned") === routeId));
          return `
            <section class="lineage-lane">
              <header>
                <div>
                  <span>${escapeHtml(route.review_status || "candidate")}</span>
                  <h3>${escapeHtml(route.label || route.id || "Unnamed route")}</h3>
                </div>
                <small>${escapeHtml(route.id || "route")}</small>
              </header>
              <p>${escapeHtml(route.description || "No route description.")}</p>
              <div class="lineage-paper-track">
                ${routePapers.length ? routePapers.map((paper) => renderLineagePaperNode(paper)).join("") : `<div class="empty-state">No papers assigned.</div>`}
              </div>
            </section>
          `;
        }).join("") : `<div class="empty-state">No routes in this lineage map.</div>`}
      </div>
    </section>
  `;
}

function renderLineagePage() {
  const project = projectById();
  if (!project) {
    renderEmpty("Project not found.");
    return;
  }
  renderProjectNav(project);
  const maps = lineageMapsForProject(project.id);
  const roundParam = params().get("round") || "";
  const selectedMap = maps.find((map) => normalizeToken(map.round) === normalizeToken(roundParam)) || maps[0] || null;
  setHeader(
    "Technical Lineage",
    selectedMap?.title || "Related Work Lineage",
    `${displayProjectTitle(project)} · paper-only related-work map`
  );
  if (!selectedMap) {
    el.content.innerHTML = `
      <section class="section-block lineage-map-shell">
        <div class="section-head">
          <div>
            <p class="eyebrow">Read-only Artifact</p>
            <h2>No related-work-lineage.json</h2>
            <p class="section-note">Technical Lineage displays workspace lineage artifacts only and does not write the Project Understanding Graph.</p>
          </div>
          <a href="${escapeAttr(projectUrl(project.id))}">Back to Project</a>
        </div>
        <div class="empty-state">No related work lineage map for this project yet.</div>
      </section>
    `;
    return;
  }

  el.content.innerHTML = `
    <section class="section-block lineage-map-shell">
      <div id="lineage-atlas-root" class="lineage-atlas-root"></div>
    </section>
  `;
  const root = document.getElementById("lineage-atlas-root");
  if (!root) return;
  if (window.ResearchBrowserLineageAtlas?.mount) {
    window.ResearchBrowserLineageAtlas.mount(root, { map: selectedMap, project });
  } else {
    root.innerHTML = renderLineageAtlasFallback(selectedMap);
  }
}

function renderLineageSummaryFacts(map) {
  const status = map.valid ? (map.status || "candidate") : "invalid";
  return `
    <dl class="lineage-summary-facts">
      <div><dt>routes</dt><dd>${Number(map.route_count || (map.routes || []).length || 0)}</dd></div>
      <div><dt>papers</dt><dd>${Number(map.paper_count || (map.papers || []).length || 0)}</dd></div>
      <div><dt>edges</dt><dd>${Number(map.edge_count || (map.explicit_edges || []).length || 0)}</dd></div>
      <div><dt>status</dt><dd>${escapeHtml(status)}</dd></div>
    </dl>
    ${Array.isArray(map.errors) && map.errors.length ? `
      <div class="lineage-boundary-note lineage-error-note">
        <strong>Validation</strong>
        <span>${map.errors.map((error) => escapeHtml(error)).join("; ")}</span>
      </div>
    ` : ""}
  `;
}

function sortedLineagePapers(papers) {
  return [...(papers || [])].sort((a, b) => {
    const yearA = Number(a.year || 9999);
    const yearB = Number(b.year || 9999);
    if (yearA !== yearB) return yearA - yearB;
    const monthA = Number(a.month || 99);
    const monthB = Number(b.month || 99);
    if (monthA !== monthB) return monthA - monthB;
    return String(a.title || "").localeCompare(String(b.title || ""));
  });
}

function lineagePaperDateValue(paper) {
  const year = Number(paper?.year || 0);
  if (!year) return 0;
  const month = Math.max(1, Math.min(12, Number(paper?.month || 1)));
  return year * 12 + month;
}

function shortLineageLabel(value, max = 34) {
  const text = String(value || "").trim();
  if (text.length <= max) return text;
  return `${text.slice(0, Math.max(0, max - 1)).trim()}…`;
}

function renderLineageGraph(map) {
  const papers = sortedLineagePapers(Array.isArray(map.papers) ? map.papers : []);
  const routes = Array.isArray(map.routes) ? map.routes : [];
  if (!papers.length) return `<div class="empty-state">No lineage graph nodes.</div>`;

  const routeMap = new Map(routes.map((route) => [route.id, route]));
  papers.forEach((paper) => {
    const routeId = paper.route || "unassigned";
    if (!routeMap.has(routeId)) {
      routeMap.set(routeId, { id: routeId, label: routeId === "unassigned" ? "Unassigned" : routeId, description: "", review_status: "unknown" });
    }
  });
  const routeIds = [...routeMap.keys()];
  const values = papers.map((paper) => lineagePaperDateValue(paper)).filter(Boolean);
  const minValue = Math.min(...values);
  const maxValue = Math.max(...values);
  const range = Math.max(1, maxValue - minValue);
  const width = 1240;
  const left = 250;
  const right = 74;
  const top = 92;
  const routeGap = 116;
  const height = Math.max(260, top + (routeIds.length - 1) * routeGap + 96);
  const routeY = new Map(routeIds.map((routeId, index) => [routeId, top + index * routeGap]));
  const xForPaper = (paper) => left + ((lineagePaperDateValue(paper) - minValue) / range) * (width - left - right);
  const nodeById = new Map();
  papers.forEach((paper) => {
    nodeById.set(paper.id, {
      paper,
      x: xForPaper(paper),
      y: routeY.get(paper.route || "unassigned") || top,
    });
  });

  const routeRows = routeIds.map((routeId) => {
    const route = routeMap.get(routeId);
    const y = routeY.get(routeId);
    return `
      <g class="lineage-graph-route" data-route-id="${escapeAttr(routeId)}">
        <text x="28" y="${y - 14}" class="lineage-graph-route-label">${escapeHtml(shortLineageLabel(route.label || route.id || "Route", 30))}</text>
        <text x="28" y="${y + 10}" class="lineage-graph-route-id">${escapeHtml(shortLineageLabel(route.id || "route", 34))}</text>
        <line x1="${left - 22}" y1="${y}" x2="${width - right + 18}" y2="${y}" />
      </g>
    `;
  }).join("");

  const sequenceEdges = routeIds.flatMap((routeId) => {
    const routePapers = sortedLineagePapers(papers.filter((paper) => (paper.route || "unassigned") === routeId));
    return routePapers.slice(1).map((paper, index) => {
      const source = nodeById.get(routePapers[index].id);
      const target = nodeById.get(paper.id);
      if (!source || !target) return "";
      return `<line class="lineage-graph-sequence-edge" x1="${source.x + 14}" y1="${source.y}" x2="${target.x - 14}" y2="${target.y}" />`;
    });
  }).join("");

  const explicitEdges = (Array.isArray(map.explicit_edges) ? map.explicit_edges : []).map((edge) => {
    const source = nodeById.get(edge.source);
    const target = nodeById.get(edge.target);
    if (!source || !target) return "";
    const midX = (source.x + target.x) / 2;
    const verticalLift = source.y === target.y ? -42 : (source.y < target.y ? -34 : 34);
    const controlY = (source.y + target.y) / 2 + verticalLift;
    return `
      <path class="lineage-graph-explicit-edge" d="M ${source.x} ${source.y} Q ${midX} ${controlY} ${target.x} ${target.y}" marker-end="url(#lineage-arrow)" />
      <text x="${midX}" y="${controlY - 8}" class="lineage-graph-edge-label">${escapeHtml(shortLineageLabel(edge.relation || "related", 18))}</text>
    `;
  }).join("");

  const nodes = papers.map((paper) => {
    const node = nodeById.get(paper.id);
    const date = [paper.year, paper.month].filter(Boolean).join("-");
    const isAnchor = (paper.roles || []).includes("baseline") || (paper.roles || []).includes("project-anchor");
    return `
      <g class="lineage-graph-node${isAnchor ? " is-anchor" : ""}" data-paper-id="${escapeAttr(paper.id || "")}" transform="translate(${node.x} ${node.y})">
        <title>${escapeHtml(paper.title || paper.id || "Untitled paper")}</title>
        <circle r="${isAnchor ? 18 : 14}" />
        <text class="lineage-graph-node-date" x="0" y="-26">${escapeHtml(date || "n.d.")}</text>
        <text class="lineage-graph-node-title" x="0" y="${isAnchor ? 38 : 34}">${escapeHtml(shortLineageLabel(paper.title || paper.id || "Untitled paper", isAnchor ? 34 : 28))}</text>
      </g>
    `;
  }).join("");

  return `
    <section class="lineage-graph-panel">
      <div class="section-head">
        <div>
          <p class="eyebrow">Lineage Graph</p>
          <h2>Paper Node Graph</h2>
          <p class="section-note">Horizontal position follows time; lanes are technical routes; thin lines are same-route sequences; gold curves are explicit cross-route edges.</p>
        </div>
      </div>
      <div class="lineage-graph-scroll">
        <svg class="lineage-graph" viewBox="0 0 ${width} ${height}" role="img" aria-label="Related work lineage graph">
          <defs>
            <marker id="lineage-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" />
            </marker>
          </defs>
          ${routeRows}
          ${sequenceEdges}
          ${explicitEdges}
          ${nodes}
        </svg>
      </div>
    </section>
  `;
}

function renderLineageLanes(map) {
  const papers = Array.isArray(map.papers) ? map.papers : [];
  const routeMap = new Map((map.routes || []).map((route) => [route.id, route]));
  const routeIds = [...routeMap.keys()];
  papers.forEach((paper) => {
    if (paper.route && !routeMap.has(paper.route)) {
      routeMap.set(paper.route, { id: paper.route, label: paper.route, description: "", review_status: "unknown" });
      routeIds.push(paper.route);
    }
  });
  const unassigned = papers.filter((paper) => !paper.route);
  if (unassigned.length) {
    routeMap.set("unassigned", { id: "unassigned", label: "Unassigned", description: "Papers without route assignment.", review_status: "unknown" });
    routeIds.push("unassigned");
  }
  if (!routeIds.length) return `<div class="empty-state">No routes in this lineage map.</div>`;
  return `
    <div class="lineage-lanes">
      ${routeIds.map((routeId) => {
        const route = routeMap.get(routeId);
        const routePapers = sortedLineagePapers(papers.filter((paper) => (paper.route || "unassigned") === routeId));
        return `
          <section class="lineage-lane">
            <header>
              <div>
                <span>${escapeHtml(route.review_status || "candidate")}</span>
                <h3>${escapeHtml(route.label || route.id || "Unnamed route")}</h3>
              </div>
              <small>${escapeHtml(route.id || "route")}</small>
            </header>
            <p>${escapeHtml(route.description || "No route description.")}</p>
            <div class="lineage-paper-track">
              ${routePapers.length ? routePapers.map((paper) => renderLineagePaperNode(paper)).join("") : `<div class="empty-state">No papers assigned.</div>`}
            </div>
          </section>
        `;
      }).join("")}
    </div>
  `;
}

function renderLineagePaperNode(paper) {
  const date = [paper.year, paper.month].filter(Boolean).join("-");
  const roles = Array.isArray(paper.roles) ? paper.roles : [];
  return `
    <article class="lineage-paper-node">
      <span>${escapeHtml(date || "n.d.")}</span>
      <h4>${escapeHtml(paper.title || paper.id || "Untitled paper")}</h4>
      <p>${escapeHtml(paper.summary || paper.source_evidence || "No summary.")}</p>
      <div>
        ${roles.map((role) => `<small>${escapeHtml(role)}</small>`).join("")}
        <small>${escapeHtml(paper.review_status || "candidate")}</small>
      </div>
    </article>
  `;
}

function renderLineageEdgeList(map) {
  const edges = Array.isArray(map.explicit_edges) ? map.explicit_edges : [];
  const papersById = new Map((map.papers || []).map((paper) => [paper.id, paper]));
  return `
    <section class="lineage-edge-list">
      <div class="section-head">
        <div>
          <p class="eyebrow">Explicit Cross-route Relationships</p>
          <h2>Non-sequential Edges</h2>
        </div>
      </div>
      ${edges.length ? edges.map((edge) => {
        const source = papersById.get(edge.source);
        const target = papersById.get(edge.target);
        return `
          <article>
            <strong>${escapeHtml(source?.title || edge.source || "unknown")} -> ${escapeHtml(target?.title || edge.target || "unknown")}</strong>
            <span>${escapeHtml(edge.relation || "related")} · ${escapeHtml(edge.confidence || "unknown")} · ${escapeHtml(edge.review_status || "candidate")}</span>
            <p>${escapeHtml(edge.rationale || edge.source_evidence || "No rationale.")}</p>
          </article>
        `;
      }).join("") : `<div class="empty-state">No explicit cross-route relationships.</div>`}
    </section>
  `;
}

function renderLineagePaperTable(map) {
  const papers = sortedLineagePapers(map.papers || []);
  return `
    <section class="lineage-paper-table">
      <div class="section-head">
        <div>
          <p class="eyebrow">Paper Table</p>
          <h2>Sources</h2>
        </div>
      </div>
      <div class="table-scroll">
        <table class="paper-summary-table">
          <thead>
            <tr>
              <th>Paper</th>
              <th>Route</th>
              <th>Status</th>
              <th>Source</th>
            </tr>
          </thead>
          <tbody>
            ${papers.map((paper) => {
              const safeUrl = safeExternalSourceUrl(paper.source_url);
              return `
                <tr>
                  <td>
                    <strong>${escapeHtml(paper.title || paper.id || "Untitled paper")}</strong>
                    <span>${escapeHtml([paper.venue, paper.year].filter(Boolean).join(" · ") || paper.id || "")}</span>
                  </td>
                  <td>${escapeHtml(paper.route || "unassigned")}</td>
                  <td>${escapeHtml(paper.review_status || "candidate")}</td>
                  <td>${safeUrl ? `<a href="${escapeAttr(safeUrl)}" target="_blank" rel="noopener noreferrer">source</a>` : `<span>${paper.source_url ? "unsafe source_url" : "no source_url"}</span>`}</td>
                </tr>
              `;
            }).join("") || `<tr><td colspan="4">No papers.</td></tr>`}
          </tbody>
        </table>
      </div>
    </section>
  `;
}

async function renderExperimentsPage() {
  const project = projectById();
  if (!project) {
    renderEmpty("Project not found.");
    return;
  }
  renderProjectNav(project);
  setHeader(
    "Experiments",
    "Experiments",
    `${displayProjectTitle(project)} · planned design and completed evidence`
  );
  el.content.innerHTML = `
    <section class="section-block experiment-page-content" aria-label="Project experiments">
      <div id="experiments-model-root" class="experiment-page-section">
        <div class="empty-state">Loading experiments...</div>
      </div>
    </section>
  `;
  const model = await loadExperimentsFromApi(project.id);
  const root = document.getElementById("experiments-model-root");
  if (root) root.innerHTML = renderExperimentsModel(model);
}

function renderExperimentsModel(model) {
  const experiments = Array.isArray(model?.experiments) ? model.experiments : [];
  const runs = Array.isArray(model?.runs) ? model.runs : [];
  const nextMoves = Array.isArray(model?.next_moves) ? model.next_moves : [];
  if (!experiments.length && !runs.length && !nextMoves.length) {
    return `
      <div class="empty-state">${escapeHtml(model?.empty_message || "No experiments recorded yet.")}</div>
      ${renderLegacyExperimentNote(model)}
    `;
  }
  return `
    <section class="experiment-page-section">
      <div class="section-head">
        <div>
          <p class="eyebrow">Read Model</p>
          <h2>Experiment Evidence Summary</h2>
        </div>
      </div>
      ${renderExperimentSummary(model)}
    </section>
    <section class="experiment-page-section">
      <div class="section-head">
        <div>
          <p class="eyebrow">Designs</p>
          <h2>Active Experiment Designs</h2>
        </div>
      </div>
      <div class="experiment-card-grid">
        ${experiments.length ? experiments.map((experiment) => renderExperimentDesignCard(experiment)).join("") : `<div class="empty-state">No active experiment designs.</div>`}
      </div>
    </section>
    <section class="experiment-page-section">
      <div class="section-head">
        <div>
          <p class="eyebrow">Evidence</p>
          <h2>Results / Evidence</h2>
        </div>
      </div>
      <div class="experiment-card-grid">
        ${runs.length ? runs.map((run) => renderExperimentRunCard(run)).join("") : `<div class="empty-state">No experiment results recorded.</div>`}
      </div>
    </section>
    <section class="experiment-page-section">
      <div class="section-head">
        <div>
          <p class="eyebrow">Next</p>
          <h2>Next Experiment Moves</h2>
        </div>
      </div>
      <div class="experiment-card-grid">
        ${nextMoves.length ? nextMoves.map((move) => renderExperimentNextMove(move)).join("") : `<div class="empty-state">No next experiment moves recorded.</div>`}
      </div>
    </section>
    ${renderLegacyExperimentNote(model)}
  `;
}

function renderExperimentSummary(model) {
  const summary = model?.summary || {};
  return `
    <div class="experiment-summary-row">
      ${renderExperimentField("total experiments", summary.total_experiments ?? 0)}
      ${renderExperimentField("planned", summary.planned ?? 0)}
      ${renderExperimentField("ready", summary.ready ?? 0)}
      ${renderExperimentField("running", summary.running ?? 0)}
      ${renderExperimentField("completed runs", summary.completed_runs ?? 0)}
      ${renderExperimentField("local results", summary.local_result_runs ?? 0)}
      ${renderExperimentField("imported evidence", summary.imported_evidence_runs ?? 0)}
      ${renderExperimentField("strongest current evidence", summary.strongest_current_evidence || "None recorded.")}
      ${renderExperimentField("highest priority unresolved", summary.highest_priority_unresolved || "None recorded.")}
    </div>
  `;
}

function renderExperimentDesignCard(experiment) {
  return `
    <article class="experiment-card">
      <div class="experiment-card-head">
        <div>
          <p class="eyebrow">${escapeHtml(experiment?.id || "experiment")}</p>
          <h3>${escapeHtml(experiment?.title || "Untitled experiment")}</h3>
        </div>
        ${statusPill(experiment?.status || "planned")}
      </div>
      ${renderExperimentField("question", experiment?.question)}
      ${renderExperimentField("hypothesis", experiment?.hypothesis)}
      ${renderExperimentList("linked claims", experiment?.linked_claims)}
      ${renderExperimentList("linked gaps", experiment?.linked_gaps)}
      ${renderExperimentField("benchmark", experiment?.benchmark)}
      ${renderExperimentField("dataset", experiment?.dataset)}
      ${renderExperimentList("models", experiment?.models)}
      ${renderExperimentList("baselines", experiment?.baselines)}
      ${renderExperimentList("metrics", experiment?.metrics)}
      ${renderExperimentList("protocol", experiment?.protocol)}
      ${renderExperimentField("expected evidence", experiment?.expected_evidence)}
      ${renderExperimentList("risks", experiment?.risks)}
      ${renderExperimentField("next action", experiment?.next_action)}
    </article>
  `;
}

function renderExperimentRunCard(run) {
  const evidenceType = normalizeToken(run?.evidence_type);
  const importedClass = evidenceType === "imported_paper_evidence" ? " is-imported" : "";
  return `
    <article class="experiment-card">
      <div class="experiment-card-head">
        <div>
          <p class="eyebrow">${escapeHtml(run?.id || "run")}</p>
          <h3>${escapeHtml(run?.summary || "Experiment result")}</h3>
        </div>
        ${statusPill(run?.status || "unknown")}
      </div>
      <p class="experiment-evidence-type${importedClass}">${escapeHtml(experimentEvidenceTypeLabel(evidenceType))}</p>
      ${renderExperimentField("experiment", run?.experiment_id)}
      ${renderExperimentField("completed", run?.completed_at)}
      ${renderExperimentList("metrics", run?.metrics)}
      ${renderExperimentList("artifacts", run?.artifacts)}
      ${renderExperimentField("interpretation", run?.interpretation)}
      ${renderExperimentList("claim impacts", run?.claim_impacts)}
      ${renderExperimentList("weaknesses", run?.weaknesses)}
    </article>
  `;
}

function experimentEvidenceTypeLabel(value) {
  const labels = {
    imported_paper_evidence: "Imported paper evidence",
    local_experiment_result: "Local experiment result",
    external_result: "External result",
    replication_result: "Replication result",
  };
  return labels[normalizeToken(value)] || "Experiment evidence";
}

function renderExperimentNextMove(move) {
  return `
    <article class="next-move-card">
      <div class="experiment-card-head">
        <div>
          <p class="eyebrow">${escapeHtml(move?.type || "next move")}</p>
          <h3>${escapeHtml(move?.linked_experiment || move?.linked_claim || "Next Experiment Moves")}</h3>
        </div>
      </div>
      ${renderExperimentField("rationale", move?.rationale)}
      ${renderExperimentField("suggested prompt", move?.suggested_prompt)}
      ${renderExperimentField("linked experiment", move?.linked_experiment)}
      ${renderExperimentField("linked claim", move?.linked_claim)}
    </article>
  `;
}

function renderExperimentField(label, value) {
  const text = Array.isArray(value) || (value && typeof value === "object")
    ? JSON.stringify(value, null, 2)
    : String(value ?? "").trim();
  return `
    <section class="experiment-field">
      <h4>${escapeHtml(label)}</h4>
      <p>${escapeHtml(text || "None recorded.")}</p>
    </section>
  `;
}

function renderExperimentList(label, value) {
  const values = Array.isArray(value) ? value : [];
  const items = values.map((item) => formatExperimentListItem(label, item)).filter(Boolean);
  return `
    <section class="experiment-field">
      <h4>${escapeHtml(label)}</h4>
      ${items.length ? `<ul>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>` : "<p>None recorded.</p>"}
    </section>
  `;
}

function formatExperimentListItem(label, item) {
  if (!item || typeof item !== "object") return String(item ?? "").trim();
  const normalizedLabel = normalizeToken(label);
  if (normalizedLabel === "metrics") {
    return [item.name, item.value].filter(Boolean).join(": ");
  }
  if (normalizedLabel === "artifacts") {
    const title = item.label || item.type || "artifact";
    return [title, item.path_or_url].filter(Boolean).join(": ");
  }
  if (normalizedLabel === "claim_impacts") {
    const impact = [item.impact, item.strength].filter(Boolean).join(" / ");
    return [item.claim, impact].filter(Boolean).join(": ");
  }
  return Object.entries(item)
    .filter(([, value]) => value !== undefined && value !== null && value !== "")
    .map(([key, value]) => `${key}: ${value}`)
    .join("; ");
}

function renderLegacyExperimentNote(model) {
  const legacy = model?.legacy_proposals || {};
  if (!legacy.found && !legacy.count) return "";
  return `
    <aside class="legacy-experiment-note">
      <strong>Legacy experiment proposals</strong>
      <span>${escapeHtml(legacy.count ?? 0)} legacy artifact${Number(legacy.count) === 1 ? "" : "s"} remain at ${escapeHtml(legacy.path || "project experiment-proposals directory")}.</span>
    </aside>
  `;
}

function wireReviewRowFocus() {
  document.querySelectorAll("[data-focus-key]").forEach((row) => {
    const focusRow = (event) => {
      if (event.target.closest("a, button")) return;
      state.focusedCandidateKey = row.dataset.focusKey || "";
      renderRoundReviewPage();
    };
    row.addEventListener("click", focusRow);
    row.addEventListener("keydown", (event) => {
      if (event.key !== "Enter" && event.key !== " ") return;
      event.preventDefault();
      state.focusedCandidateKey = row.dataset.focusKey || "";
      renderRoundReviewPage();
    });
  });
}

function renderEmpty(message) {
  el.content.innerHTML = `<div class="empty-state">${escapeHtml(message)}</div>`;
}

async function loadData() {
  const response = await fetch("/.dashboard/index.json", { cache: "no-store" });
  state.data = await response.json();
}

async function renderPage() {
  state.projectId = params().get("project") || state.data.projects?.[0]?.id || "";
  state.roundId = params().get("round") || latestRound(state.projectId)?.name || "";
  state.paperId = params().get("paper") || "";
  if (state.data.schema_version !== "research-browser-v2") {
    renderEmpty("Dashboard index is stale. Rebuild .dashboard/index.json.");
    return;
  }
  if (state.page === "projects") renderProjectsIndex();
  else if (state.page === "project") await renderProjectWorkspace();
  else if (state.page === "papers") renderProjectPapersPage();
  else if (state.page === "round") renderRoundReviewPage();
  else if (state.page === "paper") await renderPaperDetailPage();
  else if (state.page === "deep-reads") renderDeepReadsPage();
  else if (state.page === "lineage") renderLineagePage();
  else if (state.page === "experiments") await renderExperimentsPage();
  else renderProjectsIndex();
}

async function boot() {
  try {
    mountThemeToggle();
    await loadData();
    await renderPage();
  } catch (error) {
    mountThemeToggle();
    setHeader("Error", "Research Browser failed to load", "");
    renderEmpty(error.message || "UnknownError。");
  }
}

boot();
