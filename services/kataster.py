from __future__ import annotations
import re
import asyncio
import math
from datetime import date
from urllib.parse import quote
import httpx
from fastapi import HTTPException
import config

from services.validation import KATASTER_RE

# Alias järgmiseks kasutuseks selles failis (allavoolu kontrollib sama mustrit)
_KATASTER_RE = KATASTER_RE
_ADOB_RESOLVE_SEMAPHORE = asyncio.Semaphore(8)
ADOB_RESOLVE_ATTEMPTS = 4
ADOB_RESOLVE_TIMEOUT_SECONDS = 2.5
ADOB_RESOLVE_DEADLINE_SECONDS = 8.5
LAND_VALUATION_URL = "https://hindamine.kataster.ee/api/latest"
LAND_VALUATION_TIMEOUT_SECONDS = 1.5


class KatasterWFSError(Exception):
    """WFS server error - distinct from genuine 'not found'."""


def _validate_kataster_nr(kataster_nr: str) -> str:
    """Sanitize kataster_nr to prevent CQL injection."""
    if not _KATASTER_RE.match(kataster_nr or ""):
        # Ära peegelda kasutaja sisendit veateates — väldib logide mürgitust
        # ja tulevasi XSS-mustreid, kui veateade peaks kunagi HTML-i jõudma.
        raise HTTPException(status_code=400, detail="Vigane katastritunnus")
    return kataster_nr


def _normalized_date(value: object) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return date.fromisoformat(value[:10]).isoformat()
    except ValueError:
        return None


def _finite_nonnegative_number(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number >= 0 else None


async def query_land_valuation_metadata(kataster_nr: str) -> dict | None:
    """Fetch optional valuation timing without making cadastral data depend on it."""
    kataster_nr = _validate_kataster_nr(kataster_nr)
    url = f"{LAND_VALUATION_URL}/{quote(kataster_nr, safe='')}"
    try:
        async with asyncio.timeout(LAND_VALUATION_TIMEOUT_SECONDS):
            timeout = httpx.Timeout(LAND_VALUATION_TIMEOUT_SECONDS)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url)
            response.raise_for_status()
            payload = response.json()
    except (TimeoutError, httpx.HTTPError, TypeError, ValueError):
        return None

    if not isinstance(payload, dict):
        return None
    message = payload.get("message")
    assessment = message.get("assessment") if isinstance(message, dict) else None
    if payload.get("status") != "OK" or not isinstance(assessment, dict):
        return None
    if assessment.get("cadastreId") != kataster_nr:
        return None

    total_value = assessment.get("totalValue")
    assessment_year = assessment.get("assessmentYear")
    assessment_time = _normalized_date(assessment.get("assessmentTime"))
    valid_from = _normalized_date(assessment.get("validFrom"))
    valid_until_raw = assessment.get("validUntil")
    valid_until = _normalized_date(valid_until_raw) if valid_until_raw else None
    if (
        isinstance(total_value, bool)
        or not isinstance(total_value, (int, float))
        or not math.isfinite(total_value)
        or total_value < 0
        or isinstance(assessment_year, bool)
        or not isinstance(assessment_year, int)
        or not 1900 <= assessment_year <= 2100
        or assessment_time is None
        or valid_from is None
        or (valid_until_raw and valid_until is None)
    ):
        return None

    basis = assessment.get("basis")
    if isinstance(basis, str):
        basis = re.sub(r"[\x00-\x1f\x7f]+", " ", basis).strip()[:160] or None
    else:
        basis = None
    return {
        "state": "available",
        "total_value": int(total_value) if float(total_value).is_integer() else round(total_value, 2),
        "assessment_year": assessment_year,
        "assessment_time": assessment_time,
        "valid_from": valid_from,
        "valid_until": valid_until,
        "basis": basis,
    }


async def _wfs_get(url: str, timeout: float = 6.0, retries: int = 5) -> list[dict]:
    """Resilient WFS GET with retry on transient errors.

    Returns [] only on successful response with 0 features.
    Raises KatasterWFSError on timeout, connect failure, or HTTP error.

    Retries on 5xx, 408, 429, and 400 (the upstream Estonian WFS
    is highly flaky: ~25% of valid CQL queries return transient 400
    or 5xx within a 60s window). 6 attempts with backoff gives
    ~99% effective success.
    """
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(url)
                if resp.status_code in (400, 408, 429) or resp.status_code >= 500:
                    last_exc = httpx.HTTPStatusError(
                        f"WFS {resp.status_code}", request=resp.request, response=resp
                    )
                    if attempt < retries:
                        await asyncio.sleep(0.25 * (2 ** attempt))
                        continue
                    raise KatasterWFSError(f"WFS {resp.status_code}") from last_exc
                resp.raise_for_status()
                payload = resp.json()
                features = payload.get("features") if isinstance(payload, dict) else None
                if not isinstance(features, list) or any(not isinstance(feature, dict) for feature in features):
                    raise KatasterWFSError("WFS response has invalid features")
                return features
        except (httpx.TransportError, httpx.HTTPStatusError, ValueError) as e:
            last_exc = e
            if attempt < retries:
                await asyncio.sleep(0.25 * (2 ** attempt))
                continue
            raise KatasterWFSError(f"WFS request failed: {type(e).__name__}") from e
    raise KatasterWFSError(f"WFS failed after {retries + 1} attempts: {last_exc}")


async def query_kataster(
    kataster_nr: str,
    include_valuation_metadata: bool = False,
) -> dict | None:
    """Fetch kataster record. Returns None if no match, raises on WFS error."""
    kataster_nr = _validate_kataster_nr(kataster_nr)
    url = (
        f"{config.GEOBASE}/kataster/wfs?"
        f"service=WFS&request=GetFeature&typeName=kataster:ky_kehtiv"
        f"&srsName=EPSG:4326&outputFormat=application/json"
        f"&CQL_FILTER=tunnus%3D%27{kataster_nr}%27"
    )
    if include_valuation_metadata:
        features_result, valuation_result = await asyncio.gather(
            _wfs_get(url, timeout=10.0, retries=3),
            query_land_valuation_metadata(kataster_nr),
            return_exceptions=True,
        )
    else:
        valuation_result = None
        try:
            features_result = await _wfs_get(url, timeout=10.0, retries=3)
        except KatasterWFSError as exc:
            features_result = exc
    if isinstance(features_result, KatasterWFSError):
        raise HTTPException(status_code=502, detail="Katastri WFS ei vasta, proovi uuesti")
    if isinstance(features_result, Exception):
        raise features_result
    features = features_result
    if not features:
        return None
    if any(
        not isinstance(feature.get("properties"), dict)
        or feature["properties"].get("tunnus") != kataster_nr
        for feature in features
    ):
        raise HTTPException(
            status_code=502,
            detail="Katastri WFS tagastas vastuolulised andmed",
        )
    matching_features = features
    canonical_feature = matching_features[0]
    if any(feature != canonical_feature for feature in matching_features[1:]):
        raise HTTPException(
            status_code=502,
            detail="Katastri WFS tagastas vastuolulised duplikaadid",
        )
    props = canonical_feature["properties"]
    geom = canonical_feature.get("geometry")
    area_m2 = _finite_nonnegative_number(props.get("pindala"))
    if area_m2 is None or area_m2 <= 0:
        raise HTTPException(status_code=502, detail="Katastri WFS tagastas vigase pindala")
    raw_taxable_value = props.get("maks_hind")
    taxable_value = (
        None
        if raw_taxable_value is None
        else _finite_nonnegative_number(raw_taxable_value)
    )
    if raw_taxable_value is not None and taxable_value is None:
        raise HTTPException(
            status_code=502,
            detail="Katastri WFS tagastas vigase maksustamishinna",
        )
    text_values = {}
    for field, max_length in (
        ("siht1", 160),
        ("omvorm", 160),
        ("mk_nimi", 160),
        ("ov_nimi", 160),
        ("l_aadress", 300),
    ):
        value = props.get(field)
        if value is None:
            value = ""
        if not isinstance(value, str):
            raise HTTPException(
                status_code=502,
                detail=f"Katastri WFS tagastas vigase välja {field}",
            )
        text_values[field] = re.sub(r"[\x00-\x1f\x7f]+", " ", value).strip()[:max_length]

    valuation_meta = {"state": "unavailable"}
    if isinstance(valuation_result, dict) and valuation_result.get("state") == "available":
        official_value = valuation_result.get("total_value")
        try:
            values_match = (
                not isinstance(taxable_value, bool)
                and taxable_value is not None
                and math.isfinite(float(taxable_value))
                and float(taxable_value) == float(official_value)
            )
        except (TypeError, ValueError):
            values_match = False
        if values_match:
            valuation_meta = valuation_result
    return {
        "number": props.get("tunnus", kataster_nr),
        "pindala_ha": round(area_m2 / 10000, 2),
        "sihtotstarve": text_values["siht1"],
        "omvorm": text_values["omvorm"],
        "mk_nimi": text_values["mk_nimi"],
        "ov_nimi": text_values["ov_nimi"],
        "l_aadress": text_values["l_aadress"],
        "maks_hind": taxable_value,
        "maks_hind_meta": valuation_meta,
        "geometry": geom,
    }


async def resolve_kataster_by_adob_id(
    adob_id: int,
    attempts: int = ADOB_RESOLVE_ATTEMPTS,
) -> str | None:
    """Resolve a cadastral number when GeoServer omits it from GetFeatureInfo."""
    url = (
        f"{config.GEOBASE}/kataster/wfs?"
        f"service=WFS&request=GetFeature&typeName=kataster:ky_kehtiv"
        f"&srsName=EPSG:4326&outputFormat=application/json&count=1"
        f"&propertyName=adob_id,tunnus"
        f"&CQL_FILTER=adob_id%3D{adob_id}"
    )
    last_error: KatasterWFSError | None = None
    try:
        async with asyncio.timeout(ADOB_RESOLVE_DEADLINE_SECONDS):
            async with _ADOB_RESOLVE_SEMAPHORE:
                for attempt in range(attempts):
                    try:
                        features = await _wfs_get(
                            url,
                            timeout=ADOB_RESOLVE_TIMEOUT_SECONDS,
                            retries=0,
                        )
                    except KatasterWFSError as exc:
                        last_error = exc
                    else:
                        if not features:
                            return None
                        if len(features) == 1:
                            properties = features[0].get("properties")
                            if isinstance(properties, dict) and str(properties.get("adob_id")) == str(adob_id):
                                tunnus = properties.get("tunnus")
                                if isinstance(tunnus, str) and _KATASTER_RE.fullmatch(tunnus):
                                    return tunnus
                    if attempt + 1 < attempts:
                        await asyncio.sleep(0.15)
    except TimeoutError as exc:
        raise KatasterWFSError("WFS resolver deadline exceeded") from exc
    raise KatasterWFSError("WFS response omitted cadastral identifier") from last_error
