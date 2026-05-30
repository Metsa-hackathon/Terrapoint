import time
import asyncio
import os
import httpx
import orjson
from shapely.geometry import shape
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, HTMLResponse, FileResponse
from contextlib import asynccontextmanager

import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from services.kataster import query_kataster
from services.metsaregister import query_eraldis, query_eraldis_element, query_natura_2000, query_teatised, query_kahjustused
from services.layers import query_all_layers
from services.subsidies import check_subsidies
from calculators.carbon import carbon_potential
from calculators.cutting_age import cutting_age_indicator
from spatial.bbox import calculate_bbox, bbox_to_wfs_string
import config


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(title="Terrapoint", version="2.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def json_response(data: dict, status: int = 200) -> Response:
    return Response(content=orjson.dumps(data), media_type="application/json", status_code=status)


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "2.0.0", "timestamp": time.time()}


@app.get("/api/address/{q:path}")
async def address_search(q: str = ""):
    try:
        if not q or len(q) < 2:
            return json_response({"results": []})

        import urllib.parse
        cql = urllib.parse.quote(f"l_aadress LIKE '%{q}%'")
        url = (
            f"{config.GEOBASE}/kataster/wfs?"
            f"service=WFS&request=GetFeature&typeName=kataster:ky_aadress"
            f"&srsName=EPSG:4326&outputFormat=application/json"
            f"&count=10&CQL_FILTER={cql}"
        )
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            features = resp.json().get("features", [])

        results = []
        for f in features:
            p = f.get("properties", {})
            results.append({
                "aadress": p.get("l_aadress", ""),
                "maakond": p.get("mk_nimi", ""),
                "vald": p.get("ov_nimi", ""),
                "asula": p.get("ay_nimi", ""),
                "katastri_nr": p.get("tunnus", ""),
            })

        return json_response({"results": results})
    except Exception as exc:
        return json_response({"error": str(exc)}, 500)


@app.get("/api/search/{kataster_nr:path}")
async def search(kataster_nr: str, request: Request):
    try:
        return await _search(kataster_nr)
    except Exception as exc:
        import traceback
        return json_response({"error": str(exc), "trace": traceback.format_exc()}, 500)


def _filter_features_by_geometry(features, parcel_geom):
    """Filter WFS features to only those that actually intersect the parcel geometry."""
    if not features or not parcel_geom:
        return features
    try:
        parcel_shape = shape(parcel_geom)
        if not parcel_shape.is_valid:
            parcel_shape = parcel_shape.buffer(0)
        filtered = []
        for f in features:
            try:
                feat_shape = shape(f.get("geometry", {}))
                if feat_shape.intersects(parcel_shape):
                    filtered.append(f)
            except Exception:
                filtered.append(f)  # include if can't parse geometry
        return filtered
    except Exception:
        return features


# Simple in-memory search cache (TTL 5 min) to avoid re-fetching on chat
_search_cache = {}
_SEARCH_CACHE_TTL = 300  # seconds

async def _search(kataster_nr: str):
    # Check cache
    cached = _search_cache.get(kataster_nr)
    if cached and (time.time() - cached["ts"]) < _SEARCH_CACHE_TTL:
        return cached["response"]

    start = time.time()
    MAX_TIME = 8.5  # Vercel Hobby has 10s timeout, leave buffer

    kataster_data = await query_kataster(kataster_nr)
    if not kataster_data:
        return json_response({"error": "Krunti ei leitud"}, 404)

    bbox = calculate_bbox(kataster_data["geometry"])
    bbox_str = bbox_to_wfs_string(bbox)

    eraldis_task = query_eraldis(kataster_nr)
    layers_task = query_all_layers(bbox_str)
    teatised_task = query_teatised(kataster_nr)

    results = await asyncio.gather(
        eraldis_task, layers_task, teatised_task,
        return_exceptions=True
    )
    eraldised = results[0] if not isinstance(results[0], Exception) else []
    layers_data = results[1] if not isinstance(results[1], Exception) else {}
    teatised_features = results[2] if not isinstance(results[2], Exception) else []
    natura_features = layers_data.get("natura_elupaik", [])
    yrask_features = _filter_features_by_geometry(layers_data.get("yrask_eelis", []), kataster_data.get("geometry"))

    kitsendused = []
    mets_result = None
    vaartus_result = None
    sinik_result = None
    kahjustused_features = []
    carbon = {}
    raie = {}
    liikide_koosseis = []
    pindala = 0

    # Process kitsendused from layers
    for key in ["kaitsealad", "piirang", "karuputk", "malestised"]:
        for feat in layers_data.get(key, []):
            props = feat.get("properties", {})
            kitsendused.append({"tyyp": key, "kirjeldus": props.get("nimi", props.get("nimetus", key))})

    eraldised_features = []
    species_colors = {"MA": "#2d6a4f", "KU": "#1a8fd4", "KS": "#f4a261", "HB": "#adb5bd", "LH": "#6a994e", "LM": "#8d6e63", "LV": "#a1887f"}
    # Timber pricing — Eesti Erametsaliit aprill 2026
    # seisuhind = ~55% palgihinnast (raiekulud, transport, risk)
    # Allikas: erametsaliit.ee/puidu-hinnainfo
    SPECIES_PRICES = {
        "MA": {"seisuhind": 57, "log": 104, "pulp": 53},
        "KU": {"seisuhind": 60, "log": 110, "pulp": 53},
        "KS": {"seisuhind": 54, "log": 99, "pulp": 54},
        "HB": {"seisuhind": 35, "log": 63, "pulp": 45},
        "LH": {"seisuhind": 60, "log": 110, "pulp": 53},
        "LM": {"seisuhind": 36, "log": 65, "pulp": 44},
        "LV": {"seisuhind": 36, "log": 65, "pulp": 44},
        "TA": {"seisuhind": 55, "log": 100, "pulp": 50},
        "SA": {"seisuhind": 48, "log": 88, "pulp": 48},
        "VA": {"seisuhind": 35, "log": 65, "pulp": 42},
        "PK": {"seisuhind": 48, "log": 88, "pulp": 48},
        "JA": {"seisuhind": 40, "log": 75, "pulp": 45},
        "RE": {"seisuhind": 30, "log": 55, "pulp": 40},
        "SP": {"seisuhind": 42, "log": 78, "pulp": 45},
    }

    if eraldised:
        # Fetch element data for all eraldised in parallel
        element_tasks = [query_eraldis_element(e.get("id")) for e in eraldised]
        kahjustused_tasks = [query_kahjustused(e.get("id")) for e in eraldised]
        inner_results = await asyncio.gather(
            asyncio.gather(*element_tasks, return_exceptions=True),
            asyncio.gather(*kahjustused_tasks, return_exceptions=True),
        )
        all_elements = [r if not isinstance(r, Exception) else [] for r in inner_results[0]]
        all_kahjustused = [r if not isinstance(r, Exception) else [] for r in inner_results[1]]

        # Merge all liikide_koosseis from all eraldised
        for elements in all_elements:
            liikide_koosseis.extend(elements)
        for kahjust in all_kahjustused:
            kahjustused_features.extend(kahjust)

        # Aggregate across all eraldised (weighted by pindala)
        total_pindala = sum((e.get("pindala_ha") or 0) for e in eraldised)
        pindala = total_pindala

        # Weighted average tagavara and vanus
        if total_pindala > 0:
            avg_tagavara = sum((e.get("tagavara_y_ha") or 0) * (e.get("pindala_ha") or 0) for e in eraldised) / total_pindala
            avg_vanus = sum((e.get("vanus") or 0) * (e.get("pindala_ha") or 0) for e in eraldised) / total_pindala
        else:
            avg_tagavara = eraldised[0].get("tagavara_y_ha") or 0
            avg_vanus = eraldised[0].get("vanus") or 0

        # Peapuuliik = species with largest total area across all eraldised
        species_area = {}
        for e in eraldised:
            kood = e.get("puuliik_kood") or "MA"
            species_area[kood] = species_area.get(kood, 0) + (e.get("pindala_ha") or 0)
        puuliik = max(species_area, key=species_area.get) if species_area else "MA"
        primary = max(eraldised, key=lambda e: (e.get("pindala_ha") or 0))
        boniteet = primary.get("boniteedi_kood") or 3

        koosseis_with_osakaal = []
        if liikide_koosseis:
            # Filter out non-species codes (TM, PI, PS, PA, LV2, MU are forest type codes, not species)
            NON_SPECIES = {"TM", "PI", "PS", "PA", "LV2", "MU"}
            species_only = [e for e in liikide_koosseis if e.get("puuliik_kood") not in NON_SPECIES]
            if not species_only:
                species_only = liikide_koosseis  # fallback to all if no valid species

            # Aggregate by species code
            aggregated = {}
            for e in species_only:
                kood = e.get("puuliik_kood", "")
                if kood not in aggregated:
                    aggregated[kood] = {"puuliik": e.get("puuliik"), "puuliik_kood": kood, "tagavara_y_ha": 0, "vanus_sum": 0, "count": 0}
                aggregated[kood]["tagavara_y_ha"] += (e.get("tagavara_y_ha") or 0)
                aggregated[kood]["vanus_sum"] += (e.get("vanus") or 0)
                aggregated[kood]["count"] += 1

            species_list = list(aggregated.values())

            # Use tagavara for proportions; fall back to equal if all zero
            total_tagavara = sum(s["tagavara_y_ha"] for s in species_list)
            if total_tagavara > 0:
                for s in species_list:
                    koosseis_with_osakaal.append({
                        "puuliik": s["puuliik"], "puuliik_kood": s["puuliik_kood"],
                        "tagavara_y_ha": round(s["tagavara_y_ha"], 1),
                        "vanus": round(s["vanus_sum"] / s["count"]) if s["count"] else 0,
                        "osakaal": round(s["tagavara_y_ha"] / total_tagavara * 100),
                    })
            else:
                equal_pct = round(100 / len(species_list)) if species_list else 0
                for s in species_list:
                    koosseis_with_osakaal.append({
                        "puuliik": s["puuliik"], "puuliik_kood": s["puuliik_kood"],
                        "tagavara_y_ha": 0,
                        "vanus": round(s["vanus_sum"] / s["count"]) if s["count"] else 0,
                        "osakaal": equal_pct,
                    })

        # Carbon and cutting age use the final peapuuliik
        carbon = carbon_potential(avg_tagavara, total_pindala, puuliik)
        raie = cutting_age_indicator(int(avg_vanus or 0), puuliik, boniteet)

        # Build eraldised summary for frontend (including geometry and per-eraldis value)
        puuliik_nimi_map = {"MA": "harilik mänd", "KU": "harilik kuusk", "KS": "ainuroheline kask", "HB": "harilik haab", "LH": "harilik lehis", "LM": "hall lepp", "LV": "salu-lepp"}
        eraldised_summary = []
        for e in eraldised:
            geom = e.get("geometry")
            kood = e.get("puuliik_kood", "MA")
            vanus = e.get("vanus") or 0
            tagavara = e.get("tagavara_y_ha") or 0
            e_pindala = e.get("pindala_ha") or 0
            boniteet_kood = e.get("boniteedi_kood", 3)
            raievanus = e.get("raievanus") or 0
            kuivendatud = e.get("kuivendatud", False)

            # Per-eraldis valuation
            # Formula: seisuhind × tagavara × pindala × kuivendus
            # Note: tagavara (m³/ha) already reflects boniteet and age - no double-counting!
            e_prices = SPECIES_PRICES.get(kood, SPECIES_PRICES["MA"])
            e_seisuhind = e_prices["seisuhind"]
            drainage_factor = 1.1 if kuivendatud else 1.0
            eraldis_value = round(e_seisuhind * tagavara * e_pindala * drainage_factor)
            value_per_ha = round(eraldis_value / e_pindala) if e_pindala > 0 else 0

            # Per-eraldis cutting age analysis
            e_raie = cutting_age_indicator(vanus, kood, boniteet_kood)
            raie_ratio = e_raie.get("ratio", 0)
            if raie_ratio >= 1.0:
                raie_liik = "Lageraie"
                raie_color = "#e63946"  # red
            elif raie_ratio >= 0.85:
                raie_liik = "Harvendusraie"
                raie_color = "#ffc107"  # yellow
            elif raie_ratio >= 0.5:
                raie_liik = "Hooldusraie"
                raie_color = "#28a745"  # green
            else:
                raie_liik = "Noor mets"
                raie_color = "#17a2b8"  # teal — too young for any cutting

            eraldised_summary.append({
                "eraldis_nr": e.get("eraldis_nr"),
                "puuliik": e.get("puuliik"),
                "puuliik_kood": kood,
                "vanus": vanus,
                "tagavara_y_ha": tagavara,
                "pindala_ha": e_pindala,
                "boniteet": e.get("boniteet"),
                "boniteet_kood": boniteet_kood,
                "raievanus": e_raie.get("raievanus"),
                "raie_ratio": raie_ratio,
                "raie_status": e_raie.get("status"),
                "raie_liik": raie_liik,
                "kuivendatud": kuivendatud,
                # Per-eraldis valuation
                "vaartus_eur": eraldis_value,
                "vaartus_per_ha": value_per_ha,
                "seisuhind": e_seisuhind,
            })
            if geom:
                kood = e.get("puuliik_kood", "MA")
                eraldised_features.append({
                    "type": "Feature",
                    "geometry": geom,
                    "properties": {
                        "eraldis_nr": e.get("eraldis_nr"),
                        "puuliik": puuliik_nimi_map.get(kood, e.get("puuliik")),
                        "puuliik_kood": kood,
                        "vanus": e.get("vanus") or 0,
                        "tagavara_y_ha": e.get("tagavara_y_ha") or 0,
                        "pindala_ha": e_pindala,
                        "boniteet": e.get("boniteet"),
                        "korgus": e.get("korgus"),
                        "color": raie_color,
                        "raie_liik": raie_liik,
                        "raie_ratio": raie_ratio,
                        "raievanus": e_raie.get("raievanus"),
                        "vaartus_eur": eraldis_value,
                        "vaartus_per_ha": value_per_ha,
                    }
                })

        mets_result = {
            "puuliik": puuliik_nimi_map.get(puuliik, primary.get("puuliik", puuliik)),
            "puuliik_kood": puuliik,
            "vanus": int(avg_vanus),
            "tagavara_y_ha": round(avg_tagavara, 1),
            "boniteet": primary.get("boniteet"),
            "korgus": primary.get("korgus"),
            "pindala_ha": total_pindala,
            "kuivendatud": primary.get("kuivendatud"),
            "liikide_koosseis": koosseis_with_osakaal,
            "total_biomass_tons_ha": carbon.get("biomass_tons_ha"),
            "co2_tons_ha": carbon.get("co2_tons_ha"),
            "co2_tons_total": carbon.get("co2_tons_total"),
            "potential_income_eur": carbon.get("potential_income_eur"),
            "eraldised": eraldised_summary,
            "eraldisi_kokku": len(eraldised),
        }

        # Timber value = sum of all eraldiste values (consistent calculation)
        timber_value = sum(e.get("vaartus_eur", 0) for e in eraldised_summary)
        total_m3 = sum((e.get("tagavara_y_ha") or 0) * (e.get("pindala_ha") or 0) for e in eraldised)
        prices = SPECIES_PRICES.get(puuliik, SPECIES_PRICES["MA"])
        price_m3 = prices["seisuhind"]

        # Kinnistu turuväärtus = maa turuhind (metsamaal sisaldab puidu väärtust)
        # Maksuhind on Maa-ameti hinnang, metsamaal sageli ainult 500-1500 EUR/ha
        # Tegelik turuhind sõltub metsa vanusest, tagavarast ja liigist
        maksuhind = kataster_data.get("maks_hind") or 0
        kogupindala = kataster_data.get("pindala_ha") or 1
        sihtotstarve = kataster_data.get("sihtotstarve", "")
        maksuhind_ha = maksuhind / kogupindala if kogupindala > 0 else 0

        st = sihtotstarve.upper()
        if "ELAM" in st or "ÄRI" in st:
            turuhinna_tegur = 2.0
            MIN_TURUHIND_HA = 3000
        elif "POLL" in st:
            turuhinna_tegur = 1.8
            MIN_TURUHIND_HA = 2000
        elif "METS" in st or eraldised:
            turuhinna_tegur = 2.5
            MIN_TURUHIND_HA = 1500
        else:
            turuhinna_tegur = 1.5
            MIN_TURUHIND_HA = 500

        turuhind_ha = max(maksuhind_ha * turuhinna_tegur, MIN_TURUHIND_HA)

        # Maa turuhind (ilma puiduta)
        maa_turuhind = round(turuhind_ha * kogupindala)

        # Kinnistu turuväärtus = maa + puit
        kinnistu_turuväärtus = maa_turuhind + timber_value

        vaartus_result = {
            "total_value_eur": timber_value,
            "value_per_ha": round(timber_value / total_pindala) if total_pindala > 0 else 0,
            "price_per_m3": price_m3,
            "tagavara_m3": round(total_m3),
            "log_price": prices["log"],
            "pulp_price": prices["pulp"],
            "price_source": "Eesti Erametsaliit",
            "price_updated": "2026-04",
            # Kinnistu turuväärtus
            "kinnistu_turuväärtus": kinnistu_turuväärtus,
            "maa_turuhind": maa_turuhind,
            "maa_maksuhind": kataster_data.get("maks_hind") or 0,
        }

        sinik_result = {
            "co2_tons_total": carbon.get("co2_tons_total"),
            "co2_tons_ha": carbon.get("co2_tons_ha"),
            "total_biomass_tons_ha": carbon.get("biomass_tons_ha"),
            "potential_income_eur": carbon.get("potential_income_eur"),
            "cars_equivalent": carbon.get("cars_equivalent"),
            "trees_equivalent": carbon.get("trees_equivalent"),
        }

    kataster_data["mets_pindala_ha"] = pindala if eraldised else 0

    natura_2000 = bool(natura_features)
    kaitseala_features = layers_data.get("kaitsealad", [])
    toetus_features = layers_data.get("toetus_mets", [])
    vaariselupaik = bool(kaitseala_features or toetus_features)

    # Additional data for subsidy eligibility
    has_kuusk = any(e.get("puuliik_kood") == "KU" for e in eraldised) if eraldised else False
    max_kuusk_vanus = max((e.get("vanus") or 0) for e in eraldised if e.get("puuliik_kood") == "KU") if has_kuusk else 0

    subsidy_data = {
        "natura_2000": natura_2000,
        "vaariselupaik": vaariselupaik,
        "keskm_vanus": int(avg_vanus) if eraldised else 0,
        "peapuuliik_kood": puuliik if eraldised else None,
        "keskm_raievanus": eraldised[0].get("raievanus") if eraldised else None,
        "mets_pindala": pindala if eraldised else 0,
        "siht1": kataster_data.get("sihtotstarve", ""),
        "kaitseala": bool(kaitseala_features),
        "pindala_ha": kataster_data.get("pindala_ha", 0),
        "has_kuusk": has_kuusk,
        "max_kuusk_vanus": max_kuusk_vanus,
        "sood": bool(layers_data.get("sood")),
        "natura_elupaik": bool(layers_data.get("natura_elupaik")),
        "karuputk": bool(layers_data.get("karuputk")),
        "yrask_tsoon": bool(yrask_features),
    }
    toetused = check_subsidies(subsidy_data)

    riskid = {}
    # Always check layer-based risks (even without forest data)
    has_karuputk = bool(layers_data.get("karuputk"))
    has_lageraieala = bool(layers_data.get("lageraiealad"))
    riskid["karuputk"] = has_karuputk
    riskid["lageraieala"] = has_lageraieala

    if eraldised:
        # Ürask risk scoring — kuusekooreürask ohustab ainult kuuske
        yrask_score = 0
        yrask_label = "Madal"
        has_kuusk = any(e.get("puuliik_kood") == "KU" for e in eraldised)
        # Kuuse vanus eraldi — mitte kõigi eraldiste max!
        kuusk_eradised = [e for e in eraldised if e.get("puuliik_kood") == "KU"]
        max_kuusk_v = max((e.get("vanus") or 0) for e in kuusk_eradised) if kuusk_eradised else 0
        # Peapuuliik — already calculated above by tagavara*area
        peapuuliik_nimi = {"MA": "harilik mänd", "KU": "harilik kuusk", "KS": "ainuroheline kask", "HB": "harilik haab", "LH": "harilik lehis", "LM": "hall lepp", "LV": "salu-lepp"}.get(puuliik, puuliik)

        if yrask_features:
            yrask_score = 3
            yrask_label = "Kriitiline — MKE tsoonis"
        elif has_kuusk and max_kuusk_v > 50:
            yrask_score = 2
            yrask_label = "Kõrge — vana kuusk (" + str(max_kuusk_v) + "a)"
        elif has_kuusk and max_kuusk_v > 30:
            yrask_score = 1
            yrask_label = "Keskmine — kuusk üle 30a"
        else:
            yrask_score = 0
            yrask_label = "Madal"

        detail_parts = []
        if yrask_features:
            detail_parts.append("Kuusekooreüraski MKE tsoon")
        if has_kuusk:
            detail_parts.append("Kuuske on " + str(max_kuusk_v) + "a")
        else:
            detail_parts.append("Kuuske pole — üraski risk puudub")
        detail_parts.append("Peapuuliik: " + peapuuliik_nimi)

        riskid["yrask"] = {
            "score": yrask_score,
            "label": yrask_label,
            "official_zone": bool(yrask_features),
            "detail": ". ".join(detail_parts),
            "peapuuliik": peapuuliik_nimi,
        }

        # Terviseindeks (0-100): arvestab vanust, üraski riski, kahjustusi, liigilist koosseisu
        health = 100
        # Vanus: ideaalne 40-80a, alla 20a või üle 100a miinuspunktid
        avg_vanus = sum((e.get("vanus") or 0) * (e.get("pindala_ha") or 0) for e in eraldised) / max(sum((e.get("pindala_ha") or 0) for e in eraldised), 1)
        if avg_vanus < 20:
            health -= 10  # liiga noor mets
        elif avg_vanus > 100:
            health -= 15  # ülekasvanud
        elif avg_vanus > 80:
            health -= 5  # vanemapoolne
        # Üraski risk — ainult kui päriselt krundil
        health -= yrask_score * 8  # 0, 8, 16, 24
        # Kahjustused
        if kahjustused_features:
            health -= min(len(kahjustused_features) * 5, 20)
        # Karuputk
        if has_karuputk:
            health -= 10
        # Lageraieala — mets on ära raiutud
        if has_lageraieala:
            health -= 20
        # Liigiline mitmekesisus: ainult üks liik = madalam
        unique_species = set(e.get("puuliik_kood") for e in eraldised if e.get("puuliik_kood"))
        if len(unique_species) == 1:
            health -= 5
        elif len(unique_species) >= 3:
            health += 5  # mitmekesine mets on tervem
        # Kuivendamata mets — positiivne
        drained = [e for e in eraldised if e.get("kuivendatud")]
        if not drained and len(eraldised) > 0:
            health += 3  # loomulik veerežiim

        riskid["terviseindeks"] = max(0, min(100, health))
    else:
        riskid["terviseindeks"] = None

    # Process metsateatised - show active ones prominently
    TOO_NIMETUSED = {
        "TR": "Trassiraie", "HR": "Hooldusraie", "LR": "Lageraie",
        "UR": "Uuendusraie", "SR": "Sanitaarraie", "VR": "Valikraie",
        "KR": "Kujundusraie", "PR": "Peenraie", "JR": "Järjekorraline raie",
    }
    teatised = []
    for feat in teatised_features:
        p = feat.get("properties", {})
        too_kood = (p.get("too_kood") or "").upper()
        otsus = p.get("otsus") or ""
        staatus = "KEHTIV" if p.get("kehtiv_kuni") else otsus
        kehtiv = p.get("kehtiv_kuni") or ""
        teatised.append({
            "tyyp": TOO_NIMETUSED.get(too_kood, too_kood),
            "tyyp_kood": too_kood,
            "staatus": otsus,
            "kehtiv_kuni": kehtiv.replace("Z", ""),
            "pindala_ha": p.get("pindala", 0),
            "number": p.get("teatise_nr") or "",
            "maht": p.get("raiutav_maht"),
            "metskond": p.get("metskond") or "",
            "kvartal": p.get("kvartali_nr") or "",
            "eraldis": p.get("eraldise_nr"),
            "otsuse_pohjendus": (p.get("otsuse_pohjendus") or "")[:200],
            "active": bool(kehtiv),
        })

    kahjustused = []
    for feat in kahjustused_features:
        p = feat.get("properties", {})
        kahjustused.append({"tyyp": p.get("kahjustuse_tyyp", ""), "kirjeldus": p.get("kirjeldus", ""), "kuupaev": p.get("kuupaev", "")})

    mullad_features = layers_data.get("mullad", [])
    clc_features = layers_data.get("clc", [])
    mullad = mullad_features[0].get("properties", {}) if mullad_features else None
    clc = clc_features[0].get("properties", {}) if clc_features else None

    # Build map overlay layers with geometry for frontend rendering
    map_layers = {}
    LAYER_MAP = {
        "kaitsealad": {"label": "Kaitsealad", "color": "#2d6a4f"},
        "piirang": {"label": "Piiranguvööndid", "color": "#52796f"},
        "yrask_eelis": {"label": "Üraski vaatlused", "color": "#e76f51"},
        "yrask_mke": {"label": "Surnud puud (MKE)", "color": "#c1121f"},
        "sood": {"label": "Sood", "color": "#457b9d"},
        "natura_elupaik": {"label": "Natura elupaigad", "color": "#6a994e"},
        "karuputk": {"label": "Karuputk", "color": "#d63384"},
        "lageraiealad": {"label": "Lageraiealad", "color": "#adb5bd"},
        "malestised": {"label": "Mälestised", "color": "#7b2cbf"},
        "veekogud": {"label": "Järved", "color": "#48cae4"},
        "vooluveed": {"label": "Vooluveed", "color": "#0096c7"},
    }
    for key, meta in LAYER_MAP.items():
        features = layers_data.get(key, [])
        if features:
            map_layers[key] = {"label": meta["label"], "color": meta["color"], "features": features}

    # Add eraldised as a map layer (colored by species)
    if eraldised_features:
        map_layers["eraldised"] = {
            "label": "Eraldised",
            "color": "#2d6a4f",
            "features": eraldised_features,
            "type": "eraldised",
        }

    elapsed = round((time.time() - start) * 1000)

    response = json_response({
        "kataster": kataster_data,
        "mets": mets_result,
        "vaartus": vaartus_result,
        "sinik": sinik_result,
        "raie": raie,
        "kitsendused": kitsendused,
        "toetused": toetused,
        "riskid": riskid,
        "teatised": teatised,
        "kahjustused": kahjustused,
        "mullad": mullad,
        "clc": clc,
        "map_layers": map_layers,
        "meta": {"cached": False, "response_time_ms": elapsed},
    })

    # Store in cache for chat endpoint reuse
    _search_cache[kataster_nr] = {"response": response, "ts": time.time()}
    return response


def build_system_prompt(data: dict) -> str:
    """Build comprehensive system prompt with all forest data for AI advisor."""
    k = data.get("kataster", {})
    m = data.get("mets")
    v = data.get("vaartus")
    s = data.get("sinik")
    kitsendused = data.get("kitsendused", [])
    toetused = data.get("toetused", [])
    riskid = data.get("riskid", {})
    teatised = data.get("teatised", [])
    kahjustused = data.get("kahjustused", [])

    lines = []
    lines.append("Oled Terrapoint AI — Eesti metsanduse ja kinnisvara ekspert. Sa EI ole OWL ega muu mudel. Sa oled Terrapoint AI.")
    lines.append("")
    lines.append("ROLL:")
    lines.append("Sa oled kogenud metsakonsulent, kes aitab metsaomanikel oma metsast aru saada. Sa hindad metsa seisukorda, väärtust, riske ja võimalusi. Sa räägid lihtsas keeles, aga kasutad õigeid termineid. Sa annad alati konkreetseid soovitusi, mitte üldisi jutte.")
    lines.append("")
    lines.append("HINDAMISE JUHIS:")
    lines.append("Vanus: ideaalne 40-80a (küps mets). Alla 20a = noor, investeering. 60-80a = parim müügiaeg. Üle 100a = ülekasvanud, kaaluda raiet.")
    lines.append("Tagavara: hea >150 m³/ha, keskmine 80-150, madal <80. Kõrge tagavara = kõrge väärtus.")
    lines.append("Boniteet: I-II = hea kasvukoht, III = keskmine, IV-V = kehv. Hea boniteet tõstab väärtust.")
    lines.append("Liik: mänd = kõige väärtuslikum palgipuu, kuusk = hea aga üraskioht, kask = paberipuu, madalam väärtus.")
    lines.append("Üraski risk: 0-1 = normaalne, 2 = tegutse kohe (hooldusraie), 3 = kriitiline (ränne tsoonis).")
    lines.append("Terviseindeks: 80-100 = hea, 60-80 = rahuldav, alla 60 = probleemid, alla 40 = halb seisukord.")
    lines.append("CO2: iga hektar seob keskmiselt 5-15 t CO₂. Kõrge süsinikuvaru = hea kliimainvesteering.")
    lines.append("")
    lines.append("VASTUSE STRUKTUUR (kasuta seda alati):")
    lines.append("1. Lühike kokkuvõte (1 lause): mis seisus mets on")
    lines.append("2. Peamised näitajad: vanus, tagavara, väärtus, terviseindeks (konkreetsete numbritega)")
    lines.append("3. Riskid: mis on peamised ohud ja kui tõsised")
    lines.append("4. Soovitus: mida konkreetselt teha (müüa, hoida, hooldusraie, toetusi taotleda)")
    lines.append("")
    lines.append("REEGLID:")
    lines.append("- Vasta alati eesti keeles")
    lines.append("- Kasuta konkreetseid numbreid andmetest (vanus, tagavara, väärtus, CO2)")
    lines.append("- Anna selge soovitus: müüa/hoida/taotleda toetust")
    lines.append("- Kui metsa pole, ütle otse ja soovita mida teha (nt metsastamine, sihtotstarve muuta)")
    lines.append("- Kui küsitakse toetusi, loe sobivad ja ütle miks nad sobivad")
    lines.append("- Kui küsitakse müüki, arvuta konkreetne summa puidu väärtuse andmetest")
    lines.append("- Ära kasuta sidekriipse (– või -) vastustes, kirjuta laused tervikuna")
    lines.append("- Ära kasuta emoji-sid")
    lines.append("- Maksimaalselt 400 sõna")
    lines.append("- Kui küsitakse ühe eraldise kohta, keskendu ainult sellele eraldisele. Anna konkreetne hinnang: kas see eraldis on küps, noor, ülekasvanud. Soovita müüa, hoida või hooldusraie. Arvuta selle eraldise väärtus eraldi.")
    lines.append("- Ära soovita kunagi kohe lageraiet ilma muudeta. Kaalud alati hooldusraiet, harvendusraiet ja metsa hoidmist enne müüki.")
    lines.append("- LÕPETA alati konkreetse soovitusega, ära jäta lahtisteks")
    lines.append("")
    lines.append("=== KATASTRI ANDMED ===")
    lines.append(f"Number: {k.get('number', 'N/A')}")
    lines.append(f"Pindala: {k.get('pindala_ha', 0)} ha")
    lines.append(f"Asukoht: {k.get('l_aadress', '')}, {k.get('ov_nimi', '')}, {k.get('mk_nimi', '')}")
    lines.append(f"Sihtotstarve: {k.get('sihtotstarve', 'N/A')}")
    lines.append(f"Omandivorm: {k.get('omvorm', 'N/A')}")
    lines.append(f"Maksuhind: {k.get('maks_hind', 'N/A')} EUR")
    lines.append(f"Metsa pindala: {k.get('mets_pindala_ha', 0)} ha")

    if m:
        lines.append("")
        lines.append("=== METSA ANDMED ===")
        lines.append(f"Peapuuliik: {m.get('puuliik', 'N/A')} ({m.get('puuliik_kood', '')})")
        lines.append(f"Keskmine vanus: {m.get('vanus', 0)} aastat")
        lines.append(f"Tagavara: {m.get('tagavara_y_ha', 0)} m³/ha")
        lines.append(f"Boniteet: {m.get('boniteet', 'N/A')}")
        lines.append(f"Kõrgus: {m.get('korgus', 'N/A')} m")
        lines.append(f"Eraldiseid kokku: {m.get('eraldisi_kokku', 0)}")
        lines.append(f"Kuivendatud: {'Jah' if m.get('kuivendatud') else 'Ei'}")

        koosseis = m.get("liikide_koosseis", [])
        if koosseis:
            lines.append("Liikide koosseis:")
            for l in koosseis:
                lines.append(f"  - {l.get('puuliik', '?')}: {l.get('osakaal', 0)}%, tagavara {l.get('tagavara_y_ha', 0)} m³/ha, vanus {l.get('vanus', 0)} a")

        eraldised = m.get("eraldised", [])
        if eraldised:
            lines.append("Eraldised:")
            for e in eraldised:
                vaartus = e.get('vaartus_eur', 0)
                vaartus_str = f", väärtus {vaartus} EUR" if vaartus else ""
                drained = ", kuivendatud" if e.get('kuivendatud') else ""
                lines.append(f"  - Eraldis {e.get('eraldis_nr', '?')}: {e.get('puuliik', '?')}, {e.get('vanus', 0)} a, {e.get('tagavara_y_ha', 0)} m³/ha, {e.get('pindala_ha', 0)} ha, boniteet {e.get('boniteet', '?')}{vaartus_str}{drained}")

    if v:
        lines.append("")
        lines.append("=== PUIDU VÄÄRTUS ===")
        lines.append(f"Koguväärtus: {v.get('total_value_eur', 0)} EUR")
        lines.append(f"Väärtus hektari kohta: {v.get('value_per_ha', 0)} EUR/ha")
        lines.append(f"Seisuhind: {v.get('price_per_m3', 0)} EUR/m³")
        lines.append(f"Kogutagavara: {v.get('tagavara_m3', 0)} m³")
        lines.append(f"Palgi hind: {v.get('log_price', 0)} EUR/m³")
        lines.append(f"Paberipuu hind: {v.get('pulp_price', 0)} EUR/m³")
        lines.append(f"Hindade allikas: {v.get('price_source', '')} ({v.get('price_updated', '')})")

    if s:
        lines.append("")
        lines.append("=== SÜSINIK ===")
        lines.append(f"CO2 kogus: {s.get('co2_tons_total', 0)} tonni")
        lines.append(f"CO2 hektari kohta: {s.get('co2_tons_ha', 0)} t/ha")
        lines.append(f"Biomass: {s.get('total_biomass_tons_ha', 0)} t/ha")
        lines.append(f"Potentsiaalne sissetulek: {s.get('potential_income_eur', 0)} EUR")
        lines.append(f"Autoekvivalent: {s.get('cars_equivalent', 0)} autot aastas")
        lines.append(f"Puuekivalent: {s.get('trees_equivalent', 0)} küpset puud")

    if kitsendused:
        lines.append("")
        lines.append("=== KITSENDUSED ===")
        for kit in kitsendused:
            lines.append(f"  - {kit.get('tyyp', '?')}: {kit.get('kirjeldus', '')}")

    if toetused:
        lines.append("")
        lines.append("=== TOETUSED ===")
        for t in toetused:
            sobib = "SOBIB" if t.get("sobib") else "EI SOBI"
            lines.append(f"  - {t.get('nimi', '?')} ({t.get('asutus', '')}): {sobib}, {t.get('summa', '')} EUR")
            if t.get("pohjus"):
                lines.append(f"    Põhjus: {t['pohjus']}")
            if t.get("taotlusvoor"):
                lines.append(f"    Taotlusvoor: {t['taotlusvoor']}")

    raie = data.get("raie", {})
    if raie:
        lines.append("")
        lines.append("=== RAIEVALMIDUS ===")
        lines.append(f"Raievanus: {raie.get('raievanus', '?')} a, hetkel {raie.get('ratio', 0)}x. Staatus: {raie.get('label', '?')}")

    if riskid:
        lines.append("")
        lines.append("=== RISKID ===")
        yrask = riskid.get("yrask", {})
        if yrask:
            lines.append(f"Üraski risk: {yrask.get('label', 'N/A')} (skoor: {yrask.get('score', 0)})")
            if yrask.get('detail'):
                lines.append(f"  Detail: {yrask['detail']}")
        if riskid.get("karuputk"):
            lines.append("Karuputk: LEITUD")
        if riskid.get("lageraieala"):
            lines.append("Lageraieala: LEITUD")

    if teatised:
        lines.append("")
        lines.append("=== METSATEATISED ===")
        for t in teatised:
            aktiivne = "AKTIIVNE" if t.get("active") else "MITTEAKTIIVNE"
            lines.append(f"  - {t.get('tyyp', '?')} ({t.get('tyyp_kood', '')}): {aktiivne}, kehtib kuni {t.get('kehtiv_kuni', 'N/A')}")
            if t.get("maht"):
                lines.append(f"    Maht: {t['maht']} m³")
            if t.get("number"):
                lines.append(f"    Number: {t['number']}")

    if kahjustused:
        lines.append("")
        lines.append("=== KAHJUSTUSED ===")
        for kahj in kahjustused:
            lines.append(f"  - {kahj.get('tyyp', '?')}: {kahj.get('kirjeldus', '')} ({kahj.get('kuupaev', '')})")

    lines.append("")
    lines.append("Vasta kasutaja küsimusele nende andmete põhjal. Kui küsimus puudutab müüki, arvuta konkreetne summa. Kui puudutab oste, anna hinnang. Kui toetusi, ütle millised sobivad ja miks. Ole praktiline ja konkreetne.")

    return "\n".join(lines)


@app.post("/api/chat")
async def chat(request: Request):
    try:
        body = await request.json()
        kataster_nr = body.get("kataster_nr", "")
        user_message = body.get("message", "")
        history = body.get("history", [])

        if not kataster_nr or not user_message:
            return json_response({"error": "kataster_nr and message required"}, 400)

        # Use data from frontend (avoids re-fetching which is too slow for Vercel)
        data = body.get("data")
        if not data:
            return json_response({"error": "Otsi kinnistu esimesena, seejärel küsi AI-lt."}, 400)

        system_prompt = build_system_prompt(data)

        # Build messages array
        messages = [{"role": "system", "content": system_prompt}]
        for h in history:
            messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
        messages.append({"role": "user", "content": user_message})

        api_key = os.environ.get("OPENROUTER_API_KEY", "")
        if not api_key:
            return json_response({"error": "OpenRouter API key not configured"}, 500)

        api_url = "https://openrouter.ai/api/v1/chat/completions"
        model = "moonshotai/kimi-k2.6:free"

        async with httpx.AsyncClient(timeout=httpx.Timeout(7, connect=3)) as client:
            resp = await client.post(
                api_url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": messages,
                    "stream": False,
                    "temperature": 0.7,
                    "max_tokens": 500,
                },
            )
            if resp.status_code != 200:
                return json_response({"error": f"API viga: {resp.status_code}"}, 500)

            # Handle both JSON and SSE streaming responses
            content_type = resp.headers.get("content-type", "")
            if "text/event-stream" in content_type:
                # Parse SSE stream and collect full response
                full_text = ""
                for line in resp.text.split("\n"):
                    line = line.strip()
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk = orjson.loads(data_str)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            full_text += delta.get("content", "")
                        except Exception:
                            continue
                if not full_text:
                    return json_response({"error": "AI ei vastanud"}, 500)
                return json_response({"content": full_text})
            else:
                # Standard JSON response
                try:
                    result = resp.json()
                except Exception:
                    return json_response({"error": "API vastus ei ole JSON"}, 500)
                choices = result.get("choices", [])
                if not choices:
                    error = result.get("error", {}).get("message", "Tühi vastus")
                    return json_response({"error": error}, 500)
                content = choices[0].get("message", {}).get("content", "")
                if not content:
                    return json_response({"error": "AI ei vastanud"}, 500)
                return json_response({"content": content})

    except Exception as exc:
        import traceback
        return json_response({"error": str(exc), "trace": traceback.format_exc()}, 500)


@app.get("/api/export/eudr/{kataster_nr:path}")
async def export_eudr(kataster_nr: str):
    kataster_data = await query_kataster(kataster_nr)
    if not kataster_data:
        return json_response({"error": "Krunti ei leitud"}, 404)

    # Get centroid for coordinates
    try:
        geom = shape(kataster_data["geometry"])
        centroid = geom.centroid
        lon, lat = round(centroid.x, 6), round(centroid.y, 6)
    except Exception:
        lon, lat = None, None

    # Get forest data
    eraldised = await query_eraldis(kataster_nr)

    # Get Natura/protected status
    bbox = calculate_bbox(kataster_data["geometry"])
    bbox_str = bbox_to_wfs_string(bbox) if bbox else None
    natura_features = await query_natura_2000(bbox_str) if bbox_str else []
    layers_data = await query_all_layers(bbox_str) if bbox_str else {}

    # Determine deforestation risk
    kaitseala = bool(layers_data.get("kaitsealad"))
    natura_2000 = bool(natura_features)
    sood = bool(layers_data.get("sood"))

    geojson = {
        "type": "FeatureCollection",
        "name": f"eudr_{kataster_nr}",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::4326"}},
        "features": [{
            "type": "Feature",
            "geometry": kataster_data["geometry"],
            "properties": {
                # EUDR required fields
                "katastri_nr": kataster_nr,
                "riik": "EE",
                "pindala_ha": kataster_data["pindala_ha"],
                "longitude": lon,
                "latitude": lat,
                "sihtotstarve": kataster_data.get("sihtotstarve"),
                "maakond": kataster_data.get("mk_nimi"),
                "vald": kataster_data.get("ov_nimi"),
                "aadress": kataster_data.get("l_aadress"),
                # Forest data
                "mets_pindala_ha": sum(e.get("pindala_ha", 0) for e in eraldised) if eraldised else 0,
                "eraldisi": len(eraldised) if eraldised else 0,
                "peapuuliik": eraldised[0].get("puuliik_kood") if eraldised else None,
                "keskmine_vanus": int(sum((e.get("vanus") or 0) * (e.get("pindala_ha") or 0) for e in eraldised) / sum(e.get("pindala_ha", 0) for e in eraldised)) if eraldised and sum(e.get("pindala_ha", 0) for e in eraldised) > 0 else None,
                # EUDR compliance status
                "natura_2000": natura_2000,
                "kaitseala": kaitseala,
                "soode_ala": sood,
                "export_date": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            },
        }],
    }
    content = orjson.dumps(geojson, option=orjson.OPT_INDENT_2)
    return Response(
        content=content,
        media_type="application/geo+json",
        headers={"Content-Disposition": f'attachment; filename="eudr_{kataster_nr.replace(":", "_")}.geojson"'},
    )


@app.get("/")
async def root():
    html_path = PROJECT_ROOT / "index.html"
    if html_path.exists():
        return HTMLResponse(
            content=html_path.read_text(encoding="utf-8"),
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
        )
    return HTMLResponse(content="<h1>Terrapoint</h1>", status_code=500)


@app.get("/static/{filename:path}")
async def serve_static(filename: str):
    file_path = PROJECT_ROOT / "static" / filename
    if file_path.exists():
        if filename.endswith(".css"):
            return FileResponse(str(file_path), media_type="text/css", headers={"Cache-Control": "no-cache, must-revalidate"})
        if filename.endswith(".js"):
            return FileResponse(str(file_path), media_type="application/javascript", headers={"Cache-Control": "no-cache, must-revalidate"})
        return FileResponse(str(file_path), headers={"Cache-Control": "no-cache, must-revalidate"})
    return Response(status_code=404)


@app.get("/static/css/{filename:path}")
async def serve_css(filename: str):
    file_path = PROJECT_ROOT / "static" / "css" / filename
    if file_path.exists():
        return FileResponse(str(file_path), media_type="text/css")
    return Response(status_code=404)


@app.get("/static/js/{filename:path}")
async def serve_js(filename: str):
    file_path = PROJECT_ROOT / "static" / "js" / filename
    if file_path.exists():
        return FileResponse(str(file_path), media_type="application/javascript")
    return Response(status_code=404)
