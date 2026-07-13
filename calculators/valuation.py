"""Transparent, range-based forest valuation helpers."""

from __future__ import annotations


PUBLISHED_STUMPAGE_RANGES = {
    "MA": (76.1, 81.1),
    "KU": (79.6, 84.6),
    "KS": (70.5, 75.5),
    "HB": (37.6, 42.6),
    "LM": (38.6, 43.6),
    "LV": (18.6, 23.6),
}

# Secondary species are absent from the current Erametsaliit table. Retain
# conservative historical midpoints, but expose their weaker provenance and a
# wider range instead of silently substituting pine prices.
ESTIMATED_STUMPAGE_BASE = {
    "LH": 82.0,
    "TA": 55.0,
    "SA": 48.0,
    "VA": 35.0,
    "PK": 48.0,
    "JA": 40.0,
    "RE": 30.0,
    "SP": 42.0,
}

FIREWOOD_FALLBACK = (10.6, 15.6)


def _price_range(species_code: str | None) -> tuple[float, float, str]:
    code = (species_code or "").upper()
    if code in PUBLISHED_STUMPAGE_RANGES:
        low, high = PUBLISHED_STUMPAGE_RANGES[code]
        return low, high, "published"
    if code in ESTIMATED_STUMPAGE_BASE:
        base = ESTIMATED_STUMPAGE_BASE[code]
        return base * 0.75, base * 1.25, "estimated"
    return FIREWOOD_FALLBACK[0], FIREWOOD_FALLBACK[1], "fallback"


def calculate_stand_value(
    species_code: str | None,
    stock_per_ha: float,
    area_ha: float,
    elements: list[dict] | None = None,
) -> dict:
    """Estimate standing timber from live stock and species price ranges."""
    stock = max(float(stock_per_ha or 0), 0)
    area = max(float(area_ha or 0), 0)
    usable_elements = [
        item for item in (elements or [])
        if float(item.get("tagavara_y_ha") or 0) > 0
    ]

    weighted = []
    composition_used = bool(usable_elements)
    composition_coverage = 0.0
    if composition_used and stock > 0:
        element_total = sum(float(item.get("tagavara_y_ha") or 0) for item in usable_elements)
        scale = min(1.0, stock / element_total)
        for item in usable_elements:
            component_stock = float(item.get("tagavara_y_ha") or 0) * scale
            low, high, quality = _price_range(item.get("puuliik_kood"))
            weighted.append((component_stock, low, high, quality))
        known_stock = sum(component_stock for component_stock, _, _, _ in weighted)
        missing_stock = max(stock - known_stock, 0)
        if missing_stock > max(stock * 0.02, 0.1):
            weighted.append((missing_stock, FIREWOOD_FALLBACK[0], FIREWOOD_FALLBACK[1], "fallback"))
        composition_coverage = min(element_total / stock, 1.0)
    else:
        low, high, quality = _price_range(species_code)
        weighted.append((stock, low, high, quality))

    divisor = stock or 1
    low_price = sum(component_stock * low for component_stock, low, _, _ in weighted) / divisor
    high_price = sum(component_stock * high for component_stock, _, high, _ in weighted) / divisor
    base_price = (low_price + high_price) / 2
    volume = stock * area
    qualities = {quality for _, _, _, quality in weighted}
    if "fallback" in qualities:
        source_quality = "fallback"
    elif "estimated" in qualities:
        source_quality = "estimated"
    else:
        source_quality = "published"
    total_base_value = sum(component_stock * ((low + high) / 2) for component_stock, low, high, _ in weighted)
    estimated_base_value = sum(
        component_stock * ((low + high) / 2)
        for component_stock, low, high, quality in weighted
        if quality != "published"
    )

    return {
        "low_eur": round(volume * low_price),
        "base_eur": round(volume * base_price),
        "high_eur": round(volume * high_price),
        "low_price_m3": round(low_price, 2),
        "base_price_m3": round(base_price, 2),
        "high_price_m3": round(high_price, 2),
        "volume_m3": round(volume, 2),
        "composition_used": composition_used,
        "composition_coverage": round(composition_coverage, 4),
        "price_source_quality": source_quality,
        "estimated_value_share": round(estimated_base_value / total_base_value, 4) if total_base_value else 0,
    }


def valuation_reliability(
    inventory: dict | None,
    composition_coverage: float,
    estimated_price_share: float,
    post_inventory_notices: int,
    details_complete: bool,
    post_inventory_volume_ratio: float = 0,
    notices_complete: bool = True,
) -> dict:
    """Score data reliability separately from the monetary estimate."""
    inventory = inventory or {}
    age = inventory.get("inventuuri_vanus_max_a", inventory.get("vanim_inventuur_a"))
    score = 90
    reasons = []
    low_factor, high_factor = 1.0, 1.0

    if age is None:
        score -= 40
        low_factor, high_factor = 0.7, 1.3
        reasons.append("Inventuuri kuupäev puudub")
    elif age <= 3:
        reasons.append(f"Inventuuri vanus kuni {age} a")
    elif age <= 5:
        score -= 10
        low_factor, high_factor = 0.9, 1.1
        reasons.append(f"Inventuur on {age} a vana")
    elif age <= 10:
        score -= 25
        low_factor, high_factor = 0.8, 1.2
        reasons.append(f"Inventuur on {age} a vana; rahaline hinnang vajab kontrolli")
    else:
        score -= 50
        low_factor, high_factor = 0.7, 1.3
        reasons.append(f"Inventuur on {age} a vana ja ületab 10 a registripiiri")

    missing_inventory_dates = int(inventory.get("kuupaev_puudub_eraldisi") or 0)
    missing_registration_dates = int(inventory.get("registrikande_kuupaev_puudub_eraldisi") or 0)
    if missing_inventory_dates or missing_registration_dates:
        score -= 30
        low_factor = min(low_factor, 0.7)
        high_factor = max(high_factor, 1.3)
        reasons.append(
            f"Kuupäev puudub {missing_inventory_dates} inventuuril ja "
            f"{missing_registration_dates} registrikandel"
        )

    if composition_coverage < 0.5:
        score -= 15
        reasons.append("Liigilise koosseisu detailandmed on puudulikud")
    elif composition_coverage < 1:
        score -= 7
        reasons.append("Liigilise koosseisu detailandmed on osalised")
    else:
        reasons.append("Liigiline koosseis on eraldiste kaupa hinnatud")

    if estimated_price_share > 0.2:
        score -= 12
        reasons.append("Osa puuliike kasutab laiemat hinnangulist hinnavahemikku")
    if post_inventory_notices:
        score -= 20
        reasons.append(f"Pärast inventuuri on {post_inventory_notices} teatist")
        low_factor = min(low_factor, 0.4 if post_inventory_volume_ratio >= 0.8 else 0.7)
    if not details_complete:
        score -= 15
        reasons.append("Mõni Metsaregistri detailallikas ei vastanud")
    if not notices_complete:
        score -= 25
        low_factor = min(low_factor, 0.7)
        high_factor = max(high_factor, 1.3)
        reasons.append("Metsateatiste allikas ei vastanud; inventuurijärgset raiet ei saanud kontrollida")

    score = max(0, min(100, score))
    level = "kõrge" if score >= 75 else "keskmine" if score >= 50 else "madal"
    return {
        "score": score,
        "level": level,
        "reasons": reasons,
        "range_low_factor": low_factor,
        "range_high_factor": high_factor,
    }


def calculate_property_estimate(land_tax_value: float | None, timber: dict) -> dict:
    """Combine a land-tax reference with timber while exposing weak evidence."""
    if land_tax_value is None or float(land_tax_value) <= 0:
        return {
            "low_eur": None,
            "base_eur": None,
            "high_eur": None,
            "land_reference_eur": None,
            "land_low_eur": None,
            "land_high_eur": None,
            "land_reference_available": False,
            "land_method": "unavailable",
            "has_transaction_comparables": False,
        }
    land = max(float(land_tax_value or 0), 0)
    land_low = round(land * 0.7)
    land_high = round(land * 1.3)
    return {
        "low_eur": land_low + round(timber.get("low_eur", 0)),
        "base_eur": round(land) + round(timber.get("base_eur", 0)),
        "high_eur": land_high + round(timber.get("high_eur", 0)),
        "land_reference_eur": round(land),
        "land_low_eur": land_low,
        "land_high_eur": land_high,
        "land_reference_available": True,
        "land_method": "tax_value_sensitivity",
        "has_transaction_comparables": False,
    }
