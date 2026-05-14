import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class RelatedWorkLineageDashboardTest(unittest.TestCase):
    def test_lineage_page_exists_with_page_marker(self):
        html = (ROOT / "dashboard" / "lineage.html").read_text(encoding="utf-8")

        self.assertIn('data-page="lineage"', html)

    def test_app_contains_lineage_page_hooks(self):
        app = (ROOT / "dashboard" / "app.js").read_text(encoding="utf-8")

        self.assertIn("function lineageUrl(projectId, roundName)", app)
        self.assertIn("function renderLineagePage()", app)
        self.assertIn('state.page === "lineage"', app)

    def test_styles_contain_lineage_selectors(self):
        css = (ROOT / "dashboard" / "styles.css").read_text(encoding="utf-8")

        self.assertIn(".lineage-map-shell", css)
        self.assertIn(".lineage-lane", css)
        self.assertIn(".lineage-paper-node", css)


if __name__ == "__main__":
    unittest.main()
