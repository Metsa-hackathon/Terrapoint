# ruff: noqa: I001
"""Compare the timestamped public-portal discoverability snapshot with the prototype."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from services.forestry_search import get_forestry_search_engine


SNAPSHOT_PATH = PROJECT_ROOT / "evaluation" / "live_portal_snapshot_2026-08-16.json"
RESULT_JSON = PROJECT_ROOT / "evaluation" / "live_portal_comparison.json"
RESULT_MARKDOWN = PROJECT_ROOT / "evaluation" / "live_portal_comparison.md"


def compare() -> dict:
    snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    engine = get_forestry_search_engine()
    rows = []
    for item in snapshot["queries"]:
        prototype_top3 = [
            result["document"]["id"]
            for result in engine.retrieve(item["query"], limit=3)
        ]
        answer = engine.answer(item["query"])
        rows.append({
            **item,
            "prototype_top3": prototype_top3,
            "prototype_relevant_in_top3": item["relevant_document_id"] in prototype_top3,
            "prototype_status": answer["status"],
            "prototype_source_count": len(answer["sources"]),
        })
    count = len(rows)
    return {
        "schema_version": 1,
        "snapshot_sha256": hashlib.sha256(SNAPSHOT_PATH.read_bytes()).hexdigest(),
        "captured_at": snapshot["captured_at"],
        "method_limit": snapshot["method"],
        "query_count": count,
        "portal_default_zero_results": sum(row["default_result_count"] == 0 for row in rows),
        "portal_all_time_zero_results": sum(row["all_time_result_count"] == 0 for row in rows),
        "prototype_relevant_top3": sum(row["prototype_relevant_in_top3"] for row in rows),
        "prototype_with_source_or_safe_clarification": sum(
            bool(row["prototype_source_count"]) or row["prototype_status"] in {"needs_clarification", "redirect"}
            for row in rows
        ),
        "rows": rows,
    }


def markdown(result: dict) -> str:
    lines = [
        "# Avaliku Keskkonnaportaali hetktõmmise võrdlus",
        "",
        f"Hetktõmmis: {result['captured_at']}; SHA-256 `{result['snapshot_sha256']}`.",
        "",
        (
            "Oluline piirang: portaali tulemusarv mõõdab ainult leitavust. Nullist suurem "
            "arv ei tõenda, et tulemus vastab küsimusele; prototüübi top-3 mõõdab "
            "märgendatud tõendi leidmist, mitte lõppvastuse sisulist heakskiitu."
        ),
        "",
        f"- Portaali vaikimisi filtris null tulemust: **{result['portal_default_zero_results']}/{result['query_count']}**.",
        f"- Portaali kõigi aegade vaates null tulemust: **{result['portal_all_time_zero_results']}/{result['query_count']}**.",
        f"- Prototüübil märgendatud tõend top-3-s: **{result['prototype_relevant_top3']}/{result['query_count']}**.",
        f"- Prototüübil allikas või ohutu täpsustus/suunamine: **{result['prototype_with_source_or_safe_clarification']}/{result['query_count']}**.",
        "",
        "| ID | Vaikimisi | Kõik ajad | Prototüübi staatus | Õige tõend top-3-s |",
        "|---|---:|---:|---|---|",
    ]
    for row in result["rows"]:
        lines.append(
            f"| {row['id']} | {row['default_result_count']} | {row['all_time_result_count']} | "
            f"{row['prototype_status']} | {'jah' if row['prototype_relevant_in_top3'] else 'ei'} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    result = compare()
    report = markdown(result)
    if args.write:
        RESULT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        RESULT_MARKDOWN.write_text(report, encoding="utf-8")
    print(report)
    return 0 if result["prototype_relevant_top3"] == result["query_count"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
