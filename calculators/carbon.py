SPECIES_DATA = {
    "MA": {"density": 0.51, "bef": 1.34, "root_shoot": 0.26},
    "KU": {"density": 0.46, "bef": 1.42, "root_shoot": 0.29},
    "KS": {"density": 0.56, "bef": 1.30, "root_shoot": 0.24},
    "HB": {"density": 0.45, "bef": 1.40, "root_shoot": 0.24},
    "LH": {"density": 0.59, "bef": 1.25, "root_shoot": 0.20},
    "LM": {"density": 0.47, "bef": 1.38, "root_shoot": 0.27},
    "LV": {"density": 0.47, "bef": 1.38, "root_shoot": 0.27},
    "TA": {"density": 0.63, "bef": 1.30, "root_shoot": 0.24},
    "SA": {"density": 0.59, "bef": 1.32, "root_shoot": 0.22},
    "VA": {"density": 0.57, "bef": 1.35, "root_shoot": 0.22},
    "PK": {"density": 0.59, "bef": 1.30, "root_shoot": 0.22},
    "JA": {"density": 0.55, "bef": 1.32, "root_shoot": 0.23},
    "RE": {"density": 0.50, "bef": 1.35, "root_shoot": 0.25},
    "SP": {"density": 0.50, "bef": 1.35, "root_shoot": 0.25},
}

CARBON_FRACTION = 0.47
CO2_C_RATIO = 3.67
CO2_PRICE_EUR = 20  # Vabatahtlik süsinikuturg (VCM), metsakrediitide hind ~10-30 EUR/t
# Average car emits ~4.6 t CO2/year (EU average passenger car)
CO2_PER_CAR_YEAR = 4.6
# A mature tree absorbs ~22 kg CO2/year
CO2_PER_TREE_KG = 22


def carbon_potential(tagavara_y_ha: float, pindala_ha: float, peapuuliik_kood: str) -> dict:
    sp = SPECIES_DATA.get(peapuuliik_kood, SPECIES_DATA["MA"])
    biomass_ha = tagavara_y_ha * sp["density"] * sp["bef"] * (1 + sp["root_shoot"])
    carbon_ha = biomass_ha * CARBON_FRACTION
    co2_ha = carbon_ha * CO2_C_RATIO
    co2_total = co2_ha * pindala_ha

    # Equivalency calculations
    cars_equivalent = round(co2_total / CO2_PER_CAR_YEAR)
    trees_equivalent = round(co2_total * 1000 / CO2_PER_TREE_KG)  # tons to kg

    return {
        "biomass_tons_ha": round(biomass_ha, 1),
        "carbon_tons_ha": round(carbon_ha, 1),
        "co2_tons_ha": round(co2_ha, 1),
        "co2_tons_total": round(co2_total, 1),
        "potential_income_eur": round(co2_total * CO2_PRICE_EUR),
        "cars_equivalent": cars_equivalent,
        "trees_equivalent": trees_equivalent,
    }
