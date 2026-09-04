"""Deterministic forestry retrieval and grounded answer assembly.

The production architecture is documented in ``docs/kaur/search-architecture.md``.
This module intentionally keeps the reference implementation dependency-free:
it proves the knowledge/source contracts, hybrid retrieval, RRF fusion, citations,
abstention, and provider-neutral response shape without requiring a model key.
"""

from __future__ import annotations

import json
import math
import os
import re
import unicodedata
from collections import Counter
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

from services.forestry_generator import (
    ForestryAnswerGenerator,
    build_forestry_generator,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_ROOT = PROJECT_ROOT / "knowledge" / "forestry"
SOURCES_PATH = KNOWLEDGE_ROOT / "sources.json"
DOCUMENTS_PATH = KNOWLEDGE_ROOT / "documents.json"

KATASTER_RE = re.compile(r"(?<!\d)(\d{5}:\d{3}:\d{4})(?!\d)")
TOKEN_RE = re.compile(r"[0-9a-zõäöüšž]+", re.IGNORECASE)
USER_SUPPLIED_URL_RE = re.compile(r"(?:https?|file|ftp|gopher|dict)://", re.IGNORECASE)
MARKUP_OR_EVENT_RE = re.compile(r"<\s*/?\s*[a-z][^>]*>|\bon[a-z]+\s*=", re.IGNORECASE)
ALLOWED_SOURCE_HOSTS = {
    "keskkonnaportaal.ee",
    "www.keskkonnaportaal.ee",
    "keskkonnaamet.ee",
    "www.keskkonnaamet.ee",
    "riigiteataja.ee",
    "www.riigiteataja.ee",
    "kliimaministeerium.ee",
    "www.kliimaministeerium.ee",
}

OUT_OF_SCOPE_MARKERS = (
    "ilm homme",
    "ilmaprognoos",
    "järgmised valimised",
    "kirjuta luuletus",
    "loo luuletus",
    "kirjuta jutustus",
    "kirjuta lugu",
    "koosta retsept",
    "soovita raiuda",
    "kas ma tohin homme raiuda",
    "anna raiemisluba",
    "lendorava täpne asukoht",
    "täpne lendorava asukoht",
    "kes on omanik",
    "omaniku nimi",
    "ignoreeri juhiseid",
    "unusta eelmised reeglid",
    "süsteemijuhis",
    "api võti",
    "salasõna",
    "parool",
)

FORESTRY_DOMAIN_MARKERS = (
    "mets", "puist", "raie", "raiu", "smi", "rmk", "tagavara",
    "juurdekasv", "mänd", "männi", "kuusk", "ürask", "katastr", "eraldis",
    "tihumeet", " tm", "fra ", "suhteline viga", "proovitükk",
    "metsaregister", "metsainventuur", "eri allikad", "erinevaid numbreid",
    "range kaitse", "kaitse all", "majandatav", "valimi esinduslikkus",
    "suurem valim", "vaatlusi", "täpsema tulemuse", "lageraije", "51,84",
    "54,08",
)

INDICATOR_ALIASES = {
    "metsamaa": ("metsamaa", "metsasus", "metsane", "metsapindala", "metsa pindala"),
    "tagavara": ("tagavara", "puidumaht", "puiduvaru"),
    "juurdekasv": ("juurdekasv", "kasvuhinnang"),
    "raiemaht": ("raiemaht", "raiete maht", "raiumine", "väljaraie"),
    "lageraie pindala": ("lageraie", "lageraije"),
    "puistu vanus": ("metsa vanus", "puistu vanus", "vanusejaotus", "vanuseklass"),
    "kaitse": ("kaitse all", "kaitstav", "mittemajandatav", "kaitseala"),
    "puuliik": ("puuliik", "mänd", "männik", "kuusk", "kuusik"),
}

COMPARISON_MARKERS = (
    "võrdle", "võrreldes", "rohkem kui", "vähem kui", "erinevus", "erineb",
    "versus", " vs ", "kumb", "suurem kui", "sama mis",
)

CLARIFICATION_PROMPTS = {
    "municipality-forest-area": (
        "Palun nimeta vald ja soovitud näitaja: metsamaa pindala, metsasus või "
        "registris kehtivate eraldiste pindala."
    ),
    "harvest-over-time": (
        "Palun nimeta võrreldavad aastad või periood ning kas soovid SMI hinnatud "
        "toimunud raiemahtu või Metsaregistri kavandatud teatisi."
    ),
    "clearcut-over-time": (
        "Täielikuks võrdluseks palun kinnita periood; vastus vajab iga aasta sama "
        "metoodikaga lageraie hinnanguid, mitte viimase aasta korrutamist."
    ),
}

# Function words and generic portal vocabulary carry little retrieval signal.
STOPWORDS = {
    "aga", "all", "alla", "alusel", "ei", "eesti", "eestis", "ehk", "et",
    "ja", "jah", "kas", "kogu", "kui", "kuidas", "kus", "ma", "meie",
    "miks", "mis", "mida", "millal", "milline", "minu", "ning", "nii", "on",
    "oma", "osa", "palju", "praegu", "saa", "saab", "see", "seda", "selle",
    "siis", "suur", "suurem", "või", "vähem", "üle", "üks", "ühte",
}

# Lightweight suffix reduction is only the deterministic prototype's lexical
# safety net. Production uses Lucene's EstonianAnalyzer and a measured dense arm.
ESTONIAN_SUFFIXES = (
    "mistest", "misega", "mistega", "miseks", "mistel", "mistes", "mine",
    "desse", "tesse", "dega", "tega", "dele", "tele", "dest", "test",
    "delt", "telt", "del", "tel", "des", "tes", "mine", "mise", "mised",
    "misi", "mata", "maks", "mast", "vaga", "kuga", "sse", "st", "lt",
    "le", "ga", "ta", "ks", "ni", "na", "da", "ma", "vad", "nud", "tud",
    "sid", "d", "t", "s",
)

# The corpus uses official forestry terminology, while visitors often use
# colloquial or inflected forms. These transparent, reviewable expansions are
# deliberately small; they complement (rather than impersonate) the measured
# dense retrieval arm proposed for production.
QUERY_EXPANSIONS = {
    "arv": ("number", "andmeallikas", "metoodika"),
    "arvud": ("number", "andmeallikas", "metoodika"),
    "numbrid": ("number", "andmeallikas", "metoodika"),
    "puidutagavara": ("tagavara", "puidukogus"),
    "puiduvaru": ("tagavara", "puidukogus", "raiutav"),
    "raiuda": ("raie", "raiutav"),
    "raiutakse": ("raie", "raiemaht"),
    "raiumist": ("raie", "raiemaht"),
    "raiedokument": ("metsateatis", "kavandatav raie"),
    "kasvust": ("juurdekasv",),
    "majandatav": ("mittemajandatav", "majanduspiirang"),
    "männikuid": ("mänd", "männi", "puuliik"),
    "mändi": ("mänd", "männi", "puuliik"),
    "männipuistuid": ("mänd", "männi", "puuliik"),
    "kuusikuid": ("kuusk", "kuuse", "puuliik"),
    "kuuske": ("kuusk", "kuuse", "puuliik"),
    "kuusepuistuid": ("kuusk", "kuuse", "puuliik"),
    "vallal": ("vald", "omavalitsus"),
    "vallas": ("vald", "omavalitsus"),
    "metsane": ("metsasus", "metsamaa"),
    "metsapinna": ("metsamaa", "metsasus"),
    "metsaarv": ("number", "andmeallikas", "metoodika"),
    "metsastatistika": ("metsaandmed", "andmeallikas", "metoodika"),
    "tabelit": ("andmeallikas", "metoodika"),
    "erineva": ("erinevad numbrid", "andmeallikas", "metoodika"),
    "lahknevad": ("erinevad numbrid", "andmeallikas", "metoodika"),
    "proovialade": ("proovitükk", "valikuuring", "SMI"),
    "proovipunktide": ("proovitükk", "valikuuring", "SMI"),
    "registri": ("metsaregister", "eraldis"),
    "eraldiste": ("metsaregister", "eraldis"),
    "eraldisregister": ("metsaregister", "eraldis"),
    "lausinventeeritud": ("lausinventeerimine", "lausmetsakorraldus"),
    "maatüki": ("kinnistu", "katastritunnus", "metsaregister"),
    "katastriüksuse": ("kinnistu", "katastritunnus", "metsaregister"),
    "takseerandmed": ("eraldis", "metsaregister"),
    "koosseisu": ("eraldis", "puuliik", "kinnistu"),
    "raiekavatsusel": ("metsateatis", "kavandatav raie", "lubav märge"),
    "trend": ("aegrida", "muutus"),
    "aastate": ("aegrida", "20 aastat"),
    "põuad": ("põud", "kliimamuutus"),
    "soojemad": ("kliimamuutus", "soojenemine"),
    "riigimetsa": ("RMK", "riigimets"),
    "vanusejaotus": ("vanuseklass", "keskmine vanus"),
    "männikute": ("mänd", "männi", "puuliik"),
    "kuusikute": ("kuusk", "kuuse", "puuliik"),
    "vaatlusi": ("valim", "proovitükk", "täpsus"),
    "kestliku": ("jätkusuutlik", "juurdekasv", "raiemaht"),
    "kaitsestaatuse": ("kaitseala", "õiguslik kaitse"),
    "raiereegel": ("raie", "kaitseala", "tingimus"),
    "kaitsealal": ("kaitseala", "kaitstud"),
    "kaitsealadel": ("kaitseala", "kaitstud"),
}


def normalize_text(value: object) -> str:
    """Return a stable, lower-case Unicode representation for retrieval."""
    text = unicodedata.normalize("NFKC", str(value or "")).lower()
    text = text.replace("–", "-").replace("—", "-")
    return " ".join(text.split())


def raw_tokens(value: object) -> list[str]:
    return [
        token
        for token in TOKEN_RE.findall(normalize_text(value))
        if len(token) > 1 and token not in STOPWORDS
    ]


def _stem(token: str) -> str:
    if token.isdigit() or len(token) <= 4:
        return token
    for suffix in ESTONIAN_SUFFIXES:
        if token.endswith(suffix) and len(token) - len(suffix) >= 4:
            return token[: -len(suffix)]
    return token


def analysis_tokens(value: object) -> list[str]:
    return [_stem(token) for token in raw_tokens(value)]


def query_analysis_tokens(value: object) -> list[str]:
    """Analyze a query and add a bounded, auditable domain-synonym layer."""
    tokens = raw_tokens(value)
    expanded = list(tokens)
    for token in tokens:
        expanded.extend(QUERY_EXPANSIONS.get(token, ()))
    return [_stem(token) for token in expanded]


def plan_forestry_question(value: object) -> dict:
    """Extract comparison dimensions without inventing a data value."""
    normalized = normalize_text(value)
    years = list(dict.fromkeys(re.findall(r"\b(?:19|20)\d{2}\b", normalized)))
    relative_periods = []
    for amount in re.findall(r"\b(\d{1,2})\s*(?:aastat|aasta|aastaga)\b", normalized):
        relative_periods.append(f"last_{amount}_years")
    indicators = [
        indicator
        for indicator, aliases in INDICATOR_ALIASES.items()
        if any(alias in normalized for alias in aliases)
    ]
    geography = []
    if KATASTER_RE.search(normalized):
        geography.append("cadastral_parcel")
    region_match = re.search(
        r"\b([a-zõäöüšž-]{2,})\s+"
        r"(vald|vallas|vallast|vallale|linn|linnas|linnast|maakond|maakonnas|maakonnast|"
        r"omavalitsus|omavalitsuses|omavalitsusest)\b",
        normalized,
    )
    if region_match and region_match.group(1) not in {"minu", "oma", "üks", "milline"}:
        geography.append(f"{region_match.group(1)} {region_match.group(2)}")
    elif "eesti" in normalized:
        geography.append("Eesti")

    comparison = any(marker in normalized for marker in COMPARISON_MARKERS)
    missing_dimensions = []
    asks_local = any(marker in normalized for marker in ("vallas", "vallal", "omavalitsus", "maakonnas"))
    asks_time_series = any(marker in normalized for marker in ("aegrida", "läbi aastate", "trend", "varem"))
    if asks_local and not geography:
        missing_dimensions.append("geography")
    if asks_time_series and not years and not relative_periods:
        missing_dimensions.append("period")
    if comparison and not indicators:
        missing_dimensions.append("indicator")
    return {
        "comparison": comparison,
        "indicators": indicators,
        "geography": geography,
        "periods": [*years, *relative_periods],
        "missing_dimensions": missing_dimensions,
    }


def is_out_of_scope_question(value: object) -> bool:
    """Reject non-forestry, secret, restricted-data and user-URL requests."""
    normalized = normalize_text(value)
    if USER_SUPPLIED_URL_RE.search(normalized) or MARKUP_OR_EVENT_RE.search(normalized):
        return True
    if any(marker in normalized for marker in OUT_OF_SCOPE_MARKERS):
        return True
    if "lendorav" in normalized and any(marker in normalized for marker in ("asukoht", "koordinaat", "gps", "pesapaik")):
        return True
    if "omanik" in normalized and any(marker in normalized for marker in ("telefon", "kontakt", "nimi")):
        return True
    if "kas peaksin" in normalized and "raiu" in normalized:
        return True
    if (
        any(marker in normalized for marker in ("mu mets", "minu mets", "oma mets"))
        and any(marker in normalized for marker in ("soovita", "mõistlik", "peaksin"))
        and "rai" in normalized
    ):
        return True
    return not any(marker in normalized for marker in FORESTRY_DOMAIN_MARKERS)


def _character_ngrams(value: object, n: int = 3) -> Counter[str]:
    normalized = " ".join(raw_tokens(value))
    if not normalized:
        return Counter()
    padded = f"  {normalized}  "
    return Counter(padded[index:index + n] for index in range(len(padded) - n + 1))


def _cosine(left: Counter[str], right: Counter[str]) -> float:
    if not left or not right:
        return 0.0
    common = set(left) & set(right)
    numerator = sum(left[key] * right[key] for key in common)
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    return numerator / (left_norm * right_norm) if left_norm and right_norm else 0.0


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise TypeError(f"{path.name} peab sisaldama JSON objekti")
    return payload


class ForestryKnowledgeBase:
    """Validated in-memory source registry and retrieval corpus."""

    def __init__(self, sources_path: Path = SOURCES_PATH, documents_path: Path = DOCUMENTS_PATH):
        source_payload = _load_json(sources_path)
        document_payload = _load_json(documents_path)
        if source_payload.get("schema_version") != 1 or document_payload.get("schema_version") != 1:
            raise ValueError("Tundmatu metsanduse teadmusbaasi skeem")

        sources = source_payload.get("sources")
        documents = document_payload.get("documents")
        if not isinstance(sources, list) or not sources:
            raise ValueError("Allikaregister on tühi")
        if not isinstance(documents, list) or not documents:
            raise ValueError("Metsanduse dokumendikorpus on tühi")

        self.sources = self._validate_sources(sources)
        self.documents = self._validate_documents(documents)
        self.required_coverage = document_payload.get("required_coverage") or {}
        self._validate_coverage()

    @staticmethod
    def _validate_sources(sources: list[dict]) -> dict[str, dict]:
        registry: dict[str, dict] = {}
        for source in sources:
            if not isinstance(source, dict):
                raise TypeError("Allikakirje peab olema objekt")
            source_id = str(source.get("id") or "").strip()
            url = str(source.get("url") or "").strip()
            parsed = urlsplit(url)
            try:
                port = parsed.port
            except ValueError as exc:
                raise ValueError(f"Lubamatu allika URL: {url!r}") from exc
            if not source_id or source_id in registry:
                raise ValueError(f"Puuduv või korduv source_id: {source_id!r}")
            if (
                parsed.scheme != "https"
                or parsed.hostname not in ALLOWED_SOURCE_HOSTS
                or parsed.username
                or parsed.password
                or port not in (None, 443)
            ):
                raise ValueError(f"Lubamatu allika URL: {url!r}")
            if not source.get("title") or not source.get("publisher"):
                raise ValueError(f"Allikal {source_id} puudub pealkiri või väljaandja")
            registry[source_id] = dict(source)
        return registry

    def _validate_documents(self, documents: list[dict]) -> list[dict]:
        validated = []
        seen: set[str] = set()
        for document in documents:
            if not isinstance(document, dict):
                raise TypeError("Teadmuskirje peab olema objekt")
            document_id = str(document.get("id") or "").strip()
            aliases = document.get("question_aliases")
            answer = document.get("answer")
            source_refs = document.get("sources")
            if not document_id or document_id in seen:
                raise ValueError(f"Puuduv või korduv document_id: {document_id!r}")
            if not document.get("title") or not isinstance(aliases, list) or not aliases:
                raise ValueError(f"Dokumendil {document_id} puudub pealkiri või aliasküsimus")
            if not isinstance(answer, dict) or not answer.get("summary") or not answer.get("methodology"):
                raise ValueError(f"Dokumendil {document_id} puudub vastus või metoodika")
            if not isinstance(answer.get("limitations"), list) or not answer["limitations"]:
                raise ValueError(f"Dokumendil {document_id} puudub piirang")
            if not isinstance(source_refs, list) or not source_refs:
                raise ValueError(f"Dokumendil {document_id} puudub allikaviide")
            for reference in source_refs:
                if not isinstance(reference, dict) or reference.get("source_id") not in self.sources:
                    raise ValueError(f"Dokumendil {document_id} on tundmatu allikas")
                if not reference.get("locator"):
                    raise ValueError(f"Dokumendil {document_id} puudub allika locator")
            seen.add(document_id)
            validated.append(dict(document))
        return validated

    def _validate_coverage(self) -> None:
        known = {document["id"] for document in self.documents}
        for group in ("faq", "misconception"):
            coverage = self.required_coverage.get(group)
            if not isinstance(coverage, dict) or not coverage:
                raise ValueError(f"Teadmusbaasil puudub {group} katvusmanifest")
            for coverage_id, document_ids in coverage.items():
                if not isinstance(document_ids, list) or not document_ids:
                    raise ValueError(f"Katvus {coverage_id} on tühi")
                missing = set(document_ids) - known
                if missing:
                    raise ValueError(f"Katvus {coverage_id} viitab puuduvale dokumendile: {sorted(missing)}")


class ForestrySearchEngine:
    """Small hybrid retriever with RRF fusion and grounded answer output."""

    STRATEGY = "prototype-bm25-estonian-char3-terminology-rrf-rerank-v2"

    def __init__(
        self,
        knowledge_base: ForestryKnowledgeBase | None = None,
        generator: ForestryAnswerGenerator | None = None,
    ):
        self.knowledge_base = knowledge_base or ForestryKnowledgeBase()
        self.generator = generator or build_forestry_generator("extractive")
        self.documents = self.knowledge_base.documents
        self.sources = self.knowledge_base.sources
        self._index = [self._index_document(document) for document in self.documents]
        self._average_lengths = {
            field: sum(sum(item[field].values()) for item in self._index) / len(self._index)
            for field in ("stemmed_tokens", "raw_tokens")
        }
        self._df_stemmed = self._document_frequency("stemmed_tokens")
        self._df_raw = self._document_frequency("raw_tokens")

    @staticmethod
    def _field_text(document: dict) -> str:
        answer = document["answer"]
        weighted = [document["title"]] * 4
        weighted.extend(document["question_aliases"] * 5)
        weighted.extend((document.get("keywords") or []) * 3)
        weighted.extend((document.get("topics") or []) * 2)
        weighted.extend([answer["summary"], answer["methodology"]])
        weighted.extend(answer.get("limitations") or [])
        return " ".join(weighted)

    def _index_document(self, document: dict) -> dict:
        text = self._field_text(document)
        aliases = [document["title"], *document["question_aliases"]]
        stemmed = analysis_tokens(text)
        raw = raw_tokens(text)
        return {
            "document": document,
            "stemmed_tokens": Counter(stemmed),
            "raw_tokens": Counter(raw),
            "length": max(1, len(stemmed)),
            "alias_tokens": [set(analysis_tokens(alias)) for alias in aliases],
            "alias_ngrams": [_character_ngrams(alias) for alias in aliases],
            "keywords": set(analysis_tokens(" ".join(document.get("keywords") or []))),
        }

    def _document_frequency(self, field: str) -> Counter[str]:
        frequency: Counter[str] = Counter()
        for item in self._index:
            frequency.update(item[field].keys())
        return frequency

    def _bm25_scores(self, query_tokens: list[str], field: str, frequency: Counter[str]) -> dict[str, float]:
        scores: dict[str, float] = {}
        number_of_documents = len(self._index)
        k1 = 1.5
        b = 0.72
        for item in self._index:
            score = 0.0
            term_counts: Counter[str] = item[field]
            document_length = sum(term_counts.values())
            for token, query_frequency in Counter(query_tokens).items():
                tf = term_counts.get(token, 0)
                if not tf:
                    continue
                document_frequency = frequency.get(token, 0)
                inverse_document_frequency = math.log(
                    1 + (number_of_documents - document_frequency + 0.5) / (document_frequency + 0.5)
                )
                average_length = self._average_lengths[field]
                denominator = tf + k1 * (1 - b + b * document_length / average_length)
                score += inverse_document_frequency * (tf * (k1 + 1) / denominator) * min(query_frequency, 2)
            scores[item["document"]["id"]] = score
        return scores

    def _semantic_scores(self, question: str, query_tokens: set[str]) -> dict[str, float]:
        query_ngrams = _character_ngrams(question)
        scores: dict[str, float] = {}
        for item in self._index:
            alias_cosine = max((_cosine(query_ngrams, value) for value in item["alias_ngrams"]), default=0.0)
            alias_coverage = max(
                (
                    len(query_tokens & alias_tokens) / max(1, len(query_tokens | alias_tokens))
                    for alias_tokens in item["alias_tokens"]
                ),
                default=0.0,
            )
            scores[item["document"]["id"]] = 0.72 * alias_cosine + 0.28 * alias_coverage
        return scores

    @staticmethod
    def _rank(scores: dict[str, float]) -> list[str]:
        return [
            document_id
            for document_id, score in sorted(scores.items(), key=lambda item: (-item[1], item[0]))
            if score > 0
        ]

    @staticmethod
    def _rrf(rankings: list[list[str]], rank_constant: int = 60) -> dict[str, float]:
        fused: dict[str, float] = {}
        for ranking in rankings:
            for rank, document_id in enumerate(ranking, start=1):
                fused[document_id] = fused.get(document_id, 0.0) + 1.0 / (rank_constant + rank)
        return fused

    def _hybrid_rank(self, question: str) -> list[dict]:
        query_list = query_analysis_tokens(question)
        query_set = set(query_list)
        if not query_set:
            return []
        bm25_scores = self._bm25_scores(query_list, "stemmed_tokens", self._df_stemmed)
        semantic_scores = self._semantic_scores(question, query_set)
        keyword_scores = {
            item["document"]["id"]: len(query_set & item["keywords"]) / max(1, len(query_set))
            for item in self._index
        }
        fused = self._rrf([
            self._rank(bm25_scores),
            self._rank(semantic_scores),
            self._rank(keyword_scores),
        ])
        maximum_fused = max(fused.values(), default=1.0)

        ranked = []
        for item in self._index:
            document_id = item["document"]["id"]
            normalized_rrf = fused.get(document_id, 0.0) / maximum_fused
            semantic = semantic_scores.get(document_id, 0.0)
            keyword = keyword_scores.get(document_id, 0.0)
            bm25 = bm25_scores.get(document_id, 0.0)
            maximum_bm25 = max(bm25_scores.values(), default=0.0)
            bm25_norm = bm25 / maximum_bm25 if maximum_bm25 > 0 else 0.0
            # A measured, deterministic reranker for the reference corpus. The
            # cross-encoder is a production candidate, not silently simulated.
            score = 0.50 * semantic + 0.22 * normalized_rrf + 0.18 * bm25_norm + 0.10 * keyword
            ranked.append({
                "document": item["document"],
                "score": round(score, 6),
                "signals": {
                    "semantic": round(semantic, 6),
                    "rrf": round(normalized_rrf, 6),
                    "bm25": round(bm25_norm, 6),
                    "keyword": round(keyword, 6),
                },
            })
        return sorted(ranked, key=lambda item: (-item["score"], item["document"]["id"]))

    def baseline_search(self, question: str, limit: int = 3) -> list[str]:
        """A strict word-form BM25 baseline used by the committed eval harness."""
        query = raw_tokens(question)
        if not query:
            return []
        scores = self._bm25_scores(query, "raw_tokens", self._df_raw)
        return self._rank(scores)[: max(1, limit)]

    def retrieve(self, question: str, limit: int = 3) -> list[dict]:
        return self._hybrid_rank(question)[: max(1, min(limit, 8))]

    @staticmethod
    def _confidence(score: float) -> str:
        if score >= 0.74:
            return "high"
        if score >= 0.52:
            return "medium"
        return "low"

    def _source_payload(self, reference: dict) -> dict:
        source = self.sources[reference["source_id"]]
        return {
            "id": source["id"],
            "title": source["title"],
            "publisher": source["publisher"],
            "url": source["url"],
            "source_type": source["source_type"],
            "data_year": source.get("data_year"),
            "updated_at": source.get("updated_at"),
            "locator": reference["locator"],
        }

    @staticmethod
    def _safe_question(question: object) -> str:
        normalized = " ".join(str(question or "").split())
        if len(normalized) < 3:
            raise ValueError("Küsimus peab olema vähemalt 3 tähemärki pikk.")
        if len(normalized) > 500:
            raise ValueError("Küsimus võib olla kuni 500 tähemärki pikk.")
        return normalized

    def answer(self, question: object, limit: int = 3) -> dict:
        safe_question = self._safe_question(question)
        query_plan = plan_forestry_question(safe_question)
        kataster_match = KATASTER_RE.search(safe_question)
        if kataster_match:
            parcel = kataster_match.group(1)
            document = next(item for item in self.documents if item["id"] == "property-forest-data")
            sources = [self._source_payload(reference) for reference in document["sources"]]
            return {
                "status": "redirect",
                "question": safe_question,
                "query_plan": query_plan,
                "answer": {
                    "claim_type": "service_direction",
                    "sections": [{
                        "kind": "answer",
                        "title": "Kinnistupäring",
                        "text": "Katastritunnuse andmed tuleb avada kinnistuotsingus; üldine SMI tõlgendaja ei omista riiklikku hinnangut sellele kinnistule.",
                        "citations": [source["id"] for source in sources],
                    }],
                    "limitations": document["answer"]["limitations"],
                },
                "sources": sources,
                "actions": [
                    {"label": "Ava Terrapointi kinnistuotsing", "url": f"/?kataster={parcel}"},
                    {"label": "Ava riiklik Metsaportaal", "url": "https://register.metsad.ee/#/"},
                ],
                "clarification": None,
                "related_questions": document["related_questions"],
                "retrieval": {"strategy": self.STRATEGY, "confidence": "high", "documents": [document["id"]]},
            }

        normalized_question = normalize_text(safe_question)
        if is_out_of_scope_question(normalized_question):
            ranked = []
        else:
            ranked = self.retrieve(safe_question, limit=limit)

        if not ranked or ranked[0]["score"] < 0.30:
            return {
                "status": "needs_clarification",
                "question": safe_question,
                "query_plan": query_plan,
                "answer": {
                    "claim_type": "no_supported_evidence",
                    "sections": [{
                        "kind": "answer",
                        "title": "Vajan täpsustust",
                        "text": "Kinnitatud metsaallikatest ei leitud piisavalt tugevat vastet. Palun lisa küsimusse näitaja, piirkond, ajavahemik või allika nimi.",
                        "citations": [],
                    }],
                    "limitations": ["Tõendita arvulist või õiguslikku vastust ei koostatud."],
                },
                "sources": [],
                "actions": [],
                "clarification": "Kas küsid SMI riikliku statistika, Metsaregistri kinnistuandmete, RMK või õigusliku piirangu kohta?",
                "related_questions": self.suggestions("", limit=3),
                "retrieval": {"strategy": self.STRATEGY, "confidence": "low", "documents": []},
            }

        selected = ranked[0]
        document = selected["document"]
        source_payloads = [self._source_payload(reference) for reference in document["sources"]]
        citation_ids = [source["id"] for source in source_payloads]
        answer = document["answer"]
        generated_answer = self.generator.generate(
            question=safe_question,
            document=document,
            allowed_source_ids=citation_ids,
        )
        requires_clarification = answer.get("claim_type") in {
            "clarification_required",
            "clarification_and_data_requirement",
            "partial_statistical_answer_with_abstention",
            "trend_explanation_with_abstention",
        }
        status = "needs_clarification" if requires_clarification else "answered"
        clarification = CLARIFICATION_PROMPTS.get(document["id"]) if requires_clarification else None
        if requires_clarification and document["id"] == "municipality-forest-area":
            if not query_plan["geography"]:
                clarification = CLARIFICATION_PROMPTS[document["id"]]
            elif not query_plan["indicators"]:
                clarification = (
                    "Piirkond on olemas. Palun vali näitaja: metsamaa pindala, metsasus "
                    "või registris kehtivate eraldiste pindala."
                )
            else:
                clarification = (
                    "Prototüüp ei arvuta valla näitajat riiklikust SMI hinnangust. "
                    "Vastus vajab valitud näitaja ja perioodiga ametlikku ruumikihti või andmetabelit."
                )
        if requires_clarification and not clarification:
            clarification = "Palun täpsusta piirkond, periood või võrreldav näitaja."

        return {
            "status": status,
            "question": safe_question,
            "query_plan": query_plan,
            "answer": generated_answer,
            "sources": source_payloads,
            "actions": [],
            "clarification": clarification,
            "related_questions": list(document.get("related_questions") or []),
            "retrieval": {
                "strategy": self.STRATEGY,
                "generator": self.generator.provider_id,
                "confidence": self._confidence(selected["score"]),
                "documents": [item["document"]["id"] for item in ranked],
                "top_score": selected["score"],
            },
        }

    def suggestions(self, query: object = "", limit: int = 5) -> list[str]:
        safe_limit = max(1, min(int(limit), 8))
        normalized = " ".join(str(query or "").split())
        if not normalized:
            return [document["question_aliases"][0] for document in self.documents[:safe_limit]]
        ranked = self.retrieve(normalized, limit=safe_limit)
        suggestions = []
        for item in ranked:
            suggestion = item["document"]["question_aliases"][0]
            if suggestion not in suggestions:
                suggestions.append(suggestion)
        return suggestions[:safe_limit]


@lru_cache(maxsize=1)
def get_forestry_search_engine() -> ForestrySearchEngine:
    provider = os.getenv("FORESTRY_GENERATOR_PROVIDER", "extractive")
    return ForestrySearchEngine(generator=build_forestry_generator(provider))
