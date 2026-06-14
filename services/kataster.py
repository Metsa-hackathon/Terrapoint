from __future__ import annotations
import re
import asyncio
import httpx
from fastapi import HTTPException
import config

_KATASTER_RE = re.compile(r'^\d{1,5}:\d{1,4}:\d{1,5}(:\d{1,4})?$')


class KatasterWFSError(Exception):
    """WFS server error - distinct from genuine 'not found'."""


def _validate_kataster_nr(kataster_nr: str) -> str:
    """Sanitize kataster_nr to prevent CQL injection."""
    if not _KATASTER_RE.match(kataster_nr):
        raise HTTPException(status_code=400, detail=f"Vigane katastritunnus: {kataster_nr}")
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
                return resp.json().get("features", [])
        except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError) as e:
            last_exc = e
            if attempt < retries:
                await asyncio.sleep(0.25 * (2 ** attempt))
                continue
            raise KatasterWFSError(f"WFS timeout/connect: {e}") from e
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
