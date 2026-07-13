import json
import re
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).parent.parent
INDEX_HTML = (PROJECT_ROOT / "index.html").read_text(encoding="utf-8")
STYLE_CSS = (PROJECT_ROOT / "static/css/style.css").read_text(encoding="utf-8")
VERCEL_CONFIG = json.loads((PROJECT_ROOT / "vercel.json").read_text(encoding="utf-8"))


class FrontendContractTests(unittest.TestCase):
    def test_address_lookups_use_one_shared_request_path(self):
        self.assertEqual(INDEX_HTML.count("var url = '/api/address/'"), 1)
        self.assertEqual(INDEX_HTML.count("fetch(url, { signal: controller.signal })"), 1)
        self.assertIn("fetchAddressResults(query)", INDEX_HTML)
        self.assertIn("return fetchAddressResults(value)", INDEX_HTML)
        address_helper = re.search(r'function fetchAddressResults\(value\).*?\n    }', INDEX_HTML, re.DOTALL)
        self.assertIsNotNone(address_helper)
        self.assertNotIn("function attempt", address_helper.group(0))
        self.assertIn("controller.abort()", address_helper.group(0))
        self.assertIn("signal: controller.signal", address_helper.group(0))
        self.assertIn("}, 10000)", address_helper.group(0))
        self.assertNotIn("searchAddresses(value, dropdown, target)", INDEX_HTML)
        self.assertEqual(INDEX_HTML.count("landInput.addEventListener('keydown'"), 1)
        self.assertIn("cancelPendingAddressAutocomplete();", INDEX_HTML)

    def test_mobile_drawer_contains_primary_navigation(self):
        sidebar = re.search(r'<aside class="sidebar".*?</aside>', INDEX_HTML, re.DOTALL)
        self.assertIsNotNone(sidebar)
        for target in ("#meist", "#allikad", "#kontakt", "#tagasiside"):
            self.assertIn(f'href="{target}"', sidebar.group(0))
        self.assertIn("sidebar.querySelectorAll('.sidebar-nav a')", INDEX_HTML)

    def test_mobile_does_not_download_hidden_hero_images(self):
        hero_trees = re.search(r'<div class="hero-trees".*?</div>\s*</div>', INDEX_HTML, re.DOTALL)
        self.assertIsNotNone(hero_trees)
        self.assertEqual(hero_trees.group(0).count('media="(min-width: 769px)"'), 6)
        self.assertNotRegex(hero_trees.group(0), r'<img[^>]+src="/static/img/tree-')

    def test_mobile_load_does_not_force_focus_or_eager_wms(self):
        self.assertIn("window.matchMedia('(pointer: fine) and (min-width: 769px)').matches", INDEX_HTML)
        self.assertNotIn("}).addTo(map);\n\n        // Click anywhere", INDEX_HTML)
        self.assertIn("IntersectionObserver", INDEX_HTML)
        self.assertIn("{ rootMargin: '0px' }", INDEX_HTML)

    def test_mobile_header_search_target_is_at_least_44_pixels(self):
        self.assertIn(".search-box button { width: 44px; height: 44px;", STYLE_CSS)
        self.assertNotIn(".hero .search-box button { width: 38px; height: 38px;", STYLE_CSS)
        self.assertIn(".map-hint-close { width: 44px; height: 44px;", STYLE_CSS)
        self.assertIn(".ai-hint { min-height: 44px;", STYLE_CSS)
        self.assertIn(".toggle-item { min-height: 44px;", STYLE_CSS)
        self.assertIn(".kiht-legend-close { width: 44px; height: 44px;", STYLE_CSS)
        self.assertNotIn("transform: scale(0.95)", STYLE_CSS)

    def test_unhashed_static_assets_are_revalidated(self):
        static_rule = next(rule for rule in VERCEL_CONFIG["headers"] if rule["source"] == "/static/(.*)")
        cache_control = next(header["value"] for header in static_rule["headers"] if header["key"] == "Cache-Control")
        self.assertNotIn("immutable", cache_control)
        self.assertIn("must-revalidate", cache_control)

    def test_changed_stylesheet_busts_the_previous_immutable_url(self):
        self.assertIn('/static/css/style.css?r=jkl103', INDEX_HTML)
        self.assertNotIn('/static/css/style.css?r=jkl102', INDEX_HTML)
        self.assertNotIn('/static/css/style.css?r=jkl101', INDEX_HTML)

    def test_chart_library_loads_only_when_results_need_it(self):
        head = INDEX_HTML.split("</head>", 1)[0]
        self.assertNotIn('/static/js/chart.umd.min.js', head)
        self.assertIn("script.src = '/static/js/chart.umd.min.js'", INDEX_HTML)
        self.assertIn("renderId !== compositionChartRenderSequence", INDEX_HTML)
        search_start = re.search(
            r'async function doSearch\(\).*?var requestId = \+\+parcelSearchSequence;\s*var chartRenderId = \+\+compositionChartRenderSequence;',
            INDEX_HTML,
            re.DOTALL,
        )
        self.assertIsNotNone(search_start)

    def test_frontend_uses_official_metsaregister_species_labels(self):
        for mapping in (
            "KS: 'kask'", "LM: 'sanglepp'", "LV: 'hall lepp'",
            "RE: 'remmelgas'", "SP: 'sarapuu'", "PK: 'paakspuu'",
        ):
            self.assertIn(mapping, INDEX_HTML)
        for invented_name in ("Harilik kask", "Harilik remmelgas", "Salu-lepp"):
            self.assertNotIn(invented_name, INDEX_HTML)

    def test_forest_data_age_and_historical_clearcuts_are_explained(self):
        self.assertIn("Terrapointi värskushoiatuse lävend", INDEX_HTML)
        self.assertIn("Metsateatis näitab kavandatud või lubatud raiet", INDEX_HTML)
        self.assertIn("Ajalooline lageraie tuvastus", INDEX_HTML)
        self.assertIn("2011–2016", INDEX_HTML)
        self.assertIn("üldjuhul olema uuenenud 5 aasta jooksul", INDEX_HTML)
        self.assertIn("10 aasta jooksul", INDEX_HTML)
        self.assertIn("safe(renderTeatised, data.teatised, 'teatised', data.teatised_meta)", INDEX_HTML)
        self.assertIn("totalRows + ' eraldiseridu'", INDEX_HTML)
        self.assertNotIn("Krundil on tuvastatud hiljutine lageraie", INDEX_HTML)

    def test_no_forest_result_always_clears_the_previous_composition_chart(self):
        self.assertIn("renderCompositionChart(data.mets && data.mets.liikide_koosseis || [], chartRenderId)", INDEX_HTML)
        self.assertIn("compositionChart.destroy();", INDEX_HTML)
        self.assertIn("wrap.style.display = 'none';", INDEX_HTML)


if __name__ == "__main__":
    unittest.main()
