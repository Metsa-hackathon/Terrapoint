import asyncio
import httpx
import config

# Minimal layers for fast response (~1-2s total)
LAYER_CONFIGS = [
    ("kaitsealad", "eelis", "eelis:kr_kaitseala"),
    ("yrask_eelis", "eelis", "eelis:kuusekooreyrask_eelis"),
    ("piirang", "eelis", "eelis:kr_piirang"),
    ("veekaitse", "kitsendused", "kitsendused:metsakas_kpois_RANNA_VOI_KALDA_VEEKAITSEVOOND"),
    ("karuputk", "maaamet", "maaamet:karuputk"),
]


async def _fetch_layer(client, key, workspace, typename, bbox_str):
    url = (
        f"{config.GEOBASE}/{workspace}/wfs?"
        f"service=WFS&request=GetFeature&typeName={typename}"
        f"&srsName=EPSG:4326&outputFormat=application/json"
        f"&count=5"
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
    async with httpx.AsyncClient(timeout=3) as client:
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
