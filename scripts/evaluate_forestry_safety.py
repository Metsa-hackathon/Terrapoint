# ruff: noqa: I001
"""Run the frozen out-of-domain and adversarial behavior checks."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from services.forestry_search import get_forestry_search_engine


DATASET_PATH = PROJECT_ROOT / "evaluation" / "forestry_safety_queries_v3.json"
COVERAGE_PATH = PROJECT_ROOT / "evaluation" / "forestry_safety_coverage.json"
RESULT_JSON = PROJECT_ROOT / "evaluation" / "safety_results.json"
RESULT_MARKDOWN = PROJECT_ROOT / "evaluation" / "safety_results.md"


def _evaluate_coverage(dataset: dict) -> dict:
    coverage = json.loads(COVERAGE_PATH.read_text(encoding="utf-8"))
    dataset_rows = {item["id"]: item for item in dataset["queries"]}
    coverage_ids = [item.get("id") for item in coverage.get("cases", [])]
    coverage_rows = {item["id"]: item for item in coverage.get("cases", []) if item.get("id")}
    required_areas = set(coverage.get("required_control_areas", []))
    represented_areas = {
        item.get("control_area") for item in coverage.get("cases", [])
    }
    errors = []
    if coverage.get("dataset_id") != dataset.get("dataset_id"):
        errors.append("coverage dataset_id does not match the safety dataset")
    if len(coverage_ids) != len(set(coverage_ids)):
        errors.append("coverage matrix has duplicate case IDs")
    missing_cases = sorted(set(dataset_rows) - set(coverage_rows))
    extra_cases = sorted(set(coverage_rows) - set(dataset_rows))
    if missing_cases:
        errors.append(f"coverage matrix is missing cases: {', '.join(missing_cases)}")
    if extra_cases:
        errors.append(f"coverage matrix has unknown cases: {', '.join(extra_cases)}")
    tag_mismatches = sorted(
        case_id
        for case_id in set(dataset_rows) & set(coverage_rows)
        if dataset_rows[case_id]["tag"] != coverage_rows[case_id].get("tag")
    )
    if tag_mismatches:
        errors.append(f"coverage tags differ for: {', '.join(tag_mismatches)}")
    missing_areas = sorted(required_areas - represented_areas)
    if missing_areas:
        errors.append(f"required control areas are missing: {', '.join(missing_areas)}")
    category_counts = {
        area: sum(item.get("control_area") == area for item in coverage["cases"])
        for area in sorted(represented_areas)
    }
    return {
        "file": COVERAGE_PATH.name,
        "sha256": hashlib.sha256(COVERAGE_PATH.read_bytes()).hexdigest(),
        "case_count": len(coverage_ids),
        "required_control_area_count": len(required_areas),
        "category_counts": category_counts,
        "selection_rationale": coverage.get("selection_rationale", []),
        "gate_passed": not errors,
        "errors": errors,
    }


def evaluate() -> dict:
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    coverage = _evaluate_coverage(dataset)
    engine = get_forestry_search_engine()
    details = []
    for item in dataset["queries"]:
        response = engine.answer(item["query"])
        combined_text = " ".join(
            section["text"] for section in response["answer"]["sections"]
        )
        passed = response["status"] == item["expected_status"]
        if item["expect_no_sources"]:
            passed = passed and not response["sources"] and not any(
                section["citations"] for section in response["answer"]["sections"]
            )
        if item["tag"] == "xss":
            passed = passed and "<script" not in combined_text and "onerror" not in combined_text
        details.append({
            "id": item["id"],
            "tag": item["tag"],
            "expected_status": item["expected_status"],
            "actual_status": response["status"],
            "source_count": len(response["sources"]),
            "passed": passed,
        })
    passed_count = sum(item["passed"] for item in details)
    return {
        "schema_version": 1,
        "dataset_id": dataset["dataset_id"],
        "dataset_sha256": hashlib.sha256(DATASET_PATH.read_bytes()).hexdigest(),
        "status": dataset["status"],
        "checked": len(details),
        "passed": passed_count,
        "pass_rate": round(passed_count / len(details), 4),
        "gate_passed": passed_count == len(details) and coverage["gate_passed"],
        "failures": [item for item in details if not item["passed"]],
        "coverage": coverage,
        "details": details,
    }


def markdown(result: dict) -> str:
    lines = [
        "# Metsandustõlgendaja ohutuskäitumise tulemus",
        "",
        f"- Andmestik: `{result['dataset_id']}`",
        f"- SHA-256: `{result['dataset_sha256']}`",
        (
            f"- Tulemus: **{result['passed']}/{result['checked']}** "
            f"({'LÄBITUD' if result['gate_passed'] else 'LÄBIMATA'})"
        ),
        f"- Staatus: {result['status']}",
        (
            f"- Katvusmaatriks: `{result['coverage']['file']}` "
            f"(SHA-256 `{result['coverage']['sha256']}`)"
        ),
        (
            f"- Katvus: {result['coverage']['case_count']} juhtumit / "
            f"{result['coverage']['required_control_area_count']} nõutud kontrollala"
        ),
        "",
        "| ID | Klass | Oodatud | Tegelik | Allikaid | Tulemus |",
        "|---|---|---|---|---:|---|",
    ]
    for item in result["details"]:
        lines.append(
            f"| {item['id']} | {item['tag']} | {item['expected_status']} | "
            f"{item['actual_status']} | {item['source_count']} | {'✓' if item['passed'] else '✗'} |"
        )
    lines.extend([
        "",
        "## Katvuse põhjendus",
        "",
    ])
    lines.extend(f"- {item}" for item in result["coverage"]["selection_rationale"])
    lines.extend([
        "",
        "| Kontrollala | Juhtumeid |",
        "|---|---:|",
    ])
    for category, count in result["coverage"]["category_counts"].items():
        lines.append(f"| `{category}` | {count} |")
    if result["coverage"]["errors"]:
        lines.extend(["", "Katvusvead:", ""])
        lines.extend(f"- {item}" for item in result["coverage"]["errors"])
    lines.extend([
        "",
        "Kogum ei asenda sõltumatut pentesti, DPIA-d ega KAURi turbeheakskiitu.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    result = evaluate()
    report = markdown(result)
    if args.write:
        RESULT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        RESULT_MARKDOWN.write_text(report, encoding="utf-8")
    print(report)
    return 0 if result["gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
