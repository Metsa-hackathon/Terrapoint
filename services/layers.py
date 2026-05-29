import asyncio
import httpx
import config

LAYER_CONFIGS = [
    # EELIS (Keskkonnaamet) layers
    ("kaitsealad", "eelis", "eelis:kr_kaitseala"),
    ("toetus_mets", "eelis", "eelis:toetus_mets"),
    ("natura_elupaik", "eelis", "eelis:natura_elupaik"),
    ("yrask_eelis", "eelis", "eelis:kuusekooreyrask_eelis"),
    ("liigid_eelis", "eelis", "eelis:liigi_alamkirjed_avalik"),
    ("jahipiirkonnad", "eelis", "eelis:kr_jahipiirkond"),
    ("kaadamisalad", "eelis", "eelis:kaadamisalad"),
    ("sood", "eelis", "eelis:sood"),
    ("niidud", "eelis", "eelis:niidud"),
    ("piirang", "eelis", "eelis:kr_piirang"),
    ("loodusala", "eelis", "eelis:kr_loodusala"),
    ("linnuala", "eelis", "eelis:kr_linnuala"),
    ("reservaat", "eelis", "eelis:kr_reservaat"),
    ("looduslik_skv", "eelis", "eelis:kr_looduslik_skv"),
    ("veekogud", "eelis", "eelis:avalikud_jarved"),
    ("vooluveed", "eelis", "eelis:avalikud_vooluveekogud"),
    ("metsaseire", "eelis", "eelis:kr_sj_metsaseire"),

    # Kitsendused (Maa-amet / Keskkonnaamet)
    ("veekaitse", "kitsendused", "kitsendused:metsakas_kpois_RANNA_VOI_KALDA_VEEKAITSEVOOND"),
    ("piiranguvoond", "kitsendused", "kitsendused:metsakas_kpois_RANNA_VOI_KALDA_PIIRANGUVOOND"),
    ("uleujutus", "kitsendused", "kitsendused:metsakas_kpois_KORDUV_ULEUJUTUSALA"),
    ("kotkas", "kitsendused", "kitsendused:kotkas_kitsendused"),
    ("malestised", "muinsuskaitse", "muinsuskaitse:kpo_malestised"),

    # Other layers
    ("lageraiealad", "veeveeb", "veeveeb:lageraiealad"),
    ("mullad", "veeveeb", "veeveeb:mullad_boniteet"),
    ("karuputk", "maaamet", "maaamet:karuputk"),
    ("auction", "maaoksjon", "maaoksjon:auction"),
    ("clc", "keskkonnainfo", "keskkonnainfo:clc_2018_iii"),
    ("protected_sites", "ps", "ps:ProtectedSite"),
]


async def _fetch_layer(client, key, workspace, typename, bbox_str):
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
    async with httpx.AsyncClient(timeout=5) as client:
        tasks = [
            _fetch_layer(client, key, ws, tn, bbox_str)
            for key, ws, tn in LAYER_CONFIGS
        ]
        results = await asyncio.gather(*tasks)
    return {key: features for key, features in results}
