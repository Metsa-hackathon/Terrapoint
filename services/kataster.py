import httpx
import config


async def query_kataster(kataster_nr: str) -> dict | None:
    url = (
        f"{config.GEOBASE}/kataster/wfs?"
        f"service=WFS&request=GetFeature&typeName=kataster:ky_kehtiv"
        f"&srsName=EPSG:4326&outputFormat=application/json"
        f"&CQL_FILTER=tunnus%3D%27{kataster_nr}%27"
    )
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        features = resp.json().get("features", [])
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
        "geometry": geom,
    }
