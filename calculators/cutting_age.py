"""Official renewal-cutting age thresholds by species group and boniteet.

Source: Kliimaministeerium, ``Uuendusraie arvutus``, table 4:
https://kliimaministeerium.ee/media/1034/download

The source has rows only for Scots pine, Norway spruce, birch, aspen,
black alder, and hard broadleaves. It explicitly says that legislation does
not define a maturity age or diameter for grey alder. Therefore species absent
from those rows remain unknown instead of inheriting a look-alike species'
threshold. In the aspen row, classes V and Va are also explicitly blank.

WFS boniteet codes: 0=1A, 1=I, 2=II, 3=III, 4=IV, 5=V, 6=Va.
The source combines V and Va where a value exists.
"""

import math


_HARD_BROADLEAF_AGE = {0: 90, 1: 90, 2: 100, 3: 110, 4: 120, 5: 130, 6: 130}

# Values are years. ``None`` means that table 4 has no age threshold for the
# species group and boniteet; it must not be replaced by a guessed value.
CUTTING_AGE: dict[str, dict[int, int | None]] = {
    "MA": {0: 90, 1: 90, 2: 90, 3: 100, 4: 110, 5: 120, 6: 120},
    "KU": {0: 60, 1: 70, 2: 80, 3: 90, 4: 90, 5: 90, 6: 90},
    "KS": {0: 60, 1: 60, 2: 70, 3: 70, 4: 70, 5: 70, 6: 70},
    "HB": {0: 30, 1: 40, 2: 40, 3: 50, 4: 50, 5: None, 6: None},
    "LM": {0: 60, 1: 60, 2: 60, 3: 60, 4: 60, 5: 60, 6: 60},
    # Official classifier members of the table's "Kõvad lehtpuud" row.
    "TA": dict(_HARD_BROADLEAF_AGE),
    "SA": dict(_HARD_BROADLEAF_AGE),
    "VA": dict(_HARD_BROADLEAF_AGE),
    "JA": dict(_HARD_BROADLEAF_AGE),
    "KP": dict(_HARD_BROADLEAF_AGE),
}


def _finite_number(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _unknown_result(label: str, cutting_age=None, cutting_age_provenance=None) -> dict:
    return {
        "raievanus": cutting_age,
        "raievanus_provenance": cutting_age_provenance,
        "ratio": 0,
        "status": "unknown",
        "label": label,
        "age_class": "unknown",
        "age_class_label": "Määramata",
        "age_class_color": "#6b7280",
        "age_class_provenance": "Terrapointi tuletis",
    }


def cutting_age_indicator(
    vanus: int | float | None,
    puuliik_kood: str,
    boniteedi_kood: int | None,
    source_cutting_age: int | float | None = None,
) -> dict:
    """Calculate a neutral age class against a register or table threshold.

    ``source_cutting_age`` is Metsaregister's stand-specific
    ``keskm_raievanus`` and takes precedence over the generic table because it
    can reflect the registered stand composition. The resulting age class is
    still a Terrapoint derivation and is not a harvesting recommendation.
    """
    official_age = _finite_number(source_cutting_age)
    if official_age is not None and official_age > 0:
        cutting_age = official_age
        cutting_age_provenance = "Metsaregister"
    else:
        species = CUTTING_AGE.get(puuliik_kood)
        if species is None:
            return _unknown_result("Raievanus pole selle klassifikaatori kirje jaoks määratud")
        if boniteedi_kood not in species:
            return _unknown_result("Puistu boniteet pole määratud")
        cutting_age = species[boniteedi_kood]
        cutting_age_provenance = "Kliimaministeeriumi tabel 4"
        if cutting_age is None:
            return _unknown_result(
                "Selle liigi ja boniteedi jaoks pole vanusepiiri määratud",
                cutting_age_provenance=cutting_age_provenance,
            )

    stand_age = _finite_number(vanus)
    public_cutting_age = int(cutting_age) if float(cutting_age).is_integer() else cutting_age
    if stand_age is None or stand_age < 0:
        return _unknown_result(
            "Puistu vanus pole määratud",
            public_cutting_age,
            cutting_age_provenance,
        )

    ratio = stand_age / cutting_age
    if ratio < 0.85:
        status, label = "green", "Alla raievanuse"
    elif ratio < 1.0:
        status, label = "yellow", "Läheneb raievanusele"
    else:
        status, label = "red", "Raievanus saavutatud"
    if ratio < 0.50:
        age_class, age_class_label, age_class_color = "young", "Noor", "#7aa6c2"
    elif ratio < 0.85:
        age_class, age_class_label, age_class_color = "middle_aged", "Keskealine", "#4f7c9b"
    elif ratio < 1.0:
        age_class, age_class_label, age_class_color = "maturing", "Valmiv", "#756b9e"
    else:
        age_class, age_class_label, age_class_color = "cutting_age_reached", "Raievanus saavutatud", "#5b536b"
    return {
        "status": status,
        "label": label,
        "ratio": round(ratio, 2),
        "raievanus": public_cutting_age,
        "raievanus_provenance": cutting_age_provenance,
        "age_class": age_class,
        "age_class_label": age_class_label,
        "age_class_color": age_class_color,
        "age_class_provenance": "Terrapointi tuletis",
    }
