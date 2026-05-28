"""Raievanuse indikaator.
Allikas: Metsaseadus §34, Lisa 2 (Metsa majandamise eeskiri)
"""

# Raievanuse tabel: liik → {boniteet → raievanus}
CUTTING_AGE_TABLE = {
    "KU": {0: 80, 1: 80, 2: 80, 3: 70, 4: 70, 5: 65, 6: 61},
    "MA": {0: 100, 1: 100, 2: 95, 3: 85, 4: 81, 5: 75, 6: 71},
    "KS": {0: 65, 1: 65, 2: 65, 3: 60, 4: 55, 5: 55, 6: 51},
    "HB": {0: 60, 1: 60, 2: 60, 3: 55, 4: 55, 5: 51, 6: 51},
    "LM": {0: 50, 1: 50, 2: 50, 3: 45, 4: 45, 5: 41, 6: 41},
    "LV": {0: 50, 1: 50, 2: 50, 3: 45, 4: 45, 5: 41, 6: 41},
    "LH": {0: 100, 1: 100, 2: 95, 3: 85, 4: 81, 5: 75, 6: 71},
    "TA": {0: 120, 1: 120, 2: 115, 3: 105, 4: 101, 5: 95, 6: 91},
    "SA": {0: 80, 1: 80, 2: 80, 3: 70, 4: 70, 5: 65, 6: 61},
    "VA": {0: 65, 1: 65, 2: 65, 3: 60, 4: 55, 5: 55, 6: 51},
}


def cutting_age_indicator(keskm_vanus: int, peapuuliik_kood: str, boniteedi_kood: int, keskm_raievanus: float | None = None) -> dict:
    """Raievanuse indikaator: roheline/kollane/punane."""
    if keskm_raievanus and keskm_raievanus > 0:
        raievanus = keskm_raievanus
    else:
        table = CUTTING_AGE_TABLE.get(peapuuliik_kood, CUTTING_AGE_TABLE["MA"])
        raievanus = table.get(boniteedi_kood, 80)

    ratio = keskm_vanus / raievanus if raievanus > 0 else 0

    if ratio < 0.85:
        return {"status": "green", "label": "Harvendusraie", "ratio": round(ratio, 2), "raievanus": raievanus}
    elif ratio < 1.0:
        return {"status": "yellow", "label": "Läheneb raievanusele", "ratio": round(ratio, 2), "raievanus": raievanus}
    else:
        return {"status": "red", "label": "Lageraieõigus", "ratio": round(ratio, 2), "raievanus": raievanus}
