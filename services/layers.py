import asyncio
import httpx
import config

# Core layers — minimal set for fast response (~2-3s total)
LAYER_CONFIGS = [
    # EELIS (Keskkonnaamet) — most useful for forestry
    ("kaitsealad", "eelis", "eelis:kr_kaitseala"),
    ("yrask_eelis", "eelis", "eelis:kuusekooreyrask_eelis"),
    ("piirang", "eelis", "eelis:kr_piirang"),
    ("sood", "eelis", "eelis:sood"),
    ("natura_elupaik", "eelis", "eelis:natura_elupaik"),

    # Kitsendused
    ("veekaitse", "kitsendused", "kitsendused:metsakas_kpois_RANNA_VOI_KALDA_VEEKAITSEVOOND"),
    ("uleujutus", "kitsendused", "kitsendused:metsakas_kpois_KORDUV_ULEUJUTUSALA"),

    # Other
    ("karuputk", "maaamet", "maaamet:karuputk"),
]


async def _fetch_layer(client, key, workspace, typename, bbox_str):
    url = (
        f"{config.GEOBASE}/{workspace}/wfs?"
        f"service=WFS&request=GetFeature&typeName={typename}"
        f"&srsName=EPSG:4326&outputFormat=application/json"
        f"&count=10"
        f"&bbox={bbox_str},EPSG:4326"
    )
    try:
        resp = await client.get(url)
        if resp.status_code >= 400:
            return key, []
        return key, resp.json().get("features", [])
    except Exception:
        return key, []


async def query_all_layers(bbox_str: str) -> dict[str, list[dict]]:
    async with httpx.AsyncClient(timeout=4) as client:
        tasks = [
            _fetch_layer(client, key, ws, tn, bbox_str)
            for key, ws, tn in LAYER_CONFIGS
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    out = {}
    for r in results:
        if isinstance(r, Exception):
            continue
        key, features = r
        out[key] = features
    return out
