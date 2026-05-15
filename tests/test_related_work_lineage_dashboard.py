import json
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

from tools.build_dashboard_index import build_index


ROOT = Path(__file__).resolve().parents[1]


class RelatedWorkLineageDashboardTest(unittest.TestCase):
    def test_lineage_page_exists_with_page_marker(self):
        html = (ROOT / "dashboard" / "lineage.html").read_text(encoding="utf-8")

        self.assertIn('data-page="lineage"', html)
        self.assertIn('href="./lineage-atlas.bundle.css"', html)
        self.assertIn('src="./lineage-atlas.bundle.js"', html)

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

    def test_dashboard_index_fetch_bypasses_browser_cache(self):
        app = (ROOT / "dashboard" / "app.js").read_text(encoding="utf-8")

        self.assertIn('fetch("/.dashboard/index.json", { cache: "no-store" })', app)

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
