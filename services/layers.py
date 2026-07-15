import asyncio
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping, Sequence

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
DEFAULT_SOURCE_TIMEOUT_SECONDS = 7.0


@dataclass(frozen=True)
class MapStyle:
    label: str
    color: str
    dash: str | None
    weight: int | float
    fill_opacity: float


@dataclass(frozen=True)
class LayerSource:
    key: str
    theme_id: str | None
    label: str
    provider: str
    source_label: str
    interpretation: str
    style: MapStyle | None
    technical_umbrella: bool = False


@dataclass(frozen=True)
class ThemeDefinition:
    id: str
    label: str
    source_keys: tuple[str, ...]


@dataclass(frozen=True)
class SourceState:
    key: str
    state: str
    match_count: int


@dataclass(frozen=True)
class ThemeResult:
    theme_id: str
    state: str
    match_count: int
    features: tuple[dict, ...]
    source_states: tuple[SourceState, ...]


_STYLES = {
    "kaitsealad": MapStyle("Kaitsealad", "#1b4332", None, 4, 0.35),
    "natura_elupaik": MapStyle("Natura elupaigad", "#74c69d", None, 3, 0.40),
    "piirang": MapStyle("Piiranguvööndid", "#7b2cbf", "6,4", 3, 0.30),
    "yrask_eelis": MapStyle("Üraski vaatlused", "#e76f51", None, 4, 0.45),
    "yrask_mke": MapStyle("Surnud puud (MKE)", "#c1121f", None, 4, 0.55),
    "sood": MapStyle("Sood", "#1d4e89", None, 2.5, 0.40),
    "veekogud": MapStyle("Järved", "#48cae4", None, 2.5, 0.50),
    "vooluveed": MapStyle("Vooluveed", "#023e8a", None, 4, 0.0),
    "veekaitse": MapStyle("Veekaitsevöönd", "#0ea5e9", "4,3", 2.5, 0.20),
    "ranna_piirang": MapStyle("Ranna piirang", "#14b8a6", None, 2, 0.22),
    "uleujutus": MapStyle("Üleujutusala", "#06b6d4", "6,6", 2.5, 0.25),
    "kma_kitsendused": MapStyle("Kotkas (KMA)", "#b45309", "4,4", 3, 0.25),
    "malestised": MapStyle("Mälestised", "#6d28d9", None, 3, 0.40),
    "kaitsevoondid": MapStyle("Kaitsevöönd (MK)", "#a78bfa", "4,3", 2, 0.20),
    "piirangukeelualad": MapStyle("Piirangu keeluala", "#8b5cf6", None, 2, 0.18),
    "karuputk": MapStyle("Karuputk", "#d63384", "2,3", 2.5, 0.40),
    "lageraiealad": MapStyle("Lageraiealad", "#6c757d", "8,4", 3, 0.30),
}


SOURCE_REGISTRY: Mapping[str, LayerSource] = MappingProxyType({
    "kaitsealad": LayerSource(
        "kaitsealad", "nature_protection", "Kaitsealad", "Keskkonnaagentuur",
        "EELIS: kaitsealad", "Ametlikud kaitstavad loodusobjektid.", _STYLES["kaitsealad"],
    ),
    "yrask_eelis": LayerSource(
        "yrask_eelis", "forest_health", "Üraski vaatlused", "Keskkonnaagentuur",
        "EELIS: kuuse-kooreüraski vaatlused", "Registrisse kantud üraskivaatlused, mitte kahjustuse prognoos.", _STYLES["yrask_eelis"],
    ),
    "yrask_mke": LayerSource(
        "yrask_mke", "forest_health", "Surnud puud (MKE)", "Keskkonnaagentuur",
        "Metsaregister: MKE kuuse-kooreüraski kahjustused", "Metsakahjustuse ekspertiisi andmed, mitte reaalajaseire.", _STYLES["yrask_mke"],
    ),
    "piirang": LayerSource(
        "piirang", "nature_protection", "Piiranguvööndid", "Keskkonnaagentuur",
        "EELIS: kaitstavate alade piiranguvööndid", "Looduskaitselised piiranguvööndid; tegevuse tingimused vajavad eraldi kontrolli.", _STYLES["piirang"],
    ),
    "karuputk": LayerSource(
        "karuputk", "invasive_species", "Karuputke leiukohad", "Maa- ja Ruumiamet",
        "Maa- ja Ruumiamet: karuputk", "Ametlikud karuputke levikuandmed, mille täielikkus sõltub vaatlustest.", _STYLES["karuputk"],
    ),
    "sood": LayerSource(
        "sood", "flood_wetlands", "Sood", "Keskkonnaagentuur",
        "EELIS: sood", "Registrisse kantud soo- ja märgalad.", _STYLES["sood"],
    ),
    "natura_elupaik": LayerSource(
        "natura_elupaik", "species_habitats", "Natura elupaigad", "Keskkonnaagentuur",
        "EELIS: Natura elupaigad", "Natura elupaikade inventuuriandmed, mitte eraldiseisev tegevusluba või -keeld.", _STYLES["natura_elupaik"],
    ),
    "lageraiealad": LayerSource(
        "lageraiealad", "archival_clearcuts", "Lageraietuvastus 2011–2016", "Keskkonnaagentuur",
        "Keskkonnaagentuuri Veeveeb: lageraiealade tuvastus", "Arhiivne satelliidituvastus perioodist 2011–2016, mitte tänase metsaseisundi kinnitus.", _STYLES["lageraiealad"],
    ),
    "malestised": LayerSource(
        "malestised", "heritage_other", "Mälestised", "Muinsuskaitseamet",
        "Kultuurimälestiste register: mälestised", "Registrisse kantud mälestised; tegevuse tingimused sõltuvad objekti liigist.", _STYLES["malestised"],
    ),
    "veekogud": LayerSource(
        "veekogud", "water_restrictions", "Avalikud järved", "Keskkonnaagentuur",
        "EELIS: avalikud järved", "Avalike järvede geomeetria; piirangud on eraldi allikates.", _STYLES["veekogud"],
    ),
    "vooluveed": LayerSource(
        "vooluveed", "water_restrictions", "Avalikud vooluveekogud", "Keskkonnaagentuur",
        "EELIS: avalikud vooluveekogud", "Avalike vooluveekogude geomeetria; piirangud on eraldi allikates.", _STYLES["vooluveed"],
    ),
    "piirangukeelualad": LayerSource(
        "piirangukeelualad", "nature_protection", "Piirangu- ja keelualad", "Maa- ja Ruumiamet",
        "Maa- ja Ruumiamet: KPOIS piirangu- ja keelualad", "Ametlikud piirangu- ja keelualad; kattuvad eri tähendusega vööndid jäävad eraldi.", _STYLES["piirangukeelualad"],
    ),
    "kaitsevoondid": LayerSource(
        "kaitsevoondid", "heritage_other", "Mälestiste kaitsevööndid", "Muinsuskaitseamet",
        "Kultuurimälestiste register: kaitsevööndid", "Mälestiste kaitsevööndid, mida ei ühendata kaitstava objektiga üheks kirjeks.", _STYLES["kaitsevoondid"],
    ),
    "uleujutus": LayerSource(
        "uleujutus", "flood_wetlands", "Korduv üleujutusala", "Maa- ja Ruumiamet",
        "Kitsenduste kaart: korduv üleujutusala", "Ametlik kitsenduse ulatus, mitte konkreetse sündmuse või tõenäosuse prognoos.", _STYLES["uleujutus"],
    ),
    "veekaitse": LayerSource(
        "veekaitse", "water_restrictions", "Ranna või kalda veekaitsevöönd", "Maa- ja Ruumiamet",
        "Kitsenduste kaart: ranna või kalda veekaitsevöönd", "Veekaitsevöönd, mida ei ühendata sama veekogu teiste vöönditega.", _STYLES["veekaitse"],
    ),
    "ranna_piirang": LayerSource(
        "ranna_piirang", "water_restrictions", "Ranna või kalda piiranguvöönd", "Maa- ja Ruumiamet",
        "Kitsenduste kaart: ranna või kalda piiranguvöönd", "Piiranguvöönd, mida ei ühendata sama veekogu teiste vöönditega.", _STYLES["ranna_piirang"],
    ),
    "vaetiste_keeld": LayerSource(
        "vaetiste_keeld", "water_restrictions", "Väetiste ja taimekaitsevahendite kasutamise keeld", "Maa- ja Ruumiamet",
        "Kitsenduste kaart: väetiste ja taimekaitsevahendite kasutamise keeld", "Veekaitsega seotud kasutuskeeld; õiguslikke tingimusi tuleb kontrollida ametlikust allikast.", None,
    ),
    "kma_kitsendused": LayerSource(
        "kma_kitsendused", None, "KOTKAS kitsenduste koondkiht", "Maa- ja Ruumiamet",
        "Kitsenduste kaart: KOTKAS kitsendused", "Tehniline koondallikas, mille duplikaadid eemaldatakse ainult ametliku ID ja koodi alusel.", _STYLES["kma_kitsendused"], True,
    ),
    "katsealad": LayerSource(
        "katsealad", "heritage_other", "AdaptEST tegevuspiirangute alad", "Keskkonnaagentuur",
        "Metsaregister: AdaptEST tegevuspiirangute alad", "AdaptEST-i tegevuspiirangute mudelkiht, mitte kaitstava loodusobjekti register.", None,
    ),
})


THEME_REGISTRY: Mapping[str, ThemeDefinition] = MappingProxyType({
    "nature_protection": ThemeDefinition("nature_protection", "Looduskaitse", ("kaitsealad", "piirang", "piirangukeelualad")),
    "species_habitats": ThemeDefinition("species_habitats", "Liigid ja elupaigad", ("natura_elupaik",)),
    "water_restrictions": ThemeDefinition("water_restrictions", "Vesi ja kaldapiirangud", ("veekogud", "vooluveed", "veekaitse", "ranna_piirang", "vaetiste_keeld")),
    "heritage_other": ThemeDefinition(
        "heritage_other",
        "Muinsuskaitse ja muud tegevuspiirangud",
        ("malestised", "kaitsevoondid", "katsealad", "kma_kitsendused"),
    ),
    "flood_wetlands": ThemeDefinition("flood_wetlands", "Üleujutus ja märgalad", ("sood", "uleujutus")),
    "forest_health": ThemeDefinition("forest_health", "Metsatervise riskid", ("yrask_eelis", "yrask_mke")),
    "invasive_species": ThemeDefinition("invasive_species", "Võõrliigid", ("karuputk",)),
    "archival_clearcuts": ThemeDefinition("archival_clearcuts", "Lageraietuvastus 2011–2016", ("lageraiealad",)),
})


KPOIS_SPECIALIZED_KEYS = ("uleujutus", "veekaitse", "ranna_piirang", "vaetiste_keeld")


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
            payload = resp.json()
            features = payload.get("features") if isinstance(payload, dict) else None
            if not isinstance(features, list) or any(not isinstance(feature, dict) for feature in features):
                return key, [], True, False
            return key, features, False, len(features) >= MAX_FEATURES_PER_LAYER
        except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError):
            if attempt + 1 < attempts:
                await asyncio.sleep(0.3 * (2 ** attempt))
                continue
            return key, [], True, False
        except Exception:
            return key, [], True, False
    return key, [], True, False


async def query_layers(
    bbox_str: str,
    layer_keys: Sequence[str],
    source_timeout: float = DEFAULT_SOURCE_TIMEOUT_SECONDS,
) -> tuple[dict[str, list[dict]], list[str], list[str]]:
    """Return selected layer data, failed keys, and potentially truncated keys."""
    configs_by_key = {item[0]: item for item in LAYER_CONFIGS}
    unknown_keys = [key for key in layer_keys if key not in configs_by_key]
    if unknown_keys:
        raise ValueError(f"Unknown layer key(s): {', '.join(unknown_keys)}")

    selected_configs = [configs_by_key[key] for key in layer_keys]
    async with httpx.AsyncClient(timeout=source_timeout) as client:
        tasks = [
            asyncio.wait_for(
                _fetch_layer(client, key, ws, tn, bbox_str),
                timeout=source_timeout,
            )
            for key, ws, tn in selected_configs
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    out = {}
    unavailable = []
    truncated = []
    for config_item, r in zip(selected_configs, results):
        if isinstance(r, Exception):
            key = config_item[0]
            out[key] = []
            unavailable.append(key)
            continue
        key, features, failed, may_be_truncated = r
        out[key] = features
        if failed:
            unavailable.append(key)
        if may_be_truncated:
            truncated.append(key)
    return deduplicate_source_records(out), unavailable, truncated


async def query_all_layers(bbox_str: str) -> tuple[dict[str, list[dict]], list[str], list[str]]:
    """Compatibility wrapper that queries every configured layer."""
    return await query_layers(
        bbox_str,
        [key for key, _workspace, _typename in LAYER_CONFIGS],
    )


def reduce_theme(
    theme_id: str,
    source_features: Mapping[str, Sequence[dict]],
    unavailable_keys: Sequence[str],
    truncated_keys: Sequence[str],
) -> ThemeResult:
    """Reduce parcel-filtered source results into one deterministic theme result."""
    theme = THEME_REGISTRY.get(theme_id)
    if theme is None:
        raise ValueError(f"Unknown theme: {theme_id}")

    unavailable = set(unavailable_keys)
    truncated = set(truncated_keys)
    features = []
    source_states = []
    usable_source_count = 0

    for key in theme.source_keys:
        source_items = tuple(source_features.get(key, ()))
        if key in unavailable:
            source_states.append(SourceState(key, "unavailable", 0))
            continue

        usable_source_count += 1
        features.extend(source_items)
        if key in truncated:
            state = "partial"
        elif source_items:
            state = "matches"
        else:
            state = "empty"
        source_states.append(SourceState(key, state, len(source_items)))

    has_incomplete_source = any(
        source.state in ("partial", "unavailable") for source in source_states
    )
    if usable_source_count == 0:
        state = "unavailable"
    elif has_incomplete_source:
        state = "partial"
    elif features:
        state = "matches"
    else:
        state = "empty"

    return ThemeResult(
        theme_id=theme_id,
        state=state,
        match_count=len(features),
        features=tuple(features),
        source_states=tuple(source_states),
    )


def _kpois_identity(feature: dict) -> tuple[object, str] | None:
    properties = feature.get("properties")
    if not isinstance(properties, dict):
        return None
    official_id = properties.get("id")
    code = properties.get("kood") or properties.get("kma_kood")
    if official_id is None or code is None:
        return None
    normalized_code = str(code).strip().casefold()
    if not normalized_code:
        return None
    return official_id, normalized_code


def _official_feature_id(feature: dict) -> object | None:
    feature_id = feature.get("id")
    if feature_id not in (None, ""):
        try:
            hash(feature_id)
        except TypeError:
            return None
        return feature_id
    properties = feature.get("properties")
    if not isinstance(properties, dict):
        return None
    property_id = properties.get("id")
    if property_id in (None, ""):
        return None
    try:
        hash(property_id)
    except TypeError:
        return None
    return property_id


def deduplicate_source_records(
    source_features: Mapping[str, Sequence[dict]],
) -> dict[str, list[dict]]:
    """Drop only exact repeated records that share an official ID per source."""
    result = {}
    for source_key, features in source_features.items():
        unique = []
        records_by_id: dict[object, list[dict]] = {}
        for feature in features:
            official_id = _official_feature_id(feature)
            if official_id is not None and any(
                feature == previous for previous in records_by_id.get(official_id, ())
            ):
                continue
            unique.append(feature)
            if official_id is not None:
                records_by_id.setdefault(official_id, []).append(feature)
        result[source_key] = unique
    return result


def deduplicate_kpois_sources(
    source_features: Mapping[str, Sequence[dict]],
) -> dict[str, list[dict]]:
    """Remove only umbrella KPOIS records duplicated by specialized sources."""
    specialized_identities = {
        identity
        for key in KPOIS_SPECIALIZED_KEYS
        for feature in source_features.get(key, ())
        if (identity := _kpois_identity(feature)) is not None
    }
    result = {key: list(features) for key, features in source_features.items()}
    if "kma_kitsendused" in result:
        result["kma_kitsendused"] = [
            feature
            for feature in result["kma_kitsendused"]
            if _kpois_identity(feature) not in specialized_identities
        ]
    return result
