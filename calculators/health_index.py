"""Explainable remote forest-risk signal helpers."""

from __future__ import annotations


def spruce_context(stands: list[dict], elements_by_stand: list[list[dict]]) -> dict:
    spruce_ages = []
    for stand in stands:
        if stand.get("puuliik_kood") == "KU":
            spruce_ages.append(int(stand.get("vanus") or 0))
    for elements in elements_by_stand:
        for element in elements or []:
            if element.get("puuliik_kood") == "KU" and float(element.get("tagavara_y_ha") or 0) > 0:
                spruce_ages.append(int(element.get("vanus") or 0))
    return {
        "has_spruce": bool(spruce_ages),
        "max_spruce_age": max(spruce_ages, default=0),
    }


def calculate_beetle_risk(
    has_spruce: bool,
    max_spruce_age: int,
    in_mke_zone: bool,
    has_eelis_observation: bool,
) -> dict:
    if not has_spruce:
        return {
            "score": 0,
            "label": "Madal — kuuske ei tuvastatud",
            "official_zone": False,
            "detail": "Kuuske ei tuvastatud; kihikattuvus üksi ei tõesta puistu üraskikahjustust.",
        }
    if in_mke_zone:
        score, label = 3, "Kriitiline — MKE kattuvus"
    elif has_eelis_observation or max_spruce_age > 50:
        score, label = 2, "Kõrge — vaatlus või vana kuusk"
    elif max_spruce_age > 30:
        score, label = 1, "Keskmine — kuusk üle 30 a"
    else:
        score, label = 0, "Madal"
    return {
        "score": score,
        "label": label,
        "official_zone": bool(in_mke_zone),
        "detail": f"Kuuse suurim vanus {max_spruce_age} a.",
    }


def calculate_legacy_health_index(
    stands: list[dict],
    beetle_score: int,
    damage_count: int,
    has_hogweed: bool,
) -> int:
    """Preserve the v1 public API score while clients migrate to v2."""
    health = 100
    total_area = sum(float(stand.get("pindala_ha") or 0) for stand in stands)
    average_age = (
        sum(float(stand.get("vanus") or 0) * float(stand.get("pindala_ha") or 0) for stand in stands)
        / max(total_area, 1)
    )
    if average_age < 20:
        health -= 10
    elif average_age > 100:
        health -= 8
    elif average_age > 80:
        health -= 5
    health -= max(0, min(int(beetle_score or 0), 3)) * 8
    health -= min(max(int(damage_count or 0), 0) * 5, 20)
    if has_hogweed:
        health -= 10
    species = {stand.get("puuliik_kood") for stand in stands if stand.get("puuliik_kood")}
    if len(species) == 1:
        health -= 5
    elif len(species) >= 3:
        health += 5
    if stands and not any(stand.get("kuivendatud") for stand in stands):
        health += 3
    return max(0, min(100, health))


def _health_confidence(inventory: dict, details_complete: bool, risk_layers_complete: bool) -> dict:
    # Remote/register assessment cannot replace field inspection, so confidence
    # is deliberately capped at 80 even when every source responds.
    score = 80
    reasons = ["Kaug- ja registriandmed; kohapealset ülevaatust ei ole"]
    age = inventory.get("inventuuri_vanus_max_a", inventory.get("vanim_inventuur_a"))
    if age is None:
        score -= 30
        reasons.append("Inventuuri vanus teadmata")
    elif age > 10:
        score -= 40
        reasons.append(f"Inventuur on {age} a vana")
    elif age > 5:
        score -= 20
        reasons.append(f"Inventuur on {age} a vana")
    elif age > 3:
        score -= 10
        reasons.append(f"Inventuur on {age} a vana")
    else:
        reasons.append(f"Inventuur on kuni {age} a vana")
    missing_inventory_dates = int(inventory.get("kuupaev_puudub_eraldisi") or 0)
    missing_registration_dates = int(inventory.get("registrikande_kuupaev_puudub_eraldisi") or 0)
    if missing_inventory_dates or missing_registration_dates:
        score -= 30
        reasons.append(
            f"Kuupäev puudub {missing_inventory_dates} inventuuril ja "
            f"{missing_registration_dates} registrikandel"
        )
    if not details_complete:
        score -= 20
        reasons.append("Metsaregistri liigi- või kahjustusdetailid on osalised")
    if not risk_layers_complete:
        score -= 20
        reasons.append("Kõik riskikihid ei vastanud")
    score = max(0, min(80, score))
    level = "kõrge" if score >= 75 else "keskmine" if score >= 50 else "madal"
    return {"score": score, "level": level, "reasons": reasons}


def calculate_health_assessment(
    beetle_score: int,
    damage_count: int,
    has_hogweed: bool,
    inventory: dict | None,
    details_complete: bool,
    risk_layers_complete: bool,
) -> dict:
    components = []
    beetle_delta = -max(0, min(int(beetle_score or 0), 3)) * 8
    if beetle_delta:
        components.append({"key": "beetle", "label": "Üraskirisk", "delta": beetle_delta})
    damage_delta = -min(max(int(damage_count or 0), 0) * 5, 25)
    if damage_delta:
        components.append({"key": "damage", "label": "Metsaregistri kahjustused", "delta": damage_delta})
    hogweed_delta = -10 if has_hogweed else 0
    if hogweed_delta:
        components.append({"key": "hogweed", "label": "Karuputke kattuvus", "delta": hogweed_delta})

    score = max(0, min(100, 100 + sum(item["delta"] for item in components)))
    label = "Riskisignaale ei tuvastatud" if score >= 90 else "Vajab tähelepanu" if score >= 60 else "Vajab kontrolli"
    return {
        "score": score,
        "label": label,
        "methodology": "Terrapoint remote risk signal v2",
        "components": components,
        "confidence": _health_confidence(inventory or {}, details_complete, risk_layers_complete),
    }
