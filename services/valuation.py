import httpx
from datetime import date

import config
from calculators.timber import timber_value as calc_timber_value


async def get_valuation(kataster_nr: str, tagavara_y_ha: float, pindala_ha: float, peapuuliik_kood: str) -> dict:
    """Get timber valuation. Uses calculator + optional API data."""
    result = calc_timber_value(tagavara_y_ha, pindala_ha, peapuuliik_kood)

    # Try hindamine API (may return 401)
    hindamine = await _query_hindamine(kataster_nr)
    if hindamine:
        result["maa_hind"] = hindamine.get("validValue")
        result["maa_unit_value"] = hindamine.get("unitValue")

    # Try kolvikud API
    kolvikud = await _query_kolvikud(kataster_nr)
    if kolvikud:
        result["metsamaa_ha"] = kolvikud.get("metsamaa_ha")

    return result


async def _query_hindamine(kataster_nr: str) -> dict | None:
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                config.HINDAMINE_API,
                json={"cadastreId": kataster_nr},
                headers={"Content-Type": "application/json"},
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            unit = data.get("data", {}).get("cadastralUnit", {})
            calc = data.get("data", {}).get("calculation", [])
            forest_calc = next((c for c in calc if c.get("usageCode") == "811"), None)
            return {
                "validValue": unit.get("validValue"),
                "unitValue": forest_calc.get("unitValue") if forest_calc else None,
            }
    except Exception:
        return None


async def _query_kolvikud(kataster_nr: str) -> dict | None:
    try:
        today = date.today().isoformat()
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                config.KOLVIKUD_API,
                params={"code": kataster_nr, "date": today},
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            if not data:
                return None
            summary = data[0].get("landParcelSummary", [])
            metsamaa = next((s for s in summary if s.get("type", {}).get("code") == "forest"), None)
            return {
                "metsamaa_ha": metsamaa.get("computedArea", 0) / 10000 if metsamaa else 0,
            }
    except Exception:
        return None
