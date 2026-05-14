import subprocess
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class RelatedWorkLineageDashboardTest(unittest.TestCase):
    def test_lineage_page_exists_with_page_marker(self):
        html = (ROOT / "dashboard" / "lineage.html").read_text(encoding="utf-8")

        self.assertIn('data-page="lineage"', html)

    def test_app_contains_lineage_page_hooks(self):
        app = (ROOT / "dashboard" / "app.js").read_text(encoding="utf-8")

        self.assertIn("function safeExternalSourceUrl(value)", app)
        self.assertIn("function lineageUrl(projectId, roundName)", app)
        self.assertIn("function renderLineagePage()", app)
        self.assertIn("function renderLineageGraph(map)", app)
        self.assertIn('state.page === "lineage"', app)

    def test_styles_contain_lineage_selectors(self):
        css = (ROOT / "dashboard" / "styles.css").read_text(encoding="utf-8")

        self.assertIn(".lineage-map-shell", css)
        self.assertIn(".lineage-graph-panel", css)
        self.assertIn(".lineage-graph-node", css)
        self.assertIn(".lineage-graph-explicit-edge", css)
        self.assertIn(".lineage-lane", css)
        self.assertIn(".lineage-paper-node", css)

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
