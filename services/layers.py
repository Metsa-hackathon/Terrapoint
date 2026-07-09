import asyncio
import httpx
import config

# All map overlay layers
LAYER_CONFIGS = [
    ("kaitsealad", "eelis", "eelis:kr_kaitseala"),
    ("yrask_eelis", "eelis", "eelis:kuusekooreyrask_eelis"),
    ("yrask_mke", "metsaregister", "metsaregister:kuusekooreyrask_mke"),
    ("piirang", "eelis", "eelis:kr_piirang"),
    ("karuputk", "maaamet", "maaamet:karuputk"),
    ("sood", "eelis", "eelis:sood"),
    ("natura_elupaik", "eelis", "eelis:natura_elupaik"),
    ("lageraiealad", "veeveeb", "veeveeb:lageraiealad"),
    ("malestised", "muinsuskaitse", "muinsuskaitse:kpo_malestised"),
    ("veekogud", "eelis", "eelis:avalikud_jarved"),
    ("vooluveed", "eelis", "eelis:avalikud_vooluveekogud"),
    ("piirangukeelualad", "maaamet", "maaamet:kpo_piirangukeelualad"),
    ("kaitsevoondid", "muinsuskaitse", "muinsuskaitse:kpo_kaitsevoondid"),
    ("uleujutus", "kitsendused", "kitsendused:metsakas_kpois_KORDUV_ULEUJUTUSALA"),
    ("veekaitse", "kitsendused", "kitsendused:metsakas_kpois_RANNA_VOI_KALDA_VEEKAITSEVOOND"),
    ("ranna_piirang", "kitsendused", "kitsendused:metsakas_kpois_RANNA_VOI_KALDA_PIIRANGUVOOND"),
    ("vaetiste_keeld", "kitsendused", "kitsendused:metsakas_kpois_VAETISTE_JA_TAIMEKAITSEV_KEELD"),
    ("kma_kitsendused", "kitsendused", "kitsendused:kotkas_kitsendused"),
    ("katsealad", "metsaregister", "metsaregister:katsealad"),
]
MAX_FEATURES_PER_LAYER = 100


async def _fetch_layer(client, key, workspace, typename, bbox_str, attempts: int = 2):
    url = (
        f"{config.GEOBASE}/{workspace}/wfs?"
        f"service=WFS&request=GetFeature&typeName={typename}"
        f"&srsName=EPSG:4326&outputFormat=application/json"
        f"&count={MAX_FEATURES_PER_LAYER}"
        f"&bbox={bbox_str},EPSG:4326"
    )
    for attempt in range(attempts):
        try:
            resp = await client.get(url)
            # Retry on transient 5xx, 408, 429, and 400 (Estonian WFS
            # intermittently returns 400 for valid bbox queries)
            if resp.status_code in (400, 408, 429) or resp.status_code >= 500:
                if attempt + 1 < attempts:
                    await asyncio.sleep(0.3 * (2 ** attempt))
                    continue
                return key, [], True, False
            if resp.status_code >= 400:
                return key, [], True, False
            features = resp.json().get("features", [])
            return key, features, False, len(features) >= MAX_FEATURES_PER_LAYER
        except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError):
            if attempt + 1 < attempts:
                await asyncio.sleep(0.3 * (2 ** attempt))
                continue
            return key, [], True, False
        except Exception:
            return key, [], True, False
    return key, [], True, False


async def query_all_layers(bbox_str: str) -> tuple[dict[str, list[dict]], list[str], list[str]]:
    """Return layer data, failed layer keys, and potentially truncated keys."""
    async with httpx.AsyncClient(timeout=15) as client:
        tasks = [
            _fetch_layer(client, key, ws, tn, bbox_str)
            for key, ws, tn in LAYER_CONFIGS
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    out = {}
    unavailable = []
    truncated = []
    for r in results:
        if isinstance(r, Exception):
            continue
        key, features, failed, may_be_truncated = r
        out[key] = features
        if failed:
            unavailable.append(key)
        if may_be_truncated:
            truncated.append(key)
    return out, unavailable, truncated
