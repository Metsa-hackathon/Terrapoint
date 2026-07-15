from __future__ import annotations
import re
import asyncio
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


class KatasterWFSError(Exception):
    """WFS server error - distinct from genuine 'not found'."""


def _validate_kataster_nr(kataster_nr: str) -> str:
    """Sanitize kataster_nr to prevent CQL injection."""
    if not _KATASTER_RE.match(kataster_nr or ""):
        # Ära peegelda kasutaja sisendit veateates — väldib logide mürgitust
        # ja tulevasi XSS-mustreid, kui veateade peaks kunagi HTML-i jõudma.
        raise HTTPException(status_code=400, detail="Vigane katastritunnus")
    return kataster_nr


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


async def query_kataster(kataster_nr: str) -> dict | None:
    """Fetch kataster record. Returns None if no match, raises on WFS error."""
    kataster_nr = _validate_kataster_nr(kataster_nr)
    url = (
        f"{config.GEOBASE}/kataster/wfs?"
        f"service=WFS&request=GetFeature&typeName=kataster:ky_kehtiv"
        f"&srsName=EPSG:4326&outputFormat=application/json"
        f"&CQL_FILTER=tunnus%3D%27{kataster_nr}%27"
    )
    try:
        features = await _wfs_get(url, timeout=10.0, retries=3)
    except KatasterWFSError:
        raise HTTPException(status_code=502, detail="Katastri WFS ei vasta, proovi uuesti")
    if not features:
        return None
    props = features[0].get("properties", {})
    geom = features[0].get("geometry")
    return {
        "number": props.get("tunnus", kataster_nr),
        "pindala_ha": round(props.get("pindala", 0) / 10000, 2),
        "sihtotstarve": props.get("siht1", ""),
        "omvorm": props.get("omvorm", ""),
        "mk_nimi": props.get("mk_nimi", ""),
        "ov_nimi": props.get("ov_nimi", ""),
        "l_aadress": props.get("l_aadress", ""),
        "maks_hind": props.get("maks_hind"),
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
