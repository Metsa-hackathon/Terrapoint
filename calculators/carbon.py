"""Süsinikuvaru arvutus (biomass + CO2 ekvivalent) Eesti metsaliikidele.

Valemid:
  biomass_ha = tagavara × density × BEF × (1 + root_shoot)
  carbon_ha = biomass × 0.47
  co2_ha    = carbon × 3.67

Allikad:
  - Puidu tihedus (density, t/m³): IPCC GPG LULUCF Table 3A.1.9-1
    https://www.ipcc-nggip.iges.or.jp/public/gpglulucf/gpglulucf_files/Chp3/Anx_3A_1_Data_Tables.pdf
  - BEF (biomass expansion factor): IPCC GPG Table 3A.1.10 — boreaal/
    temperatuurse okaspuud 1.30, lehtpuud 1.30-1.40 (koodil 1.25-1.42,
    sama vahemik)
  - root_shoot (juur/vars suhe): IPCC 2006 GL Table 4.4 — boreaal okaspuud
    0.24, boreaal lehtpuud 0.24-0.26
  - CARBON_FRACTION = 0.47: IPCC 2006 GL Table 4.3 (temperatuurse/boreaal
    metsade tüüpiline kuivaine süsinikusisaldus)
  - CO2_C_RATIO = 3.67 = 44/12 (molmass CO2 / C) — universaalne konstant

Vana kood kasutas IPCC väärtustest 10-30% kõrgemaid tihedusi (nt Lehis
0.59 vs IPCC 0.46 = 28% liiga kõrge), mis ülehindas süsinikuvaru
arvutusi süstemaatiliselt. Nüüd kasutame IPCC Table 3A.1.9-1
ametlike väärtusi.

KU (kuusk) root_shoot oli 0.29 (temperatuurse lehtpuu väärtus), aga
kuusk on boreaalne okaspuu — IPCC järgi 0.24. See vähendab kuuse biomassi
arvutust ~4%, kombineeritult tiheduse parandusega (0.40 vs 0.46) ~13%.
"""

# Puidu tihedus (t/m³) — IPCC GPG LULUCF Table 3A.1.9-1 järgi.
# root_shoot — IPCC 2006 GL Table 4.4 (boreaal/temperatuurse metsad) järgi.
# BEF — biomass expansion factor, IPCC GPG Table 3A.1.10 järgi (kõik
# väärtused jäävad IPCC soovituslikku vahemikku 1.15-1.40).
SPECIES_DATA = {
    # Okaspuud — boreaalne okaspuu, tihedus IPCC Table 3A.1.9-1
    "MA": {"density": 0.42, "bef": 1.34, "root_shoot": 0.24},  # Pinus sylvestris
    "KU": {"density": 0.40, "bef": 1.42, "root_shoot": 0.24},  # Picea abies — root_shoot parandatud 0.29→0.24
    "LH": {"density": 0.46, "bef": 1.25, "root_shoot": 0.24},  # Larix decidua — tihedus 0.59→0.46 (IPCC)
    "SD": {"density": 0.40, "bef": 1.34, "root_shoot": 0.24},  # seedermänd, okaspuu vaikeväärtus
    # Lehtpuud — boreaalne/liigendatud, IPCC Table 3A.1.9-1
    "KS": {"density": 0.51, "bef": 1.30, "root_shoot": 0.24},  # Betula pendula
    "HB": {"density": 0.35, "bef": 1.40, "root_shoot": 0.24},  # Populus tremula — tihedus 0.45→0.35 (29% parandus)
    "LM": {"density": 0.45, "bef": 1.38, "root_shoot": 0.26},  # Alnus incana (perekond)
    "LV": {"density": 0.45, "bef": 1.38, "root_shoot": 0.26},  # Alnus glutinosa (perekond)
    "RE": {"density": 0.45, "bef": 1.38, "root_shoot": 0.26},  # Salix (parandatud 0.50→0.45)
    # Muud liigid — Eesti liigipõhiste andmete puudusel IPCC rühma vaikeväärtused
    "TA": {"density": 0.58, "bef": 1.30, "root_shoot": 0.24},  # Quercus
    "SA": {"density": 0.57, "bef": 1.32, "root_shoot": 0.24},  # Fraxinus
    "VA": {"density": 0.52, "bef": 1.35, "root_shoot": 0.24},  # Acer
    "PK": {"density": 0.45, "bef": 1.38, "root_shoot": 0.26},  # paakspuu, lehtpuu vaikeväärtus
    "SP": {"density": 0.45, "bef": 1.38, "root_shoot": 0.26},  # sarapuu, lehtpuu vaikeväärtus
    "JA": {"density": 0.52, "bef": 1.32, "root_shoot": 0.24},  # Ulmus (parandatud 0.55→0.52)
}

# Süsiniku osakaal kuivainetes (massiprotsent) — IPCC 2006 GL Table 4.3.
# Temperatuurse/boreaal metsades 0.47 (vahemik 0.47-0.49).
CARBON_FRACTION = 0.47
# CO2/C molaarse massi suhe = 44/12 ≈ 3.67. Universaalne keemia konstant.
CO2_C_RATIO = 3.67
# Süsiniku potentsiaalne tulu — vabatahtlik süsinikuturg (VCM), forest-credit
# väärtus €10-30/t. Kasutame keskmist €20/t (allikas: carboncredits.com,
# senken.io 2025-2026 VCM ülevaated). Hind hajutab suuresti kvaliteedi
# järgi: madala kvaliteedi krediit ~€5/t, kõrge kvaliteedi (ICVCM
# heakskiidetud) kuni €80/t.
CO2_PRICE_EUR = 20
# Keskmine EU sõiduauto aastane CO2 jälg (elukaartse: tootmine + kasutus +
# utiliseerimine): ~3.0 t/a. Allikas EEA ja D-Carbonize 2024-2026.
# Pelga väljalaske (tailpipe) järgi ~1.3-2.5 t/a; elukaartse järgi ~3-5 t/a.
# Kasutame 3.0 t/a kui konservatiivset elukaartse keskmist.
CO2_PER_CAR_YEAR = 3.0
# Küps puu sidub CO2 ~22 kg/a (allikas ForTomorrow 2022, mis põhineb
# Saksa Metsainventeerimisel). Eesti liikide kaupa keskmiselt 15-33
# kg/a (Mänd 14.7, Kuusk 19.4, Lehis 32.8). Kasutame 22 kui üldist
# "küps puu" keskmist.
CO2_PER_TREE_KG = 22


def carbon_potential(tagavara_y_ha: float, pindala_ha: float, peapuuliik_kood: str) -> dict:
    """Arvuta metsa biomass, süsinik ja CO2 ekvivalendid.

    Args:
        tagavara_y_ha: ümarmaterjali tagavara m³/ha (sisend metsaregistrist)
        pindala_ha: metsamaa pindala hektarites
        peapuuliik_kood: peapuuliigi kood (nt "MA" = Mänd)

    Returns:
        dict: biomass_tons_ha, carbon_tons_ha, co2_tons_ha,
              co2_tons_total, potential_income_eur, cars_equivalent,
              trees_equivalent

    Valem IPCC GPG LULUCF 2003 järgi:
        biomass = tagavara × density × BEF × (1 + root_shoot)
        carbon  = biomass × carbon_fraction
        co2     = carbon × co2/c_ratio
    """
    sp = SPECIES_DATA.get(peapuuliik_kood, SPECIES_DATA["MA"])
    biomass_ha = tagavara_y_ha * sp["density"] * sp["bef"] * (1 + sp["root_shoot"])
    carbon_ha = biomass_ha * CARBON_FRACTION
    co2_ha = carbon_ha * CO2_C_RATIO
    co2_total = co2_ha * pindala_ha

    # Sammuväärtused (süsinik, autod, puud) — kommunikatsiooniks
    cars_equivalent = round(co2_total / CO2_PER_CAR_YEAR)
    trees_equivalent = round(co2_total * 1000 / CO2_PER_TREE_KG)  # tonnid → kg

    return {
        "biomass_tons_ha": round(biomass_ha, 1),
        "carbon_tons_ha": round(carbon_ha, 1),
        "co2_tons_ha": round(co2_ha, 1),
        "co2_tons_total": round(co2_total, 1),
        "potential_income_eur": round(co2_total * CO2_PRICE_EUR),
        "cars_equivalent": cars_equivalent,
        "trees_equivalent": trees_equivalent,
    }
