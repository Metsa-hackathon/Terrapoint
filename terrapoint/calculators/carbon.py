"""Süsiniku kalkulaator (IPCC 2006 Tier 1).
Allikas: IPCC 2006 Guidelines Vol.4 Ch.4
"""

# IPCC tegurid
WOOD_DENSITY = {
    "MA": 0.42, "KU": 0.37, "KS": 0.49, "HB": 0.38,
    "LM": 0.42, "LV": 0.42, "LH": 0.45, "TA": 0.52,
    "SA": 0.49, "VA": 0.47,
}
BEF = {
    "MA": 1.3, "KU": 1.4, "KS": 1.5, "HB": 1.4,
    "LM": 1.4, "LV": 1.4, "LH": 1.3, "TA": 1.4,
    "SA": 1.4, "VA": 1.5,
}
ROOT_SHOOT = {
    "MA": 0.24, "KU": 0.22, "KS": 0.26, "HB": 0.24,
    "LM": 0.24, "LV": 0.24, "LH": 0.24, "TA": 0.28,
    "SA": 0.26, "VA": 0.26,
}
CARBON_FRACTION = 0.47
CO2_C_RATIO = 3.67  # 44/12
CO2_PRICE_EUR = 30  # €/tonn


def carbon_potential(tagavara_y_ha: float, pindala_ha: float, peapuuliik_kood: str) -> dict:
    """Süsiniku potentsiaal tonnides CO2 ekvivalenti."""
    d = WOOD_DENSITY.get(peapuuliik_kood, 0.40)
    bef = BEF.get(peapuuliik_kood, 1.4)
    rs = ROOT_SHOOT.get(peapuuliik_kood, 0.24)

    above_biomass = tagavara_y_ha * d * bef
    total_biomass = above_biomass * (1 + rs)
    carbon = total_biomass * CARBON_FRACTION
    co2_ha = carbon * CO2_C_RATIO
    co2_total = co2_ha * pindala_ha

    return {
        "biomass_tons_ha": round(above_biomass, 1),
        "total_biomass_tons_ha": round(total_biomass, 1),
        "carbon_tons_ha": round(carbon, 1),
        "co2_tons_ha": round(co2_ha, 1),
        "co2_tons_total": round(co2_total, 1),
        "potential_income_eur": round(co2_total * CO2_PRICE_EUR, 2),
    }
