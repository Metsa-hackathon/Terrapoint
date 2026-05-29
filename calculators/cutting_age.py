CUTTING_AGE = {
    "MA": {0: 80, 1: 75, 2: 70, 3: 65, 4: 60, 5: 55, 6: 50},
    "KU": {0: 80, 1: 75, 2: 70, 3: 65, 4: 60, 5: 55, 6: 50},
    "KS": {0: 60, 1: 55, 2: 50, 3: 45, 4: 40, 5: 35, 6: 30},
    "HB": {0: 60, 1: 55, 2: 50, 3: 45, 4: 40, 5: 35, 6: 30},
    "LH": {0: 100, 1: 95, 2: 90, 3: 85, 4: 80, 5: 75, 6: 70},
    "LM": {0: 60, 1: 55, 2: 50, 3: 45, 4: 40, 5: 35, 6: 30},
    "LV": {0: 60, 1: 55, 2: 50, 3: 45, 4: 40, 5: 35, 6: 30},
    "TA": {0: 120, 1: 110, 2: 100, 3: 90, 4: 80, 5: 70, 6: 60},
    "SA": {0: 80, 1: 75, 2: 70, 3: 65, 4: 60, 5: 55, 6: 50},
    "VA": {0: 60, 1: 55, 2: 50, 3: 45, 4: 40, 5: 35, 6: 30},
}


def cutting_age_indicator(vanus: int, puuliik_kood: str, boniteedi_kood: int) -> dict:
    species = CUTTING_AGE.get(puuliik_kood, CUTTING_AGE["MA"])
    raievanus = species.get(boniteedi_kood, 60)
    ratio = vanus / raievanus if raievanus else 0
    if ratio < 0.85:
        status, label = "green", "Hooldusraie"
    elif ratio < 1.0:
        status, label = "yellow", "Läheneb raievanusele"
    else:
        status, label = "red", "Raievanus käes"
    return {"status": status, "label": label, "ratio": round(ratio, 2), "raievanus": raievanus}
