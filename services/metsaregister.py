import asyncio
import re
import httpx
from fastapi import HTTPException
import config


class MetsaregisterWFSError(Exception):
    """Metsaregistri WFS-i ajutine või vigane vastus."""


async def _wfs_get(url: str, timeout: float = 10.0, retries: int = 3) -> list[dict]:
    """Resilient WFS GET — retries on transient errors.

    Returns [] only on a successful response with zero features. Raises when
    retryable failures are exhausted so callers never mistake unavailable data
    for a genuine empty result.

    Retries on 5xx, 408, 429, and 400 (Estonian WFS gives transient 400s).
    """
    for attempt in range(retries + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(url)
                if resp.status_code in (400, 408, 429) or resp.status_code >= 500:
                    if attempt < retries:
                        await asyncio.sleep(0.3 * (2 ** attempt))
                        continue
                    raise MetsaregisterWFSError(f"WFS {resp.status_code}")
                resp.raise_for_status()
                return resp.json().get("features", [])
        except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError):
            if attempt < retries:
                await asyncio.sleep(0.3 * (2 ** attempt))
                continue
            raise MetsaregisterWFSError("WFS timeout or connection failure")
        except MetsaregisterWFSError:
            raise
        except Exception as exc:
            raise MetsaregisterWFSError("WFS response could not be read") from exc
    raise MetsaregisterWFSError("WFS failed without a response")

_KATASTER_RE = re.compile(r'^\d{1,5}:\d{1,4}:\d{1,5}(:\d{1,4})?$')


def _validate_kataster_nr(kataster_nr: str) -> str:
    """Sanitize kataster_nr to prevent CQL injection."""
    if not _KATASTER_RE.match(kataster_nr):
        raise HTTPException(status_code=400, detail=f"Vigane katastritunnus: {kataster_nr}")
    return kataster_nr

SPECIES_NAMES = {
    "MA": "Mänd", "KU": "Kuusk", "KS": "Kask", "HB": "Haab",
    "LH": "Lehis", "LM": "Sanglepp", "LV": "Hall lepp",
    "TA": "Tamm", "SA": "Saar", "VA": "Vaher",
    "PK": "Pöök", "JA": "Jalakas", "RE": "Remmelgas", "SP": "Seedrip",
}

# Boniteedi klasside kaardistamine Kood → Rooma number.
# Eesti metsanduses 6 boniteediklassi (Kliimaministeerium Tabel 4):
#   1A (parim), I, II, III, IV, V (kehveim).
# WFS metsaregister.eraldis.boniteedi_kood on 0-6:
#   0 = 1A, 1 = I, 2 = II, 3 = III, 4 = IV, 5 = V, 6 = Va (alam-V).
# VANA BONITEET_MAP ({1:"I", 2:"II", 3:"III", 4:"IV", 5:"V"}) jättis WFS
# 0 ja 6 ilma nimeta ning NIIHUTAS kõik ühe võrra — WFS 0 (1A) ei saanud
# kunagi nime ja cutting_age tabel sai samuti vale koodi (nt eraldis WFS
# koodiga 3 (III) vaatas raievanust võtmelt 3 = vana 65a, aga seaduse
# järgi pidi olema 100a). See muutus sünkroonis cutting_age tabeliga.
BONITEET_MAP = {
    0: "1A", 1: "I", 2: "II", 3: "III", 4: "IV", 5: "V", 6: "Va",
}


def _first_present(*values):
    """Return the first declared WFS value, preserving valid zeroes."""
    for value in values:
        if value is not None:
            return value
    return None

# Tagavara hinnang (m³/ha) kõrguse ja boniteedi järgi — Eesti boniteeditabelid
# Võti: (boniteet_kood, kõrgus_m) → m³/ha
# Allikas: RMK boniteeditabelid, keskmised väärtused
_TAGAVARA_BY_HEIGHT = {
    # boniteet_kood: [(kõrgus, m³/ha), ...] — interpolatsiooniks
    1: [(5, 30), (10, 80), (15, 150), (20, 230), (25, 310), (30, 380)],
    2: [(5, 20), (10, 60), (15, 120), (20, 190), (25, 260), (30, 320)],
    3: [(5, 15), (10, 45), (15, 90), (20, 150), (25, 210), (30, 260)],
    4: [(5, 10), (10, 30), (15, 65), (20, 110), (25, 160), (30, 200)],
    5: [(5, 5), (10, 20), (15, 40), (20, 70), (25, 100), (30, 130)],
}


def estimate_tagavara(boniteet_kood: int, korgus: float, vanus: int) -> float:
    """Tagavara hinnang (m³/ha) kõrguse ja boniteedi järgi, kui metsaregister andmed puuduvad."""
    bk = boniteet_kood if boniteet_kood in _TAGAVARA_BY_HEIGHT else 3
    table = _TAGAVARA_BY_HEIGHT[bk]

    # Kõrguse järgi interpolatsioon
    if korgus and korgus > 0:
        if korgus <= table[0][0]:
            return float(table[0][1])
        if korgus >= table[-1][0]:
            return float(table[-1][1])
        for i in range(len(table) - 1):
            h1, v1 = table[i]
            h2, v2 = table[i + 1]
            if h1 <= korgus <= h2:
                ratio = (korgus - h1) / (h2 - h1)
                return round(v1 + ratio * (v2 - v1), 1)

    # Kui kõrgust pole, kasuta vanust
    if vanus and vanus > 0:
        # Kesmine kõrguse kasv: ~0.3 m/a (II boniteet)
        est_height = vanus * 0.3
        return estimate_tagavara(bk, est_height, 0)

    return 0.0


async def query_eraldis(kataster_nr: str) -> list[dict]:
    """Return ALL eraldised for a kataster parcel (not just the first)."""
    kataster_nr = _validate_kataster_nr(kataster_nr)
    url = (
        f"{config.GEOBASE}/metsaregister/wfs?"
        f"service=WFS&request=GetFeature&typeName=metsaregister:eraldis"
        f"&srsName=EPSG:4326&outputFormat=application/json"
        f"&CQL_FILTER=katastri_nr%3D%27{kataster_nr}%27"
    )
    features = await _wfs_get(url, timeout=20.0, retries=3)
    if not features:
        return []
    result = []
    for feat in features:
        props = feat.get("properties", {})
        kood = props.get("peapuuliik_kood", "MA")
        tagavara = _first_present(
            props.get("tagavara_1_ha"),
            props.get("tagavara_l_ha"),
            props.get("tagavara_y_ha"),
        )
        if tagavara is None:
            tagavara = estimate_tagavara(
                int(props.get("boniteedi_kood", 3)) if props.get("boniteedi_kood") is not None else 3,
                props.get("korgus", 0),
                props.get("keskm_vanus", 0),
            )
        result.append({
            "id": props.get("id"),
            "puuliik": SPECIES_NAMES.get(kood, kood),
            "puuliik_kood": kood,
            "vanus": props.get("keskm_vanus", 0),
            "tagavara_y_ha": tagavara,
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
    features = await _wfs_get(url, timeout=10.0, retries=1)
    result = []
    for feat in features:
        p = feat.get("properties", {})
        kood = p.get("puuliik_kood", "")
        tagavara = _first_present(p.get("tagavara"), p.get("tagavara_y_ha"))
        if tagavara is None:
            tagavara = estimate_tagavara(3, 0, p.get("vanus", 0))
        result.append({
            "eraldis_id": eraldis_id,
            "puuliik": SPECIES_NAMES.get(kood, kood),
            "puuliik_kood": kood,
            "vanus": p.get("vanus", 0),
            "tagavara_y_ha": tagavara,
            "taius": p.get("taius", 0),
        })
    return result


async def query_natura_2000(bbox_str: str) -> list[dict]:
    url = (
        f"{config.GEOBASE}/metsaregister/wfs?"
        f"service=WFS&request=GetFeature&typeName=metsaregister:natura_2000_alad"
        f"&srsName=EPSG:4326&outputFormat=application/json"
        f"&bbox={bbox_str},EPSG:4326"
    )
    return await _wfs_get(url, timeout=10.0, retries=1)


async def query_teatised(kataster_nr: str) -> list[dict]:
    kataster_nr = _validate_kataster_nr(kataster_nr)
    url = (
        f"{config.GEOBASE}/metsaregister/wfs?"
        f"service=WFS&request=GetFeature&typeName=metsaregister:teatis"
        f"&srsName=EPSG:4326&outputFormat=application/json"
        f"&CQL_FILTER=katastri_nr%3D%27{kataster_nr}%27"
    )
    return await _wfs_get(url, timeout=10.0, retries=2)


async def query_kahjustused(eraldis_id: int) -> list[dict]:
    url = (
        f"{config.GEOBASE}/metsaregister/wfs?"
        f"service=WFS&request=GetFeature&typeName=metsaregister:kahjustused"
        f"&srsName=EPSG:4326&outputFormat=application/json"
        f"&CQL_FILTER=eraldis_id%3D{eraldis_id}"
    )
    return await _wfs_get(url, timeout=10.0, retries=1)
