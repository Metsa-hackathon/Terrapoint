# ruff: noqa: I001
"""Evaluate the deterministic forestry retriever against the frozen Estonian set."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from urllib.parse import urlsplit


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from services.forestry_search import get_forestry_search_engine


DATASET_PATH = PROJECT_ROOT / "evaluation" / "forestry_queries_v2.json"
RESULTS_JSON_PATH = PROJECT_ROOT / "evaluation" / "results.json"
RESULTS_MARKDOWN_PATH = PROJECT_ROOT / "evaluation" / "results.md"


def _read_dataset(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if payload.get("schema_version") != 1 or not isinstance(payload.get("queries"), list):
        raise ValueError("Unsupported evaluation dataset")
    return payload


def _load_dataset(path: Path) -> dict:
    payload = _read_dataset(path)
    development_from = payload.get("development_from")
    if development_from:
        source_path = (path.parent / development_from).resolve()
        if source_path.parent != path.parent.resolve():
            raise ValueError("development_from must stay inside evaluation/")
        source = _read_dataset(source_path)
        previous_answerable = [
            {
                **item,
                "id": f"prior-{item['id']}",
                "split": "development",
            }
            for item in source["queries"]
            if item["kind"] == "answerable"
        ]
        payload["queries"] = previous_answerable + payload["queries"]
    query_ids = [item.get("id") for item in payload["queries"]]
    if len(query_ids) != len(set(query_ids)) or any(not value for value in query_ids):
        raise ValueError("Evaluation query IDs must be present and unique")
    return payload


def _reciprocal_rank(ranking: list[str], relevant: set[str]) -> float:
    for index, document_id in enumerate(ranking, start=1):
        if document_id in relevant:
            return 1.0 / index
    return 0.0


def _ndcg_at_k(ranking: list[str], relevant: set[str], k: int = 3) -> float:
    dcg = sum(
        1.0 / math.log2(index + 2)
        for index, document_id in enumerate(ranking[:k])
        if document_id in relevant
    )
    ideal_hits = min(k, len(relevant))
    ideal = sum(1.0 / math.log2(index + 2) for index in range(ideal_hits))
    return dcg / ideal if ideal else 0.0


def _round(value: float) -> float:
    return round(value, 4)


def _retrieval_metrics(rows: list[dict], engine) -> dict:
    answerable = [row for row in rows if row["kind"] == "answerable"]
    details = []
    baseline_recall = hybrid_recall = 0
    baseline_ndcg = hybrid_ndcg = 0.0
    baseline_mrr = hybrid_mrr = 0.0
    critical_regressions = []

    for row in answerable:
        relevant = set(row["relevant_document_ids"])
        baseline = engine.baseline_search(row["query"], limit=8)
        hybrid = [
            item["document"]["id"]
            for item in engine.retrieve(row["query"], limit=8)
        ]
        baseline_hit = bool(relevant & set(baseline[:3]))
        hybrid_hit = bool(relevant & set(hybrid[:3]))
        baseline_recall += baseline_hit
        hybrid_recall += hybrid_hit
        baseline_ndcg += _ndcg_at_k(baseline, relevant)
        hybrid_ndcg += _ndcg_at_k(hybrid, relevant)
        baseline_mrr += _reciprocal_rank(baseline, relevant)
        hybrid_mrr += _reciprocal_rank(hybrid, relevant)
        is_critical = any(tag in {"protection-critical", "legal-critical"} for tag in row["tags"])
        if is_critical and baseline_hit and not hybrid_hit:
            critical_regressions.append(row["id"])
        details.append({
            "id": row["id"],
            "query": row["query"],
            "relevant_document_ids": sorted(relevant),
            "baseline_top3": baseline[:3],
            "hybrid_top3": hybrid[:3],
            "baseline_hit": baseline_hit,
            "hybrid_hit": hybrid_hit,
        })

    count = len(answerable)
    if not count:
        raise ValueError("Evaluation split has no answerable queries")
    return {
        "query_count": count,
        "baseline": {
            "recall_at_3": _round(baseline_recall / count),
            "ndcg_at_3": _round(baseline_ndcg / count),
            "mrr": _round(baseline_mrr / count),
        },
        "hybrid": {
            "recall_at_3": _round(hybrid_recall / count),
            "ndcg_at_3": _round(hybrid_ndcg / count),
            "mrr": _round(hybrid_mrr / count),
        },
        "recall_at_3_absolute_gain": _round((hybrid_recall - baseline_recall) / count),
        "critical_regressions": critical_regressions,
        "failures": [item for item in details if not item["hybrid_hit"]],
        "details": details,
    }


def _behavior_metrics(rows: list[dict], engine) -> dict:
    checks = []
    citation_checks = []
    grounding_checks = []
    document_by_id = {document["id"]: document for document in engine.documents}
    for row in rows:
        if row["kind"] == "answerable":
            response = engine.answer(row["query"])
            returned_source_ids = {source["id"] for source in response["sources"]}
            cited_source_ids = {
                source_id
                for section in response["answer"]["sections"]
                for source_id in section["citations"]
            }
            urls_allowed = all(
                urlsplit(source["url"]).scheme == "https"
                and source["id"] in engine.sources
                and source["url"] == engine.sources[source["id"]]["url"]
                for source in response["sources"]
            )
            valid = bool(returned_source_ids) and cited_source_ids <= returned_source_ids and urls_allowed
            citation_checks.append({"id": row["id"], "passed": valid})

            selected_documents = response["retrieval"]["documents"]
            selected_id = selected_documents[0] if selected_documents else None
            field_faithful = False
            if selected_id is not None:
                selected_document = document_by_id[selected_id]
                selected_source_ids = [
                    reference["source_id"] for reference in selected_document["sources"]
                ]
                sections = response["answer"]["sections"]
                field_faithful = (
                    response["retrieval"].get("generator") == "extractive-v1"
                    and response["answer"]["claim_type"]
                    == selected_document["answer"]["claim_type"]
                    and len(sections) == 2
                    and sections[0]["text"] == selected_document["answer"]["summary"]
                    and sections[1]["text"] == selected_document["answer"]["methodology"]
                    and response["answer"]["limitations"]
                    == selected_document["answer"]["limitations"]
                    and returned_source_ids == set(selected_source_ids)
                    and all(
                        section["citations"] == selected_source_ids
                        for section in sections
                    )
                )
            grounding_checks.append({
                "id": row["id"],
                "selected_document_id": selected_id,
                "passed": field_faithful,
            })
        elif row["kind"] in {"redirect", "abstain"}:
            response = engine.answer(row["query"])
            expected_status = row["expected_status"]
            valid = response["status"] == expected_status
            if row["kind"] == "redirect":
                valid = valid and row["expected_document_id"] in response["retrieval"]["documents"]
            else:
                valid = valid and not response["sources"] and not any(
                    section["citations"] for section in response["answer"]["sections"]
                )
            checks.append({
                "id": row["id"],
                "kind": row["kind"],
                "expected_status": expected_status,
                "actual_status": response["status"],
                "passed": valid,
            })

    citation_passed = sum(item["passed"] for item in citation_checks)
    grounding_passed = sum(item["passed"] for item in grounding_checks)
    behavior_passed = sum(item["passed"] for item in checks)
    return {
        "citation_integrity": {
            "checked": len(citation_checks),
            "passed": citation_passed,
            "rate": _round(citation_passed / len(citation_checks)) if citation_checks else 1.0,
        },
        "extractive_answer_faithfulness": {
            "definition": (
                "Both displayed answer sections and limitations exactly match the selected "
                "editor-approved knowledge fields, and every citation matches that document."
            ),
            "checked": len(grounding_checks),
            "passed": grounding_passed,
            "rate": _round(grounding_passed / len(grounding_checks)) if grounding_checks else 1.0,
            "failures": [item for item in grounding_checks if not item["passed"]],
        },
        "redirect_and_abstention": {
            "checked": len(checks),
            "passed": behavior_passed,
            "rate": _round(behavior_passed / len(checks)) if checks else 1.0,
            "failures": [item for item in checks if not item["passed"]],
        },
    }


def _coverage(rows: list[dict]) -> dict:
    tags = {tag for row in rows for tag in row.get("tags", [])}
    expected_faq = {f"FAQ-{index:02d}" for index in range(1, 19)}
    expected_mis = {f"MIS-{index:02d}" for index in range(1, 13)}
    return {
        "faq": {"expected": 18, "covered": len(tags & expected_faq), "missing": sorted(expected_faq - tags)},
        "misconceptions": {"expected": 12, "covered": len(tags & expected_mis), "missing": sorted(expected_mis - tags)},
    }


def evaluate(dataset_path: Path = DATASET_PATH) -> dict:
    dataset = _load_dataset(dataset_path)
    engine = get_forestry_search_engine()
    splits = {}
    for split in ("development", "locked"):
        rows = [row for row in dataset["queries"] if row["split"] == split]
        splits[split] = {
            "retrieval": _retrieval_metrics(rows, engine),
            "behavior": _behavior_metrics(rows, engine),
            "coverage": _coverage(rows),
        }

    locked = splits["locked"]
    retrieval = locked["retrieval"]
    behavior = locked["behavior"]
    coverage = locked["coverage"]
    gate_checks = {
        "hybrid_recall_at_3_gte_0_90": retrieval["hybrid"]["recall_at_3"] >= 0.90,
        "recall_gain_gte_0_15": retrieval["recall_at_3_absolute_gain"] >= 0.15,
        "hybrid_ndcg_at_3_gte_0_80": retrieval["hybrid"]["ndcg_at_3"] >= 0.80,
        "no_critical_retrieval_regression": not retrieval["critical_regressions"],
        "citation_integrity_100_percent": behavior["citation_integrity"]["rate"] == 1.0,
        "extractive_answer_faithfulness_100_percent": (
            behavior["extractive_answer_faithfulness"]["rate"] == 1.0
        ),
        "redirect_and_abstention_100_percent": behavior["redirect_and_abstention"]["rate"] == 1.0,
        "all_required_topics_covered": not coverage["faq"]["missing"] and not coverage["misconceptions"]["missing"],
    }
    return {
        "schema_version": 1,
        "dataset_id": dataset["dataset_id"],
        "dataset_file": dataset_path.name,
        "dataset_sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
        "dataset_frozen_at": dataset["frozen_at"],
        "dataset_status": dataset["status"],
        "engine_strategy": engine.STRATEGY,
        "splits": splits,
        "gate": {"passed": all(gate_checks.values()), "checks": gate_checks},
    }


def _markdown(results: dict) -> str:
    lines = [
        "# Metsandusotsingu hindamistulemus",
        "",
        f"- Andmestik: `{results['dataset_id']}` (külmutatud {results['dataset_frozen_at']})",
        f"- SHA-256: `{results['dataset_sha256']}`",
        f"- Mootor: `{results['engine_strategy']}`",
        f"- Värav: **{'LÄBITUD' if results['gate']['passed'] else 'LÄBIMATA'}**",
        f"- Staatus: {results['dataset_status']}",
        "",
        "| Jaotus | Päringuid | Meetod | Recall@3 | nDCG@3 | MRR |",
        "|---|---:|---|---:|---:|---:|",
    ]
    for split_name, split in results["splits"].items():
        retrieval = split["retrieval"]
        for method in ("baseline", "hybrid"):
            metrics = retrieval[method]
            lines.append(
                f"| {split_name} | {retrieval['query_count']} | {method} | "
                f"{metrics['recall_at_3']:.4f} | {metrics['ndcg_at_3']:.4f} | {metrics['mrr']:.4f} |"
            )
    locked = results["splits"]["locked"]
    lines.extend([
        "",
        (
            f"Lukustatud jaotuse Recall@3 absoluutne paranemine: "
            f"`{locked['retrieval']['recall_at_3_absolute_gain']:+.4f}`."
        ),
        (
            "Lukustatud jaotuse extractive-vastuse allikaväljade täpne "
            f"faithfulness: `{locked['behavior']['extractive_answer_faithfulness']['rate']:.4f}`."
        ),
        "",
        "## Väravakontrollid",
        "",
    ])
    for name, passed in results["gate"]["checks"].items():
        lines.append(f"- {'✓' if passed else '✗'} `{name}`")
    failures = locked["retrieval"]["failures"]
    lines.extend(["", "## Lukustatud jaotuse retrieval'i möödalasud", ""])
    if failures:
        for item in failures:
            lines.append(
                f"- `{item['id']}` — {item['query']} (oodatud "
                f"`{', '.join(item['relevant_document_ids'])}`, top-3 "
                f"`{', '.join(item['hybrid_top3'])}`)"
            )
    else:
        lines.append("Puuduvad.")
    lines.extend([
        "",
        (
            "Kontrollkogum on prototüübi tõend, mitte KAURi sisuline heakskiit. "
            "Enne pilooti kinnitab KAUR kuldmärgendid ja lävendid ning avaldab uue "
            "versiooniga lukustatud kogumi."
        ),
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DATASET_PATH, help="evaluation dataset JSON")
    parser.add_argument("--write", action="store_true", help="write deterministic JSON and Markdown reports")
    parser.add_argument("--enforce", action="store_true", help="return non-zero when the locked gate fails")
    args = parser.parse_args()
    dataset_path = args.dataset if args.dataset.is_absolute() else (PROJECT_ROOT / args.dataset)
    results = evaluate(dataset_path.resolve())
    markdown = _markdown(results)
    if args.write:
        RESULTS_JSON_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        RESULTS_MARKDOWN_PATH.write_text(markdown, encoding="utf-8")
    print(markdown)
    return 1 if args.enforce and not results["gate"]["passed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
