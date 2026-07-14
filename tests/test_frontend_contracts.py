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
        self.assertIn('/static/css/style.css?r=jkl107', INDEX_HTML)
        self.assertIn('/static/css/font-sizes.css?r=jkl034', INDEX_HTML)
        self.assertNotIn('/static/css/style.css?r=jkl106', INDEX_HTML)
        self.assertNotIn('/static/css/font-sizes.css?r=jkl033', INDEX_HTML)
        self.assertNotIn('/static/css/style.css?r=jkl105', INDEX_HTML)
        self.assertNotIn('/static/css/style.css?r=jkl104', INDEX_HTML)
        self.assertNotIn('/static/css/style.css?r=jkl103', INDEX_HTML)
        self.assertNotIn('/static/css/style.css?r=jkl102', INDEX_HTML)

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

    def test_dashboard_removes_contextless_stand_numbers_but_keeps_details(self):
        self.assertNotIn("'<div>#</div>", INDEX_HTML)
        self.assertNotIn('class="er-nr"', INDEX_HTML)
        self.assertNotIn('eraldis-label', INDEX_HTML)
        self.assertIn('Eraldiste andmed', INDEX_HTML)
        self.assertIn('grid-template-columns: minmax(0, 1fr) 32px 48px 42px 46px 72px;', STYLE_CSS)

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
        self.assertIn("teatisedStatusBadge(t.staatus, t.active, t.arhiiv)", INDEX_HTML)
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
        self.assertIn("Kinnistu ja puidu hinnang", INDEX_HTML)
        self.assertIn("Hinnangu usaldus", INDEX_HTML)
        self.assertIn("Kuidas hinnang kujuneb", INDEX_HTML)
        self.assertIn("terviseindeks_selgitus", INDEX_HTML)
        self.assertIn("Terrapointi kaugandmete terviseskoor", INDEX_HTML)
        self.assertIn("data.terviseskoor != null", INDEX_HTML)
        self.assertIn("data.yrask_hinnang || data.yrask", INDEX_HTML)
        self.assertIn("Maa maksustamishind puudub; kinnistu koguhinnangut ei kuvata", INDEX_HTML)
        self.assertIn("e.vaartus_hinnang_eur != null ? e.vaartus_hinnang_eur : e.vaartus_eur", INDEX_HTML)
        self.assertIn("p.vaartus_hinnang_eur != null ? p.vaartus_hinnang_eur : p.vaartus_eur", INDEX_HTML)
        self.assertIn("and not sampled_eraldised", API_PY)
        self.assertIn("t >= 90 ? 'var(--data-state-ok)'", INDEX_HTML)
        self.assertNotIn('class="evidence-details" open', INDEX_HTML)
        self.assertIn("min-height: 44px;\n    display: flex;", STYLE_CSS)
        self.assertIn("sourceLinksHtml", INDEX_HTML)
        self.assertIn("https://erametsaliit.ee/wp-content/uploads/2026/05/puiduhinnad-2026-i-kv.pdf", API_PY)
        self.assertIn("https://maaruum.ee/maakataster-ja-maa-hindamine/kinnisvaratehingud/kinnisvaratehingute-statistika", API_PY)
        self.assertIn("https://keskkonnaagentuur.ee/node/2695", API_PY)

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
        self.assertIn("toetus-eligibility-badge", STYLE_CSS)
        self.assertIn("toetus-verification-list", STYLE_CSS)
        self.assertIn("t.disclaimer", rendered)
        self.assertIn("toetus-more-matches", rendered)
        self.assertIn("t.eligibility_status || (t.sobib", rendered)
        self.assertIn("t.application_status || legacyApplicationStatus", rendered)

    def test_subsidy_counts_have_explicit_contrast_and_mobile_avoids_nested_scroll(self):
        self.assertIn(".toetus-group-heading > span { background: var(--success); color: #fff; }", STYLE_CSS)
        self.assertIn(".toetus-group-check > span { background: var(--warn); color: #fff; }", STYLE_CSS)
        self.assertIn(".toetus-details-count { background: var(--ink-5); color: #fff; }", STYLE_CSS)
        self.assertIn(".toetus-list-scroll { max-height: none; overflow-y: visible; }", STYLE_CSS)

    def test_subsidy_inputs_preserve_source_completeness(self):
        self.assertIn('"forest_data_complete": "metsaregister.eraldised" not in unavailable_sources', API_PY)
        self.assertIn('"stand_data_complete": stand_data_complete', API_PY)
        self.assertIn('"protection_data_complete": protection_data_complete', API_PY)
        self.assertIn('"vep_data_complete": False', API_PY)
        self.assertIn('spatial_status = _build_spatial_status(', API_PY)
        self.assertIn('spatial_status["kaitseala"]["intersects"] is True', API_PY)

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
        helper = re.search(r'function resetParcelResult\(requestId\).*?\n    }', INDEX_HTML, re.DOTALL)
        self.assertIsNotNone(clear_helper)
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
function updateMapLegend() {{}}
function updateKihtLegend() {{}}
function aiShowUnavailableData() {{ aiUnavailable = true; }}
function aiRenderEraldisHints(value) {{ hints = value; }}
function cancelMapSelection() {{}}
function closeEraldisSheet() {{ sheet.remove(); }}
var _aiUserScrolledUp = true;
{clear_helper.group(0)}
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
            INDEX_HTML.index("function collapseMapLegendOnMobile()"),
            INDEX_HTML.index("document.addEventListener('DOMContentLoaded'"),
        )
        self.assertIn("collapseMapLegendOnMobile();", INDEX_HTML)

    def test_primary_timber_value_uses_grouped_number_format(self):
        self.assertIn("formatEur(data.base_value_eur != null ? data.base_value_eur : data.total_value_eur)", INDEX_HTML)
        self.assertNotIn("animateNumber(animEl, data.total_value_eur, '', 0);", INDEX_HTML)


if __name__ == "__main__":
    unittest.main()
