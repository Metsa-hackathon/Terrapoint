import math


METSAREGISTER_URL = "https://register.metsad.ee/otsiEraldis"
FOREST_ACT_VALIDITY_URL = "https://www.riigiteataja.ee/akt/109042026002#para11"
FOREST_INVENTORY_ACCURACY_URL = "https://www.riigiteataja.ee/akt/131052024011#para13"
LAND_VALUE_URL = "https://maaruum.ee/maakataster-ja-maa-hindamine/maa-hindamine/maa-korraline-hindamine"
TIMBER_PRICE_URL = "https://erametsaliit.ee/wp-content/uploads/2026/05/puiduhinnad-2026-i-kv.pdf"
FOREST_ASSORTMENT_METHOD_URL = "https://www.riigiteataja.ee/aktilisa/1180/3202/5002/VV_17m_lisa5.pdf"
FOREST_HARVEST_COST_METHOD_URL = "https://www.riigiteataja.ee/aktilisa/1180/3202/5002/VV_17m_lisa7.pdf"


def _finite_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _valid_range(estimate: dict, *, require_base: bool) -> bool:
    low = estimate.get("low_eur")
    base = estimate.get("base_eur")
    high = estimate.get("high_eur")
    if not (_finite_number(low) and _finite_number(high) and low <= high):
        return False
    if base is None:
        return not require_base
    return _finite_number(base) and low <= base <= high


def _inventory_confidence(
    inventory: dict,
    reliability: dict,
    official_stands: int,
    estimated_stands: int,
    unknown_stands: int,
    unavailable_stands: int,
) -> dict:
    status = inventory.get("staatus")
    level = {"värske": "kõrge", "hoiatus": "keskmine", "kriitiline": "madal"}.get(status, "teadmata")
    rank = {"teadmata": 0, "madal": 0, "keskmine": 1, "kõrge": 2, "hea": 2}
    reliability_level = reliability.get("level", "teadmata")
    if rank.get(reliability_level, 0) < rank.get(level, 0):
        level = reliability_level

    if unavailable_stands:
        level = "madal"
        label = "Tagavaraandmed on puudulikud"
    elif estimated_stands and not official_stands and not unknown_stands and not unavailable_stands:
        level = "madal"
        label = "Tagavara on Terrapointi hinnang"
    elif estimated_stands:
        if rank.get(level, 0) > rank["keskmine"]:
            level = "keskmine"
        label = "Tagavara on osaliselt hinnanguline"
    elif unknown_stands:
        if rank.get(level, 0) > rank["keskmine"]:
            level = "keskmine"
        label = "Tagavara päritolu vajab kontrolli"
    else:
        label = {
            "kõrge": "Värske registriinfo",
            "hea": "Värske registriinfo",
            "keskmine": "Kontrolli inventuuri vanust",
            "madal": "Vajab uut inventuuri või kohapealset kontrolli",
            "teadmata": "Andmete vanus vajab kontrolli",
        }.get(level, "Andmete usaldus vajab kontrolli")
    reasons = []
    inventory_age = inventory.get("inventuuri_vanus_max_a")
    if inventory_age is not None:
        reasons.append(f"Vanim inventuur on {inventory_age} täisaastat vana.")
    if estimated_stands:
        reasons.append(f"{estimated_stands} eraldise tagavara on Terrapointi hinnang, sest registri tagavara puudus.")
    if unknown_stands:
        reasons.append(f"{unknown_stands} eraldise tagavara päritolu ei ole vastuses määratud.")
    if unavailable_stands:
        reasons.append(f"{unavailable_stands} eraldise tagavara ega hinnangu jaoks vajalikud lähteandmed ei ole saadaval.")
    for reason in reliability.get("reasons") or []:
        if reason not in reasons:
            reasons.append(reason)
    reasons.append("Metsakorralduse juhendi veapiir ei ole selle kinnistu mõõdetud veavahemik.")
    return {"level": level, "label": label, "reasons": reasons}


def _value_confidence(reliability: dict) -> dict:
    level = reliability.get("level", "teadmata")
    return {
        "level": level,
        "label": {
            "kõrge": "Kõrge lähteandmete usaldus",
            "hea": "Kõrge lähteandmete usaldus",
            "keskmine": "Keskmine lähteandmestik",
            "madal": "Nõrk lähteandmestik",
        }.get(level, "Usaldus vajab kontrolli"),
        "score": reliability.get("score"),
        "reasons": list(reliability.get("reasons") or []),
    }


def build_asset_passports(
    stands: list[dict],
    inventory: dict,
    reliability: dict,
    timber_estimate: dict,
    property_estimate: dict,
    total_volume_m3: float,
) -> list[dict]:
    official_stands = sum(stand.get("tagavara_provenance") == "official" for stand in stands)
    estimated_stands = sum(stand.get("tagavara_provenance") == "estimated" for stand in stands)
    unavailable_stands = sum(stand.get("tagavara_provenance") == "unavailable" for stand in stands)
    unknown_stands = len(stands) - official_stands - estimated_stands - unavailable_stands
    usable_stands = official_stands + estimated_stands + unknown_stands
    if estimated_stands and official_stands:
        volume_provenance = "mixed"
        volume_provenance_label = "Registriandmed + Terrapointi hinnang"
    elif estimated_stands and not official_stands and not unknown_stands and not unavailable_stands:
        volume_provenance = "estimate"
        volume_provenance_label = "Hinnatud Metsaregistri andmete põhjal"
    elif official_stands and not estimated_stands and not unknown_stands and not unavailable_stands:
        volume_provenance = "derived"
        volume_provenance_label = "Arvutatud Metsaregistri andmetest"
    else:
        volume_provenance = "unknown" if not usable_stands else "mixed"
        volume_provenance_label = "Tagavaraandmed puuduvad" if not usable_stands else "Sisendid on osaliselt puudu"

    volume_limitations = [
        "Kasvava metsa tagavara ei ole automaatselt raiutav ega müüdav puidukogus.",
        "Tulemus ei arvesta inventuuri järel toimunud, kuid tõendamata raiet, kasvu ega kahjustust.",
    ]
    if estimated_stands:
        volume_limitations.append(
            f"{estimated_stands} eraldise tagavara on hinnanguline, sest registritagavara puudus."
        )

    volume_source_name = "Metsaregister"
    volume_derivation = "Eraldise elus tagavara m³/ha × pindala; seejärel liidetakse eraldiste tulemused."
    if estimated_stands:
        volume_source_name = "Metsaregistri sisendid ja Terrapointi hinnang"
        volume_derivation += (
            " Puuduva registritagavara korral hindab Terrapoint m³/ha boniteedi ja kõrguse või vanuse järgi."
        )
        volume_limitations.append("Puuduva registritagavara asendamiseks kasutatav kasvutabel on Terrapointi sisemine heuristik.")
    if unavailable_stands:
        volume_limitations.append(
            f"{unavailable_stands} eraldise tagavara ei olnud registris ega seda saanud olemasolevatest andmetest hinnata."
        )

    value_confidence = _value_confidence(reliability)
    land_available = (
        property_estimate.get("land_reference_available") is True
        and _finite_number(property_estimate.get("land_reference_eur"))
    )
    stock_available = usable_stands > 0 and unavailable_stands == 0
    timber_range_available = _valid_range(timber_estimate, require_base=True)
    timber_available = (
        stock_available
        and timber_range_available
    )
    property_available = (
        land_available
        and timber_available
        and _valid_range(property_estimate, require_base=False)
    )
    timber_unavailable_label = (
        "Puidu hinnangut ei saa tagavaraandmeteta arvutada"
        if not stock_available
        else "Puidu hinnavahemiku lähteandmed puuduvad"
    )
    if not land_available and not stock_available:
        property_unavailable_label = "Maa maksustamishind ja puidu tagavaraandmed puuduvad"
    elif not land_available and not timber_available:
        property_unavailable_label = "Maa maksustamishind ja puidu hinnavahemik puuduvad"
    elif not land_available:
        property_unavailable_label = "Maa maksustamishind puudub"
    elif not stock_available:
        property_unavailable_label = "Puidu tagavaraandmed puuduvad"
    elif not timber_available:
        property_unavailable_label = "Puidu hinnavahemiku lähteandmed puuduvad"
    else:
        property_unavailable_label = "Kinnistu hinnavahemiku lähteandmed puuduvad"

    return [
        {
            "id": "forest_volume",
            "label": "Kasvava metsa kogumaht",
            "available": usable_stands > 0 and unavailable_stands == 0,
            "unavailable_label": "Eraldiste tagavara lähteandmed puuduvad",
            "value": round(total_volume_m3) if usable_stands > 0 and unavailable_stands == 0 else None,
            "unit": "m³",
            "provenance": volume_provenance,
            "provenance_label": volume_provenance_label,
            "source": {
                "name": volume_source_name,
                "url": METSAREGISTER_URL,
                "oldest_as_of": inventory.get("vanim_invent_kp"),
                "newest_as_of": inventory.get("uusim_invent_kp"),
            },
            "methodology_sources": [
                {"label": "Inventuuriandmete kehtivus", "url": FOREST_ACT_VALIDITY_URL},
                {"label": "Inventuuri lubatud veapiirid", "url": FOREST_INVENTORY_ACCURACY_URL},
            ],
            "derivation": volume_derivation,
            "confidence": _inventory_confidence(
                inventory,
                reliability,
                official_stands,
                estimated_stands,
                unknown_stands,
                unavailable_stands,
            ),
            "quality": {
                "total_stands": len(stands),
                "official_stands": official_stands,
                "estimated_stands": estimated_stands,
                "unknown_stands": unknown_stands,
                "unavailable_stands": unavailable_stands,
            },
            "limitations": volume_limitations,
            "ai_question": "Selgita selle kinnistu kasvava metsa tagavara, andmete päritolu ja ebakindlust. Ära käsitle tagavara automaatselt raiutava kogusena.",
        },
        {
            "id": "timber_value",
            "label": "Kasvava puidu indikatiivne hinnavahemik",
            "available": timber_available,
            "unavailable_label": timber_unavailable_label,
            "range": {
                "low": timber_estimate.get("low_eur") if timber_available else None,
                "base": timber_estimate.get("base_eur") if timber_available else None,
                "high": timber_estimate.get("high_eur") if timber_available else None,
            },
            "unit": "€",
            "provenance": "estimate",
            "provenance_label": "Arvutuslik hinnavahemik",
            "source": {"name": "Metsaregister ja Eesti Erametsaliit", "url": TIMBER_PRICE_URL, "as_of": "2026-03"},
            "methodology_sources": [
                {"label": "Ametlik sortimenteerimise metoodika", "url": FOREST_ASSORTMENT_METHOD_URL},
                {"label": "Ametlik ülestöötamiskulude metoodika", "url": FOREST_HARVEST_COST_METHOD_URL},
            ],
            "derivation": "Iga eraldise elus tagavara × pindala. Alumine piir kasutab küttepuidu ja ülemine piir avaldatud või hinnangulise liigihinna olemasolul palgi kännuraha; toetamata liigile jääb küttepuidu vahemik. Tegelik sortimendijaotus ei ole registri koondandmetest teada.",
            "confidence": value_confidence,
            "limitations": [
                "Stsenaarium ei ole ostupakkumine ega kutselise hindaja koostatud turuväärtus.",
                "Tegelik sortimendijaotus sõltub puude diameetrist, kõrgusest, kvaliteedist ja kahjustustest.",
                "Realiseeritavat väärtust mõjutavad raievalmidus, piirangud, ligipääs, kokkuveokaugus, töömaht ja müügihetke turg.",
            ] + ([f"{estimated_stands} eraldise tagavara on hinnanguline."] if estimated_stands else [])
              + ([f"{unavailable_stands} eraldise tagavara puudub."] if unavailable_stands else []),
            "ai_question": "Selgita kasvava puidu hinnavahemikku, selle arvutuskäiku ja peamisi ebakindlusi selle kinnistu andmete põhjal.",
        },
        {
            "id": "land_reference",
            "label": "Maa maksustamishind",
            "available": land_available,
            "unavailable_label": "Maa maksustamishind puudub",
            "value": property_estimate.get("land_reference_eur") if land_available else None,
            "unit": "€",
            "provenance": "official",
            "provenance_label": "Maa- ja Ruumiamet",
            "source": {"name": "Maa- ja Ruumiamet", "url": LAND_VALUE_URL},
            "derivation": "Katastriüksuse kehtiv maksustamishind; Terrapoint seda väärtust ümber ei arvuta.",
            "confidence": {"level": "official", "label": "Ametlik referentsväärtus", "reasons": []},
            "limitations": ["Maksustamishind ei ole kinnistu turuhind ega tõenda võimalikku müügihinda."],
            "ai_question": "Selgita selle kinnistu maa maksustamishinna tähendust ja miks see ei ole sama mis turuhind.",
        },
        {
            "id": "property_estimate",
            "label": "Kogu kinnistu indikatiivne hinnavahemik",
            "available": property_available,
            "unavailable_label": property_unavailable_label,
            "range": {
                "low": property_estimate.get("low_eur") if property_available else None,
                "base": property_estimate.get("base_eur") if property_available else None,
                "high": property_estimate.get("high_eur") if property_available else None,
            },
            "unit": "€",
            "provenance": "estimate",
            "provenance_label": "Maa maksustamishind + puidu hinnavahemik",
            "source": {"name": "Metsaregister ja Maa- ja Ruumiamet", "url": LAND_VALUE_URL},
            "derivation": "Kasvava puidu hinnavahemik + maa maksustamishinna ±30% vahemik. See ei ole kinnistu turuhind ega müügihinna prognoos. Keskpunkti ei kuvata, sest tehinguvõrdlusi ei kasutata.",
            "confidence": value_confidence,
            "limitations": [
                "Avalikke võrreldavaid tehinguid selles vahemikus ei kasutata.",
                "Vahemik ei arvesta rahalise koefitsiendina õiguslikku ligipääsu, servituute, piirangute täpset mõju, puidu kvaliteeti ega müügikanali likviidsust.",
                "Vahemik ei arvesta rahalise koefitsiendina ka raievalmidust, ülestöötamise ja transpordi erikulu ega tuvastamata kahjustusi.",
                "Vahemik ei asenda kutselist hindamisakti ega siduvat ostupakkumist.",
            ],
            "ai_question": "Selgita maa ja puidu indikatiivset vahemikku, selle osakaale ning milliseid andmeid tuleks enne müügiotsust kontrollida.",
        },
    ]
