import time
import asyncio
import orjson
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, HTMLResponse, FileResponse
from contextlib import asynccontextmanager

import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from services.kataster import query_kataster
from services.metsaregister import query_eraldis, query_eraldis_element, query_natura_2000, query_yrask_mke, query_teatised, query_kahjustused
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


@app.get("/api/search/{kataster_nr:path}")
async def search(kataster_nr: str, request: Request):
    try:
        return await _search(kataster_nr)
    except Exception as exc:
        import traceback
        return json_response({"error": str(exc), "trace": traceback.format_exc()}, 500)


async def _search(kataster_nr: str):
    start = time.time()
    MAX_TIME = 8.5  # Vercel Hobby has 10s timeout, leave buffer

    kataster_data = await query_kataster(kataster_nr)
    if not kataster_data:
        return json_response({"error": "Krunti ei leitud"}, 404)

    bbox = calculate_bbox(kataster_data["geometry"])
    bbox_str = bbox_to_wfs_string(bbox)

    eraldis_task = query_eraldis(kataster_nr)
    layers_task = query_all_layers(bbox_str)
    natura_task = query_natura_2000(bbox_str)
    yrask_task = query_yrask_mke(bbox_str)
    teatised_task = query_teatised(kataster_nr)

    results = await asyncio.gather(
        eraldis_task, layers_task, natura_task, yrask_task, teatised_task,
        return_exceptions=True
    )
    eraldised = results[0] if not isinstance(results[0], Exception) else []
    layers_data = results[1] if not isinstance(results[1], Exception) else {}
    natura_features = results[2] if not isinstance(results[2], Exception) else []
    yrask_features = results[3] if not isinstance(results[3], Exception) else []
    teatised_features = results[4] if not isinstance(results[4], Exception) else []

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
    for key in ["kaitsealad", "veekaitse", "piiranguvoond", "uleujutus", "kotkas", "malestised"]:
        for feat in layers_data.get(key, []):
            props = feat.get("properties", {})
            kitsendused.append({"tyyp": key, "kirjeldus": props.get("nimi", props.get("nimetus", key))})

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

        # Use primary eraldis (largest pindala) for species/boniteet display
        primary = max(eraldised, key=lambda e: (e.get("pindala_ha") or 0))
        puuliik = primary.get("puuliik_kood") or "MA"
        boniteet = primary.get("boniteedi_kood") or 3

        carbon = carbon_potential(avg_tagavara, total_pindala, puuliik)
        raie = cutting_age_indicator(int(avg_vanus or 0), puuliik, boniteet)

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

        # Build eraldised summary for frontend
        eraldised_summary = []
        for e in eraldised:
            eraldised_summary.append({
                "eraldis_nr": e.get("eraldis_nr"),
                "puuliik": e.get("puuliik"),
                "puuliik_kood": e.get("puuliik_kood"),
                "vanus": e.get("vanus") or 0,
                "tagavara_y_ha": e.get("tagavara_y_ha") or 0,
                "pindala_ha": e.get("pindala_ha") or 0,
                "boniteet": e.get("boniteet"),
            })

        mets_result = {
            "puuliik": primary.get("puuliik"),
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

        # Timber pricing — Erametsaliit aprill 2026 (palgihinnad, seisuhind ≈ palgihind/2.3)
        SPECIES_PRICES = {
            "MA": {"seisuhind": 45, "log": 104.37, "pulp": 53.14},
            "KU": {"seisuhind": 48, "log": 109.54, "pulp": 53.00},
            "KS": {"seisuhind": 43, "log": 98.80, "pulp": 53.79},
            "HB": {"seisuhind": 27, "log": 62.97, "pulp": 44.77},
            "LH": {"seisuhind": 40, "log": 85.00, "pulp": 50.00},
            "LM": {"seisuhind": 28, "log": 65.00, "pulp": 44.00},
            "LV": {"seisuhind": 28, "log": 65.00, "pulp": 44.00},
            "TA": {"seisuhind": 50, "log": 110.00, "pulp": 55.00},
            "SA": {"seisuhind": 45, "log": 100.00, "pulp": 50.00},
            "VA": {"seisuhind": 32, "log": 72.00, "pulp": 45.00},
        }
        prices = SPECIES_PRICES.get(puuliik, SPECIES_PRICES["MA"])
        price_m3 = prices["seisuhind"]
        total_m3 = avg_tagavara * total_pindala
        vaartus_result = {
            "total_value_eur": round(total_m3 * price_m3),
            "value_per_ha": round(avg_tagavara * price_m3),
            "price_per_m3": price_m3,
            "tagavara_m3": round(total_m3),
            "log_price": prices["log"],
            "pulp_price": prices["pulp"],
            "price_source": "Erametsaliit aprill 2026",
            "price_updated": "2026-04",
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

    subsidy_data = {
        "natura_2000": natura_2000,
        "vaariselupaik": vaariselupaik,
        "keskm_vanus": int(avg_vanus) if eraldised else 0,
        "peapuuliik_kood": eraldised[0].get("puuliik_kood") if eraldised else None,
        "keskm_raievanus": eraldised[0].get("raievanus") if eraldised else None,
        "mets_pindala": pindala if eraldised else 0,
        "siht1": kataster_data.get("sihtotstarve", ""),
        "kaitseala": bool(kaitseala_features),
    }
    toetused = check_subsidies(subsidy_data)

    riskid = {}
    if eraldised:
        riskid["raievanus"] = raie

        # Improved ürask risk scoring: consider official zone, species, and age
        yrask_score = 0
        yrask_label = "Madal"
        has_kuusk = any(e.get("puuliik_kood") == "KU" for e in eraldised)
        max_vanus = max((e.get("vanus") or 0) for e in eraldised)

        if yrask_features:
            yrask_score = 3
            yrask_label = "Kriitiline — tsoonis"
        elif has_kuusk and max_vanus > 50:
            yrask_score = 2
            yrask_label = "Kõrge — vana kuusemets"
        elif has_kuusk and max_vanus > 30:
            yrask_score = 1
            yrask_label = "Keskmine — kuusk üle 30a"
        else:
            yrask_score = 0
            yrask_label = "Madal"

        riskid["yrask"] = {
            "score": yrask_score,
            "label": yrask_label,
            "official_zone": bool(yrask_features),
            "detail": "Kuusekooreüraski MKE tsoon" if yrask_features else None,
        }
        riskid["terviseindeks"] = None
        riskid["karuputk"] = bool(layers_data.get("karuputk"))
        riskid["lageraieala"] = bool(layers_data.get("lageraiealad"))

    # Process metsateatised - show active ones prominently
    teatised = []
    for feat in teatised_features:
        p = feat.get("properties", {})
        staatus = p.get("staatus", "")
        teatised.append({
            "tyyp": p.get("teatise_tyyp", ""),
            "staatus": staatus,
            "kehtiv_kuni": p.get("kehtiv_kuni", ""),
            "pindala_ha": p.get("pindala", 0),
            "number": p.get("teatise_nr", ""),
            "active": staatus.upper() in ("KEHTIV", "ESITATUD", "MENETLUSES"),
        })

    kahjustused = []
    for feat in kahjustused_features:
        p = feat.get("properties", {})
        kahjustused.append({"tyyp": p.get("kahjustuse_tyyp", ""), "kirjeldus": p.get("kirjeldus", ""), "kuupaev": p.get("kuupaev", "")})

    mullad_features = layers_data.get("mullad", [])
    clc_features = layers_data.get("clc", [])
    mullad = mullad_features[0].get("properties", {}) if mullad_features else None
    clc = clc_features[0].get("properties", {}) if clc_features else None

    elapsed = round((time.time() - start) * 1000)

    return json_response({
        "kataster": kataster_data,
        "mets": mets_result,
        "vaartus": vaartus_result,
        "sinik": sinik_result,
        "kitsendused": kitsendused,
        "toetused": toetused,
        "riskid": riskid,
        "teatised": teatised,
        "kahjustused": kahjustused,
        "mullad": mullad,
        "clc": clc,
        "meta": {"cached": False, "response_time_ms": elapsed},
    })


@app.get("/api/export/eudr/{kataster_nr:path}")
async def export_eudr(kataster_nr: str):
    kataster_data = await query_kataster(kataster_nr)
    if not kataster_data:
        return json_response({"error": "Krunti ei leitud"}, 404)

    geojson = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "geometry": kataster_data["geometry"],
            "properties": {"katastri_nr": kataster_nr, "pindala_ha": kataster_data["pindala_ha"]},
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
        return HTMLResponse(content=html_path.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>Terrapoint</h1>", status_code=500)


@app.get("/static/{filename:path}")
async def serve_static(filename: str):
    file_path = PROJECT_ROOT / "static" / filename
    if file_path.exists():
        return FileResponse(str(file_path))
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
