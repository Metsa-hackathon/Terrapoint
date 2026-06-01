"""
Terrapoint — Eesti metsa- ja kinnistuandmete API

Versioon: 2.1.0
Autor: Terrapoint
"""

import time
import asyncio
import os
import httpx
import orjson
from shapely.geometry import shape
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, HTMLResponse, FileResponse
from fastapi import HTTPException
from pydantic import BaseModel, Field
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
from api.cache import search_cache


# ── Pydantic schemas ──────────────────────────────────────────────

class ChatRequest(BaseModel):
    """AI vestluse päring."""
    kataster_nr: str = Field(..., min_length=1, description="Katastritunnus (nt 78404:409:0113)")
    message: str = Field(..., min_length=1, max_length=2000, description="Kasutaja sõnum")
    history: list[dict] = Field(default_factory=list, description="Vestluse ajalugu")
    data: dict | None = Field(default=None, description="Eelnevalt laetud kinnistuandmed")


class ErrorResponse(BaseModel):
    """Standardne veavastus."""
    error: str = Field(..., description="Inimloetav veateade")
    code: str | None = Field(default=None, description="Veakood (nt NOT_FOUND, VALIDATION_ERROR)")


# ── Application setup ─────────────────────────────────────────────

_uptime_start = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(
    title="Terrapoint",
    description="Eesti metsa- ja kinnistuandmete API. Otsing katastritunnuse järgi, metsaeraldiste analüüs, väärtuse hindamine, süsinikuarvutus, toetused ja riskihinnang.",
    version="2.1.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def json_response(data: dict, status: int = 200) -> Response:
    return Response(content=orjson.dumps(data), media_type="application/json", status_code=status)


@app.get("/api/health")
async def health():
    """API tervisekontroll.

    Tagastab API oleku, versiooni, tööaja ja vahemälu statistika.
    Kasuta monitorimiseks ja load balanceri tervisekontrolliks.
    """
    uptime_seconds = int(time.time() - _uptime_start)
    return {
        "status": "ok",
        "version": "2.1.0",
        "uptime_seconds": uptime_seconds,
        "uptime_formatted": f"{uptime_seconds // 86400}d {(uptime_seconds % 86400) // 3600}h {(uptime_seconds % 3600) // 60}m",
        "cache": {
            "hits": 0,  # tracked below
            "size": search_cache.size if hasattr(search_cache, 'size') else "—",
        },
        "timestamp": time.time(),
    }


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


VPS_API = "https://terrapoint.46-62-230-110.sslip.io/api"

@app.get("/api/search/{kataster_nr:path}")
async def search(kataster_nr: str, request: Request):
    # On Vercel, proxy to VPS to avoid 10s timeout
    if os.environ.get("VERCEL"):
        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                resp = await client.get(f"{VPS_API}/search/{kataster_nr}")
                return Response(content=resp.content, status_code=resp.status_code, media_type="application/json")
        except Exception as exc:
            return json_response({"error": f"VPS proxy error: {exc}"}, 502)
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
# Search cache: track hits/misses
_search_cache_hits = 0
_search_cache_misses = 0

async def _search_core(kataster_nr: str, start: float) -> dict:
    """Sisemine otsinguloogika — eraldatud, et saaks timeout-i panna."""
    kataster_data = await query_kataster(kataster_nr)
    if not kataster_data:
        return {"error": "Krunti ei leitud", "_status": 404}

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

    # Skip per-eraldis API calls if too many eraldised or running low on time
    elapsed = time.time() - start
    skip_details = len(eraldised) > 30 or elapsed > 3.0
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
        # Fetch element data for all eraldised in parallel (skip if low on time)
        if not skip_details:
            element_tasks = [query_eraldis_element(e.get("id")) for e in eraldised]
            kahjustused_tasks = [query_kahjustused(e.get("id")) for e in eraldised]
            inner_results = await asyncio.gather(
                asyncio.gather(*element_tasks, return_exceptions=True),
                asyncio.gather(*kahjustused_tasks, return_exceptions=True),
            )
            all_elements = [r if not isinstance(r, Exception) else [] for r in inner_results[0]]
            all_kahjustused = [r if not isinstance(r, Exception) else [] for r in inner_results[1]]
        else:
            all_elements = []
            all_kahjustused = []

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
                # Fall back to area-based proportions from eraldised
                eraldis_species_area = {}
                for e in eraldised:
                    k = e.get("puuliik_kood", "MA")
                    eraldis_species_area[k] = eraldis_species_area.get(k, 0) + (e.get("pindala_ha") or 0)
                total_area = sum(eraldis_species_area.values()) or 1
                for s in species_list:
                    kood = s["puuliik_kood"]
                    area_pct = round((eraldis_species_area.get(kood, 0) / total_area) * 100)
                    koosseis_with_osakaal.append({
                        "puuliik": s["puuliik"], "puuliik_kood": kood,
                        "tagavara_y_ha": round(s["tagavara_y_ha"], 1) if s["tagavara_y_ha"] else 0,
                        "vanus": round(s["vanus_sum"] / s["count"]) if s["count"] else 0,
                        "osakaal": area_pct if area_pct > 0 else round(100 / len(species_list)),
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

            # Vanuserühm metsaomaniku jaoks
            if vanus <= 20:
                vanuseruhm = "noormets"
                vanuseruhm_label = "Noormets (kuni 20a)"
                vanuseruhm_desc = "Mets on veel noor, vajab hooldust ja harvendusraiet"
            elif vanus <= 60:
                vanuseruhm = "keskmine"
                vanuseruhm_label = "Keskmine mets (20-60a)"
                vanuseruhm_desc = "Mets kasvab aktiivselt, hea aeg hooldusraieks"
            elif vanus <= 100:
                vanuseruhm = "kups"
                vanuseruhm_label = "Küps mets (60-100a)"
                vanuseruhm_desc = "Mets on küps, kaaluda raiet või müüki"
            else:
                vanuseruhm = "vanamets"
                vanuseruhm_label = "Vana mets (100a+)"
                vanuseruhm_desc = "Ülekasvanud mets, raiumine soovitatav"

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
                "vaartus_eur": eraldis_value,
                "vaartus_per_ha": value_per_ha,
                "seisuhind": e_seisuhind,
                "vanuseruhm": vanuseruhm,
                "vanuseruhm_label": vanuseruhm_label,
                "vanuseruhm_desc": vanuseruhm_desc,
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
                        "vanuseruhm": vanuseruhm,
                        "vanuseruhm_label": vanuseruhm_label,
                        "vanuseruhm_desc": vanuseruhm_desc,
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

        # Kaalutud keskmine seisuhind kõigi eraldiste liikide järgi
        prices = SPECIES_PRICES.get(puuliik, SPECIES_PRICES["MA"])
        weighted_price_sum = 0.0
        weighted_log_sum = 0.0
        weighted_pulp_sum = 0.0
        for e in eraldised:
            e_kood = e.get("puuliik_kood", puuliik)
            e_p = SPECIES_PRICES.get(e_kood, SPECIES_PRICES["MA"])
            e_m3 = (e.get("tagavara_y_ha") or 0) * (e.get("pindala_ha") or 0)
            weighted_price_sum += e_p["seisuhind"] * e_m3
            weighted_log_sum += e_p["log"] * e_m3
            weighted_pulp_sum += e_p["pulp"] * e_m3
        if total_m3 > 0:
            price_m3 = round(weighted_price_sum / total_m3, 2)
            log_price = round(weighted_log_sum / total_m3, 2)
            pulp_price = round(weighted_pulp_sum / total_m3, 2)
        else:
            price_m3 = prices["seisuhind"]
            log_price = prices["log"]
            pulp_price = prices["pulp"]

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
            "log_price": log_price,
            "pulp_price": pulp_price,
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
    vaariselupaik = bool(kaitseala_features)

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

    return {
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
        "map_layers": map_layers,
        "meta": {"response_time_ms": elapsed, "partial": skip_details},
    }


async def _search(kataster_nr: str) -> Response:
    """Täielik kinnistu päring: kataster + eraldised + kihid + teatised.

    Kogub kõik andmed paralleelselt ja tagastab JSON-vastuse.
    Kasutab 8-sekundilist timeout-i, et Vercel 10s piirist mitte üle minna.
    """
    global _search_cache_hits, _search_cache_misses

    # Check cache
    cached_response = search_cache.get(kataster_nr)
    if cached_response is not None:
        _search_cache_hits += 1
        return cached_response
    _search_cache_misses += 1

    start = time.time()
    try:
        data = await asyncio.wait_for(_search_core(kataster_nr, start), timeout=25.0)
    except asyncio.TimeoutError:
        elapsed = round((time.time() - start) * 1000)
        data = {"error": "Otsing aegus osaliselt", "meta": {"response_time_ms": elapsed, "timeout": True}}

    if data.get("error"):
        status = data.pop("_status", 404)
        return json_response(data, status)

    response = json_response(data)
    search_cache.set(kataster_nr, response, ttl=300)
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
    lines.append("Oled Terrapoint AI, Eesti metsanduse ekspert. Vasta eesti keeles, kasuta konkreetseid numbreid. Maks 300 sõna. Ära kasuta sidekriipse ega emoji-sid. Struktuur: 1) kokkuvõte 2) näitajad 3) ohutegurid 4) soovitus. Lõpeta alati konkreetse soovitusega. Vanus 40-80a=küps, tagavara >150m³/ha=hea, boniteet I-II=hea. Mänd=väärtuslik, kuusk=üraskioht. Ära soovita kohe lageraiet.")
    lines.append("")
    lines.append("=== KATASTRIÜKSUSE ANDMED ===")
    lines.append(f"Number: {k.get('number', 'N/A')}")
    lines.append(f"Pindala: {k.get('pindala_ha', 0)} ha")
    lines.append(f"Asukoht: {k.get('l_aadress', '')}, {k.get('ov_nimi', '')}, {k.get('mk_nimi', '')}")
    lines.append(f"Sihtotstarve: {k.get('sihtotstarve', 'N/A')}")
    lines.append(f"Omand: {k.get('omvorm', 'N/A')}")
    lines.append(f"Maksuhind: {k.get('maks_hind', 'N/A')} EUR")
    lines.append(f"Metsa pindala: {k.get('mets_pindala_ha', 0)} ha")

    if m:
        lines.append("")
        lines.append("=== METSA ERALDISED ===")
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
            for e in eraldised[:5]:
                vaartus = e.get('vaartus_eur', 0)
                vaartus_str = f", {vaartus} EUR" if vaartus else ""
                lines.append(f"  E{e.get('eraldis_nr','?')}: {e.get('puuliik','?')}, {e.get('vanus',0)}a, {e.get('tagavara_y_ha',0)} m³/ha, {e.get('pindala_ha',0)} ha{vaartus_str}")
            if len(eraldised) > 5:
                lines.append(f"  ... ja veel {len(eraldised)-5} eraldist")

    if v:
        lines.append("")
        lines.append("=== METSA MAJANDUSLIK VÄÄRTUS ===")
        lines.append(f"Koguväärtus: {v.get('total_value_eur', 0)} EUR")
        lines.append(f"Väärtus hektari kohta: {v.get('value_per_ha', 0)} EUR/ha")
        lines.append(f"Seisuhind: {v.get('price_per_m3', 0)} EUR/m³")
        lines.append(f"Kogutagavara: {v.get('tagavara_m3', 0)} m³")
        lines.append(f"Palgi hind: {v.get('log_price', 0)} EUR/m³")
        lines.append(f"Paberipuu hind: {v.get('pulp_price', 0)} EUR/m³")
        lines.append(f"Hindade allikas: {v.get('price_source', '')} ({v.get('price_updated', '')})")

    if s:
        lines.append("")
        lines.append("=== SÜSINIKUVARU ===")
        lines.append(f"CO2 kogus: {s.get('co2_tons_total', 0)} tonni")
        lines.append(f"CO2 hektari kohta: {s.get('co2_tons_ha', 0)} t/ha")
        lines.append(f"Biomass: {s.get('total_biomass_tons_ha', 0)} t/ha")
        lines.append(f"Potentsiaalne sissetulek: {s.get('potential_income_eur', 0)} EUR")
        lines.append(f"Autoekvivalent: {s.get('cars_equivalent', 0)} autot aastas")
        lines.append(f"Puuekivalent: {s.get('trees_equivalent', 0)} küpset puud")

    if kitsendused:
        lines.append("KITSENDUSED: " + ", ".join(f"{kit.get('tyyp','?')}" for kit in kitsendused[:3]))

    if toetused:
        sobivad = [t for t in toetused if t.get("sobib")]
        lines.append("TOETUSED: " + ", ".join(f"{t.get('nimi','?')} ({t.get('summa','')} EUR)" for t in sobivad[:3]))

    raie = data.get("raie", {})
    if raie:
        lines.append(f"RAIE: {raie.get('label','?')} ({raie.get('ratio',0)}x)")

    if riskid:
        lines.append("")
        lines.append("=== OHUTEGURID ===")
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
    """AI metsanduse nõustaja.

    Kasutab OpenRouter AI-d, et vastata küsimustele
    kinnistu andmete põhjal. Edastab eelnevalt laaditud
    andmed (data) koos süsteemi promptiga AI-le.
    """
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
        model = os.environ.get("OPENROUTER_MODEL", "poolside/laguna-xs.2:free")

        async with httpx.AsyncClient(timeout=httpx.Timeout(25, connect=5)) as client:
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
                    "max_tokens": 10000,
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
                import re
                full_text = re.sub(r'<𝑎𝑛𝑡𝑚𝑙:thinking_mode>[^<]*</𝑎𝑛𝑡𝑚𝑙:thinking_mode>', '', full_text)
                full_text = re.sub(r'</?assistant>', '', full_text).strip()
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
                # Strip thinking/assistant tags that leak from reasoning models
                import re
                content = re.sub(r'<𝑎𝑛𝑡𝑚𝑙:thinking_mode>[^<]*</𝑎𝑛𝑡𝑚𝑙:thinking_mode>', '', content)
                content = re.sub(r'</?assistant>', '', content).strip()
                return json_response({"content": content})

    except httpx.ReadTimeout:
        return json_response({"error": "AI vastus võttis liiga kaua. Proovi lühemat küsimust."}, 504)
    except Exception as exc:
        return json_response({"error": f"Serveri viga: {str(exc)}"}, 500)


@app.get("/api/export/eudr/{kataster_nr:path}")
async def export_eudr(kataster_nr: str):
    """Ekspordi EUDR GeoJSON fail.

    Tagastab EL deforestatsioonivastase määruse nõuetele
    vastava GeoJSON faili alla laadimiseks.
    Sisaldab katastriandmeid, metsaeraldiseid ja looduskaitsestaatust.
    """
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
    """Lehe avaleht — esitleb HTML index faili."""
    html_path = PROJECT_ROOT / "index.html"
    if html_path.exists():
        return HTMLResponse(
            content=html_path.read_text(encoding="utf-8"),
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
        )
    return HTMLResponse(content="<h1>Terrapoint</h1>", status_code=500)


@app.get("/static/{filename:path}")
async def serve_static(filename: str):
    """Teeninda staatilisi faile (/static/ kataloogist)."""
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
    """Teeninda CSS faile (/static/css/ kataloogist)."""
    file_path = PROJECT_ROOT / "static" / "css" / filename
    if file_path.exists():
        return FileResponse(str(file_path), media_type="text/css")
    return Response(status_code=404)
