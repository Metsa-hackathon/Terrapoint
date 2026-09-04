# ruff: noqa: I001
"""Validate the forestry corpus and print a reproducible content manifest."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from services.forestry_search import DOCUMENTS_PATH, SOURCES_PATH, ForestryKnowledgeBase


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    knowledge = ForestryKnowledgeBase()
    manifest = {
        "schema_version": 1,
        "sources": len(knowledge.sources),
        "documents": len(knowledge.documents),
        "faq_topics": len(knowledge.required_coverage["faq"]),
        "misconceptions": len(knowledge.required_coverage["misconception"]),
        "files": {
            str(SOURCES_PATH.relative_to(PROJECT_ROOT)): _sha256(SOURCES_PATH),
            str(DOCUMENTS_PATH.relative_to(PROJECT_ROOT)): _sha256(DOCUMENTS_PATH),
        },
        "status": "valid",
    }
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
