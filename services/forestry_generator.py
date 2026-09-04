"""Provider-neutral answer-generation contract for the forestry explainer."""

from __future__ import annotations

from typing import Protocol


class ForestryAnswerGenerator(Protocol):
    """A replaceable generator receives evidence, never arbitrary tools or URLs."""

    provider_id: str

    def generate(
        self,
        *,
        question: str,
        document: dict,
        allowed_source_ids: list[str],
    ) -> dict:
        ...


def validate_generated_answer(payload: object, allowed_source_ids: list[str]) -> dict:
    """Fail closed when a provider returns citations or shapes outside evidence."""
    if not isinstance(payload, dict):
        raise TypeError("Generator output must be an object")
    claim_type = payload.get("claim_type")
    sections = payload.get("sections")
    limitations = payload.get("limitations")
    if not isinstance(claim_type, str) or not claim_type:
        raise ValueError("Generator output has no claim type")
    if not isinstance(sections, list) or not sections:
        raise ValueError("Generator output has no sections")
    if not isinstance(limitations, list) or not limitations:
        raise ValueError("Generator output has no limitations")

    allowed = set(allowed_source_ids)
    normalized_sections = []
    for section in sections:
        if not isinstance(section, dict):
            raise TypeError("Generator section must be an object")
        title = section.get("title")
        text = section.get("text")
        citations = section.get("citations")
        if not isinstance(title, str) or not title or not isinstance(text, str) or not text:
            raise ValueError("Generator section has no title or text")
        if len(text) > 4_000 or not isinstance(citations, list):
            raise ValueError("Generator section exceeds output contract")
        if any(not isinstance(source_id, str) or source_id not in allowed for source_id in citations):
            raise ValueError("Generator cited evidence outside retrieval context")
        normalized_sections.append({
            "kind": str(section.get("kind") or "answer"),
            "title": title,
            "text": text,
            "citations": list(dict.fromkeys(citations)),
        })

    normalized_limitations = []
    for limitation in limitations:
        if not isinstance(limitation, str) or not limitation or len(limitation) > 1_000:
            raise ValueError("Generator limitation exceeds output contract")
        normalized_limitations.append(limitation)
    return {
        "claim_type": claim_type,
        "sections": normalized_sections,
        "limitations": normalized_limitations,
    }


class ExtractiveForestryGenerator:
    """Auditable fallback that copies only editor-approved knowledge fields."""

    provider_id = "extractive-v1"

    def generate(
        self,
        *,
        question: str,
        document: dict,
        allowed_source_ids: list[str],
    ) -> dict:
        del question  # The fallback never paraphrases from model knowledge.
        answer = document["answer"]
        payload = {
            "claim_type": answer["claim_type"],
            "sections": [
                {
                    "kind": "answer",
                    "title": "Lühivastus",
                    "text": answer["summary"],
                    "citations": allowed_source_ids,
                },
                {
                    "kind": "methodology",
                    "title": "Kuidas seda tõlgendada?",
                    "text": answer["methodology"],
                    "citations": allowed_source_ids,
                },
            ],
            "limitations": list(answer["limitations"]),
        }
        return validate_generated_answer(payload, allowed_source_ids)


def build_forestry_generator(provider: str = "extractive") -> ForestryAnswerGenerator:
    """Resolve a configured provider without silently substituting a model."""
    normalized = provider.strip().lower()
    if normalized in {"", "extractive"}:
        return ExtractiveForestryGenerator()
    raise ValueError(f"Unsupported forestry generator provider: {provider!r}")
