import json
import re
import subprocess
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).parent.parent
INDEX_HTML = (PROJECT_ROOT / "index.html").read_text(encoding="utf-8")
STYLE_CSS = (PROJECT_ROOT / "static/css/style.css").read_text(encoding="utf-8")
FONT_SIZES_CSS = (PROJECT_ROOT / "static/css/font-sizes.css").read_text(encoding="utf-8")
API_PY = (PROJECT_ROOT / "api/index.py").read_text(encoding="utf-8")
VERCEL_CONFIG = json.loads((PROJECT_ROOT / "vercel.json").read_text(encoding="utf-8"))


def _marked_js_source(start_marker, end_marker):
    start = INDEX_HTML.index(start_marker) + len(start_marker)
    end = INDEX_HTML.index(end_marker, start)
    return INDEX_HTML[start:end]


def _extract_js_function(name):
    start = INDEX_HTML.index(f"function {name}(")
    brace = INDEX_HTML.index("{", start)
    depth = 0
    quote = None
    escaped = False
    line_comment = False
    block_comment = False
    index = brace
    while index < len(INDEX_HTML):
        char = INDEX_HTML[index]
        next_char = INDEX_HTML[index + 1] if index + 1 < len(INDEX_HTML) else ""
        if line_comment:
            if char == "\n":
                line_comment = False
        elif block_comment:
            if char == "*" and next_char == "/":
                block_comment = False
                index += 1
        elif quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
        elif char == "/" and next_char == "/":
            line_comment = True
            index += 1
        elif char == "/" and next_char == "*":
            block_comment = True
            index += 1
        elif char in ("'", '"', "`"):
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return INDEX_HTML[start:index + 1]
        index += 1
    raise AssertionError(f"Unclosed JavaScript function: {name}")


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
        self.assertIn(".map-workspace-button { min-width: 44px; min-height: 44px;", STYLE_CSS)
        self.assertIn(".map-view-preset { min-height: 44px;", STYLE_CSS)
        self.assertNotIn(".map-theme-toggle", STYLE_CSS)
        self.assertNotIn("transform: scale(0.95)", STYLE_CSS)

    def test_unhashed_static_assets_are_revalidated(self):
        static_rule = next(rule for rule in VERCEL_CONFIG["headers"] if rule["source"] == "/static/(.*)")
        cache_control = next(header["value"] for header in static_rule["headers"] if header["key"] == "Cache-Control")
        self.assertNotIn("immutable", cache_control)
        self.assertIn("must-revalidate", cache_control)

    def test_changed_stylesheet_busts_the_previous_immutable_url(self):
        self.assertIn('/static/css/style.css?r=jkl113', INDEX_HTML)
        self.assertNotIn('/static/css/style.css?r=jkl112', INDEX_HTML)
        self.assertNotIn('/static/css/style.css?r=jkl111', INDEX_HTML)
        self.assertNotIn('/static/css/style.css?r=jkl110', INDEX_HTML)
        self.assertNotIn('/static/css/style.css?r=jkl109', INDEX_HTML)
        self.assertIn('/static/css/font-sizes.css?r=jkl034', INDEX_HTML)
        self.assertNotIn('/static/css/style.css?r=jkl108', INDEX_HTML)
        self.assertNotIn('/static/css/style.css?r=jkl107', INDEX_HTML)
        self.assertNotIn('/static/css/style.css?r=jkl106', INDEX_HTML)
        self.assertNotIn('/static/css/font-sizes.css?r=jkl033', INDEX_HTML)
        self.assertNotIn('/static/css/style.css?r=jkl105', INDEX_HTML)
        self.assertNotIn('/static/css/style.css?r=jkl104', INDEX_HTML)
        self.assertNotIn('/static/css/style.css?r=jkl103', INDEX_HTML)
        self.assertNotIn('/static/css/style.css?r=jkl102', INDEX_HTML)

    def test_asset_passports_render_traceable_values_and_contextual_ai_actions(self):
        helper_start = INDEX_HTML.index("    function renderAssetPassports(passports, reliability)")
        helper_end = INDEX_HTML.index("    function renderVaartus(data)", helper_start)
        helper = INDEX_HTML[helper_start:helper_end]
        value_render = re.search(r'function renderVaartus\(data\).*?\n    }', INDEX_HTML, re.DOTALL)
        self.assertIsNotNone(value_render)
        self.assertIn("data.andmepassid", value_render.group(0))
        self.assertIn("var hasAssetPassports", value_render.group(0))
        self.assertIn("var timberPassport", value_render.group(0))
        self.assertIn("if (!hasAssetPassports || timberValueAvailable)", value_render.group(0))
        self.assertIn("if (!hasAssetPassports)", value_render.group(0))
        self.assertIn("renderAssetPassports", value_render.group(0))
        self.assertIn("asset-ai-btn", helper)
        self.assertIn("safeExternalUrl", helper)
        self.assertIn("tihumeetrit", helper)
        self.assertIn("data-ai-question", helper)
        self.assertIn("document.getElementById('dashboard').addEventListener('click'", INDEX_HTML)
        self.assertIn("aiSendMessage(question)", INDEX_HTML)
        self.assertIn('<span class="asset-range-separator" aria-hidden="true">–</span><span class="sr-only"> kuni </span>', helper)
        self.assertIn('<span class="asset-passport-heading">', helper)
        self.assertNotIn('<div class="asset-passport-heading">', helper)
        self.assertIn('id="ai-chat-status" class="sr-only" aria-live="polite"', INDEX_HTML)
        self.assertIn("function aiSetStatus(message)", INDEX_HTML)
        self.assertIn("function aiDrainQueue()", INDEX_HTML)
        self.assertIn("function aiQueueWaitMs(now)", INDEX_HTML)
        self.assertIn("function aiRejectQueue(message)", INDEX_HTML)
        self.assertIn("var next = aiMessageQueue[0]", INDEX_HTML)
        self.assertIn("if (!queuedEntry) aiAppendMessage('user', message);", INDEX_HTML)
        self.assertIn("function aiClearSubmittedInput(input, message)", INDEX_HTML)
        self.assertIn("if (!queuedEntry) aiClearSubmittedInput(input, message);", INDEX_HTML)
        self.assertNotIn("var nextMsg = aiMessageQueue.shift()", INDEX_HTML)
        self.assertNotIn("aiMessageQueue.push(pendingUserMsg)", INDEX_HTML)
        self.assertIn("kõrge: 'Kõrge lähteandmestik'", helper)
        self.assertIn("Puidustsenaariumide keskpunkt / ha", INDEX_HTML)
        self.assertIn("Sortimendita keskpunkt", INDEX_HTML)
        self.assertIn('<div>Eraldis ja lähteandmed</div><div style="text-align:right">Puidustsenaarium</div>', INDEX_HTML)
        self.assertNotIn("Puidu keskväärtus / ha", INDEX_HTML)
        self.assertNotIn("Kaalutud kännuraha", INDEX_HTML)
        self.assertNotIn("Vaata kinnistu turuväärtust", INDEX_HTML)
        self.assertIn("Keskpunkt ' + formatEur(midpoint)", INDEX_HTML)
        self.assertNotIn("metsa majanduslikku väärtust", INDEX_HTML)
        self.assertNotIn("kogu kinnistu väärtust eurodes", INDEX_HTML)

        script = f"""
            const EUR_FORMATTER = new Intl.NumberFormat('et-EE', {{style:'currency',currency:'EUR',maximumFractionDigits:0}});
            const DATE_FORMATTER = new Intl.DateTimeFormat('et-EE', {{day:'2-digit',month:'2-digit',year:'numeric',timeZone:'UTC'}});
            const NUMBER_FORMATTERS = {{}};
            function escHtml(value) {{ return String(value == null ? '' : value).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\"/g,'&quot;'); }}
            function formatEur(value) {{ return value == null ? '—' : EUR_FORMATTER.format(Math.round(value)); }}
            function formatNum(value) {{ return value == null ? '—' : new Intl.NumberFormat('et-EE').format(Number(value)); }}
            function formatDateEt(value) {{
              if (!value) return '—';
              const parts = String(value).slice(0, 10).split('-').map(Number);
              return DATE_FORMATTER.format(new Date(Date.UTC(parts[0], parts[1] - 1, parts[2])));
            }}
            function safeExternalUrl(value) {{ try {{ const url = new URL(String(value)); return url.protocol === 'https:' ? url.href : ''; }} catch (error) {{ return ''; }} }}
            {helper}
            const html = renderAssetPassports({json.dumps([
                {
                    "id": "forest_volume", "label": "Kasvava metsa tagavara", "available": True,
                    "value": 224, "unit": "m³", "provenance": "derived", "provenance_label": "Terrapointi tuletis",
                    "source": {"name": "Metsaregister", "url": "https://register.metsad.ee/otsiEraldis", "oldest_as_of": "2024-01-15", "newest_as_of": "2025-02-01"},
                    "methodology_sources": [{"label": "Veapiirid", "url": "https://www.riigiteataja.ee/akt/example"}],
                    "derivation": "Tagavara × pindala", "confidence": {"label": "Värske registriinfo", "reasons": ["Inventuur on värske."]},
                    "limitations": ["Ei ole raiutav kogus."], "ai_question": "Selgita & kontrolli"
                },
                {
                    "id": "land_reference", "label": "Maa ametlik referents", "available": False,
                    "unit": "€", "provenance": "official", "provenance_label": "Ametlik katastriandmestik",
                    "source": {"name": "Vale", "url": "javascript:alert(1)"}, "derivation": "Puudub",
                    "confidence": {"label": "Ametlik referentsväärtus", "reasons": []}, "limitations": [], "ai_question": "Selgita"
                }
            ], ensure_ascii=False)}, {{level:'madal'}});
            process.stdout.write(html);
        """
        html = subprocess.run(["node", "-e", script], check=True, capture_output=True, text=True).stdout
        self.assertIn("224", html)
        self.assertIn("m³", html)
        self.assertIn("ehk 224 tihumeetrit", html)
        self.assertIn("Terrapointi tuletis", html)
        self.assertIn("Metsaregister", html)
        self.assertIn("Andmed puuduvad", html)
        self.assertIn("Selgita &amp; kontrolli", html)
        self.assertIn("asset-trust-madal", html)
        self.assertNotIn("javascript:", html)
        self.assertLess(html.index("Kasvava metsa tagavara"), html.index("Maa ametlik referents"))

        for css_class in (
            ".asset-ledger", ".asset-trust-strip", ".asset-passport",
            ".asset-passport-origin", ".asset-ai-btn", ".asset-trust-kõrge",
        ):
            self.assertIn(css_class, STYLE_CSS)

        self.assertRegex(
            STYLE_CSS,
            r"(?m)^\.sr-only\s*\{[^}]*position:\s*absolute;[^}]*clip:\s*rect\(0, 0, 0, 0\);",
        )
        self.assertRegex(
            STYLE_CSS,
            r"(?m)^\.asset-ledger\s*\{[^}]*container-type:\s*inline-size;",
        )
        self.assertRegex(
            STYLE_CSS,
            r"(?s)@container\s*\(max-width:\s*420px\)\s*\{.*?\.asset-passport summary\s*\{[^}]*grid-template-columns:\s*minmax\(0, 1fr\) 16px;",
        )

    def test_dashboard_uses_desktop_space_without_widening_prose_sections(self):
        self.assertIn("--dashboard-max-w: min(calc(100vw - 48px), 1600px);", STYLE_CSS)
        self.assertRegex(
            STYLE_CSS,
            r"@media \(min-width: 769px\) \{\s*\.dashboard > \* \{[^}]*max-width: var\(--dashboard-max-w\);",
        )
        self.assertRegex(
            STYLE_CSS,
            r"(?m)^\.metrics-grid \{[^}]*grid-template-columns: repeat\(3, minmax\(0, 1fr\)\);",
        )
        self.assertRegex(
            STYLE_CSS,
            r"@media \(max-width: 1180px\) \{\s*\.metrics-grid \{ grid-template-columns: repeat\(2, minmax\(0, 1fr\)\); \}",
        )
        self.assertRegex(
            STYLE_CSS,
            r"@media \(max-width: 768px\) \{\s*\.metrics-grid \{ grid-template-columns: minmax\(0, 1fr\);",
        )
        self.assertRegex(STYLE_CSS, r"\.about-inner\s*\{\s*max-width:\s*980px;")
        self.assertRegex(STYLE_CSS, r"\.contact-inner\s*\{\s*max-width:\s*760px;")

    def test_dashboard_typography_has_readable_hierarchy_without_scale_hacks(self):
        desktop = re.search(r"(?m)^:root \{([^}]*)\}", FONT_SIZES_CSS)
        tablet = re.search(r"@media \(max-width: 1180px\) \{\s*:root \{([^}]*)\}", FONT_SIZES_CSS)
        mobile = re.search(r"@media \(max-width: 768px\) \{\s*:root \{([^}]*)\}", FONT_SIZES_CSS)
        self.assertIsNotNone(desktop)
        self.assertIsNotNone(tablet)
        self.assertIsNotNone(mobile)
        self.assertIn("--tier-1-title:  17px;", desktop.group(1))
        self.assertIn("--tier-2-row:    16px;", desktop.group(1))
        self.assertIn("--tier-3-table:  13px;", desktop.group(1))
        self.assertIn("--tier-1-title:  16px;", tablet.group(1))
        self.assertIn("--tier-2-row:    15.5px;", tablet.group(1))
        self.assertIn("--tier-2-row:    15px;", mobile.group(1))

        heading = re.search(r"(?m)^\.card-header h3 \{([^}]*)\}", STYLE_CSS)
        card = re.search(r"(?m)^\.metric-card \{([^}]*)\}", STYLE_CSS)
        self.assertIsNotNone(heading)
        self.assertIsNotNone(card)
        self.assertIn("font-size: var(--tier-1-title);", heading.group(1))
        self.assertIn("font-weight: 700;", heading.group(1))
        self.assertNotRegex(heading.group(1), r"transform\s*:\s*scale\s*\(")
        self.assertNotRegex(STYLE_CSS, r"(?s)\.metric-card\s*>\s*\.card-header\s*\{[^}]*transform\s*:\s*scale\s*\(")
        self.assertIn("border: 1px solid var(--hair);", card.group(1))

    def test_expanded_explanations_use_full_width_and_preserve_value_formatting(self):
        toggle = re.search(r'function toggleDD\(el, id\).*?\n    }', INDEX_HTML, re.DOTALL)
        explanation = re.search(r"(?m)^\.info-dd-text \{([^}]*)\}", STYLE_CSS)
        field = re.search(r"(?m)^\.info-dd-text \.dd-field \{([^}]*)\}", STYLE_CSS)
        value = re.search(r"(?m)^\.info-dd-text \.dd-value \{([^}]*)\}", STYLE_CSS)
        self.assertIsNotNone(toggle)
        self.assertIsNotNone(explanation)
        self.assertIsNotNone(field)
        self.assertIsNotNone(value)
        self.assertIn("row.appendChild(txt)", toggle.group(0))
        self.assertIn("txt.classList.toggle('show')", toggle.group(0))
        self.assertIn("el.setAttribute('aria-expanded'", toggle.group(0))
        self.assertIn(".info-row:has(.info-dd-text.show) { flex-wrap: wrap;", STYLE_CSS)
        self.assertIn("flex: 1 0 100%;", explanation.group(1))
        self.assertIn("width: 100%;", explanation.group(1))
        self.assertIn("font-size: 14px;", field.group(1))
        self.assertIn("font-size: 13.5px;", value.group(1))
        self.assertIn("word-break: normal;", value.group(1))

    def test_redundant_composition_chart_is_removed(self):
        self.assertNotIn('id="composition-wrap"', INDEX_HTML)
        self.assertNotIn('id="chart-composition-eraldised"', INDEX_HTML)
        self.assertNotIn('/static/js/chart.umd.min.js', INDEX_HTML)
        self.assertNotIn('renderCompositionChart', INDEX_HTML)
        self.assertNotIn('compositionChartRenderSequence', INDEX_HTML)
        self.assertNotIn('.card-composition-chart', STYLE_CSS)

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

    def test_dashboard_uses_one_official_compartment_number_everywhere(self):
        number_helper = re.search(r'function canonicalEraldisNumber\(value\).*?\n    }', INDEX_HTML, re.DOTALL)
        label_helper = re.search(r'function eraldisLabel\(value\).*?\n    }', INDEX_HTML, re.DOTALL)
        sort_helper = re.search(r'function sortEraldisedForDisplay\(items\).*?\n    }', INDEX_HTML, re.DOTALL)
        self.assertIsNotNone(number_helper)
        self.assertIsNotNone(label_helper)
        self.assertIsNotNone(sort_helper)

        script = f"""
{number_helper.group(0)}
{label_helper.group(0)}
{sort_helper.group(0)}
const stands = [
  {{id: 11108251, eraldis_nr: 16}},
  {{id: 9543691, eraldis_nr: 1}},
  {{id: 9397257, eraldis_nr: 5}},
  {{id: 12345678, eraldis_nr: null}},
];
const acceptedValues = [
  0, 16, 16.0, '16', ' 16.0 ', '1e2',
  Number.MAX_SAFE_INTEGER, String(Number.MAX_SAFE_INTEGER),
];
const rejectedValues = [
  null, undefined, true, false, '', '   ', 'not-a-number',
  -1, -1.0, '-1', 16.5, '16.5', NaN, Infinity, -Infinity, 'Infinity',
  [], {{}}, Number.MAX_SAFE_INTEGER + 1, String(Number.MAX_SAFE_INTEGER + 1),
];
const sorted = sortEraldisedForDisplay(stands);
console.log(JSON.stringify({{
  numbers: sorted.map(item => canonicalEraldisNumber(item.eraldis_nr)),
  labels: sorted.map(item => eraldisLabel(item.eraldis_nr)),
  internalIds: sorted.map(item => item.id),
  acceptedNumbers: acceptedValues.map(canonicalEraldisNumber),
  rejectedNumbers: rejectedValues.map(canonicalEraldisNumber),
}}));
"""
        result = subprocess.run(["node", "-e", script], check=True, capture_output=True, text=True)
        state = json.loads(result.stdout)

        self.assertEqual(state["numbers"], ["1", "5", "16", None])
        self.assertEqual(state["labels"], ["Eraldis 1", "Eraldis 5", "Eraldis 16", "Eraldise number puudub"])
        self.assertEqual(state["internalIds"], [9543691, 9397257, 11108251, 12345678])
        self.assertEqual(state["acceptedNumbers"], [
            "0", "16", "16", "16", "16", "100",
            "9007199254740991", "9007199254740991",
        ])
        self.assertEqual(state["rejectedNumbers"], [None] * 20)
        self.assertIn("sortEraldisedForDisplay(data.eraldised).forEach", INDEX_HTML)
        self.assertIn("sortEraldisedForDisplay(eraldised).forEach", INDEX_HTML)
        self.assertIn('class="er-number"', INDEX_HTML)
        self.assertIn("eraldisLabel(e.eraldis_nr)", INDEX_HTML)
        self.assertIn("var labels = L.layerGroup();", INDEX_HTML)
        self.assertIn("canonicalEraldisNumber(p.eraldis_nr)", INDEX_HTML)
        self.assertIn("eraldisLabel(e.eraldis_nr)", INDEX_HTML)
        self.assertIn(".eraldis-label", STYLE_CSS)

        forest_render = re.search(r'function renderMets\(data\).*?\n    }', INDEX_HTML, re.DOTALL)
        picker_render = re.search(r'function openEraldisSheet\(eraldised, triggerBtn\).*?\n    }', INDEX_HTML, re.DOTALL)
        self.assertIsNotNone(forest_render)
        self.assertIsNotNone(picker_render)
        self.assertIn("canonicalEraldisNumber(e.eraldis_nr)", picker_render.group(0))
        self.assertIn("sortEraldisedForDisplay(data.eraldised).forEach(function(e)", forest_render.group(0))
        self.assertIn("var standLabel = eraldisLabel(e.eraldis_nr);", forest_render.group(0))
        self.assertIn(
            "'<div class=\"er-stand-heading\"><span class=\"er-number\" title=\"' + escHtml(standLabel) + '\" aria-label=\"' + escHtml(standLabel) + '\">'",
            forest_render.group(0),
        )
        self.assertNotIn("(i + 1)", forest_render.group(0))

    def test_map_labels_prefer_server_point_with_old_backend_fallback(self):
        map_render = re.search(r'function addEraldisedLayer\(features\).*?\n    }', INDEX_HTML, re.DOTALL)
        label_css = re.search(r'(?m)^\.eraldis-label \{([^}]*)\}', STYLE_CSS)
        self.assertIsNotNone(map_render)
        self.assertIsNotNone(label_css)

        source = map_render.group(0)
        self.assertIn("canonicalEraldisNumber(p.eraldis_nr)", source)
        self.assertIn("Object.prototype.hasOwnProperty.call(p, 'label_point')", source)
        self.assertIn("[p.label_point[1], p.label_point[0]]", source)
        self.assertIn("layer.getBounds().getCenter()", source)
        self.assertNotIn("iconAnchor: [0, 0]", source)
        self.assertIn("transform: translate(-50%, -50%);", label_css.group(1))

    def test_notice_compartment_number_prefers_canonical_and_supports_legacy_responses(self):
        number_helper = re.search(r'function canonicalEraldisNumber\(value\).*?\n    }', INDEX_HTML, re.DOTALL)
        notice_helper = re.search(r'function noticeEraldisNumber\(notice\).*?\n    }', INDEX_HTML, re.DOTALL)
        render = re.search(r'function renderTeatised\(data, meta\).*?\n    }', INDEX_HTML, re.DOTALL)
        self.assertIsNotNone(number_helper)
        self.assertIsNotNone(notice_helper)
        self.assertIsNotNone(render)

        script = f"""
{number_helper.group(0)}
{notice_helper.group(0)}
console.log(JSON.stringify({{
  canonical: noticeEraldisNumber({{eraldis_nr: 16, eraldis: 9543691, teatise_eraldis_nr: 11108251}}),
  legacyMissing: noticeEraldisNumber({{eraldis: 5}}),
  legacyNull: noticeEraldisNumber({{eraldis_nr: null, eraldis: 7}}),
  canonicalNumeric: noticeEraldisNumber({{eraldis_nr: '16.0', eraldis: 5}}),
  legacyNumeric: noticeEraldisNumber({{eraldis: '5.0'}}),
  legacyZero: noticeEraldisNumber({{eraldis: '0.0'}}),
  legacyInvalid: noticeEraldisNumber({{eraldis: '5.5'}}),
  legacyYear: noticeEraldisNumber({{eraldis: '2026.0'}}),
  rawOnly: noticeEraldisNumber({{teatise_eraldis_nr: 11108251}}),
}}));
"""
        result = subprocess.run(["node", "-e", script], check=True, capture_output=True, text=True)
        state = json.loads(result.stdout)

        self.assertEqual(state["canonical"], "16")
        self.assertEqual(state["legacyMissing"], "5")
        self.assertEqual(state["legacyNull"], "7")
        self.assertEqual(state["canonicalNumeric"], "16")
        self.assertEqual(state["legacyNumeric"], "5")
        self.assertEqual(state["legacyZero"], "0")
        self.assertIsNone(state["legacyInvalid"])
        self.assertIsNone(state["legacyYear"])
        self.assertIsNone(state["rawOnly"])
        self.assertIn("var eraldisNr = noticeEraldisNumber(t);", render.group(0))
        self.assertIn("eraldisLabel(eraldisNr)", render.group(0))
        self.assertNotIn("t.eraldis", render.group(0))
        self.assertNotIn("teatise_eraldis_nr", render.group(0))

    def test_notice_compartment_column_preserves_full_ellipsized_label(self):
        render = re.search(r'function renderTeatised\(data, meta\).*?\n    }', INDEX_HTML, re.DOTALL)
        desktop_columns = re.search(
            r"(?m)^\.teatised-table-header,\s*\n\.teatised-row \{\s*\n\s*grid-template-columns: ([^;]+);",
            STYLE_CSS,
        )
        self.assertIsNotNone(render)
        self.assertIsNotNone(desktop_columns)
        self.assertIn("84px", desktop_columns.group(1))
        self.assertIn('<span class="teatised-eraldis-prefix">Eraldis </span>', render.group(0))
        self.assertNotIn("eraldisText.slice", render.group(0))
        self.assertIn("escHtml(eraldisNr)", render.group(0))
        self.assertIn("title=\"' + escHtml(eraldisText) + '\"", render.group(0))
        self.assertIn("aria-label=\"' + escHtml(eraldisText) + '\"", render.group(0))
        mobile_prefix_rule = ".teatised-row .teatised-eraldis-prefix { display: none; }"
        self.assertIn(mobile_prefix_rule, STYLE_CSS)
        prefix_rule_index = STYLE_CSS.index(mobile_prefix_rule)
        mobile_breakpoint_index = STYLE_CSS.rfind("@media (max-width: 640px) {", 0, prefix_rule_index)
        next_breakpoint_index = STYLE_CSS.find("@media (", prefix_rule_index)
        self.assertGreater(mobile_breakpoint_index, -1)
        self.assertLess(prefix_rule_index, next_breakpoint_index)
        self.assertIn("grid-template-columns: minmax(0, 1fr);", STYLE_CSS)

    def test_results_start_at_dashboard_and_cards_keep_natural_height(self):
        self.assertNotIn("document.getElementById('card-vaartus')", INDEX_HTML)
        self.assertIn("dashboard.scrollIntoView({ behavior: scrollBehavior, block: 'start' })", INDEX_HTML)
        self.assertIn(".metrics-grid {", STYLE_CSS)
        self.assertIn("align-items: start;", STYLE_CSS)
        self.assertIn("#dashboard { scroll-margin-top:", STYLE_CSS)

    def test_mobile_notices_use_stacked_labeled_rows(self):
        for label in ('Tüüp', 'Eraldis', 'Staatus', 'Kehtiv kuni', 'Pindala'):
            self.assertIn(f'data-label="{label}"', INDEX_HTML)
        self.assertIn('.teatised-table-header { display: none; }', STYLE_CSS)
        self.assertIn("content: attr(data-label);", STYLE_CSS)
        self.assertIn("formatDateEt(t.kehtiv_kuni)", INDEX_HTML)
        self.assertIn(
            "teatisedStatusBadge(t.event_status, t.event_status_label, t.staatus, t.active, t.arhiiv)",
            INDEX_HTML,
        )
        self.assertIn('class="teatised-type-value"', INDEX_HTML)
        self.assertIn(".teatised-row .teatised-type-value { grid-column: 2; }", STYLE_CSS)

    def test_inline_explanations_are_keyboard_accessible_buttons(self):
        helper = re.search(r'function ddInfo\(text, valueText\).*?\n    }', INDEX_HTML, re.DOTALL)
        self.assertIsNotNone(helper)
        self.assertIn('<button type="button" class="info-dd"', helper.group(0))
        self.assertIn('aria-expanded="false"', helper.group(0))
        self.assertIn('aria-controls="', helper.group(0))
        self.assertIn("el.setAttribute('aria-expanded'", INDEX_HTML)
        self.assertNotIn("margin: -15px -10px -15px 0", STYLE_CSS)
        disclosure_css = re.search(r'\.info-dd-text \{.*?\n\}', STYLE_CSS, re.DOTALL)
        self.assertIsNotNone(disclosure_css)
        self.assertIn("position: static;", disclosure_css.group(0))
        self.assertNotIn("position: absolute;", disclosure_css.group(0))

    def test_valuation_and_health_show_method_confidence_and_sources(self):
        self.assertIn("Metsa vara ja andmete usaldus", INDEX_HTML)
        self.assertIn("Hinnangu usaldus", INDEX_HTML)
        self.assertIn("Kuidas hinnang kujuneb", INDEX_HTML)
        self.assertIn("terviseindeks_selgitus", INDEX_HTML)
        self.assertIn("Terrapointi kaugandmete terviseskoor", INDEX_HTML)
        self.assertIn("data.terviseskoor != null", INDEX_HTML)
        self.assertIn("data.yrask_hinnang || data.yrask", INDEX_HTML)
        self.assertIn("Maa maksustamishind puudub; kinnistu koguhinnangut ei kuvata", INDEX_HTML)
        self.assertIn("e.vaartus_hinnang_eur != null ? e.vaartus_hinnang_eur : e.vaartus_eur", INDEX_HTML)
        self.assertIn("standScenarioHtml(p)", INDEX_HTML)
        self.assertIn("vaartus_min_eur", INDEX_HTML)
        self.assertIn("vaartus_max_eur", INDEX_HTML)
        self.assertIn("and not sampled_eraldised", API_PY)
        self.assertIn("t >= 90 ? 'var(--data-state-ok)'", INDEX_HTML)
        self.assertNotIn('class="evidence-details" open', INDEX_HTML)
        self.assertIn("min-height: 44px;\n    display: flex;", STYLE_CSS)
        self.assertIn("sourceLinksHtml", INDEX_HTML)
        self.assertIn("https://erametsaliit.ee/wp-content/uploads/2026/05/puiduhinnad-2026-i-kv.pdf", API_PY)
        self.assertIn("https://maaruum.ee/maakataster-ja-maa-hindamine/kinnisvaratehingud/kinnisvaratehingute-statistika", API_PY)
        self.assertIn("https://keskkonnaagentuur.ee/node/2695", API_PY)

    def test_compartment_scenarios_show_range_keep_zero_and_enrich_map_details(self):
        number_helper = _extract_js_function("canonicalEraldisNumber")
        scenario_helper = _extract_js_function("standScenarioHtml")
        merge_helper = _extract_js_function("mergeMapStandDetails")
        script = rf"""
function escHtml(value) {{ return String(value == null ? '' : value); }}
function formatEur(value) {{ return value == null ? '—' : String(Math.round(value)).replace(/\B(?=(\d{{3}})+(?!\d))/g, ' ') + ' €'; }}
{number_helper}
{scenario_helper}
{merge_helper}
const searchData = {{
  kataster: {{number: '78404:409:0113'}},
  map_layers: {{eraldised: {{features: [{{
    type: 'Feature', geometry: {{type: 'Polygon', coordinates: []}},
    properties: {{
      eraldis_nr: 4, tagavara_y_ha: 210,
      vaartus_min_eur: 1000, vaartus_hinnang_eur: 1500, vaartus_max_eur: 2000,
    }},
  }}]}}}},
}};
const persistent = {{stands: {{state: 'matches', features: [{{
  type: 'Feature', geometry: {{type: 'Polygon', coordinates: []}},
  properties: {{eraldis_nr: 4, source_key: 'metsaregister_eraldis'}},
}}]}}}};
const merged = mergeMapStandDetails(persistent, searchData, '78404:409:0113');
console.log(JSON.stringify({{
  range: standScenarioHtml({{vaartus_min_eur: 1000, vaartus_hinnang_eur: 1500, vaartus_max_eur: 2000}}),
  zero: standScenarioHtml({{vaartus_min_eur: 0, vaartus_hinnang_eur: 0, vaartus_max_eur: 0}}),
  properties: merged.stands.features[0].properties,
}}));
"""
        result = subprocess.run(["node", "-e", script], check=True, capture_output=True, text=True)
        state = json.loads(result.stdout)

        self.assertIn("1 000 €", state["range"])
        self.assertIn("2 000 €", state["range"])
        self.assertIn("Keskpunkt 1 500 €", state["range"])
        self.assertIn("0 €", state["zero"])
        self.assertEqual(state["properties"]["tagavara_y_ha"], 210)
        self.assertEqual(state["properties"]["vaartus_min_eur"], 1000)
        self.assertEqual(state["properties"]["vaartus_hinnang_eur"], 1500)
        self.assertEqual(state["properties"]["vaartus_max_eur"], 2000)
        self.assertEqual(state["properties"]["source_key"], "metsaregister_eraldis")

        apply_payload = _extract_js_function("applyMapContextPayload")
        do_search = _extract_js_function("doSearch")
        self.assertIn("mergeMapStandDetails", apply_payload)
        self.assertIn("enrichVisibleMapStands", do_search)
        self.assertIn('class="er-stand-summary"', INDEX_HTML)
        self.assertIn('<div>Eraldis ja lähteandmed</div><div style="text-align:right">Puidustsenaarium</div>', INDEX_HTML)
        self.assertRegex(
            STYLE_CSS,
            r"\.eraldised-row\s*\{\s*grid-template-columns:\s*minmax\(0, 1fr\) minmax\(124px, auto\);",
        )

    def test_subsidies_render_auditable_status_source_and_compartment_reasons(self):
        render = re.search(r'function renderToetused\(data\).*?\n    }', INDEX_HTML, re.DOTALL)
        self.assertIsNotNone(render)
        rendered = render.group(0)

        for contract in (
            "eligibility_status",
            "eligibility_reason",
            "application_status",
            "application_channel",
            "verification_items",
            "source_name",
            "source_url",
            "verified_at",
            "match_reason",
            "is_recommended",
            "relevance",
            "info_url",
            "legal_url",
        ):
            self.assertIn(contract, rendered)
        for label in (
            "Tõenäoliselt sobib",
            "Vajab kontrolli",
            "Ei sobi teadaolevate andmete põhjal",
            "Lõpliku otsuse teeb toetuse andja",
        ):
            self.assertIn(label, rendered)
        self.assertIn('target="_blank" rel="noopener"', rendered)
        self.assertIn("function safeExternalUrl(value)", INDEX_HTML)
        self.assertIn("return url.protocol === 'https:' ? url.href : '';", INDEX_HTML)
        self.assertIn("safeExternalUrl(t.info_url", rendered)
        self.assertIn("safeExternalUrl(t.legal_url", rendered)
        self.assertIn("toetus-eligibility-badge", STYLE_CSS)
        self.assertIn("toetus-verification-list", STYLE_CSS)
        self.assertIn("t.disclaimer", rendered)
        self.assertIn("toetus-more-matches", rendered)
        self.assertIn("t.eligibility_status || (t.sobib", rendered)
        self.assertIn("t.application_status || legacyApplicationStatus", rendered)
        self.assertIn("t.is_recommended === true", rendered)
        self.assertNotIn("((t.eraldised_match || []).length ? 'possible'", rendered)
        self.assertIn("Sinu kinnistuga seotud", rendered)
        self.assertIn("Võib olla asjakohane, kontrolli tingimusi", rendered)
        self.assertIn("Muud meetmed ja lõppenud voorud", rendered)
        self.assertNotIn("https://www.eramets.ee/toetused/';", rendered)

    def test_subsidies_execute_grouping_and_safe_official_links(self):
        render = re.search(r'function renderToetused\(data\).*?\n    }', INDEX_HTML, re.DOTALL).group(0)
        safe_start = INDEX_HTML.index("    function safeExternalUrl(value)")
        safe_end = INDEX_HTML.index("    function sourceLinksHtml", safe_start)
        safe_helper = INDEX_HTML[safe_start:safe_end]
        payload = [
            {
                "name": "Soovitatud meede", "category": "metsahooldus",
                "eligibility_status": "Tõenäoliselt sobib", "application_status": "upcoming",
                "relevance": "matched", "is_recommended": True,
                "source_url": "https://official.example/info", "legal_url": "https://official.example/law",
            },
            {
                "name": "Jälgitav meede", "category": "maaparandus",
                "eligibility_status": "Vajab kontrolli", "application_status": "awaiting_dates",
                "relevance": "watchlist", "is_recommended": False,
            },
            {
                "name": "Kontrollitav meede", "category": "looduskaitse",
                "eligibility_status": "Vajab kontrolli", "application_status": "year_round",
                "relevance": "insufficient_data", "is_recommended": False,
            },
            {
                "name": "Lõppenud meede", "category": "ühistu",
                "eligibility_status": "Vajab kontrolli", "application_status": "closed",
                "relevance": "archived", "is_recommended": False,
                "source_url": "javascript:alert(1)", "legal_url": "data:text/html,unsafe",
            },
            {
                "name": "Vana payload", "category": "inventeerimine",
                "eligibility_status": "Vajab kontrolli", "application_status": "upcoming",
                "eraldised_match": [{"eraldis_nr": 1, "match_reason": "vana vaste"}],
            },
        ]
        script = f"""
            var output = {{innerHTML: ''}};
            global.document = {{getElementById: function() {{ return output; }}}};
            function escHtml(value) {{ return String(value == null ? '' : value).replace(/[&<>\"']/g, ''); }}
            function formatNum(value) {{ return String(value); }}
            function eraldisLabel(value) {{ return 'Eraldis ' + value; }}
            {safe_helper}
            {render}
            renderToetused({json.dumps(payload, ensure_ascii=False)});
            process.stdout.write(output.innerHTML);
        """
        html = subprocess.run(["node", "-e", script], check=True, capture_output=True, text=True).stdout

        labels = [
            "Sinu kinnistuga seotud", "Soovitatud meede",
            "Jälgi ametliku vooru avanemist", "Jälgitav meede",
            "Võib olla asjakohane, kontrolli tingimusi", "Kontrollitav meede", "Vana payload",
            "Muud meetmed ja lõppenud voorud", "Lõppenud meede",
        ]
        positions = [html.index(label) for label in labels]
        self.assertEqual(positions, sorted(positions))
        self.assertIn('href="https://official.example/info"', html)
        self.assertIn('href="https://official.example/law"', html)
        self.assertNotIn("javascript:", html)
        self.assertNotIn("data:text/html", html)

    def test_subsidy_counts_have_explicit_contrast_and_mobile_avoids_nested_scroll(self):
        self.assertIn(".toetus-group-heading > span { background: var(--success); color: #fff; }", STYLE_CSS)
        self.assertIn(".toetus-details-count { background: var(--ink-5); color: #fff; }", STYLE_CSS)
        self.assertIn(".toetus-list-scroll { max-height: none; overflow-y: visible; }", STYLE_CSS)

    def test_subsidy_inputs_preserve_source_completeness(self):
        self.assertIn('"forest_data_complete": "metsaregister.eraldised" not in unavailable_sources', API_PY)
        self.assertIn('"stand_data_complete": stand_data_complete', API_PY)
        self.assertIn('"protection_data_complete": protection_data_complete', API_PY)
        self.assertIn('"natura_data_complete": spatial_status["natura_2000"]["sources_complete"]', API_PY)
        self.assertIn('"vep_data_complete": False', API_PY)
        self.assertIn('spatial_status = _build_spatial_status(', API_PY)
        self.assertIn('spatial_status["kaitseala"]["intersects"] is True', API_PY)
        self.assertIn('"registreerimise_kp": stand.get("registreerimise_kp")', API_PY)

    def test_archive_notice_outage_does_not_show_broad_data_warning(self):
        helper = re.search(r'function shouldShowBroadPartialWarning\(meta\).*?\n    }', INDEX_HTML, re.DOTALL)
        self.assertIsNotNone(helper)
        self.assertIn("if (!meta || !meta.partial) return false;", helper.group(0))
        self.assertIn("if (meta.ai_analysis_available === true) return false;", helper.group(0))
        self.assertIn("source !== 'metsaregister.teatis_arhiiv'", helper.group(0))
        self.assertIn("return sources.length === 0 ||", helper.group(0))
        self.assertIn("if (shouldShowBroadPartialWarning(data.meta))", INDEX_HTML)
        self.assertIn("meta.ai_analysis_available !== true", INDEX_HTML)

    def test_partial_warning_policy_executes_for_ai_ready_and_blocking_states(self):
        broad = re.search(r'function shouldShowBroadPartialWarning\(meta\).*?\n    }', INDEX_HTML, re.DOTALL)
        detail = re.search(r'function shouldShowDetailLimitWarning\(meta\).*?\n    }', INDEX_HTML, re.DOTALL)
        self.assertIsNotNone(broad)
        self.assertIsNotNone(detail)
        script = f"""
{broad.group(0)}
{detail.group(0)}
const states = {json.dumps([
    {"partial": False, "ai_analysis_available": True, "unavailable_sources": []},
    {"partial": True, "ai_analysis_available": True, "unavailable_sources": ["metsaregister.teatised"]},
    {"partial": False, "ai_analysis_available": True, "details_skipped": True, "unavailable_sources": []},
    {"partial": True, "ai_analysis_available": False, "unavailable_sources": ["metsaregister.eraldised"]},
])};
console.log(JSON.stringify(states.map(meta => [
    shouldShowBroadPartialWarning(meta),
    shouldShowDetailLimitWarning(meta),
])));
"""

        result = subprocess.run(["node", "-e", script], check=True, capture_output=True, text=True)

        self.assertEqual(json.loads(result.stdout), [
            [False, False],
            [False, False],
            [False, False],
            [True, False],
        ])

    def test_ai_uses_dedicated_readiness_instead_of_general_partial_state(self):
        self.assertIn("data.meta.ai_analysis_available === true", INDEX_HTML)
        self.assertIn("data.chat_snapshot", INDEX_HTML)
        self.assertIn("snapshot: currentData.chat_snapshot", INDEX_HTML)
        self.assertIn("delete trimmed.chat_snapshot", INDEX_HTML)
        self.assertNotIn("data.kataster && !(data.meta && data.meta.partial)", INDEX_HTML)
        self.assertIn("AI analüüs vajab katastri ja metsa põhiandmeid", API_PY)
        self.assertNotIn("AI analüüs vajab täielikke kinnistuandmeid", API_PY)

    def test_eudr_protection_policy_is_tri_state_and_requires_complete_sources(self):
        helper = re.search(r'function eudrProtectionState\(spatialStatus\).*?\n    }', INDEX_HTML, re.DOTALL)
        self.assertIsNotNone(helper)
        script = f"""
{helper.group(0)}
const states = [
  {{
    natura_2000: {{intersects: false, sources_complete: true}},
    kaitseala: {{intersects: false, sources_complete: true}},
    sood: {{intersects: false, sources_complete: true}},
  }},
  {{
    natura_2000: {{intersects: null, sources_complete: false}},
    kaitseala: {{intersects: false, sources_complete: true}},
    sood: {{intersects: false, sources_complete: true}},
  }},
  {{
    natura_2000: {{intersects: false, sources_complete: true}},
    kaitseala: {{intersects: true, sources_complete: false}},
    sood: {{intersects: false, sources_complete: true}},
  }},
  undefined,
];
console.log(JSON.stringify(states.map(eudrProtectionState)));
"""
        result = subprocess.run(["node", "-e", script], check=True, capture_output=True, text=True)
        states = json.loads(result.stdout)

        self.assertEqual(states[0]["riskLevel"], "Madal risk — kaitseala ei ole")
        self.assertTrue(states[0]["sourcesComplete"])
        self.assertEqual(states[1]["riskLevel"], "Staatus teadmata — osa ruumiandmeid puudub")
        self.assertFalse(states[1]["sourcesComplete"])
        self.assertEqual(states[2]["riskLevel"], "Kõrge risk — kaitseala piirangud")
        self.assertTrue(states[2]["kaitseala"])
        self.assertFalse(states[2]["sourcesComplete"])
        self.assertIsNone(states[3]["natura"])
        self.assertFalse(states[3]["sourcesComplete"])

    def test_reset_parcel_result_clears_previous_map_ai_and_value_state(self):
        clear_helper = re.search(r'function clearParcelPanels\(\).*?\n    }', INDEX_HTML, re.DOTALL)
        analytical_helper = re.search(r'function resetAnalyticalResult\(requestId\).*?\n    }', INDEX_HTML, re.DOTALL)
        helper = re.search(r'function resetParcelResult\(requestId\).*?\n    }', INDEX_HTML, re.DOTALL)
        self.assertIsNotNone(clear_helper)
        self.assertIsNotNone(analytical_helper)
        self.assertIsNotNone(helper)
        script = f"""
var parcelSearchSequence = 4;
var currentData = {{kataster: {{number: '78404:409:0113'}}}};
var window = {{_timberValue: 100, _vaartusData: {{total: 100}}, _mapLayersData: {{eraldised: {{}}}}}};
var parcelLayer = {{id: 'old'}};
var overlayLayers = {{eraldised: {{}}, kaitsealad: {{}}}};
var removedParcel = false;
var popupClosed = false;
var aiUnavailable = false;
var hints = null;
var restrictionsLink = {{style: {{display: 'block'}}}};
var inputArea = {{style: {{display: ''}}}};
var sheet = {{removed: false, remove() {{ this.removed = true; }}}};
var katasterPanel = {{innerHTML: '78404:409:0113'}};
var eudrPanel = {{innerHTML: 'EUDR eksport'}};
var map = {{
  hasLayer() {{ return true; }},
  removeLayer() {{ removedParcel = true; }},
  closePopup() {{ popupClosed = true; }},
}};
var document = {{getElementById(id) {{
  return {{
    'kitsendused-link': restrictionsLink,
    'ai-chat-input-area': inputArea,
    'eraldis-sheet': sheet,
    'kataster-info': katasterPanel,
    'eudr-info': eudrPanel,
  }}[id] || null;
}}}};
function removeOverlayLayer(name) {{ delete overlayLayers[name]; }}
function renderMapWorkspaceState() {{}}
function aiShowUnavailableData() {{ aiUnavailable = true; }}
function aiRenderEraldisHints(value) {{ hints = value; }}
function cancelMapSelection() {{}}
function closeEraldisSheet() {{ sheet.remove(); }}
var _aiUserScrolledUp = true;
{clear_helper.group(0)}
{analytical_helper.group(0)}
{helper.group(0)}
const staleResult = resetParcelResult(3);
const currentResult = resetParcelResult(4);
console.log(JSON.stringify({{
  staleResult,
  currentResult,
  currentData,
  timber: window._timberValue,
  valuation: window._vaartusData,
  mapData: window._mapLayersData,
  parcelLayer,
  overlays: Object.keys(overlayLayers),
  removedParcel,
  popupClosed,
  aiUnavailable,
  hints,
  restrictionsDisplay: restrictionsLink.style.display,
  inputDisplay: inputArea.style.display,
  sheetRemoved: sheet.removed,
  katasterPanel: katasterPanel.innerHTML,
  eudrPanel: eudrPanel.innerHTML,
}}));
"""
        result = subprocess.run(["node", "-e", script], check=True, capture_output=True, text=True)
        state = json.loads(result.stdout)

        self.assertFalse(state["staleResult"])
        self.assertTrue(state["currentResult"])
        self.assertIsNone(state["currentData"])
        self.assertEqual(state["timber"], 0)
        self.assertEqual(state["valuation"], {})
        self.assertEqual(state["mapData"], {})
        self.assertIsNone(state["parcelLayer"])
        self.assertEqual(state["overlays"], [])
        self.assertTrue(state["removedParcel"])
        self.assertTrue(state["popupClosed"])
        self.assertTrue(state["aiUnavailable"])
        self.assertEqual(state["hints"], [])
        self.assertEqual(state["restrictionsDisplay"], "none")
        self.assertEqual(state["inputDisplay"], "none")
        self.assertTrue(state["sheetRemoved"])
        self.assertNotIn("78404:409:0113", state["katasterPanel"])
        self.assertNotIn("EUDR eksport", state["eudrPanel"])

        do_search = INDEX_HTML.index("async function doSearch()")
        loading_call = INDEX_HTML.index("showLoading();", do_search)
        replacement_call = INDEX_HTML.index("var requestId = beginParcelReplacement();", do_search)
        self.assertLess(replacement_call, loading_call)

        catch_guard = INDEX_HTML.index("if (requestId !== parcelSearchSequence) return;", INDEX_HTML.index("} catch (err)"))
        reset_call = INDEX_HTML.index("resetParcelResult(requestId);", catch_guard)
        self.assertGreater(reset_call, catch_guard)

    def test_restriction_policy_never_calls_unknown_sources_empty(self):
        protection_helper = re.search(r'function eudrProtectionState\(spatialStatus\).*?\n    }', INDEX_HTML, re.DOTALL)
        helper = re.search(r'function restrictionDataState\(spatialStatus, meta\).*?\n    }', INDEX_HTML, re.DOTALL)
        self.assertIsNotNone(protection_helper)
        self.assertIsNotNone(helper)
        script = f"""
{protection_helper.group(0)}
{helper.group(0)}
const complete = restrictionDataState({{
  natura_2000: {{intersects: false, sources_complete: true}},
  kaitseala: {{intersects: false, sources_complete: true}},
  sood: {{intersects: false, sources_complete: true}},
}}, {{unavailable_sources: [], truncated_layers: []}});
const protectedState = restrictionDataState({{
  natura_2000: {{intersects: true, sources_complete: true}},
  kaitseala: {{intersects: false, sources_complete: true}},
  sood: {{intersects: false, sources_complete: true}},
}}, {{unavailable_sources: [], truncated_layers: []}});
const unknown = restrictionDataState(undefined, {{unavailable_sources: ['layers.piirang'], truncated_layers: []}});
const unrelated = restrictionDataState({{
  natura_2000: {{intersects: false, sources_complete: true}},
  kaitseala: {{intersects: false, sources_complete: true}},
  sood: {{intersects: false, sources_complete: true}},
}}, {{unavailable_sources: ['layers.yrask_eelis'], truncated_layers: ['veekogud']}});
console.log(JSON.stringify({{complete, protectedState, unknown, unrelated}}));
"""
        result = subprocess.run(["node", "-e", script], check=True, capture_output=True, text=True)
        states = json.loads(result.stdout)

        self.assertTrue(states["complete"]["canClaimEmpty"])
        self.assertFalse(states["protectedState"]["canClaimEmpty"])
        self.assertIn("Natura 2000", states["protectedState"]["detected"])
        self.assertFalse(states["unknown"]["canClaimEmpty"])
        self.assertFalse(states["unknown"]["sourcesComplete"])
        self.assertTrue(states["unrelated"]["canClaimEmpty"])
        self.assertTrue(states["unrelated"]["sourcesComplete"])

    def test_ai_stream_and_snapshot_freshness_use_explicit_ownership(self):
        owns = re.search(r'function aiOwnsStream\(generation, controller, katasterNr\).*?\n    }', INDEX_HTML, re.DOTALL)
        record = re.search(r'function recordChatSnapshotReceipt\(data, nowMs\).*?\n    }', INDEX_HTML, re.DOTALL)
        fresh = re.search(r'function hasFreshChatSnapshot\(data, nowMs\).*?\n    }', INDEX_HTML, re.DOTALL)
        self.assertIsNotNone(owns)
        self.assertIsNotNone(record)
        self.assertIsNotNone(fresh)
        script = f"""
var aiStreamGeneration = 4;
var aiAbortController = {{id: 1}};
var aiCurrentKataster = '78404:409:0113';
var aiSnapshotReceipt = null;
{owns.group(0)}
{record.group(0)}
{fresh.group(0)}
const snapshot = {{chat_snapshot: 'x', chat_snapshot_expires_at: 1, chat_snapshot_ttl_seconds: 1800}};
recordChatSnapshotReceipt(snapshot, 1000);
console.log(JSON.stringify({{
  owner: aiOwnsStream(4, aiAbortController, '78404:409:0113'),
  staleGeneration: aiOwnsStream(3, aiAbortController, '78404:409:0113'),
  staleParcel: aiOwnsStream(4, aiAbortController, '17501:002:0490'),
  fresh: hasFreshChatSnapshot(snapshot, 1000000),
  expiring: hasFreshChatSnapshot(snapshot, 1780000),
  missing: hasFreshChatSnapshot({{}}, 100000),
}}));
"""
        result = subprocess.run(["node", "-e", script], check=True, capture_output=True, text=True)
        state = json.loads(result.stdout)

        self.assertTrue(state["owner"])
        self.assertFalse(state["staleGeneration"])
        self.assertFalse(state["staleParcel"])
        self.assertTrue(state["fresh"])
        self.assertFalse(state["expiring"])
        self.assertFalse(state["missing"])
        self.assertIn("CHAT_SNAPSHOT_EXPIRED", INDEX_HTML)
        self.assertIn("chatError.code = j.code", INDEX_HTML)

    def test_address_submissions_begin_parcel_replacement_before_resolution(self):
        self.assertIn("function beginParcelReplacement()", INDEX_HTML)
        for function_name in ("smartSubmit", "chipSubmit", "navSmartSubmit"):
            function = re.search(rf'function {function_name}\(value\).*?\n        }}', INDEX_HTML, re.DOTALL)
            self.assertIsNotNone(function)
            normalized_branch = function.group(0).find("if (normalizedKataster)")
            if normalized_branch < 0:
                normalized_branch = function.group(0).find("if (KATASTER_RE.test(value))")
            replacement = function.group(0).find("beginParcelReplacement();")
            fetch_call = function.group(0).find("fetchAddresses(value)")
            self.assertGreater(replacement, normalized_branch)
            self.assertLess(replacement, fetch_call)

    def test_address_resolution_requires_address_and_parcel_ownership(self):
        helper = re.search(
            r'function addressResolutionOwns\(addressRequestId, parcelRequestId\).*?\n    }',
            INDEX_HTML,
            re.DOTALL,
        )
        self.assertIsNotNone(helper)
        script = f"""
var addressResolutionSequence = 4;
var parcelSearchSequence = 8;
{helper.group(0)}
console.log(JSON.stringify({{
  current: addressResolutionOwns(4, 8),
  staleAddress: addressResolutionOwns(3, 8),
  staleParcel: addressResolutionOwns(4, 7),
}}));
"""
        result = subprocess.run(["node", "-e", script], check=True, capture_output=True, text=True)
        state = json.loads(result.stdout)

        self.assertTrue(state["current"])
        self.assertFalse(state["staleAddress"])
        self.assertFalse(state["staleParcel"])

        for function_name in ("smartSubmit", "chipSubmit", "navSmartSubmit"):
            function = re.search(rf'function {function_name}\(value\).*?\n        }}', INDEX_HTML, re.DOTALL)
            self.assertIsNotNone(function)
            source = function.group(0)
            self.assertIn("var parcelRequestId = beginParcelReplacement();", source)
            self.assertGreaterEqual(
                source.count("addressResolutionOwns(requestId, parcelRequestId)"),
                2,
            )
            self.assertLess(source.find("showLoading();"), source.find("fetchAddresses(value)"))

    def test_parcel_replacement_releases_aborted_search_busy_state(self):
        helper = re.search(r'function clearSearchBusyState\(\).*?\n    }', INDEX_HTML, re.DOTALL)
        begin = re.search(r'function beginParcelReplacement\(\).*?\n    }', INDEX_HTML, re.DOTALL)
        self.assertIsNotNone(helper)
        self.assertIsNotNone(begin)
        script = f"""
function classList(initial) {{
  const values = new Set(initial);
  return {{
    remove(value) {{ values.delete(value); }},
    values() {{ return Array.from(values); }},
  }};
}}
const navBox = {{classList: classList(['is-searching'])}};
const landBox = {{classList: classList(['is-searching'])}};
const nav = {{disabled: true, classList: classList(['is-loading']), closest() {{ return navBox; }}}};
const land = {{disabled: true, classList: classList(['is-loading']), closest() {{ return landBox; }}}};
const document = {{getElementById(id) {{ return id === 'search-btn' ? nav : id === 'search-btn-landing' ? land : null; }}}};
{helper.group(0)}
clearSearchBusyState();
console.log(JSON.stringify({{
  navDisabled: nav.disabled,
  landDisabled: land.disabled,
  navClasses: nav.classList.values(),
  landClasses: land.classList.values(),
  navBoxClasses: navBox.classList.values(),
  landBoxClasses: landBox.classList.values(),
}}));
"""
        result = subprocess.run(["node", "-e", script], check=True, capture_output=True, text=True)
        state = json.loads(result.stdout)

        self.assertFalse(state["navDisabled"])
        self.assertFalse(state["landDisabled"])
        self.assertEqual(state["navClasses"], [])
        self.assertEqual(state["landClasses"], [])
        self.assertEqual(state["navBoxClasses"], [])
        self.assertEqual(state["landBoxClasses"], [])
        self.assertIn("clearSearchBusyState();", begin.group(0))

    def test_editing_input_cancels_owned_address_loading_state(self):
        helper = re.search(r'function cancelActiveAddressResolution\(\).*?\n    }', INDEX_HTML, re.DOTALL)
        self.assertIsNotNone(helper)
        script = f"""
var addressResolutionSequence = 4;
var parcelSearchSequence = 8;
var activeAddressResolution = {{addressRequestId: 4, parcelRequestId: 8}};
var hidden = false;
function hideLoading() {{ hidden = true; }}
{helper.group(0)}
cancelActiveAddressResolution();
console.log(JSON.stringify({{
  addressResolutionSequence,
  activeAddressResolution,
  hidden,
}}));
"""
        result = subprocess.run(["node", "-e", script], check=True, capture_output=True, text=True)
        state = json.loads(result.stdout)

        self.assertEqual(state["addressResolutionSequence"], 5)
        self.assertIsNone(state["activeAddressResolution"])
        self.assertTrue(state["hidden"])
        self.assertGreaterEqual(INDEX_HTML.count("cancelPendingInputOperations();"), 2)

    def test_editing_input_cancels_active_parcel_search(self):
        helper = re.search(r'function cancelPendingInputOperations\(\).*?\n    }', INDEX_HTML, re.DOTALL)
        self.assertIsNotNone(helper)
        script = f"""
var parcelSearchSequence = 7;
var aborted = false;
var activeParcelSearch = {{abort() {{ aborted = true; }}}};
var resetId = null;
var busyCleared = false;
var loadingHidden = false;
function cancelActiveAddressResolution() {{}}
function clearSearchBusyState() {{ busyCleared = true; }}
function resetParcelResult(requestId) {{ resetId = requestId; }}
function hideLoading() {{ loadingHidden = true; }}
{helper.group(0)}
cancelPendingInputOperations();
console.log(JSON.stringify({{
  parcelSearchSequence,
  aborted,
  activeParcelSearch,
  resetId,
  busyCleared,
  loadingHidden,
}}));
"""
        result = subprocess.run(["node", "-e", script], check=True, capture_output=True, text=True)
        state = json.loads(result.stdout)

        self.assertEqual(state["parcelSearchSequence"], 8)
        self.assertTrue(state["aborted"])
        self.assertIsNone(state["activeParcelSearch"])
        self.assertEqual(state["resetId"], 8)
        self.assertTrue(state["busyCleared"])
        self.assertTrue(state["loadingHidden"])

    def test_registry_dates_are_validated_before_formatting(self):
        self.assertIn("if (!match) return '—';", INDEX_HTML)
        self.assertIn("date.getUTCFullYear() !== year", INDEX_HTML)
        self.assertIn("Andmete kuvamine ebaõnnestus", INDEX_HTML)

    def test_redundant_center_map_button_is_removed(self):
        self.assertNotIn("CenterControl", INDEX_HTML)
        self.assertNotIn('aria-label="Center map"', INDEX_HTML)

    def test_successful_search_hides_stale_map_hint(self):
        self.assertIn("mapHint.classList.add('hidden')", INDEX_HTML)
        self.assertLess(
            INDEX_HTML.index("function dismissMapHint()"),
            INDEX_HTML.index("document.addEventListener('DOMContentLoaded'"),
        )
        self.assertLess(
            INDEX_HTML.index("function closeMapWorkspaceOnMobile(restoreFocus)"),
            INDEX_HTML.index("document.addEventListener('DOMContentLoaded'"),
        )
        self.assertEqual(INDEX_HTML.count("closeMapWorkspaceOnMobile(false);"), 1)

    def test_primary_timber_value_uses_grouped_number_format(self):
        self.assertIn("formatEur(data.base_value_eur != null ? data.base_value_eur : data.total_value_eur)", INDEX_HTML)
        self.assertNotIn("animateNumber(animEl, data.total_value_eur, '', 0);", INDEX_HTML)

    def test_map_workspace_is_minimal_and_ai_analysis_follows_the_map(self):
        map_start = INDEX_HTML.index('<div class="map-section">')
        ai_start = INDEX_HTML.index('<div class="ai-chat-section" id="ai-chat-section">')
        metrics_start = INDEX_HTML.index('<div class="metrics-grid">')
        self.assertLess(map_start, ai_start)
        self.assertLess(ai_start, metrics_start)

        workspace = re.search(
            r'<div class="map-controls" id="map-controls">.*?</div>\s*</div>\s*</div>',
            INDEX_HTML,
            re.DOTALL,
        )
        self.assertIsNotNone(workspace)
        self.assertEqual(
            re.findall(
                r'<button[^>]+class="map-view-preset"[^>]+data-map-view="([^"]+)"[^>]*>([^<]+)</button>',
                workspace.group(0),
            ),
            [('overview', 'Ülevaade'), ('restrictions', 'Piirangud'), ('risks', 'Riskid')],
        )
        self.assertNotIn('Aktiivsed teemad', workspace.group(0))
        self.assertNotIn('id="map-workspace-theme-controls"', workspace.group(0))
        self.assertNotIn('id="map-workspace-reset"', workspace.group(0))
        self.assertIn(".map-workspace.is-open .map-workspace-opener { display: none; }", STYLE_CSS)

        render = _extract_js_function("renderMapWorkspaceState")
        self.assertIn("mapWorkspaceState.basemapNotice ||", render)
        self.assertIn("status.hidden = hasParcel && mapWorkspaceState.loadingStatus === 'success' && !mapWorkspaceState.basemapNotice;", render)
        self.assertNotIn("toggleTheme:", INDEX_HTML)
        self.assertNotIn("function toggleMapThemeSelection", INDEX_HTML)
        self.assertIn("if (!MAP_VIEW_PRESETS[viewId]) return Promise.resolve(false);", _extract_js_function("selectMapView"))
        self.assertIn("availableViews: Object.keys(MAP_VIEW_PRESETS)", INDEX_HTML)

        init_map = _extract_js_function("initMap")
        base_layers = re.search(r"var baseLayers = \{(.*?)\n\s*\};", init_map, re.DOTALL)
        self.assertIsNotNone(base_layers)
        self.assertEqual(base_layers.group(1).count(":"), 2)
        self.assertIn("'Maa- ja Ruumiamet · ortofoto': maaruumOrthophoto", base_layers.group(1))
        self.assertIn("'Maa- ja Ruumiamet · halltoonides kaart': maaruumGrayMap", base_layers.group(1))
        self.assertNotIn("Esri", base_layers.group(1))

    def test_map_workspace_presets_state_and_reset_are_deterministic(self):
        source = _marked_js_source("// MAP_WORKSPACE_PURE_START", "// MAP_WORKSPACE_PURE_END")
        script = f"""
'use strict';
{source}
const expected = {{
  overview: ['nature_protection', 'species_habitats', 'water_restrictions', 'heritage_other'],
  restrictions: ['nature_protection', 'species_habitats', 'water_restrictions', 'heritage_other', 'flood_wetlands'],
  risks: ['flood_wetlands', 'forest_health', 'invasive_species'],
}};
const presetSnapshot = Object.fromEntries(Object.entries(MAP_VIEW_PRESETS).map(([id, preset]) => [id, preset.themeIds]));
let mutationBlocked = false;
try {{ MAP_VIEW_PRESETS.overview.themeIds.push('parcel'); }} catch (_) {{ mutationBlocked = true; }}
let state = createMapWorkspaceState('session-basemap');
state = selectMapViewPreset(state, 'risks');
const selectedLabel = mapViewDisplayLabel(state);
const restored = selectMapViewPreset(state, 'overview');
const populated = Object.assign({{}}, restored, {{
  parcelId: 'old', themeResults: {{nature_protection: {{state: 'matches'}}}},
  themeCache: {{nature_protection: {{state: 'matches'}}}}, hasValidPersistentContext: true,
  requestGeneration: 7, requestController: {{id: 'old'}},
}});
const reset = resetMapWorkspaceForParcel(populated, '78404:409:0113');
const initialContextThemes = mapContextThemeIdsForState(Object.assign({{}}, reset, {{parcelId: '78404:409:0113'}}));
console.log(JSON.stringify({{
  expected,
  presetSnapshot,
  frozen: Object.isFrozen(MAP_VIEW_PRESETS) && Object.isFrozen(MAP_VIEW_PRESETS.overview) && Object.isFrozen(MAP_VIEW_PRESETS.overview.themeIds),
  mutationBlocked,
  selectedThemes: state.activeThemeIds,
  selectedLabel,
  restoredView: restored.viewId,
  restoredThemes: restored.activeThemeIds,
  restoredBasemap: restored.selectedBasemapId,
  reset,
  initialContextThemes,
}}));
"""
        result = subprocess.run(["node", "-e", script], check=True, capture_output=True, text=True)
        state = json.loads(result.stdout)

        self.assertEqual(state["presetSnapshot"], state["expected"])
        self.assertTrue(state["frozen"])
        self.assertTrue(state["mutationBlocked"])
        self.assertEqual(state["selectedThemes"], state["expected"]["risks"])
        self.assertEqual(state["selectedLabel"], "Riskid")
        self.assertEqual(state["restoredView"], "overview")
        self.assertEqual(state["restoredThemes"], state["expected"]["overview"])
        self.assertEqual(state["restoredBasemap"], "session-basemap")
        self.assertEqual(state["reset"]["parcelId"], "78404:409:0113")
        self.assertEqual(state["reset"]["viewId"], "overview")
        self.assertEqual(state["reset"]["selectedBasemapId"], "session-basemap")
        self.assertEqual(state["reset"]["themeResults"], {})
        self.assertEqual(state["reset"]["themeCache"], {})
        self.assertFalse(state["reset"]["hasValidPersistentContext"])
        self.assertEqual(state["reset"]["requestGeneration"], 8)
        self.assertIsNone(state["reset"]["requestController"])
        self.assertEqual(state["initialContextThemes"], state["expected"]["overview"])

    def test_official_maaruum_basemaps_use_verified_wmts_contracts_and_default(self):
        init_map = _extract_js_function("initMap")
        orthophoto_url = (
            "https://tiles.maaamet.ee/tm/wmts/1.0.0/foto/default/GMC/"
            "{z}/{y}/{x}.jpg?ASUTUS=Terrapoint&KESKKOND=PROD&IS=terrapoint.ee"
        )
        gray_map_url = (
            "https://tiles.maaamet.ee/tm/wmts/1.0.0/hallkaart/default/GMC/"
            "{z}/{y}/{x}.png?ASUTUS=Terrapoint&KESKKOND=PROD&IS=terrapoint.ee"
        )

        self.assertIn("var mapWorkspaceState = createMapWorkspaceState('maaruum-orthophoto');", INDEX_HTML)
        self.assertIn(orthophoto_url, init_map)
        self.assertIn(gray_map_url, init_map)
        self.assertIn("const maaruumOrthophoto = L.tileLayer(", init_map)
        self.assertIn("const maaruumGrayMap = L.tileLayer(", init_map)
        orthophoto = re.search(
            r"const maaruumOrthophoto = L\.tileLayer\(.*?\{(.*?)\}\s*\);",
            init_map,
            re.DOTALL,
        )
        gray_map = re.search(
            r"const maaruumGrayMap = L\.tileLayer\(.*?\{(.*?)\}\s*\);",
            init_map,
            re.DOTALL,
        )
        self.assertIsNotNone(orthophoto)
        self.assertIsNotNone(gray_map)
        self.assertIn("minZoom: 6", init_map)
        self.assertIn("tileSize: 256", orthophoto.group(1))
        self.assertIn("minZoom: 6", orthophoto.group(1))
        self.assertIn("maxNativeZoom: 18", orthophoto.group(1))
        self.assertIn("maxZoom: 19", orthophoto.group(1))
        self.assertIn("tileSize: 256", gray_map.group(1))
        self.assertIn("minZoom: 6", gray_map.group(1))
        self.assertIn("maxZoom: 19", gray_map.group(1))
        self.assertIn("maaruumOrthophoto.addTo(map);", init_map)
        self.assertNotIn("esriWorldImagery.addTo(map);", init_map)

    def test_official_basemap_failures_switch_to_independent_neutral_map_without_looping(self):
        init_map = _extract_js_function("initMap")
        fallback = _extract_js_function("activateOfficialBasemapFallback")
        independent_fallback = _extract_js_function("activateIndependentNeutralFallback")

        self.assertEqual(init_map.count("maaruumOrthophoto.on('tileerror'"), 1)
        self.assertEqual(init_map.count("maaruumGrayMap.on('tileerror'"), 1)
        self.assertIn("if (orthophotoFallbackUsed || !map.hasLayer(maaruumOrthophoto)) return false;", fallback)
        self.assertIn("orthophotoFallbackUsed = true;", fallback)
        self.assertIn("map.removeLayer(maaruumOrthophoto);", fallback)
        self.assertIn("maaruumGrayMap.addTo(map);", fallback)
        self.assertIn("'maaruum-gray'", fallback)
        self.assertIn("renderMapWorkspaceState();", fallback)
        self.assertNotIn("removeOverlayLayer", fallback)
        self.assertNotIn("clearMapContextThemeLayers", fallback)
        self.assertIn("grayFallbackUsed", independent_fallback)
        self.assertIn("map.removeLayer(maaruumGrayMap);", independent_fallback)
        self.assertIn("esriLightGrayCanvas.addTo(map);", independent_fallback)
        self.assertIn("'esri-light-gray'", independent_fallback)
        self.assertNotIn("esriLightGrayCanvas.on('tileerror'", init_map)
        self.assertIn("if (basemapId === 'maaruum-orthophoto') orthophotoFallbackUsed = false;", init_map)

    def test_official_basemap_fallback_eligibility_resets_for_explicit_reselection(self):
        init_map = _extract_js_function("initMap")
        script = f"""
const createdLayers = [];
function makeLayer(url) {{
  const layer = {{
    url,
    handlers: {{}},
    addTo(target) {{ target.layers.add(this); return this; }},
    on(name, handler) {{ this.handlers[name] = handler; return this; }},
    fire(name) {{ if (this.handlers[name]) this.handlers[name](); }},
  }};
  createdLayers.push(layer);
  return layer;
}}
const mapStub = {{
  layers: new Set(),
  handlers: {{}},
  setView() {{ return this; }},
  on(name, handler) {{ this.handlers[name] = handler; return this; }},
  hasLayer(layer) {{ return this.layers.has(layer); }},
  removeLayer(layer) {{ this.layers.delete(layer); return this; }},
  getContainer() {{ return {{}}; }},
  invalidateSize() {{}},
}};
const tileLayer = function(url) {{ return makeLayer(url); }};
tileLayer.wms = function(url) {{ return makeLayer(url); }};
const control = function() {{ return {{addTo() {{ return this; }}}}; }};
control.zoom = control;
control.attribution = control;
control.layers = control;
const L = {{
  CRS: {{EPSG3857: {{}}}},
  map() {{ return mapStub; }},
  tileLayer,
  control,
}};
const window = {{addEventListener() {{}}}};
const BASEMAP_ACCESSED_AT = '2026-07-15T00:00:00Z';
const requestAnimationFrame = function() {{}};
const setTimeout = function() {{ return 1; }};
const clearTimeout = function() {{}};
let map;
let katasterWmsLayer;
let mapWorkspaceState = {{selectedBasemapId: 'maaruum-orthophoto'}};
function selectMapBasemap(state, selectedBasemapId, basemapNotice) {{
  return {{selectedBasemapId, basemapNotice}};
}}
function renderMapWorkspaceState() {{}}
function handleMapClick() {{}}
{init_map}
initMap();
const orthophoto = createdLayers.find(layer => layer.url.includes('/foto/'));
const gray = createdLayers.find(layer => layer.url.includes('/hallkaart/'));
const esri = createdLayers.find(layer => layer.url.includes('World_Light_Gray_Base'));
const baseLayers = [orthophoto, gray, esri];
function explicitlySelect(layer) {{
  baseLayers.forEach(candidate => mapStub.layers.delete(candidate));
  mapStub.layers.add(layer);
  mapStub.handlers.baselayerchange({{layer}});
}}
explicitlySelect(gray);
gray.fire('tileerror');
const firstGrayFailure = mapWorkspaceState.selectedBasemapId;
explicitlySelect(orthophoto);
orthophoto.fire('tileerror');
const secondCycleGray = mapWorkspaceState.selectedBasemapId;
gray.fire('tileerror');
const secondCycleEsri = mapWorkspaceState.selectedBasemapId;
gray.fire('tileerror');
const automaticLoopBlocked = mapWorkspaceState.selectedBasemapId;
explicitlySelect(gray);
gray.fire('tileerror');
console.log(JSON.stringify({{
  firstGrayFailure,
  secondCycleGray,
  secondCycleEsri,
  automaticLoopBlocked,
  explicitGrayReselection: mapWorkspaceState.selectedBasemapId,
  esriActive: mapStub.hasLayer(esri),
}}));
"""
        result = subprocess.run(["node", "-e", script], check=True, capture_output=True, text=True)
        state = json.loads(result.stdout)

        self.assertEqual(state["firstGrayFailure"], "esri-light-gray")
        self.assertEqual(state["secondCycleGray"], "maaruum-gray")
        self.assertEqual(state["secondCycleEsri"], "esri-light-gray")
        self.assertEqual(state["automaticLoopBlocked"], "esri-light-gray")
        self.assertEqual(state["explicitGrayReselection"], "esri-light-gray")
        self.assertTrue(state["esriActive"])

    def test_basemap_selection_state_is_preserved_but_omitted_from_compact_legend(self):
        pure = _marked_js_source("// MAP_WORKSPACE_PURE_START", "// MAP_WORKSPACE_PURE_END")
        script = f"""
{pure}
const initial = createMapWorkspaceState();
const fallback = selectMapBasemap(initial, 'maaruum-gray', 'Ortofoto ei laadinud; kasutusel on ametlik neutraalne varualuskaart.');
const orthophoto = selectMapBasemap(fallback, 'maaruum-orthophoto', null);
console.log(JSON.stringify({{
  initial,
  fallback,
  orthophoto,
  fallbackRows: mapWorkspaceLegendModel(fallback).rows,
  orthophotoRows: mapWorkspaceLegendModel(orthophoto).rows,
}}));
"""
        result = subprocess.run(["node", "-e", script], check=True, capture_output=True, text=True)
        state = json.loads(result.stdout)

        self.assertEqual(state["initial"]["selectedBasemapId"], "maaruum-orthophoto")
        self.assertEqual(state["fallback"]["selectedBasemapId"], "maaruum-gray")
        self.assertIsNone(state["orthophoto"]["basemapNotice"])
        self.assertEqual(state["fallbackRows"], [])
        self.assertEqual(state["orthophotoRows"], [])

    def test_basemap_runtime_offers_two_official_choices_and_hides_esri_fallback(self):
        init_map = _extract_js_function("initMap")
        change_handler = re.search(
            r"map\.on\('baselayerchange', function\(event\) \{(.*?)\n\s*\}\);",
            init_map,
            re.DOTALL,
        )
        self.assertIsNotNone(change_handler)
        handler = change_handler.group(1)

        for layer_name, basemap_id in (
            ("maaruumOrthophoto", "maaruum-orthophoto"),
            ("maaruumGrayMap", "maaruum-gray"),
        ):
            self.assertIn(f"event.layer === {layer_name}", handler)
            self.assertIn(f"'{basemap_id}'", handler)
        self.assertIn("selectMapBasemap", handler)
        self.assertIn("renderMapWorkspaceState();", handler)
        self.assertNotIn("customized", handler)
        self.assertIn("'Maa- ja Ruumiamet · ortofoto': maaruumOrthophoto", init_map)
        self.assertIn("'Maa- ja Ruumiamet · halltoonides kaart': maaruumGrayMap", init_map)
        self.assertNotIn("'Esri · World Light Gray Canvas': esriLightGrayCanvas", init_map)
        self.assertNotIn("esriWorldImagery", init_map)
        self.assertNotIn("esriWayback", init_map)
        self.assertIn("map.hasLayer(esriLightGrayCanvas)", handler)
        self.assertNotIn("Esri satelliit (värskeim)", INDEX_HTML)
        self.assertNotIn("Ortofoto 2026", INDEX_HTML)
        self.assertNotIn("2026. aasta ortofoto", INDEX_HTML)

    def test_official_attribution_uses_dynamic_extraction_date_not_flight_date(self):
        init_map = _extract_js_function("initMap")
        self.assertIn("new Intl.DateTimeFormat('et-EE')", init_map)
        self.assertIn("basemapExtractionDateEt", init_map)
        self.assertIn("Maa- ja Ruumiameti ortofoto", init_map)
        self.assertIn("Maa- ja Ruumiameti halltoonides kaart", init_map)
        self.assertIn("väljavõte ' + basemapExtractionDateEt", init_map)
        self.assertIn("pildistusaeg erineb asukohati", init_map)
        self.assertNotIn("värskeim", init_map)

    def test_map_workspace_has_one_semantic_legend_and_product_view_controls(self):
        workspace = re.search(r'<div class="map-controls" id="map-controls">.*?</div>\s*</div>\s*</div>', INDEX_HTML, re.DOTALL)
        self.assertIsNotNone(workspace)
        source = workspace.group(0)

        self.assertIn('id="map-workspace"', source)
        self.assertIn('id="map-workspace-opener"', source)
        self.assertIn('aria-controls="map-workspace-panel"', source)
        self.assertIn('aria-expanded="false"', source)
        self.assertIn('id="map-workspace-panel"', source)
        self.assertIn('id="map-workspace-close"', source)
        self.assertIn('id="map-workspace-status"', source)
        self.assertIn('Vali kinnistu', source)
        self.assertNotIn('id="map-workspace-theme-controls"', source)
        self.assertNotIn('id="map-workspace-reset"', source)
        self.assertIn('Kaardil', source)
        self.assertEqual(INDEX_HTML.count('role="region" aria-label="Kaardi legend"'), 1)
        self.assertEqual(source.count('role="region" aria-label="Kaardi legend"'), 1)
        self.assertEqual(
            re.findall(r'<button[^>]+class="map-view-preset"[^>]+data-map-view="([^"]+)"[^>]*>([^<]+)</button>', source),
            [
                ('overview', 'Ülevaade'),
                ('restrictions', 'Piirangud'),
                ('risks', 'Riskid'),
            ],
        )

        for legacy in ('id="map-legend"', 'id="map-kiht-legend"', 'class="layer-toggle"', 'data-layer='):
            self.assertNotIn(legacy, INDEX_HTML)
        self.assertNotIn(".layer-toggle input[type=checkbox]", INDEX_HTML)
        self.assertNotIn("function updateMapLegend", INDEX_HTML)
        self.assertNotIn("function updateKihtLegend", INDEX_HTML)

    def test_map_legend_model_keeps_required_empty_and_failure_rows_visible(self):
        pure = _marked_js_source("// MAP_WORKSPACE_PURE_START", "// MAP_WORKSPACE_PURE_END")
        script = f"""
{pure}
const source = {{key: 'official', label: 'Ametlik kiht', provider: 'Amet', interpretation: 'Kontrolli tingimusi.', data_as_of: null, checked_at: '2026-07-14T12:30:00Z'}};
const persistentContext = {{
  parcel: {{state: 'matches', feature: {{type: 'Feature', geometry: {{type: 'Polygon', coordinates: []}}, properties: {{}}}}, source}},
  stands: {{state: 'unavailable', count: 0, features: [], source}},
}};
let overview = Object.assign({{}}, createMapWorkspaceState('base'), {{
  parcelId: '78404:409:0113', hasValidPersistentContext: true, persistentContext,
  themeResults: {{
    nature_protection: {{id: 'nature_protection', label: 'Looduskaitse', state: 'matches', match_count: 2, features: [{{}}, {{}}], sources: [Object.assign({{}}, source, {{state: 'matches', match_count: 2}})]}},
    species_habitats: {{id: 'species_habitats', label: 'Liigid ja elupaigad', state: 'empty', match_count: 0, features: [], sources: [Object.assign({{}}, source, {{state: 'empty', match_count: 0}})]}},
    water_restrictions: {{id: 'water_restrictions', label: 'Vesi ja kaldapiirangud', state: 'unavailable', match_count: 0, features: [], sources: [Object.assign({{}}, source, {{state: 'unavailable', match_count: 0}})]}},
    heritage_other: {{id: 'heritage_other', label: 'Muinsuskaitse ja muud tegevuspiirangud', state: 'partial', match_count: 0, features: [], sources: [Object.assign({{}}, source, {{state: 'partial', match_count: 0}})]}},
  }},
}});
const overviewModel = mapWorkspaceLegendModel(overview);
const risks = Object.assign({{}}, selectMapViewPreset(overview, 'risks'), {{
  themeResults: {{
    flood_wetlands: {{id: 'flood_wetlands', label: 'Üleujutus ja märgalad', state: 'empty', match_count: 0, features: [], sources: []}},
    forest_health: {{id: 'forest_health', label: 'Metsatervise riskid', state: 'partial', match_count: 3, features: [{{}}, {{}}, {{}}], sources: []}},
    invasive_species: {{id: 'invasive_species', label: 'Võõrliigid', state: 'unavailable', match_count: 0, features: [], sources: []}},
  }},
}});
const riskModel = mapWorkspaceLegendModel(risks);
console.log(JSON.stringify({{
  overviewRows: overviewModel.rows.map(row => [row.id, row.status]),
  aggregateChecks: overviewModel.aggregate.checks.map(check => [check.id, check.status]),
  riskRows: riskModel.rows.map(row => [row.id, row.status]),
}}));
"""
        result = subprocess.run(["node", "-e", script], check=True, capture_output=True, text=True)
        model = json.loads(result.stdout)

        self.assertEqual(model["overviewRows"], [
            ["parcel", "Kinnistu leitud"],
            ["stands", "Allikas ei vasta"],
            ["overview_check", "Piirangute kontroll osaline"],
            ["nature_protection", "2 vastet"],
        ])
        self.assertEqual(model["aggregateChecks"], [
            ["nature_protection", "2 vastet"],
            ["species_habitats", "Vasteid ei leitud"],
            ["water_restrictions", "Allikas ei vasta"],
            ["heritage_other", "Puudumist ei saa kinnitada · osaline"],
        ])
        self.assertEqual(model["riskRows"], [
            ["parcel", "Kinnistu leitud"],
            ["stands", "Allikas ei vasta"],
            ["flood_wetlands", "Vasteid ei leitud"],
            ["forest_health", "3 vastet · osaline"],
            ["invasive_species", "Allikas ei vasta"],
        ])

    def test_map_status_source_freshness_and_event_wording_are_explicit(self):
        pure = _marked_js_source("// MAP_WORKSPACE_PURE_START", "// MAP_WORKSPACE_PURE_END")
        script = f"""
{pure}
const source = {{
  key: 'official', label: 'EELIS: ametlik kiht', provider: 'Keskkonnaagentuur',
  interpretation: 'Registrikanne ei ole tegevusluba.', data_as_of: null,
  checked_at: '2026-07-14T12:30:00Z', state: 'empty', match_count: 0,
}};
console.log(JSON.stringify({{
  statuses: [
    mapResultStatusText(null, 'theme', 'loading'),
    mapResultStatusText({{state: 'matches', match_count: 4}}, 'theme', 'refreshing'),
    mapResultStatusText({{state: 'empty', match_count: 0}}, 'theme'),
    mapResultStatusText({{state: 'matches', match_count: 4}}, 'theme'),
    mapResultStatusText({{state: 'partial', match_count: 2}}, 'theme'),
    mapResultStatusText({{state: 'partial', match_count: 0}}, 'theme'),
    mapResultStatusText({{state: 'unavailable', match_count: 0}}, 'theme'),
    mapResultStatusText({{state: 'unavailable', match_count: 0}}, 'theme', 'refreshing'),
  ],
  sourceHtml: mapSourceDetailsHtml(source),
}}));
"""
        result = subprocess.run(["node", "-e", script], check=True, capture_output=True, text=True)
        rendered = json.loads(result.stdout)
        self.assertEqual(rendered["statuses"], [
            "Laadib", "Uuendab", "Vasteid ei leitud", "4 vastet",
            "2 vastet · osaline", "Puudumist ei saa kinnitada · osaline",
            "Allikas ei vasta", "Laadib",
        ])
        self.assertIn("Keskkonnaagentuur · EELIS: ametlik kiht", rendered["sourceHtml"])
        self.assertIn("Registrikanne ei ole tegevusluba.", rendered["sourceHtml"])
        self.assertIn('class="map-source-as-of">Andmete ajaseis teadmata', rendered["sourceHtml"])
        self.assertIn('class="map-source-checked">Viimati edukalt kontrollitud ', rendered["sourceHtml"])
        self.assertNotRegex(rendered["sourceHtml"], r"map-source-as-of[^<]*Kontrollitud")

    def test_removed_history_layers_are_not_offered_in_the_minimal_workspace(self):
        pure = _marked_js_source("// MAP_WORKSPACE_PURE_START", "// MAP_WORKSPACE_PURE_END")
        script = f"""
{pure}
let state = createMapWorkspaceState('base');
const refusedHistoryView = selectMapViewPreset(state, 'history');
console.log(JSON.stringify({{
  presetIds: Object.keys(MAP_VIEW_PRESETS),
  refusedHistoryView,
}}));
"""
        result = subprocess.run(["node", "-e", script], check=True, capture_output=True, text=True)
        state = json.loads(result.stdout)

        self.assertEqual(state["presetIds"], ["overview", "restrictions", "risks"])
        self.assertEqual(state["refusedHistoryView"]["viewId"], "overview")

    def test_map_workspace_keyboard_aria_details_and_retry_contract(self):
        init = _extract_js_function("initMapWorkspaceControls")
        open_workspace = _extract_js_function("openMapWorkspace")
        close_mobile = _extract_js_function("closeMapWorkspaceOnMobile")
        render = _extract_js_function("renderMapWorkspaceState")
        row = _extract_js_function("mapLegendRowHtml")

        self.assertIn("event.key === 'Escape'", init)
        self.assertIn("closeMapWorkspace(true)", init)
        self.assertIn("opener.focus()", init)
        self.assertIn("setAttribute('aria-expanded'", init)
        self.assertIn("map-workspace-close", init)
        self.assertIn("data-map-view", init)
        self.assertNotIn("data-map-theme", init)
        self.assertIn("retryMapContext()", init)
        self.assertIn("<details", row)
        self.assertIn("<summary", row)
        summary = re.search(r"<summary.*?</summary>", row, re.DOTALL)
        self.assertIsNotNone(summary)
        self.assertNotIn("<button", summary.group(0))
        self.assertIn("mapWorkspaceLegendModel(mapWorkspaceState)", render)
        self.assertNotIn("availableMapThemeIds(mapWorkspaceState)", render)
        self.assertIn("window.matchMedia('(max-width: 640px)').matches", open_workspace)
        self.assertIn("requestAnimationFrame(function()", open_workspace)
        self.assertIn("window.scrollTo(0, window.scrollY + mapSection.getBoundingClientRect().top - 64)", open_workspace)
        self.assertIn("closeMapWorkspace(Boolean(restoreFocus))", close_mobile)
        self.assertNotIn("hiddenCount", row)

    def test_map_workspace_css_is_restrained_scrollable_and_mobile_sheet(self):
        desktop = re.search(r"(?m)^\.map-workspace \{([^}]*)\}", STYLE_CSS)
        self.assertIsNotNone(desktop)
        self.assertIn("width: min(340px, calc(100vw - 24px));", desktop.group(1))
        self.assertIn("max-height: calc(100% - 24px);", desktop.group(1))
        self.assertIn("overflow: hidden;", desktop.group(1))
        self.assertIn(".map-workspace-panel-body { overflow-y: auto;", STYLE_CSS)
        self.assertRegex(STYLE_CSS, r"@media \(max-width: 640px\) \{[\s\S]*?\.map-workspace-panel \{[^}]*position: fixed;[^}]*max-height: 72vh;[^}]*overflow: hidden;")
        self.assertIn(".map-workspace-button:focus-visible", STYLE_CSS)
        self.assertIn(".map-view-preset:focus-visible", STYLE_CSS)
        self.assertNotIn(".map-theme-toggle", STYLE_CSS)

    def test_map_age_legend_and_ai_picker_use_neutral_age_classes(self):
        row = _extract_js_function("mapStandAgeLegendHtml")
        picker = _extract_js_function("openEraldisSheet")
        for label in ("Noor", "Keskealine", "Valmiv", "Raievanus saavutatud", "Määramata"):
            self.assertIn(label, row)
        for harvest_term in ("Lageraie", "Harvendusraie", "Hooldusraie", "raie staatus"):
            self.assertNotIn(harvest_term, row)
        self.assertIn("e.age_class_label", picker)
        self.assertIn("e.age_class_color", picker)
        self.assertNotIn("e.raie_liik", picker)
        for old_variable in (
            "--map-eraldis-lageraie", "--map-eraldis-harvendus",
            "--map-eraldis-hooldus", "--map-eraldis-noor",
        ):
            self.assertNotIn(old_variable, INDEX_HTML)
            self.assertNotIn(old_variable, STYLE_CSS)
        for variable in (
            "--map-age-young", "--map-age-middle", "--map-age-maturing",
            "--map-age-reached", "--map-age-unknown",
        ):
            self.assertIn(variable, STYLE_CSS)

    def test_map_ui_preserves_result_cards_without_rendering_them(self):
        for element_id in (
            "card-kataster", "kataster-info", "card-mets", "mets-info",
            "card-vaartus", "vaartus-info", "card-sinik", "sinik-info",
            "card-riskid", "riskid-info", "card-eudr", "eudr-info",
            "card-kitsendused", "kitsendused-info", "card-teatised", "teatised-info",
            "card-toetused", "toetused-info",
        ):
            self.assertIn(f'id="{element_id}"', INDEX_HTML)

        forbidden_renderers = (
            "renderKataster", "renderMets", "renderVaartus", "renderSinik",
            "renderRiskid", "renderTeatised", "renderKitsendused", "renderToetused", "renderEudr",
        )
        for function_name in (
            "initMapWorkspaceControls", "openMapWorkspace", "closeMapWorkspace",
            "closeMapWorkspaceOnMobile", "selectMapView",
            "retryMapContext", "renderMapWorkspaceState",
        ):
            source = _extract_js_function(function_name)
            for renderer in forbidden_renderers:
                self.assertNotIn(renderer, source, f"{function_name} must not call {renderer}")

    def test_map_request_ownership_and_refreshing_retain_valid_results(self):
        source = _marked_js_source("// MAP_WORKSPACE_PURE_START", "// MAP_WORKSPACE_PURE_END")
        script = f"""
{source}
const controller = {{id: 'current'}};
let state = createMapWorkspaceState('orthophoto');
state = Object.assign({{}}, selectMapViewPreset(state, 'risks'), {{
  parcelId: '78404:409:0113',
  themeResults: {{forest_health: {{state: 'matches', features: [{{id: 1}}]}}}},
  themeCache: {{forest_health: {{state: 'matches', features: [{{id: 1}}]}}}},
  hasValidPersistentContext: true,
  requestGeneration: 5,
}});
const refreshing = beginMapContextRequestState(state, 6, controller, true);
const requested = serverBackedThemeIds(refreshing.activeThemeIds);
const switchedView = selectMapViewPreset(refreshing, 'restrictions');
console.log(JSON.stringify({{
  requested,
  loadingStatus: refreshing.loadingStatus,
  retainedResults: refreshing.themeResults,
  retainedCache: refreshing.themeCache,
  owner: mapContextRequestOwns(refreshing, 6, controller, '78404:409:0113', requested),
  staleGeneration: mapContextRequestOwns(refreshing, 5, controller, '78404:409:0113', requested),
  staleController: mapContextRequestOwns(refreshing, 6, {{id: 'other'}}, '78404:409:0113', requested),
  staleParcel: mapContextRequestOwns(refreshing, 6, controller, '17501:002:0490', requested),
  inactiveThemes: mapContextRequestOwns(refreshing, 6, controller, '78404:409:0113', ['nature_protection']),
  stillOwnsPersistentBootstrap: mapContextRequestOwns(switchedView, 6, controller, '78404:409:0113', requested),
}}));
"""
        result = subprocess.run(["node", "-e", script], check=True, capture_output=True, text=True)
        state = json.loads(result.stdout)

        self.assertEqual(state["requested"], ["flood_wetlands", "forest_health", "invasive_species"])
        self.assertEqual(state["loadingStatus"], "refreshing")
        self.assertEqual(state["retainedResults"]["forest_health"]["features"], [{"id": 1}])
        self.assertEqual(state["retainedCache"]["forest_health"]["features"], [{"id": 1}])
        self.assertTrue(state["owner"])
        self.assertFalse(state["staleGeneration"])
        self.assertFalse(state["staleController"])
        self.assertFalse(state["staleParcel"])
        self.assertFalse(state["inactiveThemes"])
        self.assertTrue(state["stillOwnsPersistentBootstrap"])

    def test_map_context_fetch_repeats_theme_params_and_rejects_invalid_echoes(self):
        source = _marked_js_source("// MAP_WORKSPACE_PURE_START", "// MAP_WORKSPACE_PURE_END")
        script = f"""
{source}
let captured = null;
const feature = {{type: 'Feature', geometry: {{type: 'Polygon', coordinates: []}}, properties: {{}}}};
const sourceRow = {{key: 'official'}};
function payload(parcelId, themeIds) {{
  return {{
    parcel_id: parcelId,
    requested_themes: themeIds,
    persistent: {{
      parcel: {{state: 'matches', feature, source: sourceRow}},
      stands: {{state: 'empty', features: [], source: sourceRow}},
    }},
    themes: Object.fromEntries(themeIds.map(function(themeId) {{
      return [themeId, {{id: themeId, state: 'empty', features: [], sources: [{{key: 'official', state: 'empty'}}]}}];
    }})),
  }};
}}
global.fetch = async function(url, options) {{
  captured = {{url, signalMatches: options.signal instanceof AbortSignal}};
  return {{
    ok: true,
    json: async function() {{
      return payload('78404:409:0113', ['forest_health', 'flood_wetlands']);
    }},
  }};
}};
(async function() {{
  const response = await fetchMapContext('78404:409:0113', ['forest_health', 'flood_wetlands'], new AbortController());
  let invalidParcel = false;
  let invalidOrder = false;
  global.fetch = async function() {{ return {{ok: true, json: async function() {{ return payload('other', ['forest_health', 'flood_wetlands']); }}}}; }};
  try {{ await fetchMapContext('78404:409:0113', ['forest_health', 'flood_wetlands'], new AbortController()); }} catch (_) {{ invalidParcel = true; }}
  global.fetch = async function() {{ return {{ok: true, json: async function() {{ return payload('78404:409:0113', ['flood_wetlands', 'forest_health']); }}}}; }};
  try {{ await fetchMapContext('78404:409:0113', ['forest_health', 'flood_wetlands'], new AbortController()); }} catch (_) {{ invalidOrder = true; }}
  console.log(JSON.stringify({{captured, responseParcel: response.parcel_id, invalidParcel, invalidOrder}}));
}})().catch(function(error) {{ console.error(error); process.exit(1); }});
"""
        result = subprocess.run(["node", "-e", script], check=True, capture_output=True, text=True)
        state = json.loads(result.stdout)

        self.assertEqual(
            state["captured"]["url"],
            "/api/map-context/78404%3A409%3A0113?themes=forest_health&themes=flood_wetlands",
        )
        self.assertTrue(state["captured"]["signalMatches"])
        self.assertEqual(state["responseParcel"], "78404:409:0113")
        self.assertTrue(state["invalidParcel"])
        self.assertTrue(state["invalidOrder"])

    def test_map_theme_source_grouping_uses_metadata_and_deterministic_fallback(self):
        source = _marked_js_source("// MAP_WORKSPACE_PURE_START", "// MAP_WORKSPACE_PURE_END")
        script = f"""
{source}
const theme = {{
  id: 'forest_health',
  sources: [
    {{key: 'official', style: {{color: '#123456', weight: 7, fillOpacity: 0.4, dash: '2,3'}}}},
    {{key: 'fallback'}},
  ],
  features: [
    {{type: 'Feature', geometry: {{type: 'Point', coordinates: [24, 59]}}, properties: {{source_key: 'official'}}}},
    {{type: 'Feature', geometry: {{type: 'Point', coordinates: [25, 59]}}, properties: {{source_key: 'fallback'}}}},
    {{type: 'Feature', geometry: {{type: 'Point', coordinates: [26, 59]}}, properties: {{source_key: 'fallback'}}}},
  ],
}};
const grouped = groupThemeFeaturesBySource(theme);
const second = groupThemeFeaturesBySource(theme);
console.log(JSON.stringify({{grouped, fallbackAgain: second[1].style}}));
"""
        result = subprocess.run(["node", "-e", script], check=True, capture_output=True, text=True)
        state = json.loads(result.stdout)

        self.assertEqual([group["sourceKey"] for group in state["grouped"]], ["official", "fallback"])
        self.assertEqual(len(state["grouped"][0]["features"]), 1)
        self.assertEqual(len(state["grouped"][1]["features"]), 2)
        self.assertEqual(state["grouped"][0]["style"], {
            "color": "#123456", "weight": 7, "fillOpacity": 0.4, "dash": "2,3",
        })
        self.assertEqual(state["grouped"][1]["style"], state["fallbackAgain"])
        self.assertNotEqual(state["grouped"][1]["style"]["color"], "#123456")

    def test_removed_history_and_subsidy_views_do_not_build_hidden_map_themes(self):
        self.assertNotIn("deriveForestNoticeTheme", INDEX_HTML)
        self.assertNotIn("deriveSubsidyIndicatorTheme", INDEX_HTML)
        self.assertNotIn("deriveClientMapThemes", INDEX_HTML)
        self.assertNotIn("subsidy_indicators", INDEX_HTML)
        self.assertNotIn("forest_notices", INDEX_HTML)

    def test_per_theme_refresh_failure_and_cached_revisit_are_explicit(self):
        source = _marked_js_source("// MAP_WORKSPACE_PURE_START", "// MAP_WORKSPACE_PURE_END")
        script = f"""
{source}
const controller = {{id: 'refresh'}};
const cached = {{id: 'forest_health', label: 'Metsatervise riskid', state: 'matches', match_count: 1, features: [{{id: 1}}], sources: []}};
let state = Object.assign({{}}, selectMapViewPreset(createMapWorkspaceState(), 'risks'), {{
  parcelId: '78404:409:0113', hasValidPersistentContext: true,
  persistentContext: {{parcel: {{state: 'matches'}}, stands: {{state: 'empty', count: 0, features: []}}}},
  themeResults: {{forest_health: cached}}, themeCache: {{forest_health: cached}}, requestGeneration: 2,
}});
const refreshing = beginMapContextRequestState(state, 3, controller, false, ['forest_health']);
const failed = failMapContextRequestState(refreshing, ['forest_health'], 'Ajutine tõrge');
const failedModel = mapWorkspaceLegendModel(failed);
const switchedAway = selectMapViewPreset(failed, 'restrictions');
const revisited = selectMapViewPreset(switchedAway, 'risks');
const revisiting = beginMapContextRequestState(revisited, 4, {{id: 'revisit'}}, false, ['forest_health']);
const succeeded = applyMapContextResultState(revisiting, {{
  persistent: state.persistentContext,
  themes: {{forest_health: {{id: 'forest_health', state: 'empty', match_count: 0, features: [], sources: []}}}},
}}, ['forest_health']);
const overviewThemeIds = MAP_VIEW_PRESETS.overview.themeIds;
const overviewThemes = Object.fromEntries(overviewThemeIds.map(id => [id, {{id, state: 'empty', match_count: 0, features: [], sources: []}}]));
let overview = Object.assign({{}}, selectMapViewPreset(state, 'overview'), {{themeResults: overviewThemes, themeCache: overviewThemes}});
overview = beginMapContextRequestState(overview, 5, {{id: 'overview'}}, false, overviewThemeIds);
overview = failMapContextRequestState(overview, overviewThemeIds, 'Ajutine tõrge');
const overviewAggregate = mapWorkspaceLegendModel(overview).aggregate.status;
console.log(JSON.stringify({{refreshing, failed, failedRows: failedModel.rows, switchedAway, revisited, revisiting, succeeded, overviewAggregate}}));
"""
        result = subprocess.run(["node", "-e", script], check=True, capture_output=True, text=True)
        state = json.loads(result.stdout)

        self.assertEqual(state["refreshing"]["loadingStatus"], "refreshing")
        self.assertTrue(state["refreshing"]["themeResults"]["forest_health"]["previous_result"])
        failed_theme = state["failed"]["themeResults"]["forest_health"]
        self.assertEqual(failed_theme["state"], "partial")
        self.assertTrue(failed_theme["previous_result"])
        self.assertTrue(failed_theme["refresh_failed"])
        self.assertTrue(failed_theme["stale"])
        failed_row = next(row for row in state["failedRows"] if row["id"] == "forest_health")
        self.assertIn("osaline", failed_row["status"])
        self.assertEqual(state["switchedAway"]["viewId"], "restrictions")
        self.assertEqual(state["revisited"]["themeResults"]["forest_health"]["features"], [{"id": 1}])
        self.assertEqual(state["revisiting"]["loadingStatus"], "refreshing")
        self.assertEqual(state["succeeded"]["themeResults"]["forest_health"]["state"], "empty")
        self.assertFalse(state["succeeded"]["themeResults"]["forest_health"].get("stale", False))
        self.assertEqual(state["overviewAggregate"], "Piirangute kontroll osaline")

    def test_legacy_fallback_layers_are_scoped_and_cleared_on_success_and_view_changes(self):
        clear = _extract_js_function("clearLegacyMapFallbackLayers")
        apply_payload = _extract_js_function("applyMapContextPayload")
        for function_name in ("selectMapView",):
            self.assertIn("clearLegacyMapFallbackLayers();", _extract_js_function(function_name))
        self.assertIn("clearLegacyMapFallbackLayers();", apply_payload)
        self.assertIn("LEGACY_MAP_FALLBACK_PREFIX", _extract_js_function("loadMapLayers"))

        script = f"""
const LEGACY_MAP_FALLBACK_PREFIX = 'legacy-fallback:';
let legacyMapFallbackActive = true;
const removed = [];
const overlayLayers = {{eraldised: {{}}, 'legacy-fallback:kaitsealad': {{}}, 'map-context:risk:0': {{}}}};
function removeOverlayLayer(name) {{ removed.push(name); delete overlayLayers[name]; }}
{clear}
clearLegacyMapFallbackLayers();
console.log(JSON.stringify({{removed, remaining: Object.keys(overlayLayers), active: legacyMapFallbackActive}}));
"""
        result = subprocess.run(["node", "-e", script], check=True, capture_output=True, text=True)
        state = json.loads(result.stdout)
        self.assertEqual(state["removed"], ["eraldised", "legacy-fallback:kaitsealad"])
        self.assertEqual(state["remaining"], ["map-context:risk:0"])
        self.assertFalse(state["active"])

    def test_failed_risk_request_cannot_restore_pending_legacy_overview_layers(self):
        pure = _marked_js_source("// MAP_WORKSPACE_PURE_START", "// MAP_WORKSPACE_PURE_END")
        clear = _extract_js_function("clearLegacyMapFallbackLayers")
        load = _extract_js_function("loadMapLayers")
        set_fallback = _extract_js_function("setLegacyMapFallback")
        apply_fallback = _extract_js_function("applyLegacyMapFallback")
        request_context = _extract_js_function("requestMapContextForParcel")
        select_view = _extract_js_function("selectMapView")
        script = f"""
{pure}
const LEGACY_MAP_FALLBACK_PREFIX = 'legacy-fallback:';
let pendingLegacyMapFallback = null;
let legacyMapFallbackActive = false;
const overlayLayers = {{}};
const window = {{}};
function removeOverlayLayer(name) {{ delete overlayLayers[name]; }}
function addEraldisedLayer(features) {{ overlayLayers.eraldised = {{features}}; }}
function addOverlayLayer(name, features) {{ overlayLayers[name] = {{features}}; }}
function showParcel() {{}}
function renderMapWorkspaceState() {{}}
function applyMapContextPayload() {{ throw new Error('Unexpected successful context'); }}
function fetchMapContext() {{ return Promise.reject(new Error('Context unavailable')); }}
{clear}
{load}
{set_fallback}
{apply_fallback}
{request_context}
{select_view}
const parcelId = '78404:409:0113';
let mapWorkspaceState = Object.assign({{}}, createMapWorkspaceState(), {{
  parcelId,
  loadingStatus: 'error',
  errorStatus: 'Initial context unavailable',
}});
const legacyData = {{
  kataster: {{number: parcelId, geometry: {{type: 'Polygon', coordinates: []}}}},
  map_layers: {{
    eraldised: {{features: [{{id: 'stand'}}]}},
    kaitsealad: {{features: [{{id: 'overview-protection'}}]}},
    natura_elupaik: {{features: [{{id: 'overview-habitat'}}]}},
  }},
}};
(async function() {{
  const initiallyApplied = setLegacyMapFallback(parcelId, legacyData);
  const initialLayers = Object.keys(overlayLayers).sort();
  const requestResult = await selectMapView('risks');
  console.log(JSON.stringify({{
    initiallyApplied,
    initialLayers,
    requestResult,
    finalView: mapWorkspaceState.viewId,
    finalStatus: mapWorkspaceState.loadingStatus,
    finalLayers: Object.keys(overlayLayers).sort(),
    pendingFallback: pendingLegacyMapFallback,
    fallbackActive: legacyMapFallbackActive,
  }}));
}})().catch(function(error) {{ console.error(error); process.exit(1); }});
"""
        result = subprocess.run(["node", "-e", script], check=True, capture_output=True, text=True)
        state = json.loads(result.stdout)

        self.assertTrue(state["initiallyApplied"])
        self.assertEqual(state["initialLayers"], [
            "eraldised", "legacy-fallback:kaitsealad", "legacy-fallback:natura_elupaik",
        ])
        self.assertFalse(state["requestResult"])
        self.assertEqual(state["finalView"], "risks")
        self.assertEqual(state["finalStatus"], "error")
        self.assertEqual(state["finalLayers"], [])
        self.assertIsNone(state["pendingFallback"])
        self.assertFalse(state["fallbackActive"])

    def test_search_uses_map_layer_opt_out_and_async_completion_does_not_close_mobile_panel(self):
        search = _extract_js_function("searchParcel").replace(
            "function searchParcel", "async function searchParcel", 1
        )
        script = f"""
const API_BASE = 'https://example.test/api';
let requestedUrl = null;
global.fetch = async function(url) {{ requestedUrl = url; return {{ok: true, json: async function() {{ return {{kataster: {{number: 'x'}}}}; }}}}; }};
{search}
(async function() {{
  await searchParcel('78404:409:0113', new AbortController());
  console.log(JSON.stringify(requestedUrl));
}})().catch(function(error) {{ console.error(error); process.exit(1); }});
"""
        result = subprocess.run(["node", "-e", script], check=True, capture_output=True, text=True)
        self.assertEqual(
            json.loads(result.stdout),
            "https://example.test/api/search/78404%3A409%3A0113?include_map_layers=false",
        )
        self.assertNotIn("closeMapWorkspaceOnMobile", _extract_js_function("applyMapContextPayload"))
        self.assertNotIn("closeMapWorkspaceOnMobile", _extract_js_function("doSearch"))
        self.assertNotIn(".focus(", _extract_js_function("applyMapContextPayload"))
        self.assertNotIn(".focus(", _extract_js_function("doSearch"))
        self.assertIn("closeMapWorkspaceOnMobile(false);", _extract_js_function("beginParcelReplacement"))

    def test_stand_popup_always_reports_inventory_freshness(self):
        source = _extract_js_function("addEraldisedLayer")
        self.assertIn("Inventuuri kuupäev: ", source)
        self.assertIn("Inventuuri kuupäev teadmata", source)
        self.assertIn("age_class_label", source)
        self.assertIn("age_class_provenance", source)

    def test_server_theme_details_show_official_provenance_and_match_count_without_fabrication(self):
        pure = _marked_js_source("// MAP_WORKSPACE_PURE_START", "// MAP_WORKSPACE_PURE_END")
        script = f"""
{pure}
console.log(JSON.stringify(mapSourceDetailsHtml({{
  key: 'kaitsealad', provider: 'Keskkonnaagentuur', label: 'EELIS: kaitsealad',
  interpretation: 'Ametlik kattuvus.', match_count: 2,
}})));
"""
        result = subprocess.run(["node", "-e", script], check=True, capture_output=True, text=True)
        detail = json.loads(result.stdout)
        self.assertIn("Ametlik andmekiht", detail)
        self.assertIn("Kattuvusi: 2", detail)
        self.assertNotIn("%", detail)

    def test_map_runtime_is_parallel_isolated_and_uses_legacy_only_as_failure_fallback(self):
        do_search = _extract_js_function("doSearch")
        apply_payload = _extract_js_function("applyMapContextPayload")
        self.assertIn("var mapContextPromise = requestMapContextForParcel(nr);", do_search)
        self.assertLess(
            do_search.index("requestMapContextForParcel(nr)"),
            do_search.index("await searchParcel(nr, controller)"),
        )
        self.assertNotIn("loadMapLayers(data.map_layers", do_search)
        self.assertNotIn("deriveClientMapThemes", do_search)
        self.assertIn("setLegacyMapFallback(nr, data);", do_search)
        self.assertNotIn("hideLoading()", apply_payload)
        self.assertNotIn("showDashboard()", apply_payload)
        self.assertLess(do_search.index("safe(renderEudr"), do_search.index("hideLoading()"))
        self.assertLess(do_search.index("hideLoading()"), do_search.index("showDashboard()"))

        fallback = _extract_js_function("applyLegacyMapFallback")
        self.assertIn("mapWorkspaceState.hasValidPersistentContext", fallback)
        self.assertIn("mapWorkspaceState.loadingStatus !== 'error'", fallback)
        self.assertIn("loadMapLayers", fallback)

        forbidden_renderers = (
            "renderKataster", "renderMets", "renderVaartus", "renderSinik",
            "renderRiskid", "renderTeatised", "renderKitsendused", "renderToetused", "renderEudr",
        )
        for function_name in (
            "selectMapView",
            "retryMapContext", "renderMapWorkspaceState",
        ):
            source = _extract_js_function(function_name)
            for renderer in forbidden_renderers:
                self.assertNotIn(renderer, source, f"{function_name} must not call {renderer}")

    def test_map_stand_popup_uses_neutral_age_class_contract(self):
        source = _extract_js_function("addEraldisedLayer")
        self.assertIn("age_class_label", source)
        self.assertIn("age_class_color", source)
        self.assertIn("age_class_provenance", source)
        self.assertNotIn("raie_liik", source)
        self.assertNotIn("vanuseruhm_desc", source)

    def test_notice_badges_prefer_canonical_event_status_over_legacy_active_flag(self):
        badge = _extract_js_function("teatisedStatusBadge")
        script = f"""
function escHtml(value) {{
  return String(value).replace(/[&<>\"']/g, character => ({{'&':'&amp;', '<':'&lt;', '>':'&gt;', '\"':'&quot;', "'":'&#39;'}})[character]);
}}
{badge}
const statuses = [
  teatisedStatusBadge('permitted_current', 'Kehtiv lubatud töö', 'EI', false, false),
  teatisedStatusBadge('not_permitted', 'Töö ei ole lubatud', 'EI', true, false),
  teatisedStatusBadge('registered', 'Registreeritud', 'JAH', true, false),
  teatisedStatusBadge('archived', 'Arhiivitud sündmus', 'KEHTIV', true, false),
  teatisedStatusBadge('not_current', 'Ei ole praegu kehtiv', 'KEHTIV', true, false),
  teatisedStatusBadge('unknown', 'Staatus määramata', 'MALFORMED', true, false),
  teatisedStatusBadge('unknown', '<b>Kontrollimata</b>', 'KEHTIV', true, false),
  teatisedStatusBadge(undefined, undefined, 'KEHTIV', true, false),
];
console.log(JSON.stringify(statuses));
"""
        result = subprocess.run(["node", "-e", script], check=True, capture_output=True, text=True)
        statuses = json.loads(result.stdout)

        expected_classes = (
            "status-permitted-current", "status-not-permitted", "status-registered",
            "status-archived", "status-not-current", "status-unknown",
        )
        for rendered, expected_class in zip(statuses, expected_classes):
            self.assertIn(expected_class, rendered)
        self.assertIn("Kehtiv lubatud töö", statuses[0])
        self.assertIn("Töö ei ole lubatud", statuses[1])
        self.assertIn("Staatus määramata", statuses[5])
        self.assertNotIn("status-kehtiv", statuses[1])
        self.assertNotIn("status-kehtiv", statuses[5])
        self.assertIn("&lt;b&gt;Kontrollimata&lt;/b&gt;", statuses[6])
        self.assertNotIn("<b>", statuses[6])
        self.assertIn("status-kehtiv", statuses[7])

    def test_search_failure_preserves_successful_map_context_for_same_parcel(self):
        owns_map = _extract_js_function("hasPersistentMapContextForParcel")
        do_search = _extract_js_function("doSearch").replace(
            "function doSearch", "async function doSearch", 1
        )
        script = f"""
let parcelSearchSequence = 0;
let activeParcelSearch = null;
let mapWorkspaceState = {{parcelId: null, hasValidPersistentContext: false, persistentContext: null}};
const overlayLayers = {{}};
const classList = {{add() {{}}, remove() {{}}}};
const searchBox = {{classList}};
const searchButton = {{disabled: false, classList, closest() {{ return searchBox; }}}};
const elements = {{
  'kataster-input': {{value: '78404:409:0113'}},
  'search-btn': searchButton,
  'search-btn-landing': null,
  'map-controls': {{style: {{display: 'none'}}}},
}};
const document = {{getElementById(id) {{ return elements[id] || null; }}}};
function beginParcelReplacement() {{ parcelSearchSequence += 1; return parcelSearchSequence; }}
function showLoading() {{}}
function requestMapContextForParcel(parcelId) {{
  mapWorkspaceState = {{
    parcelId,
    hasValidPersistentContext: true,
    persistentContext: {{parcel: {{state: 'matches', feature: {{type: 'Feature', geometry: {{type: 'Polygon'}}, properties: {{}}}}}}}},
  }};
  overlayLayers.parcel = {{id: 'parcel'}};
  overlayLayers.stands = {{id: 'stands'}};
  return Promise.resolve(true);
}}
async function searchParcel() {{ throw new Error('Analüüsiteenus ei vasta'); }}
function resetMapWorkspaceForParcel() {{ throw new Error('Map context must not be reset'); }}
let fullResetCount = 0;
function resetParcelResult() {{ fullResetCount += 1; overlayLayers.parcel = null; }}
let analyticalResetCount = 0;
function resetAnalyticalResult() {{ analyticalResetCount += 1; }}
function hideLoading() {{}}
function showDashboard() {{}}
let renderedError = null;
function renderErrorState(message) {{ renderedError = message; }}
function showError() {{}}
function clearSearchBusyState() {{}}
function isMapRecord(value) {{ return Boolean(value && typeof value === 'object' && !Array.isArray(value)); }}
function isMapFeature(value) {{
  return Boolean(isMapRecord(value) && value.type === 'Feature' && isMapRecord(value.geometry) && isMapRecord(value.properties));
}}
{owns_map}
{do_search}
(async function() {{
  await doSearch();
  console.log(JSON.stringify({{
    fullResetCount,
    analyticalResetCount,
    renderedError,
    parcelId: mapWorkspaceState.parcelId,
    hasContext: mapWorkspaceState.hasValidPersistentContext,
    overlays: Object.keys(overlayLayers).filter(key => overlayLayers[key]),
  }}));
}})().catch(error => {{ console.error(error); process.exit(1); }});
"""
        result = subprocess.run(["node", "-e", script], check=True, capture_output=True, text=True)
        state = json.loads(result.stdout)

        self.assertEqual(state["fullResetCount"], 0)
        self.assertEqual(state["analyticalResetCount"], 1)
        self.assertEqual(state["renderedError"], "Analüüsiteenus ei vasta")
        self.assertEqual(state["parcelId"], "78404:409:0113")
        self.assertTrue(state["hasContext"])
        self.assertEqual(state["overlays"], ["parcel", "stands"])

    def test_search_failure_does_not_abort_pending_map_context_for_same_parcel(self):
        owns_map = _extract_js_function("hasPersistentMapContextForParcel")
        owns_pending_map = _extract_js_function("hasActiveMapContextRequestForParcel")
        do_search = _extract_js_function("doSearch").replace(
            "function doSearch", "async function doSearch", 1
        )
        script = f"""
let parcelSearchSequence = 0;
let activeParcelSearch = null;
let mapWorkspaceState = {{parcelId: null, hasValidPersistentContext: false, persistentContext: null}};
const overlayLayers = {{}};
const classList = {{add() {{}}, remove() {{}}}};
const searchBox = {{classList}};
const searchButton = {{disabled: false, classList, closest() {{ return searchBox; }}}};
const elements = {{
  'kataster-input': {{value: '78404:409:0113'}},
  'search-btn': searchButton,
  'search-btn-landing': null,
  'map-controls': {{style: {{display: 'none'}}}},
}};
const document = {{getElementById(id) {{ return elements[id] || null; }}}};
function beginParcelReplacement() {{ parcelSearchSequence += 1; return parcelSearchSequence; }}
function showLoading() {{}}
let finishMapContext = null;
function requestMapContextForParcel(parcelId) {{
  const controller = {{aborted: false, abort() {{ this.aborted = true; }}}};
  mapWorkspaceState = {{
    parcelId,
    loadingStatus: 'loading',
    requestController: controller,
    hasValidPersistentContext: false,
    persistentContext: null,
  }};
  return new Promise(resolve => {{
    finishMapContext = function() {{
      if (!controller.aborted) {{
        mapWorkspaceState = {{
          parcelId,
          loadingStatus: 'success',
          requestController: null,
          hasValidPersistentContext: true,
          persistentContext: {{parcel: {{state: 'matches', feature: {{type: 'Feature', geometry: {{type: 'Polygon'}}, properties: {{}}}}}}}},
        }};
        overlayLayers.parcel = {{id: 'parcel'}};
      }}
      resolve(!controller.aborted);
    }};
  }});
}}
async function searchParcel() {{ throw new Error('Analüüsiteenus ei vasta'); }}
let fullResetCount = 0;
function resetParcelResult() {{
  fullResetCount += 1;
  if (mapWorkspaceState.requestController) mapWorkspaceState.requestController.abort();
  mapWorkspaceState = {{parcelId: null, hasValidPersistentContext: false, persistentContext: null}};
}}
let analyticalResetCount = 0;
function resetAnalyticalResult() {{ analyticalResetCount += 1; }}
function hideLoading() {{}}
function showDashboard() {{}}
let renderedError = null;
function renderErrorState(message) {{ renderedError = message; }}
function showError() {{}}
function clearSearchBusyState() {{}}
function isMapRecord(value) {{ return Boolean(value && typeof value === 'object' && !Array.isArray(value)); }}
function isMapFeature(value) {{
  return Boolean(isMapRecord(value) && value.type === 'Feature' && isMapRecord(value.geometry) && isMapRecord(value.properties));
}}
{owns_map}
{owns_pending_map}
{do_search}
(async function() {{
  await doSearch();
  const pendingSurvived = fullResetCount === 0 && mapWorkspaceState.requestController.aborted === false;
  finishMapContext();
  await Promise.resolve();
  console.log(JSON.stringify({{
    pendingSurvived,
    fullResetCount,
    analyticalResetCount,
    renderedError,
    parcelId: mapWorkspaceState.parcelId,
    hasContext: mapWorkspaceState.hasValidPersistentContext,
    overlays: Object.keys(overlayLayers),
  }}));
}})().catch(error => {{ console.error(error); process.exit(1); }});
"""
        result = subprocess.run(["node", "-e", script], check=True, capture_output=True, text=True)
        state = json.loads(result.stdout)

        self.assertTrue(state["pendingSurvived"])
        self.assertEqual(state["fullResetCount"], 0)
        self.assertEqual(state["analyticalResetCount"], 1)
        self.assertEqual(state["renderedError"], "Analüüsiteenus ei vasta")
        self.assertEqual(state["parcelId"], "78404:409:0113")
        self.assertTrue(state["hasContext"])
        self.assertEqual(state["overlays"], ["parcel"])

    def test_legacy_stand_layer_prefers_age_color_and_matches_age_legend(self):
        layer = _extract_js_function("addEraldisedLayer")
        legend = _extract_js_function("mapStandAgeLegendHtml")
        script = f"""
let capturedStyle = null;
const map = {{}};
const overlayLayers = {{}};
function removeOverlayLayer() {{}}
const L = {{
  layerGroup(items) {{ return {{items, addTo() {{ return this; }}}}; }},
  geoJSON(collection, options) {{
    capturedStyle = options.style(collection.features[0]);
    return {{collection, options}};
  }},
}};
{layer}
{legend}
addEraldisedLayer([{{
  type: 'Feature', geometry: {{type: 'Polygon', coordinates: []}},
  properties: {{
    color: '#ff0000',
    age_class_color: 'var(--map-age-maturing)',
    age_class_label: 'Valmiv',
  }},
}}]);
console.log(JSON.stringify({{capturedStyle, legend: mapStandAgeLegendHtml()}}));
"""
        result = subprocess.run(["node", "-e", script], check=True, capture_output=True, text=True)
        state = json.loads(result.stdout)

        self.assertEqual(state["capturedStyle"]["fillColor"], "var(--map-age-maturing)")
        self.assertEqual(state["capturedStyle"]["color"], "var(--map-age-maturing)")
        self.assertNotIn("#ff0000", state["capturedStyle"].values())
        self.assertIn('--age-color:var(--map-age-maturing)"></span>Valmiv', state["legend"])

    def test_workspace_rerender_restores_keyboard_focus_and_open_rows(self):
        capture = _extract_js_function("captureMapWorkspaceDomState")
        restore = _extract_js_function("restoreMapWorkspaceDomState")
        script = f"""
function makeElement(attributes) {{
  return {{
    attributes: attributes || {{}}, disabled: false, open: false, isConnected: true,
    getAttribute(name) {{ return this.attributes[name] == null ? null : this.attributes[name]; }},
    matches(selector) {{
      if (selector === 'summary') return this.attributes.role === 'summary';
      const match = /^\\[([^\\]]+)\\]$/.exec(selector);
      return Boolean(match && this.attributes[match[1]] != null);
    }},
    closest(selector) {{ return selector === '[data-map-row]' ? this.row || null : null; }},
    querySelector(selector) {{ return selector === 'summary' ? this.summary || null : null; }},
    focus(options) {{ this.focusOptions = options; document.activeElement = this; }},
  }};
}}
let openRows = [];
let allRows = [];
let controls = {{}};
const legend = {{
  querySelectorAll(selector) {{
    if (selector === 'details[data-map-row][open]') return openRows;
    if (selector === 'details[data-map-row]') return allRows;
    return [];
  }},
}};
const document = {{
  activeElement: null,
  getElementById(id) {{ return id === 'map-workspace-legend' ? legend : controls[id] || null; }},
  querySelectorAll(selector) {{ return controls[selector] || []; }},
}};
{capture}
{restore}

const oldRow = makeElement({{'data-map-row': 'forest_health'}});
oldRow.open = true;
const oldView = makeElement({{'data-map-view': 'risks'}});
openRows = [oldRow];
document.activeElement = oldView;
const keyboardViewState = captureMapWorkspaceDomState();

const newSummary = makeElement({{role: 'summary'}});
const newRow = makeElement({{'data-map-row': 'forest_health'}});
newRow.summary = newSummary;
newSummary.row = newRow;
const newView = makeElement({{'data-map-view': 'risks'}});
allRows = [newRow];
openRows = [];
controls['[data-map-view]'] = [newView];
controls['[data-map-theme]'] = [];
controls['[data-map-retry]'] = [];
restoreMapWorkspaceDomState(keyboardViewState);

const oldRetry = makeElement({{'data-map-retry': 'row:forest_health'}});
oldRetry.row = newRow;
document.activeElement = oldRetry;
newRow.open = true;
openRows = [newRow];
const retryState = captureMapWorkspaceDomState();
const replacementRetry = makeElement({{'data-map-retry': 'row:forest_health'}});
controls['[data-map-retry]'] = [replacementRetry];
restoreMapWorkspaceDomState(retryState);

const disabledRetry = makeElement({{'data-map-retry': 'row:forest_health'}});
disabledRetry.disabled = true;
controls['[data-map-retry]'] = [disabledRetry];
document.activeElement = oldRetry;
restoreMapWorkspaceDomState(retryState);

controls['[data-map-retry]'] = [];
newSummary.focusOptions = null;
restoreMapWorkspaceDomState(retryState);

console.log(JSON.stringify({{
  keyboardFocusRestored: newView.focusOptions,
  rowReopened: newRow.open,
  retryFocusRestored: replacementRetry.focusOptions,
  disabledRetryFocused: Boolean(disabledRetry.focusOptions),
  completedRetrySummaryFocus: newSummary.focusOptions,
}}));
"""
        result = subprocess.run(["node", "-e", script], check=True, capture_output=True, text=True)
        state = json.loads(result.stdout)

        self.assertEqual(state["keyboardFocusRestored"], {"preventScroll": True})
        self.assertTrue(state["rowReopened"])
        self.assertEqual(state["retryFocusRestored"], {"preventScroll": True})
        self.assertFalse(state["disabledRetryFocused"])
        self.assertEqual(state["completedRetrySummaryFocus"], {"preventScroll": True})

        render = _extract_js_function("renderMapWorkspaceState")
        self.assertLess(
            render.index("captureMapWorkspaceDomState()"),
            render.index("legend.innerHTML"),
        )
        self.assertGreater(
            render.index("restoreMapWorkspaceDomState"),
            render.index("legend.innerHTML"),
        )

    def test_retry_controls_have_contextual_escaped_accessible_names(self):
        pure = _marked_js_source("// MAP_WORKSPACE_PURE_START", "// MAP_WORKSPACE_PURE_END")
        row = _extract_js_function("mapLegendRowHtml")
        script = f"""
{pure}
function mapStandAgeLegendHtml() {{ return ''; }}
{row}
const html = mapLegendRowHtml({{
  id: 'overview_check', label: 'Piirangute kontroll',
  status: 'Piirangute kontroll osaline', color: '#000', interpretation: 'Kontroll.',
  checks: [
    {{id: 'nature_protection', label: 'Looduskaitse', status: 'Allikas ei vasta', result: {{state: 'unavailable'}}}},
    {{id: 'water_restrictions', label: 'Vesi <ja> kaldad', status: 'Puudumist ei saa kinnitada · osaline', result: {{state: 'partial'}}}},
  ],
}});
console.log(JSON.stringify(html));
"""
        result = subprocess.run(["node", "-e", script], check=True, capture_output=True, text=True)
        html = json.loads(result.stdout)

        self.assertIn('aria-label="Proovi uuesti: Looduskaitse"', html)
        self.assertIn('aria-label="Proovi uuesti: Vesi &lt;ja&gt; kaldad"', html)
        self.assertIn('aria-label="Proovi uuesti: Piirangute kontroll"', html)
        self.assertIn('data-map-retry="check:nature_protection"', html)
        self.assertIn('data-map-retry="row:overview_check"', html)
        self.assertNotIn('aria-label="Proovi uuesti: Vesi <ja> kaldad"', html)

    def test_incomplete_stands_keep_features_visible_and_report_partial_geometry(self):
        pure = _marked_js_source("// MAP_WORKSPACE_PURE_START", "// MAP_WORKSPACE_PURE_END")
        row = _extract_js_function("mapLegendRowHtml")
        render = _extract_js_function("renderMapWorkspaceState")
        script = f"""
{pure}
function mapStandAgeLegendHtml() {{ return ''; }}
{row}
const feature = {{type: 'Feature', geometry: {{type: 'Polygon', coordinates: []}}, properties: {{}}}};
const state = Object.assign({{}}, createMapWorkspaceState(), {{
  parcelId: '78404:409:0113', hasValidPersistentContext: true, loadingStatus: 'success',
  persistentContext: {{
    parcel: {{state: 'matches', feature, source: {{key: 'parcel'}}}},
    stands: {{state: 'matches', complete: false, count: 1, features: [feature], source: {{key: 'stands'}}}},
  }},
}});
const stands = mapWorkspaceLegendModel(state).rows.find(item => item.id === 'stands');
console.log(JSON.stringify({{stands, html: mapLegendRowHtml(stands)}}));
"""
        result = subprocess.run(["node", "-e", script], check=True, capture_output=True, text=True)
        state = json.loads(result.stdout)

        self.assertEqual(state["stands"]["status"], "Leiti 1 eraldist · osaline")
        self.assertIn("kasutuskõlbmatu", state["stands"]["interpretation"])
        self.assertIn('aria-label="Proovi uuesti: Metsaeraldised"', state["html"])
        self.assertIn("data-map-retry", state["html"])
        self.assertIn(
            "persistent.stands.state === 'matches' && persistent.stands.features.length",
            render,
        )
        self.assertNotIn("persistent.stands.complete === true", render)

    def test_source_freshness_separates_attempts_from_success_and_never_uses_browser_time(self):
        pure = _marked_js_source("// MAP_WORKSPACE_PURE_START", "// MAP_WORKSPACE_PURE_END")
        script = f"""
{pure}
const unavailable = mapSourceDetailsHtml({{
  key: 'official', provider: 'Amet', label: 'Kiht', state: 'unavailable',
  attempted_at: '2026-07-15T12:30:00Z', checked_at: null,
}});
const successful = mapSourceDetailsHtml({{
  key: 'official', provider: 'Amet', label: 'Kiht', state: 'matches',
  attempted_at: '2026-07-15T12:30:00Z', checked_at: '2026-07-15T12:29:00Z',
}});
console.log(JSON.stringify({{unavailable, successful}}));
"""
        result = subprocess.run(["node", "-e", script], check=True, capture_output=True, text=True)
        state = json.loads(result.stdout)

        self.assertIn('class="map-source-attempted">Kontrollikatse ', state["unavailable"])
        self.assertIn(
            'class="map-source-checked">Viimase eduka kontrolli aeg teadmata',
            state["unavailable"],
        )
        self.assertNotIn("Viimati edukalt kontrollitud", state["unavailable"])
        self.assertIn('class="map-source-attempted">Kontrollikatse ', state["successful"])
        self.assertIn('class="map-source-checked">Viimati edukalt kontrollitud ', state["successful"])


if __name__ == "__main__":
    unittest.main()
