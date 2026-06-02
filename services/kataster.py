import re
import httpx
from fastapi import HTTPException
import config

_KATASTER_RE = re.compile(r'^\d{1,5}:\d{1,4}:\d{1,5}(:\d{1,4})?$')


def _validate_kataster_nr(kataster_nr: str) -> str:
    """Sanitize kataster_nr to prevent CQL injection."""
    if not _KATASTER_RE.match(kataster_nr):
        raise HTTPException(status_code=400, detail=f"Vigane katastritunnus: {kataster_nr}")
    return kataster_nr


async def query_kataster(kataster_nr: str) -> dict | None:
    kataster_nr = _validate_kataster_nr(kataster_nr)
    url = (
        f"{config.GEOBASE}/kataster/wfs?"
        f"service=WFS&request=GetFeature&typeName=kataster:ky_kehtiv"
        f"&srsName=EPSG:4326&outputFormat=application/json"
        f"&CQL_FILTER=tunnus%3D%27{kataster_nr}%27"
    )
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            features = resp.json().get("features", [])
        except Exception:
            return None
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
