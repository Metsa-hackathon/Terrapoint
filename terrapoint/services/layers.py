import asyncio
import httpx

import config

LAYER_CONFIGS = [
    ("kaitsealad", "eelis", "eelis:kr_kaitseala"),
    ("toetus_mets", "eelis", "eelis:toetus_mets"),
    ("natura_elupaik", "eelis", "eelis:natura_elupaik"),
    ("yrask_eelis", "eelis", "eelis:kuusekooreyrask_eelis"),
    ("veekaitse", "kitsendused", "kitsendused:metsakas_kpois_RANNA_VOI_KALDA_VEEKAITSEVOOND"),
    ("piiranguvoond", "kitsendused", "kitsendused:metsakas_kpois_RANNA_VOI_KALDA_PIIRANGUVOOND"),
    ("uleujutus", "kitsendused", "kitsendused:metsakas_kpois_KORDUV_ULEUJUTUSALA"),
    ("kotkas", "kitsendused", "kitsendused:kotkas_kitsendused"),
    ("malestised", "muinsuskaitse", "muinsuskaitse:kpo_malestised"),
    ("lageraiealad", "veeveeb", "veeveeb:lageraiealad"),
    ("karuputk", "maaamet", "maaamet:karuputk"),
    ("auction", "maaoksjon", "maaoksjon:auction"),
]


async def _fetch_layer(client: httpx.AsyncClient, key: str, workspace: str, typename: str, bbox_str: str) -> tuple[str, list[dict]]:
    url = (
        f"{config.GEOBASE}/{workspace}/wfs?"
        f"service=WFS&request=GetFeature&typeName={typename}"
        f"&srsName=EPSG:4326&outputFormat=application/json"
        f"&bbox={bbox_str}"
    )
    try:
        resp = await client.get(url)
        resp.raise_for_status()
        return key, resp.json().get("features", [])
    except Exception:
        return key, []


async def query_all_layers(bbox_str: str) -> dict[str, list[dict]]:
    """BBOX fanout to all restriction/overlay layers."""
    async with httpx.AsyncClient(timeout=30) as client:
        tasks = [
            _fetch_layer(client, key, ws, tn, bbox_str)
            for key, ws, tn in LAYER_CONFIGS
        ]
        results = await asyncio.gather(*tasks)

    return {key: features for key, features in results}
