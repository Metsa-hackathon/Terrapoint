"""Run deterministic accessibility contract and colour-contrast checks."""

from __future__ import annotations

import argparse
import json
from html.parser import HTMLParser
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
HTML_PATH = PROJECT_ROOT / "static" / "embed" / "index.html"
CSS_PATH = PROJECT_ROOT / "static" / "embed" / "widget.css"
JAVASCRIPT_PATH = PROJECT_ROOT / "static" / "embed" / "widget.js"
RESULT_JSON = PROJECT_ROOT / "evaluation" / "accessibility_results.json"
RESULT_MARKDOWN = PROJECT_ROOT / "evaluation" / "accessibility_results.md"


class WidgetHTMLParser(HTMLParser):
    """Collect the small set of DOM facts used by the static audit."""

    def __init__(self) -> None:
        super().__init__()
        self.elements: list[tuple[str, dict[str, str]]] = []
        self.ids: list[str] = []
        self.heading_levels: list[int] = []
        self.html_language = ""

    def handle_starttag(self, tag: str, attributes: list[tuple[str, str | None]]) -> None:
        attrs = {name: value or "" for name, value in attributes}
        self.elements.append((tag, attrs))
        if attrs.get("id"):
            self.ids.append(attrs["id"])
        if tag == "html":
            self.html_language = attrs.get("lang", "")
        if len(tag) == 2 and tag[0] == "h" and tag[1].isdigit():
            self.heading_levels.append(int(tag[1]))


def _relative_luminance(colour: str) -> float:
    channels = [int(colour[index:index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [
        channel / 12.92
        if channel <= 0.04045
        else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast_ratio(foreground: str, background: str) -> float:
    lighter, darker = sorted(
        (_relative_luminance(foreground), _relative_luminance(background)),
        reverse=True,
    )
    return (lighter + 0.05) / (darker + 0.05)


def _css_has_colour(css: str, colour: str) -> bool:
    if colour in css:
        return True
    if len(colour) == 7 and all(colour[index] == colour[index + 1] for index in (1, 3, 5)):
        shorthand = f"#{colour[1]}{colour[3]}{colour[5]}"
        return shorthand in css
    return False


def _has_element(
    elements: list[tuple[str, dict[str, str]]],
    tag: str,
    **required: str,
) -> bool:
    return any(
        element_tag == tag
        and all(attributes.get(name) == value for name, value in required.items())
        for element_tag, attributes in elements
    )


def _check(name: str, passed: bool, evidence: str) -> dict:
    return {"name": name, "passed": bool(passed), "evidence": evidence}


def audit() -> dict:
    html = HTML_PATH.read_text(encoding="utf-8")
    css = CSS_PATH.read_text(encoding="utf-8")
    javascript = JAVASCRIPT_PATH.read_text(encoding="utf-8")
    parser = WidgetHTMLParser()
    parser.feed(html)
    ids = set(parser.ids)
    aria_targets = [
        target
        for _tag, attrs in parser.elements
        for target in attrs.get("aria-labelledby", "").split()
    ]
    positive_tabindexes = [
        attrs["tabindex"]
        for _tag, attrs in parser.elements
        if attrs.get("tabindex", "").lstrip("-").isdigit()
        and int(attrs["tabindex"]) > 0
    ]
    heading_order_valid = bool(parser.heading_levels) and parser.heading_levels[0] == 1 and all(
        current <= previous + 1
        for previous, current in zip(parser.heading_levels, parser.heading_levels[1:])
    )

    structural_checks = [
        _check("document_language", parser.html_language == "et", '<html lang="et">'),
        _check(
            "single_labelled_main",
            sum(tag == "main" for tag, _attrs in parser.elements) == 1
            and _has_element(parser.elements, "main", **{"aria-labelledby": "widget-title"})
            and "widget-title" in ids,
            "Üks main-landmark on seotud nähtava H1-ga.",
        ),
        _check(
            "question_name_and_description",
            _has_element(parser.elements, "label", **{"for": "question"})
            and _has_element(
                parser.elements,
                "textarea",
                id="question",
                **{"aria-describedby": "question-help"},
            )
            and "question-help" in ids,
            "Textarea nimi tuleb label'ist ja juhis aria-describedby kaudu.",
        ),
        _check(
            "live_status_and_alert",
            _has_element(parser.elements, "p", id="request-status", role="status")
            and _has_element(parser.elements, "div", id="error-message", role="alert"),
            "Asünkroonne olek ja vead on eraldi live-region'ites.",
        ),
        _check(
            "result_focus_target",
            _has_element(parser.elements, "h2", id="result-title", tabindex="-1")
            and 'resultTitle.focus({ preventScroll: true })' in javascript,
            "Tulemuse kuvamisel liigub fookus programmiliselt vastuse H2-le.",
        ),
        _check(
            "form_busy_and_invalid_state",
            'form.setAttribute("aria-busy", "true")' in javascript
            and 'question.setAttribute("aria-invalid", "true")' in javascript,
            "Laadimine ja lokaalne valideerimisviga jõuavad accessibility API-sse.",
        ),
        _check(
            "label_references_resolve",
            bool(aria_targets) and all(target in ids for target in aria_targets),
            "Kõik aria-labelledby IDREF-id lahenevad samas dokumendis.",
        ),
        _check(
            "unique_ids",
            len(parser.ids) == len(ids),
            "Dokumendis ei ole korduvaid id atribuute.",
        ),
        _check(
            "logical_heading_order",
            heading_order_valid,
            f"Pealkirjatasemed DOM-is: {parser.heading_levels}.",
        ),
        _check(
            "no_positive_tabindex",
            not positive_tabindexes,
            "Tabijärjekord järgib DOM-i; positiivseid tabindex väärtusi pole.",
        ),
        _check(
            "visible_focus_contract",
            ":focus-visible" in css
            and "outline: 3px solid #7a4a00" in css
            and "outline-offset: 3px" in css,
            "3 px kõrge kontrastiga väline fookusrõngas kõigil interaktiivsetel elementidel.",
        ),
        _check(
            "reduced_motion_contract",
            "@media (prefers-reduced-motion: reduce)" in css,
            "Vähendatud liikumise kasutajaeelistus on CSS-is toetatud.",
        ),
        _check(
            "responsive_and_target_size_contract",
            "@media (max-width: 540px)" in css and "min-height: 2.75rem" in css,
            "Mobiilipaigutus ja 44 px põhitoimingu kõrgus on määratud.",
        ),
    ]

    colour_pairs = [
        ("body text", "#17332d", "#f2f6f1", 4.5),
        ("primary heading", "#123f34", "#ffffff", 4.5),
        ("lead text", "#46615b", "#ffffff", 4.5),
        ("review status text", "#6b4e13", "#f2f6f1", 4.5),
        ("secondary text", "#61736e", "#ffffff", 4.5),
        ("placeholder text", "#61736e", "#fbfdfb", 4.5),
        ("primary button text", "#ffffff", "#176a56", 4.5),
        ("question chip text", "#245348", "#f6faf7", 4.5),
        ("request status", "#526b64", "#f2f6f1", 4.5),
        ("error text", "#78281f", "#fff1ef", 4.5),
        ("confidence text", "#34554d", "#e9f1ed", 4.5),
        ("clarification text", "#573f10", "#fff6dd", 4.5),
        ("source link", "#0e604c", "#ffffff", 4.5),
        ("footer text", "#60736d", "#f2f6f1", 4.5),
        ("textarea boundary", "#748f84", "#fbfdfb", 3.0),
        ("chip boundary", "#7b9489", "#f6faf7", 3.0),
        ("focus ring on card", "#7a4a00", "#ffffff", 3.0),
        ("focus ring on page", "#7a4a00", "#f2f6f1", 3.0),
    ]
    contrast_checks = []
    for name, foreground, background, minimum in colour_pairs:
        ratio = _contrast_ratio(foreground, background)
        colours_present = _css_has_colour(css, foreground) and _css_has_colour(css, background)
        contrast_checks.append({
            "name": name,
            "foreground": foreground,
            "background": background,
            "ratio": round(ratio, 2),
            "minimum": minimum,
            "passed": colours_present and ratio >= minimum,
        })

    passed = all(item["passed"] for item in structural_checks + contrast_checks)
    return {
        "schema_version": 1,
        "audited_at": "2026-08-16",
        "target": "static/embed/index.html",
        "standard": "WCAG 2.2 AA local prototype contract",
        "gate_passed": passed,
        "structural_checks": structural_checks,
        "contrast_checks": contrast_checks,
        "limitations": [
            "Static checks do not emulate a named screen reader or browser/OS combination.",
            "Keyboard and accessibility-tree smoke evidence is recorded separately in docs/kaur/accessibility-qa.md.",
            "Independent WCAG conformance review remains a pre-publication KAUR gate.",
        ],
    }


def markdown(result: dict) -> str:
    lines = [
        "# Metsanduswidget'i ligipääsetavuse lokaalne audit",
        "",
        f"- Kuupäev: {result['audited_at']}",
        f"- Siht: `{result['target']}`",
        f"- Tulemus: **{'LÄBITUD' if result['gate_passed'] else 'LÄBIMATA'}**",
        f"- Tase: {result['standard']}",
        "",
        "## Struktuur ja käitumisleping",
        "",
        "| Kontroll | Tulemus | Tõend |",
        "|---|---|---|",
    ]
    for item in result["structural_checks"]:
        lines.append(
            f"| `{item['name']}` | {'✓' if item['passed'] else '✗'} | {item['evidence']} |"
        )
    lines.extend([
        "",
        "## Kontrast",
        "",
        "| Paar | Suhe | Miinimum | Tulemus |",
        "|---|---:|---:|---|",
    ])
    for item in result["contrast_checks"]:
        lines.append(
            f"| {item['name']} (`{item['foreground']}` / `{item['background']}`) | "
            f"{item['ratio']:.2f}:1 | {item['minimum']:.1f}:1 | "
            f"{'✓' if item['passed'] else '✗'} |"
        )
    lines.extend(["", "## Piirangud", ""])
    lines.extend(f"- {item}" for item in result["limitations"])
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    result = audit()
    report = markdown(result)
    if args.write:
        RESULT_JSON.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        RESULT_MARKDOWN.write_text(report, encoding="utf-8")
    print(report)
    return 0 if result["gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
