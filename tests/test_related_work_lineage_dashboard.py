import json
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

from tools.build_dashboard_index import build_index


ROOT = Path(__file__).resolve().parents[1]


class RelatedWorkLineageDashboardTest(unittest.TestCase):
    def test_dashboard_source_uses_english_copy(self):
        dashboard_files = [
            path
            for path in (ROOT / "dashboard").rglob("*")
            if path.suffix in {".css", ".html", ".js", ".jsx"}
            and "node_modules" not in path.parts
        ]
        for path in dashboard_files:
            text = path.read_text(encoding="utf-8")
            self.assertNotRegex(text, r"[\u4e00-\u9fff]", str(path))

    def test_lineage_page_exists_with_page_marker(self):
        html = (ROOT / "dashboard" / "lineage.html").read_text(encoding="utf-8")

        self.assertIn('data-page="lineage"', html)
        self.assertIn('href="./lineage-atlas.bundle.css?v=english-dashboard-20260603a"', html)
        self.assertIn('src="./lineage-atlas.bundle.js?v=english-dashboard-20260603a"', html)

    def test_app_contains_lineage_page_hooks(self):
        app = (ROOT / "dashboard" / "app.js").read_text(encoding="utf-8")

        self.assertIn("function safeExternalSourceUrl(value)", app)
        self.assertIn("function lineageUrl(projectId, roundName)", app)
        self.assertIn("function renderLineageAtlasFallback(map)", app)
        self.assertIn("function renderLineagePage()", app)
        self.assertIn("ResearchBrowserLineageAtlas.mount", app)
        self.assertIn("lineage-atlas-root", app)
        self.assertIn("function renderLineageGraph(map)", app)
        self.assertIn("function renderLineagePaperTable(map)", app)
        self.assertNotIn("${renderLineageSummaryFacts(selectedMap)}", app)
        self.assertNotIn("renderLineageGraph(selectedMap)", app)
        self.assertNotIn("renderLineagePaperTable(selectedMap)", app)
        self.assertIn('state.page === "lineage"', app)

    def test_project_page_contains_understanding_update_surface(self):
        app = (ROOT / "dashboard" / "app.js").read_text(encoding="utf-8")
        project_html = (ROOT / "dashboard" / "project.html").read_text(encoding="utf-8")

        self.assertIn("loadProjectUnderstandingFromApi", app)
        self.assertIn("renderProjectUnderstandingPanel", app)
        self.assertIn("/api/project-understanding", app)
        self.assertIn("Recent Understanding", app)
        self.assertIn("Next Moves", app)
        self.assertIn("app.js?v=english-dashboard-20260603a", project_html)
        self.assertIn("project-graph.bundle.js?v=english-dashboard-20260603a", project_html)

    def test_dashboard_pages_cache_bust_static_assets(self):
        for path in (ROOT / "dashboard").glob("*.html"):
            html = path.read_text(encoding="utf-8")
            self.assertNotIn('src="./app.js"', html, str(path))
            self.assertNotIn('href="./styles.css"', html, str(path))
            if "app.js" in html:
                self.assertIn("app.js?v=english-dashboard-20260603a", html, str(path))
            if "styles.css" in html:
                self.assertIn("styles.css?v=english-dashboard-20260603a", html, str(path))
            self.assertNotIn('href="./index.html"', html, str(path))
            self.assertIn('href="./index.html?v=english-dashboard-20260603a"', html, str(path))

    def test_experiments_page_replaces_proposal_framing(self):
        app = (ROOT / "dashboard" / "app.js").read_text(encoding="utf-8")
        html = (ROOT / "dashboard" / "experiments.html").read_text(encoding="utf-8")
        legacy_html = (ROOT / "dashboard" / "experiment-proposals.html").read_text(encoding="utf-8")

        self.assertIn('data-page="experiments"', html)
        self.assertIn("<title>Research Browser · Experiments</title>", html)
        self.assertIn("function experimentsUrl(projectId)", app)
        self.assertIn("/api/experiments", app)
        self.assertNotIn("Experiment Proposals</a>", app)
        self.assertIn('data-page="experiments"', legacy_html)

    def test_experiments_renderer_shows_designs_results_and_next_moves(self):
        app = (ROOT / "dashboard" / "app.js").read_text(encoding="utf-8")

        self.assertIn("async function loadExperimentsFromApi(projectId)", app)
        self.assertIn("async function renderExperimentsPage()", app)
        self.assertIn("function renderExperimentDesignCard(experiment)", app)
        self.assertIn("function renderExperimentRunCard(run)", app)
        self.assertIn("function formatExperimentListItem(label, item)", app)
        self.assertIn("Experiment Evidence Summary", app)
        self.assertIn("Active Experiment Designs", app)
        self.assertIn("Results / Evidence", app)
        self.assertIn("Next Experiment Moves", app)
        self.assertIn("imported_paper_evidence", app)
        self.assertIn("const model = await response.json();", app)
        self.assertIn("model && typeof model === \"object\" ? model : emptyExperimentsModel(projectId)", app)
        self.assertIn("!experiments.length && !runs.length && !nextMoves.length", app)
        self.assertIn('class="experiment-evidence-type${importedClass}"', app)
        self.assertIn('const importedClass = evidenceType === "imported_paper_evidence" ? " is-imported" : "";', app)
        self.assertIn('return [item.name, item.value].filter(Boolean).join(": ");', app)
        self.assertIn('return [title, item.path_or_url].filter(Boolean).join(": ");', app)
        self.assertIn("Local experiment result", app)
        self.assertNotIn("planned / pending / not yet graph evidence", app)

    def test_dashboard_app_versions_page_urls(self):
        app = (ROOT / "dashboard" / "app.js").read_text(encoding="utf-8")

        self.assertIn('const DASHBOARD_PAGE_VERSION = "english-dashboard-20260603a";', app)
        self.assertIn('function dashboardPageUrl(pageName, params = {})', app)
        self.assertIn('return `./${pageName}.html?${search.toString()}`;', app)
        self.assertNotIn("`./project.html?project=", app)
        self.assertNotIn("`./papers.html?", app)
        self.assertNotIn("`./paper.html?project=", app)

    def test_project_page_hides_old_workflow_panels(self):
        app = (ROOT / "dashboard" / "app.js").read_text(encoding="utf-8")
        project_start = app.index("async function renderProjectWorkspace()")
        project_end = app.index("function hasProjectUnderstanding", project_start)
        project_renderer = app[project_start:project_end]

        self.assertNotIn("project-workspace-grid", project_renderer)
        self.assertNotIn("Current Question", project_renderer)
        self.assertNotIn("Search Status", project_renderer)
        self.assertNotIn("renderHumanGatePanel", project_renderer)

    def test_workspace_page_hooks_and_primary_nav(self):
        app = (ROOT / "dashboard" / "app.js").read_text(encoding="utf-8")

        self.assertIn("function workspaceUrl(projectId, mode = \"understanding\")", app)
        self.assertIn("function currentWorkspaceMode", app)
        self.assertIn("async function loadWorkspaceGraphFromApi", app)
        self.assertIn("async function renderWorkspacePage()", app)
        self.assertIn("ResearchBrowserWorkspaceIsland.mount", app)
        self.assertIn('current === "workspace"', app)
        self.assertIn(">Workspace</a>", app)
        self.assertIn(">Papers</a>", app)
        self.assertNotIn(">Technical Lineage</a>", app)
        self.assertNotIn(">Experiments</a>", app)

    def test_workspace_navigation_preserves_page_scroll(self):
        app = (ROOT / "dashboard" / "app.js").read_text(encoding="utf-8")
        styles = (ROOT / "dashboard" / "styles.css").read_text(encoding="utf-8")

        self.assertIn("const scrollX = window.scrollX;", app)
        self.assertIn("const scrollY = window.scrollY;", app)
        self.assertIn("window.requestAnimationFrame(() => window.scrollTo(scrollX, scrollY));", app)
        self.assertIn(".workspace-page-shell", styles)
        self.assertIn("overflow-anchor: none;", styles)

    def test_workspace_nav_preserves_current_mode_when_already_in_workspace(self):
        app = (ROOT / "dashboard" / "app.js").read_text(encoding="utf-8")

        self.assertIn("function currentWorkspaceMode", app)
        self.assertIn('return normalizeToken(params().get("mode") || legacyWorkspaceModeForPage(page)) || "understanding";', app)
        self.assertIn("const workspaceMode = currentWorkspaceMode(current);", app)
        self.assertIn('workspaceUrl(project.id, workspaceMode)', app)

    def test_workspace_navigation_stays_workspace_and_papers_only(self):
        app = (ROOT / "dashboard" / "app.js").read_text(encoding="utf-8")

        self.assertIn("function workspaceUrl(projectId, mode = \"understanding\")", app)
        self.assertIn("function legacyWorkspaceModeForPage", app)
        self.assertIn('if (state.page === "lineage") return "literature";', app)
        self.assertIn('if (state.page === "experiments") return "experiments";', app)
        self.assertIn(">Workspace</a>", app)
        self.assertIn(">Papers</a>", app)
        self.assertNotIn(">Technical Lineage</a>", app)
        self.assertNotIn(">Experiments</a>", app)

    def test_workspace_loader_uses_one_mode_layer_request(self):
        app = (ROOT / "dashboard" / "app.js").read_text(encoding="utf-8")

        self.assertIn("async function loadWorkspaceGraphFromApi", app)
        self.assertIn("search.set(\"mode\", options.mode || \"understanding\")", app)
        self.assertIn("if (options.layer) search.set(\"layer\", options.layer)", app)
        self.assertIn("if (options.focus_id) search.set(\"focus_id\", options.focus_id)", app)
        self.assertIn("if (options.selected_id) search.set(\"selected_id\", options.selected_id)", app)
        self.assertNotIn("Promise.all([loadWorkspaceGraphFromApi", app)

    def test_dashboard_cleanup_removes_low_value_metrics_and_read_only_state(self):
        app = (ROOT / "dashboard" / "app.js").read_text(encoding="utf-8")

        project_index_start = app.index("function renderProjectsIndex()")
        project_index_end = app.index("async function renderProjectWorkspace()", project_index_start)
        project_index = app[project_index_start:project_index_end]
        self.assertNotIn("Candidate", project_index)
        self.assertNotIn("ProjectPaper", project_index)
        self.assertNotIn("paper_count", project_index)
        self.assertNotIn("Rounds", project_index)
        self.assertNotIn("Claims", project_index)

        paper_detail_start = app.index("async function renderPaperDetailPage()")
        paper_detail_end = app.index("function renderPaperInsightMap", paper_detail_start)
        paper_detail = app[paper_detail_start:paper_detail_end]
        self.assertNotIn("Read-only Paper State", paper_detail)
        self.assertNotIn("renderPaperReadOnlyStatusPanel", paper_detail)

    def test_legacy_graph_pages_delegate_to_workspace_modes(self):
        app = (ROOT / "dashboard" / "app.js").read_text(encoding="utf-8")

        self.assertIn("function legacyWorkspaceModeForPage", app)
        self.assertIn('if (state.page === "lineage") return "literature";', app)
        self.assertIn('if (state.page === "experiments") return "experiments";', app)

    def test_dashboard_index_fetch_bypasses_browser_cache(self):
        app = (ROOT / "dashboard" / "app.js").read_text(encoding="utf-8")

        self.assertIn('fetch("/.dashboard/index.json", { cache: "no-store" })', app)

    def test_query_params_are_parsed_defensively(self):
        app = (ROOT / "dashboard" / "app.js").read_text(encoding="utf-8")

        self.assertIn("function params(search = window.location.search)", app)
        self.assertIn("catch (_error)", app)
        self.assertIn("return new URLSearchParams()", app)

    def test_lineage_atlas_source_and_build_script_exist(self):
        package = json.loads((ROOT / "dashboard" / "package.json").read_text(encoding="utf-8"))

        self.assertEqual(
            package["scripts"].get("build:lineage-atlas"),
            "vite build --config lineage-atlas/vite.config.mjs",
        )
        self.assertTrue((ROOT / "dashboard" / "lineage-atlas" / "vite.config.mjs").is_file())
        self.assertTrue(
            (ROOT / "dashboard" / "lineage-atlas" / "src" / "LineageAtlasApp.jsx").is_file()
        )
        self.assertTrue((ROOT / "dashboard" / "lineage-atlas" / "src" / "lineage-atlas.css").is_file())

    def test_workspace_page_and_island_bundle_exist(self):
        html = (ROOT / "dashboard" / "workspace.html").read_text(encoding="utf-8")
        package = json.loads((ROOT / "dashboard" / "package.json").read_text(encoding="utf-8"))

        self.assertIn('data-page="workspace"', html)
        self.assertIn("workspace-island.bundle.js?v=english-dashboard-20260603a", html)
        self.assertIn("workspace-island.bundle.css?v=english-dashboard-20260603a", html)
        self.assertEqual(
            "vite build --config workspace-island/vite.config.mjs",
            package["scripts"].get("build:workspace-island"),
        )
        self.assertTrue((ROOT / "dashboard" / "workspace-island" / "src" / "WorkspaceIslandApp.jsx").is_file())
        self.assertTrue((ROOT / "dashboard" / "workspace-island" / "src" / "workspace-island.css").is_file())

    def test_workspace_island_contains_layer_overview_and_terminal_run_rules(self):
        source = (ROOT / "dashboard" / "workspace-island" / "src" / "WorkspaceIslandApp.jsx").read_text(encoding="utf-8")

        self.assertIn("WorkspaceInspector", source)
        self.assertIn("function nodeNavigationTarget", source)
        self.assertIn("onNavigate?.(target)", source)
        self.assertIn("modeLabels", source)
        self.assertIn("understanding", source)
        self.assertIn("literature", source)
        self.assertIn("experiments", source)
        self.assertIn("WorkspaceExperimentArenaNode", source)
        self.assertIn("buildExperimentsArenaOverviewFlowModel", source)
        self.assertIn("buildExperimentsArenaFocusFlowModel", source)
        self.assertIn("evaluation_arena", source)
        self.assertIn("Evaluation Arena", source)
        self.assertNotIn("run_detail", source)

    def test_workspace_island_uses_mode_specific_renderers_and_breadcrumb(self):
        source = (ROOT / "dashboard" / "workspace-island" / "src" / "WorkspaceIslandApp.jsx").read_text(encoding="utf-8")

        self.assertIn("function WorkspaceBreadcrumb", source)
        self.assertIn('className="workspace-stage-breadcrumb"', source)
        self.assertIn("onNavigate?.(crumb)", source)
        self.assertIn("function UnderstandingGraphRenderer", source)
        self.assertIn("function LiteratureGraphRenderer", source)
        self.assertIn("function ExperimentsGraphRenderer", source)
        self.assertIn("function WorkspaceGraphRenderer", source)
        self.assertIn("nodeTypes={workspaceNodeTypes}", source)
        self.assertIn("fitViewOptions={{ padding: 0.1, maxZoom: 1.12 }}", source)
        self.assertIn("maskColor=\"var(--workspace-minimap-mask)\"", source)

    def test_workspace_island_shared_paper_focus_and_experiment_arena_copy(self):
        source = (ROOT / "dashboard" / "workspace-island" / "src" / "WorkspaceIslandApp.jsx").read_text(encoding="utf-8")
        styles = (ROOT / "dashboard" / "workspace-island" / "src" / "workspace-island.css").read_text(encoding="utf-8")

        self.assertIn("Paper Brief", source)
        self.assertIn("Paper Argument Nodes", source)
        self.assertIn("Evaluation Arena", source)
        self.assertIn("Runs / Results", source)
        self.assertIn("Imported Paper", source)
        self.assertIn("workspace-experiment-arena-node", source)
        self.assertIn("workspace-run-result-node", source)
        self.assertIn("overflow-y: auto;", styles)

    def test_workspace_island_uses_api_breadcrumb_as_authoritative_contract(self):
        source = (ROOT / "dashboard" / "workspace-island" / "src" / "WorkspaceIslandApp.jsx").read_text(encoding="utf-8")

        self.assertIn("function normalizeBreadcrumb", source)
        self.assertNotIn("function currentBreadcrumbTarget", source)
        self.assertNotIn("function breadcrumbLabelForTarget", source)
        self.assertNotIn("normalized.push(currentTarget)", source)
        self.assertNotIn("selected_id || target?.focus_id || target?.layer", source)

    def test_workspace_island_breadcrumb_fallback_is_mode_root_only(self):
        source = (ROOT / "dashboard" / "workspace-island" / "src" / "WorkspaceIslandApp.jsx").read_text(encoding="utf-8")

        self.assertIn("modeLabels[model?.mode]", source)
        self.assertIn("layer: model?.layer || \"\"", source)
        self.assertNotIn("isTopLevelWorkspaceLayer", source)

    def test_workspace_island_terminal_argument_nodes_do_not_navigate(self):
        source = (ROOT / "dashboard" / "workspace-island" / "src" / "WorkspaceIslandApp.jsx").read_text(encoding="utf-8")

        self.assertIn("function nodeNavigationTarget", source)
        self.assertIn("if (!target) return", source)
        self.assertNotIn("item.drill || item.inspector || { selected_id: item.id }", source)

    def test_workspace_island_omits_node_badges_and_raw_metadata(self):
        source = (ROOT / "dashboard" / "workspace-island" / "src" / "WorkspaceIslandApp.jsx").read_text(encoding="utf-8")

        self.assertNotIn("function DisplayBadges", source)
        self.assertNotIn("<DisplayBadges", source)
        self.assertNotIn("display?.badges", source)
        self.assertNotIn("metadata?.role", source)
        self.assertNotIn("node.metadata.role", source)

    def test_workspace_paper_source_nodes_show_titles_only(self):
        source = (ROOT / "dashboard" / "workspace-island" / "src" / "WorkspaceIslandApp.jsx").read_text(encoding="utf-8")
        styles = (ROOT / "dashboard" / "workspace-island" / "src" / "workspace-island.css").read_text(encoding="utf-8")

        self.assertIn('className="workspace-paper-source-title"', source)
        self.assertNotIn("node.local_id || node.source_id", source)
        self.assertNotIn('node.subtitle || "paper/source"', source)
        self.assertIn(".workspace-paper-source-title", styles)
        self.assertIn("grid-template-columns: minmax(0, 1fr);", styles)

    def test_workspace_island_has_understanding_specific_layout(self):
        source = (ROOT / "dashboard" / "workspace-island" / "src" / "WorkspaceIslandApp.jsx").read_text(encoding="utf-8")

        self.assertIn("function WorkspaceLaneFrameNode", source)
        self.assertIn("function buildUnderstandingFlowModel", source)
        self.assertIn("function buildUnderstandingOverviewFlowModel", source)
        self.assertIn("function buildUnderstandingClaimFocusFlowModel", source)
        self.assertIn("function buildUnderstandingPaperFocusFlowModel", source)
        self.assertIn("workspaceLaneFrameNode", source)
        self.assertIn("workspaceArgumentAtomNode", source)
        self.assertIn("workspacePaperSourceNode", source)
        self.assertIn("model?.mode === \"understanding\"", source)

    def test_workspace_island_has_literature_route_timeline_layout(self):
        source = (ROOT / "dashboard" / "workspace-island" / "src" / "WorkspaceIslandApp.jsx").read_text(encoding="utf-8")
        styles = (ROOT / "dashboard" / "workspace-island" / "src" / "workspace-island.css").read_text(encoding="utf-8")

        self.assertIn("function buildLiteratureOverviewFlowModel", source)
        self.assertIn("workspaceRouteFrameNode", source)
        self.assertNotIn("workspaceLiteratureRouteNode", source)
        self.assertIn("function buildLiteratureRouteFocusFlowModel", source)
        self.assertIn("sortLiteraturePapersByTime", source)
        self.assertIn("routeColorIndex", source)
        self.assertIn("workspaceTimelinePaperNode", source)
        self.assertIn("edges: [],", source)
        self.assertNotIn("visiblePaperIds.has(edge.source) && visiblePaperIds.has(edge.target)", source)
        self.assertIn(".workspace-route-frame-node", styles)
        self.assertIn("const handleNodeClick = useCallback", source)
        self.assertIn('flowNode?.type !== "workspaceRouteFrameNode"', source)
        self.assertIn("onNodeClick={handleNodeClick}", source)
        self.assertIn("zIndex: 2,", source)
        self.assertIn("zIndex: 3,", source)
        self.assertNotIn(".workspace-literature-route-node", styles)
        self.assertIn(".workspace-timeline-paper-node", styles)

    def test_literature_paper_focus_uses_shared_paper_graph_layout(self):
        source = (ROOT / "dashboard" / "workspace-island" / "src" / "WorkspaceIslandApp.jsx").read_text(encoding="utf-8")

        self.assertIn('if (model?.layer === "paper_focus" || model?.layer === "literature_paper_focus")', source)
        self.assertIn("buildUnderstandingPaperFocusFlowModel(model, onNavigate)", source)

    def test_workspace_island_has_experiments_specific_layout(self):
        source = (ROOT / "dashboard" / "workspace-island" / "src" / "WorkspaceIslandApp.jsx").read_text(encoding="utf-8")
        styles = (ROOT / "dashboard" / "workspace-island" / "src" / "workspace-island.css").read_text(encoding="utf-8")

        self.assertIn("function buildExperimentsOverviewFlowModel", source)
        self.assertIn("function buildExperimentsArenaFocusFlowModel", source)
        self.assertIn("function buildExperimentsDesignFocusFlowModel", source)
        self.assertIn("workspaceExperimentArenaNode", source)
        self.assertIn("workspaceExperimentEntityNode", source)
        self.assertIn("workspaceExperimentMethodPanelNode", source)
        self.assertIn("workspaceRunResultNode", source)
        self.assertIn("function toExperimentEdge", source)
        self.assertIn('model?.layer === "experiment_design_focus"', source)
        self.assertIn("Evaluation Context", source)
        self.assertIn('node.entity_type === "evaluation_context"', source)
        self.assertIn("Design Method", source)
        self.assertIn("Runs / Results", source)
        self.assertIn('const graphKey = `${model?.mode || ""}:${model?.layer || ""}:${model?.focus_id || ""}`;', source)
        self.assertIn("key={graphKey}", source)
        self.assertIn(".workspace-experiment-arena-node", styles)
        self.assertIn(".workspace-experiment-entity-node", styles)
        self.assertIn(".workspace-experiment-arena-node strong", styles)
        self.assertIn(".workspace-experiment-context-panel", styles)
        self.assertIn("workspaceExperimentContextPanelNode", source)
        self.assertNotIn("font-size: 18px;", styles)
        self.assertNotIn(".workspace-experiment-arena-node strong,\n.workspace-run-result-node strong", styles)
        self.assertNotIn("overflow-wrap: anywhere;", styles.split(".workspace-experiment-arena-node", 1)[1].split(".workspace-experiment-entity-node", 1)[0])
        design_focus = source.split("function buildExperimentsDesignFocusFlowModel", 1)[1].split(
            "function buildExperimentsOverviewFlowModel", 1
        )[0]
        self.assertIn('type: "workspaceExperimentMethodPanelNode"', design_focus)
        self.assertNotIn('["model", "baseline", "protocol", "ablation"].includes(node.entity_type)', design_focus)
        self.assertIn("workspace-experiment-method-group-button nodrag", source)
        self.assertIn("data.onNodeAction?.(group.target)", source)
        self.assertIn('selected_id: `${methodNode.id}:${kind}`', source)
        self.assertIn("const runNodeStep = 152;", design_focus)
        self.assertIn("const runNodeHeight = 112;", design_focus)
        self.assertNotIn("runNodes.length * 112 + 92", design_focus)

    def test_workspace_island_arena_focus_does_not_render_runs_column(self):
        source = (ROOT / "dashboard" / "workspace-island" / "src" / "WorkspaceIslandApp.jsx").read_text(encoding="utf-8")

        self.assertIn("function buildExperimentsDesignFocusFlowModel", source)
        arena_focus = source.split("function buildExperimentsArenaFocusFlowModel", 1)[1].split(
            "function buildExperimentsDesignFocusFlowModel", 1
        )[0]
        self.assertNotIn('entity_type === "run"', arena_focus)
        self.assertNotIn('title: "Runs / Results"', arena_focus)

    def test_workspace_island_reuses_root_and_supports_immersive_focus(self):
        source = (ROOT / "dashboard" / "workspace-island" / "src" / "WorkspaceIslandApp.jsx").read_text(encoding="utf-8")
        styles = (ROOT / "dashboard" / "workspace-island" / "src" / "workspace-island.css").read_text(encoding="utf-8")

        self.assertIn("previous.render(<WorkspaceIslandApp {...props} />);", source)
        self.assertNotIn("if (previous) previous.unmount();", source)
        self.assertIn("workspace-island-focus-button", source)
        self.assertIn("workspace-island-immersive-active", source)
        self.assertIn("isImmersive ? \"Exit\" : \"Focus\"", source)
        self.assertIn(".workspace-island-shell.is-immersive", styles)
        self.assertIn("position: fixed;", styles)
        self.assertIn("body.workspace-island-immersive-active", styles)

    def test_workspace_claim_focus_stacks_argument_lanes(self):
        source = (ROOT / "dashboard" / "workspace-island" / "src" / "WorkspaceIslandApp.jsx").read_text(encoding="utf-8")

        self.assertIn("function claimFocusFrameHeight", source)
        self.assertIn("function buildClaimFocusLaneLayout", source)
        self.assertIn("leftStackY += evidenceHeight + laneGap;", source)

    def test_workspace_claim_focus_argument_atoms_are_inspector_buttons(self):
        source = (ROOT / "dashboard" / "workspace-island" / "src" / "WorkspaceIslandApp.jsx").read_text(encoding="utf-8")

        self.assertIn("const canInspect = Boolean(node.inspector);", source)
        self.assertIn("className={`workspace-argument-atom tone-${data.tone || \"x\"}`}", source)
        self.assertIn("onClick={() => data.onNodeAction?.(node)}", source)
        self.assertIn('frameHeight: claimFocusFrameHeight((nodeCounts.get("warrant") || 0))', source)
        self.assertNotIn('{ key: "warrant", title: "Warrants / Bridges", tone: "w", x: 720, y: 310', source)

    def test_workspace_island_visual_style_guardrails(self):
        css = (ROOT / "dashboard" / "workspace-island" / "src" / "workspace-island.css").read_text(encoding="utf-8")

        self.assertIn(".workspace-knowledge-canvas", css)
        self.assertIn("--workspace-grid-color", css)
        self.assertIn("--workspace-minimap-mask", css)
        self.assertIn(".workspace-stage-breadcrumb", css)
        self.assertIn(".workspace-node-card", css)
        self.assertIn(".workspace-node-card.is-dimmed", css)
        self.assertIn(".workspace-node-card.is-selected", css)
        self.assertIn(".workspace-knowledge-canvas .react-flow__controls-button", css)
        self.assertIn(".workspace-knowledge-canvas .react-flow__minimap", css)
        self.assertIn(".workspace-knowledge-canvas.is-literature .workspace-node-card", css)
        self.assertIn("height: calc(100vh - 215px)", css)
        self.assertIn("min-height: 0", css)
        self.assertIn("overflow-y: auto", css)
        self.assertIn(".workspace-lane-frame", css)
        self.assertIn(".workspace-argument-atom", css)
        self.assertIn(".workspace-paper-source-node", css)
        self.assertNotIn("background: var(--surface-2);\n  cursor: pointer;\n}", css)

    def test_lineage_atlas_uses_shallow_model_not_project_graph_builders(self):
        source = (
            ROOT / "dashboard" / "lineage-atlas" / "src" / "LineageAtlasApp.jsx"
        ).read_text(encoding="utf-8")

        self.assertIn("function buildLineageAtlasModel", source)
        self.assertIn("routeNode", source)
        self.assertIn("paperNode", source)
        self.assertNotIn("buildProjectGraphFlowModel", source)
        self.assertNotIn("buildClaimFocusFlowModel", source)
        self.assertNotIn("paperArgumentNode", source)

    def test_lineage_atlas_shallow_model_code_quality_guards(self):
        source = (
            ROOT / "dashboard" / "lineage-atlas" / "src" / "LineageAtlasApp.jsx"
        ).read_text(encoding="utf-8")

        self.assertIn("function sanitizeLineageItems", source)
        self.assertIn("function firstNonEmptyText(...values)", source)
        self.assertIn('const text = String(value || "").replace(/\\s+/g, " ").trim();', source)
        self.assertIn("return text;", source)
        self.assertIn('typeof item === "object"', source)
        self.assertIn("encodeURIComponent(String(value || prefix))", source)
        self.assertIn("map.display?.topic_name", source)
        self.assertIn("firstNonEmptyText(", source)
        self.assertIn("cleanLineageTitle(map.title)", source)
        self.assertLess(source.index("map.topic_name"), source.index("map.display?.topic_name"))
        self.assertLess(source.index("map.display?.topic_name"), source.index("cleanLineageTitle(map.title)"))
        self.assertLess(source.index("cleanLineageTitle(map.title)"), source.index("project.title"))
        self.assertLess(source.index("project.title"), source.index("project.name"))
        self.assertLess(source.index("project.name"), source.index("project.id"))
        self.assertIn('flowSafeId("route", route.id)', source)
        self.assertIn('flowIndexedId("paper", paperEntry.index, paperEntry.rawIdOrFallback)', source)
        self.assertIn("paperNodeIdByRawId", source)
        self.assertIn("paperNodeIdByRawId.get(edge.source)", source)
        self.assertIn("Array.isArray(map.explicit_edges) ? sanitizeLineageItems(map.explicit_edges) : []", source)
        self.assertIn("explicitEdges.forEach((edge, edgeIndex) => {", source)
        self.assertIn("`explicit:${edgeIndex}:${source}:${target}:${flowSafeId(\"relation\", edge.relation)}`", source)
        self.assertIn("const roles = Array.isArray(paper.roles) ? paper.roles : []", source)
        self.assertIn("if (query && !routeMatchesQuery && routePapers.length === 0) return;", source)
        self.assertIn('className="lineage-atlas-node-button"', source)
        self.assertNotIn("<button\n      type=\"button\"\n      className={`lineage-atlas-route-node", source)
        self.assertIn("export function mount(element, propsOrMap = {}, maybeProject = {})", source)
        self.assertIn('propsOrMap && ("map" in propsOrMap || "project" in propsOrMap)', source)
        self.assertIn(": { map: propsOrMap, project: maybeProject };", source)
        self.assertIn("<LineageAtlasApp {...props} />", source)

    def test_lineage_atlas_has_controls_and_inspector_states(self):
        source = (
            ROOT / "dashboard" / "lineage-atlas" / "src" / "LineageAtlasApp.jsx"
        ).read_text(encoding="utf-8")

        self.assertIn("lineage-atlas-controlbar", source)
        self.assertIn("Show edges", source)
        self.assertIn("Search papers and routes", source)
        self.assertIn("LineageInspector", source)
        self.assertIn("source evidence", source.lower())

    def test_lineage_atlas_inspector_sanitizes_source_urls_and_visible_selection(self):
        source = (
            ROOT / "dashboard" / "lineage-atlas" / "src" / "LineageAtlasApp.jsx"
        ).read_text(encoding="utf-8")

        self.assertIn("function safeExternalSourceUrl(value)", source)
        self.assertIn("const url = new URL(raw);", source)
        self.assertIn('["http:", "https:"].includes(url.protocol)', source)
        self.assertIn("const sourceUrl = safeExternalSourceUrl(firstNonEmptyText(paper.source_url, paper.url));", source)
        self.assertIn('href={sourceUrl}', source)
        self.assertNotIn('href={firstNonEmptyText(paper.source_url, paper.url)}', source)
        self.assertIn("const inspectorSelection = useMemo(", source)
        self.assertIn("const visibleNodeIds = new Set(model.nodes.map((node) => node.id));", source)
        self.assertIn('return { type: "map" };', source)
        self.assertIn("selected={inspectorSelection}", source)

    def test_lineage_atlas_fallback_filters_non_object_items(self):
        app = (ROOT / "dashboard" / "app.js").read_text(encoding="utf-8")

        self.assertIn(
            'map.routes.filter((route) => route && typeof route === "object" && !Array.isArray(route))',
            app,
        )
        self.assertIn(
            'map.papers.filter((paper) => paper && typeof paper === "object" && !Array.isArray(paper))',
            app,
        )

    def test_dashboard_index_passes_lineage_atlas_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lineage_dir = root / "wiki" / "projects" / "DemoProject" / "literature-rounds" / "demo-round"
            lineage_dir.mkdir(parents=True)
            (lineage_dir / "related-work-lineage.json").write_text(
                json.dumps(
                    {
                        "schema_version": "related-work-lineage-v1",
                        "project": "DemoProject",
                        "round": "demo-round",
                        "title": "Demo Lineage Atlas",
                        "status": "candidate",
                        "topic_name": "Visual Affordance Grounding",
                        "source_boundary": "related_work_lineage_only_not_graph_truth",
                        "display": {"layout": "atlas", "focus": "field"},
                        "route_narrowing": {
                            "input_mode": "baseline_papers",
                            "user_direction": "Map visual affordance grounding related work.",
                            "selected_anchor_papers": ["paper-1"],
                            "candidate_routes": [],
                        },
                        "baseline_paper_field_scope": {
                            "primary_problem": "Grounding visible affordances for action.",
                            "input_output": "Images to actionable affordance labels.",
                            "benchmarks_or_datasets": ["DemoBench"],
                            "evaluation_setting": "Offline benchmark comparison.",
                            "survey_boundary": "Vision-language affordance grounding.",
                            "exclusion_rules": ["Exclude pure robotics control papers."],
                            "field_structure": {
                                "lane_axis": {
                                    "name": "supervision_regime",
                                    "why_this_axis_defines_field_structure": "It separates how affordance evidence enters the model.",
                                    "selected_lanes": ["supervised", "language-grounded"],
                                },
                                "non_lane_axes": [],
                            },
                            "derived_taxonomy": [
                                {
                                    "axis": "supervision_regime",
                                    "values": ["supervised", "language-grounded"],
                                }
                            ],
                        },
                        "axis_candidates": [
                            {
                                "axis": "supervision_regime",
                                "lanes": ["supervised", "language-grounded"],
                                "source": ["paper-1"],
                                "why_field_native": "The literature groups methods by supervision source.",
                                "risk": "May hide deployment setting.",
                                "tests": {
                                    "baseline_removal": "Still separates neighbor papers.",
                                    "neighbor_paper": "Neighbor papers use same distinction.",
                                    "project_intent": "Matches affordance grounding scope.",
                                    "non_component": "Not a model component.",
                                },
                                "decision": "selected",
                                "reason": "Best field-level axis.",
                            }
                        ],
                        "routes": [
                            {
                                "id": "supervised",
                                "label": "Supervised",
                                "description": "Explicit affordance labels.",
                                "review_status": "candidate",
                            },
                            {
                                "id": "language-grounded",
                                "label": "Language Grounded",
                                "description": "Language supervision and grounding.",
                                "review_status": "candidate",
                            },
                        ],
                        "papers": [
                            {
                                "id": "paper-1",
                                "kind": "paper",
                                "title": "Demo Affordance Paper",
                                "source_url": "https://example.org/paper-1",
                                "source_evidence": "Demo fixture.",
                                "identity": {"doi": "10.0000/demo"},
                                "route": "supervised",
                                "field_position": "Supervised affordance labels.",
                                "method_setting": "Image classification.",
                                "artifact_type": "Benchmark paper.",
                                "review_status": "candidate",
                            },
                            {
                                "id": "paper-2",
                                "kind": "paper",
                                "title": "Language Grounded Affordance Paper",
                                "source_url": "https://example.org/paper-2",
                                "source_evidence": "Demo fixture.",
                                "identity": {"doi": "10.0000/demo2"},
                                "route": "language-grounded",
                                "field_position": "Language-grounded affordance labels.",
                                "method_setting": "Vision-language retrieval.",
                                "artifact_type": "Method paper.",
                                "review_status": "candidate",
                            },
                        ],
                        "explicit_edges": [
                            {
                                "source": "paper-1",
                                "target": "paper-2",
                                "relation": "influences",
                                "rationale": "Later paper builds on supervised framing.",
                                "confidence": "medium",
                                "source_evidence": "Demo fixture.",
                                "review_status": "candidate",
                            }
                        ],
                        "major_trends": [
                            {
                                "name": "Language grounding",
                                "evidence_papers": ["paper-2"],
                            }
                        ],
                        "notable_forks": [
                            {
                                "name": "Label source split",
                                "sides": ["supervised", "language-grounded"],
                            }
                        ],
                        "search_log": [
                            {
                                "query_type": "taxonomy-derived",
                                "query": "visual affordance grounding language supervision",
                            }
                        ],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            index = build_index(root)

        self.assertEqual(len(index.get("lineage_maps", [])), 1)
        lineage_map = index["lineage_maps"][0]

        self.assertEqual(lineage_map.get("id"), "DemoProject/demo-round")
        self.assertEqual(lineage_map.get("topic_name"), "Visual Affordance Grounding")
        self.assertTrue(lineage_map.get("baseline_paper_field_scope"))
        self.assertIsInstance(lineage_map.get("baseline_paper_field_scope"), dict)
        self.assertIsInstance(lineage_map.get("axis_candidates"), list)
        self.assertIsInstance(lineage_map.get("major_trends"), list)
        self.assertIsInstance(lineage_map.get("notable_forks"), list)
        self.assertIsInstance(lineage_map.get("search_log"), list)

    def test_dashboard_index_type_gates_lineage_atlas_map_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lineage_dir = root / "wiki" / "projects" / "DemoProject" / "literature-rounds" / "demo-round"
            lineage_dir.mkdir(parents=True)
            (lineage_dir / "related-work-lineage.json").write_text(
                '{"project":"DemoProject","round":"demo-round","display":[],"baseline_paper_field_scope":"invalid","route_narrowing":[]}\n',
                encoding="utf-8",
            )

            index = build_index(root)

        self.assertEqual(index["lineage_maps"][0]["display"], {})
        self.assertEqual(index["lineage_maps"][0]["baseline_paper_field_scope"], {})
        self.assertEqual(index["lineage_maps"][0]["route_narrowing"], {})

    def test_styles_contain_lineage_atlas_selectors(self):
        css = (
            ROOT / "dashboard" / "lineage-atlas" / "src" / "lineage-atlas.css"
        ).read_text(encoding="utf-8")
        dashboard_css = (ROOT / "dashboard" / "styles.css").read_text(encoding="utf-8")

        self.assertIn("min-height: calc(100vh - 150px)", css)
        self.assertIn(".lineage-atlas-shell", css)
        self.assertIn(".lineage-atlas-topic-node", css)
        self.assertIn(".lineage-atlas-route-node", css)
        self.assertIn(".lineage-atlas-paper-node", css)
        self.assertIn(".lineage-atlas-inspector", css)
        self.assertIn(".react-flow__controls-button", css)
        self.assertIn("--graph-grid-color", css)
        self.assertIn(".lineage-map-shell:has(.lineage-atlas-root)", dashboard_css)

    def test_demo_badge_renders_for_demo_projects(self):
        script = textwrap.dedent(
            """
            const fs = require("fs");
            const vm = require("vm");
            const assert = require("assert");

            const elements = {
              "page-title": { textContent: "", innerHTML: "", className: "" },
              "page-subtitle": { textContent: "", innerHTML: "", className: "" },
              "page-kicker": { textContent: "", innerHTML: "", className: "" },
              "page-content": { textContent: "", innerHTML: "", className: "" },
              "project-nav": { textContent: "", innerHTML: "", className: "" },
            };
            const body = {
              dataset: { page: "projects" },
              querySelector: () => null,
            };
            const document = {
              body,
              documentElement: { dataset: {} },
              getElementById: (id) => elements[id] || null,
              querySelector: () => null,
              querySelectorAll: () => [],
            };
            const window = {
              location: { search: "" },
              localStorage: { getItem: () => null, setItem: () => null },
            };
            const context = {
              console,
              document,
              window,
              URL,
              URLSearchParams,
              Map,
              Set,
              fetch: async () => ({ ok: true, json: async () => ({}) }),
              setTimeout,
              clearTimeout,
              requestAnimationFrame: () => 0,
              cancelAnimationFrame: () => {},
            };
            vm.createContext(context);
            const source = fs.readFileSync("__APP_JS__", "utf8").replace(/\\nboot\\(\\);\\s*$/, "\\n");
            vm.runInContext(source, context);

            assert.equal(context.renderDemoBadge({ demo: true }), '<span class="demo-badge">Demo</span>');
            assert.equal(context.renderDemoBadge({ demo: false }), "");
            assert.equal(context.renderDemoBadge({}), "");

            vm.runInContext(`
              state.data = {
                schema_version: "research-browser-v2",
                projects: [
                  {
                    id: "DemoProject",
                    title: "Demo Project",
                    demo: true,
                    overview: { direction: "Demo direction" },
                    stats: {},
                  }
                ],
                papers: [],
                literature_rounds: [],
                lineage_maps: [],
              };
            `, context);
            context.renderProjectsIndex();
            assert(elements["page-content"].innerHTML.includes('<span class="demo-badge">Demo</span>'));
            """
        ).replace("__APP_JS__", (ROOT / "dashboard" / "app.js").as_posix())
        completed = subprocess.run(
            ["node", "-e", script],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)

    def test_lineage_rendering_regressions(self):
        script = textwrap.dedent(
            """
            const fs = require("fs");
            const vm = require("vm");
            const assert = require("assert");

            const elements = {{
              "page-title": {{ textContent: "", innerHTML: "", className: "" }},
              "page-subtitle": {{ textContent: "", innerHTML: "", className: "" }},
              "page-kicker": {{ textContent: "", innerHTML: "", className: "" }},
              "page-content": {{ textContent: "", innerHTML: "", className: "" }},
              "project-nav": {{ textContent: "", innerHTML: "", className: "" }},
            }};
            const body = {{
              dataset: {{ page: "lineage" }},
              querySelector: () => null,
            }};
            const document = {{
              body,
              documentElement: {{ dataset: {{}} }},
              getElementById: (id) => elements[id] || null,
              querySelector: () => null,
              querySelectorAll: () => [],
            }};
            const window = {{
              location: {{ search: "?project=DemoProject&round=selected-round" }},
              localStorage: {{ getItem: () => null, setItem: () => null }},
            }};
            const context = {{
              console,
              document,
              window,
              URL,
              URLSearchParams,
              Map,
              Set,
              fetch: async () => ({{ ok: true, json: async () => ({{}}) }}),
              setTimeout,
              clearTimeout,
              requestAnimationFrame: () => 0,
              cancelAnimationFrame: () => {{}},
            }};
            vm.createContext(context);
            const source = fs.readFileSync("__APP_JS__", "utf8").replace(/\\nboot\\(\\);\\s*$/, "\\n");
            vm.runInContext(source, context);

            const map = {{
              project: "DemoProject",
              round: "selected-round",
              title: "Selected Round",
              valid: true,
              status: "candidate",
              routes: [
                {{ id: "route-1", label: "Route <One>", description: "Desc", review_status: "candidate" }},
              ],
              papers: [
                {{
                  id: "paper-1",
                  title: "<img src=x onerror=alert(1)>",
                  summary: "<script>alert(1)</script>",
                  route: "route-1",
                  source_url: "javascript:alert(1)",
                  review_status: "candidate",
                }},
              ],
              explicit_edges: [],
            }};
            const table = context.renderLineagePaperTable(map);
            assert(!table.includes('href="javascript:alert(1)"'), table);
            assert(table.includes("unsafe source_url"), table);
            assert.equal(context.safeExternalSourceUrl("https://example.org/paper"), "https://example.org/paper");
            assert.equal(context.safeExternalSourceUrl("http://example.org/paper"), "http://example.org/paper");
            assert.equal(context.safeExternalSourceUrl("/relative/paper"), "");
            assert.equal(context.safeExternalSourceUrl("javascript:alert(1)"), "");

            const node = context.renderLineagePaperNode(map.papers[0]);
            assert(node.includes("&lt;img src=x onerror=alert(1)&gt;"), node);
            assert(node.includes("&lt;script&gt;alert(1)&lt;/script&gt;"), node);
            assert(!node.includes("<script>alert(1)</script>"), node);

            const graphMap = {
              ...map,
              routes: [
                { id: "route-1", label: "Route One", description: "Desc", review_status: "candidate" },
                { id: "route-2", label: "Route Two", description: "Desc", review_status: "candidate" },
              ],
              papers: [
                { id: "paper-1", title: "Paper <One>", year: 2021, month: "01", route: "route-1", review_status: "candidate" },
                { id: "paper-2", title: "Paper Two", year: 2022, month: "02", route: "route-1", review_status: "candidate" },
                { id: "paper-3", title: "Paper Three", year: 2023, month: "03", route: "route-2", review_status: "candidate" },
              ],
              explicit_edges: [
                { source: "paper-2", target: "paper-3", relation: "influences", confidence: "medium", review_status: "candidate", rationale: "Cross route" },
              ],
            };
            const graph = context.renderLineageGraph(graphMap);
            assert(graph.includes("<svg"), graph);
            assert(graph.includes("lineage-graph-node"), graph);
            assert(graph.includes("lineage-graph-sequence-edge"), graph);
            assert(graph.includes("lineage-graph-explicit-edge"), graph);
            assert(graph.includes('data-paper-id="paper-1"'), graph);
            assert(graph.includes("Paper &lt;One&gt;"), graph);
            assert(!graph.includes("Paper <One>"), graph);

            const fallback = context.renderLineageAtlasFallback({
              title: "Fallback",
              routes: [
                null,
                "bad-route",
                { id: "route-1", label: "Route One", description: "Desc", review_status: "candidate" },
              ],
              papers: [
                null,
                "bad-paper",
                { id: "paper-1", title: "Paper One", route: "route-1", review_status: "candidate" },
              ],
            });
            assert(fallback.includes("Route One"), fallback);
            assert(fallback.includes("Paper One"), fallback);
            assert(!fallback.includes("bad-route"), fallback);
            assert(!fallback.includes("bad-paper"), fallback);

            context.fixtureMaps = [
              {{ ...map, id: "DemoProject/zz-round", round: "zz-round", title: "ZZ Round" }},
              {{ ...map, id: "DemoProject/selected-round", round: "selected-round", title: "Selected Round" }},
            ];
            vm.runInContext(`
              state.data = {{
                schema_version: "research-browser-v2",
                projects: [{{ id: "DemoProject", title: "Demo Project" }}],
                lineage_maps: fixtureMaps,
              }};
              state.projectId = "DemoProject";
            `, context);
            context.renderLineagePage();
            assert.equal(elements["page-title"].textContent, "Selected Round");

            window.location.search = "?project=DemoProject";
            context.renderLineagePage();
            assert.equal(elements["page-title"].textContent, "ZZ Round");
            """
        ).replace("__APP_JS__", (ROOT / "dashboard" / "app.js").as_posix()).replace("{{", "{").replace("}}", "}")
        completed = subprocess.run(
            ["node", "-e", script],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)


if __name__ == "__main__":
    unittest.main()
