import httpx
import config

SPECIES_NAMES = {
    "MA": "Mänd", "KU": "Kuusk", "KS": "Kask", "HB": "Haab",
    "LH": "Lehis", "LM": "Sanglepp", "LV": "Hall lepp",
    "TA": "Tamm", "SA": "Saar", "VA": "Vaher",
    "PK": "Pöök", "JA": "Jalakas", "RE": "Remmelgas", "SP": "Seedrip",
}

BONITEET_MAP = {0: "I", 1: "II", 2: "III", 3: "IV", 4: "V", 5: "VI", 6: "VII"}


async def query_eraldis(kataster_nr: str) -> list[dict]:
    """Return ALL eraldised for a kataster parcel (not just the first)."""
    url = (
        f"{config.GEOBASE}/metsaregister/wfs?"
        f"service=WFS&request=GetFeature&typeName=metsaregister:eraldis"
        f"&srsName=EPSG:4326&outputFormat=application/json"
        f"&CQL_FILTER=katastri_nr%3D%27{kataster_nr}%27"
    )
    async with httpx.AsyncClient(timeout=3) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        features = resp.json().get("features", [])
    if not features:
        return []
    result = []
    for feat in features:
        props = feat.get("properties", {})
        kood = props.get("peapuuliik_kood", "MA")
        result.append({
            "id": props.get("id"),
            "puuliik": SPECIES_NAMES.get(kood, kood),
            "puuliik_kood": kood,
            "vanus": props.get("keskm_vanus", 0),
            "tagavara_y_ha": props.get("tagavara_1_ha") or props.get("tagavara_y_ha") or 0,
            "boniteet": BONITEET_MAP.get(int(props.get("boniteedi_kood", 3)) if props.get("boniteedi_kood") is not None else 3, "III"),
            "boniteedi_kood": int(props.get("boniteedi_kood", 3)) if props.get("boniteedi_kood") is not None else 3,
            "raievanus": props.get("keskm_raievanus"),
            "korgus": props.get("korgus"),
            "pindala_ha": props.get("pindala", 0),
            "taius_1": props.get("taius_1"),
            "kuivendatud": bool(props.get("kuivendatud", False)),
            "tuleohu_kood": props.get("tuleohu_kood"),
            "siht1": props.get("siht1"),
            "eraldis_nr": props.get("eraldise_nr"),
            "geometry": feat.get("geometry"),
        })
    return result


async def query_eraldis_element(eraldis_id: int) -> list[dict]:
    url = (
        f"{config.GEOBASE}/metsaregister/wfs?"
        f"service=WFS&request=GetFeature&typeName=metsaregister:eraldis_element"
        f"&srsName=EPSG:4326&outputFormat=application/json"
        f"&CQL_FILTER=eraldis_id%3D{eraldis_id}"
    )
    async with httpx.AsyncClient(timeout=3) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        features = resp.json().get("features", [])
    result = []
    for feat in features:
        p = feat.get("properties", {})
        kood = p.get("puuliik_kood", "")
        result.append({
            "puuliik": SPECIES_NAMES.get(kood, kood),
            "puuliik_kood": kood,
            "vanus": p.get("vanus", 0),
            "tagavara_y_ha": p.get("tagavara") or p.get("tagavara_y_ha") or 0,
            "taius": p.get("taius", 0),
        })
    return result


async def query_natura_2000(bbox_str: str) -> list[dict]:
    url = (
        f"{config.GEOBASE}/metsaregister/wfs?"
        f"service=WFS&request=GetFeature&typeName=metsaregister:natura_2000_alad"
        f"&srsName=EPSG:4326&outputFormat=application/json"
        f"&bbox={bbox_str}"
    )
    async with httpx.AsyncClient(timeout=3) as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json().get("features", [])
        except Exception:
            return []


async def query_yrask_mke(bbox_str: str) -> list[dict]:
    url = (
        f"{config.GEOBASE}/metsaregister/wfs?"
        f"service=WFS&request=GetFeature&typeName=metsaregister:kuusekooreyrask_mke"
        f"&srsName=EPSG:4326&outputFormat=application/json"
        f"&bbox={bbox_str}"
    )
    async with httpx.AsyncClient(timeout=3) as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json().get("features", [])
        except Exception:
            return []


async def query_teatised(kataster_nr: str) -> list[dict]:
    url = (
        f"{config.GEOBASE}/metsaregister/wfs?"
        f"service=WFS&request=GetFeature&typeName=metsaregister:teatis"
        f"&srsName=EPSG:4326&outputFormat=application/json"
        f"&CQL_FILTER=katastri_nr%3D%27{kataster_nr}%27"
    )
    async with httpx.AsyncClient(timeout=3) as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json().get("features", [])
        except Exception:
            return []


async def query_kahjustused(eraldis_id: int) -> list[dict]:
    url = (
        f"{config.GEOBASE}/metsaregister/wfs?"
        f"service=WFS&request=GetFeature&typeName=metsaregister:kahjustused"
        f"&srsName=EPSG:4326&outputFormat=application/json"
        f"&CQL_FILTER=eraldis_id%3D{eraldis_id}"
    )
    async with httpx.AsyncClient(timeout=3) as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json().get("features", [])
        except Exception:
            return []
