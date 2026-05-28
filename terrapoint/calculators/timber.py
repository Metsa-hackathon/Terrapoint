"""Puidu turuväärtuse kalkulaator.
Allikas: erametsaliit.ee/puidu-hinnainfo/ (aprill 2026)
"""

# Hinnad €/m³ seisuhind (erametsaliit.ee, aprill 2026)
PRICES_LOG = {
    "KU": 109.54, "MA": 104.37, "KS": 98.80, "HB": 62.97,
    "LM": 65.00, "LV": 65.00, "LH": 95.00, "TA": 120.00,
    "SA": 110.00, "VA": 85.00,
}
PRICES_PULP = {
    "KU": 53.00, "MA": 53.14, "KS": 53.79, "HB": 44.77,
    "LM": 41.56, "LV": 41.56, "LH": 50.00, "TA": 55.00,
    "SA": 55.00, "VA": 50.00,
}

HARVEST_COST = 18  # €/m³
TRANSPORT_COST = 9  # €/m³


def timber_value(tagavara_y_ha: float, pindala_ha: float, peapuuliik_kood: str) -> dict:
    """Calculate timber market value (seisuhind)."""
    tagavara_total = tagavara_y_ha * pindala_ha
    log_price = PRICES_LOG.get(peapuuliik_kood, 80.0)
    pulp_price = PRICES_PULP.get(peapuuliik_kood, 45.0)

    # 60% palk, 40% paberipuit
    avg_price = log_price * 0.6 + pulp_price * 0.4
    net_price = avg_price - HARVEST_COST - TRANSPORT_COST

    return {
        "tagavara_m3": round(tagavara_total, 1),
        "price_per_m3": round(net_price, 2),
        "log_price": log_price,
        "pulp_price": pulp_price,
        "total_value_eur": round(tagavara_total * net_price, 2),
        "value_per_ha": round(tagavara_y_ha * net_price, 2),
    }
