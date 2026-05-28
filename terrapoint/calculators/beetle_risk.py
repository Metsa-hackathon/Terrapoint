"""Kooreüraski riskiskoor 0-3.
Ainult kuusemetsadel (KU).
"""


def beetle_risk(peapuuliik_kood: str, keskm_vanus: int, kuivendatud: bool = False, taius_1: float = 0, official_zone: bool = False, nearby_damage: bool = False) -> dict:
    """Üraski riskiskoor 0-3."""
    if peapuuliik_kood != "KU":
        return {"score": 0, "label": "Puudub", "official_zone": False}

    if keskm_vanus < 40:
        base_risk = 0
    elif keskm_vanus < 60:
        base_risk = 1
    elif keskm_vanus < 80:
        base_risk = 2
    else:
        base_risk = 3

    # Kuivendamata metsad haavatavamad
    if not kuivendatud:
        base_risk = min(3, base_risk + 1)

    # Tihedus
    if taius_1 > 1.0:
        base_risk = min(3, base_risk + 1)

    # Ametlikud MKE tsoonid
    if official_zone:
        return {"score": 3, "label": "Kõrge (ametlik tsoon)", "official_zone": True}

    # Läheduses kahjustused
    if nearby_damage:
        base_risk = min(3, base_risk + 1)

    base_risk = min(3, base_risk)
    labels = {0: "Madal", 1: "Keskmine", 2: "Kõrge", 3: "Väga kõrge"}

    return {"score": base_risk, "label": labels[base_risk], "official_zone": False}
