import httpx
from urllib.parse import quote

import config


async def query_kataster(kataster_nr: str) -> dict | None:
    """Query kataster:ky_kehtiv WFS for parcel data."""
    encoded_nr = quote(kataster_nr, safe="")
    cql = f"tunnus = '{kataster_nr}'"
    cql_encoded = cql.replace("=", "%20%3D%20").replace("'", "%27").replace(kataster_nr, encoded_nr)

    url = (
        f"{config.GEOBASE}/kataster/wfs?"
        f"service=WFS&request=GetFeature&typeName=kataster:ky_kehtiv"
        f"&srsName=EPSG:4326&outputFormat=application/json"
        f"&CQL_FILTER=tunnus%20%3D%20%27{encoded_nr}%27"
    )

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

    features = data.get("features", [])
    if not features:
        return None

    props = features[0].get("properties", {})
    geometry = features[0].get("geometry")

    pindala_m2 = props.get("pindala", 0) or 0

    return {
        "number": props.get("tunnus", kataster_nr),
        "pindala_ha": round(pindala_m2 / 10000, 2),
        "mets_pindala_ha": round((props.get("mets") or 0) / 10000, 2) if props.get("mets") else None,
        "sihtotstarve": props.get("siht1"),
        "omvorm": props.get("omvorm"),
        "maks_hind": props.get("maks_hind"),
        "mk_nimi": props.get("mk_nimi"),
        "ov_nimi": props.get("ov_nimi"),
        "l_aadress": props.get("l_aadress"),
        "geometry": geometry,
    }
