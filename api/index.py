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
    start = time.time()
    MAX_TIME = 8.5  # Vercel Hobby has 10s timeout, leave buffer

    kataster_data = await query_kataster(kataster_nr)
    if not kataster_data:
        return json_response({"error": "Krunti ei leitud"}, 404)

    bbox = calculate_bbox(kataster_data["geometry"])
    bbox_str = bbox_to_wfs_string(bbox)

    # Default values if something times out
    eraldis_data = None
    kitsendused = []
    mets_result = None
    vaartus_result = None
    sinik_result = None
    kahjustused_features = []
    carbon = {}
    raie = {}
    liikide_koosseis = []
    teatised_features = []
    natura_features = []
    yrask_features = []
    layers_data = {}
    pindala = 0

    try:
        eraldis_task = asyncio.create_task(query_eraldis(kataster_nr))
        layers_task = asyncio.create_task(query_all_layers(bbox_str))
        natura_task = asyncio.create_task(query_natura_2000(bbox_str))
        yrask_task = asyncio.create_task(query_yrask_mke(bbox_str))
        teatised_task = asyncio.create_task(query_teatised(kataster_nr))

        remaining = max(1.0, MAX_TIME - (time.time() - start) - 1.0)
        done, pending = await asyncio.wait(
            [eraldis_task, layers_task, natura_task, yrask_task, teatised_task],
            timeout=remaining,
        )

        for t in done:
            try:
                result = t.result()
                if t is eraldis_task:
                    eraldis_data = result
                elif t is layers_task:
                    layers_data = result
                elif t is natura_task:
                    natura_features = result
                elif t is yrask_task:
                    yrask_features = result
                elif t is teatised_task:
                    teatised_features = result
            except Exception:
                pass

        for t in pending:
            t.cancel()
    except Exception:
        pass

    # Process what we got, even if partial
    for key in ["kaitsealad", "veekaitse", "piiranguvoond", "uleujutus", "kotkas", "malestised"]:
        for feat in layers_data.get(key, []):
            props = feat.get("properties", {})
            kitsendused.append({"tyyp": key, "kirjeldus": props.get("nimi", props.get("nimetus", key))})

    if eraldis_data:
        eraldis_id = eraldis_data.get("id")
        if eraldis_id:
            try:
                el_comp, kahj = await asyncio.wait_for(
                    asyncio.gather(
                        query_eraldis_element(eraldis_id),
                        query_kahjustused(eraldis_id),
                    ),
                    timeout=1.5,
                )
                liikide_koosseis = el_comp
                kahjustused_features = kahj
            except (asyncio.TimeoutError, Exception):
                pass

        tagavara = eraldis_data.get("tagavara_y_ha", 0)
        pindala = eraldis_data.get("pindala_ha", 0)
        puuliik = eraldis_data.get("puuliik_kood", "MA") or "MA"
        vanus = int(eraldis_data.get("vanus", 0) or 0)
        boniteet = int(eraldis_data.get("boniteedi_kood", 3) or 3)

        carbon = carbon_potential(tagavara, pindala, puuliik)
        raie = cutting_age_indicator(vanus, puuliik, boniteet)

        koosseis_with_osakaal = []
        if liikide_koosseis:
            total = sum(e.get("tagavara_y_ha", 0) for e in liikide_koosseis) or 1
            for e in liikide_koosseis:
                koosseis_with_osakaal.append({**e, "osakaal": round(e.get("tagavara_y_ha", 0) / total * 100)})

        mets_result = {
            "puuliik": eraldis_data.get("puuliik"),
            "puuliik_kood": puuliik,
            "vanus": vanus,
            "tagavara_y_ha": tagavara,
            "boniteet": eraldis_data.get("boniteet"),
            "korgus": eraldis_data.get("korgus"),
            "pindala_ha": pindala,
            "kuivendatud": eraldis_data.get("kuivendatud"),
            "liikide_koosseis": koosseis_with_osakaal,
            "total_biomass_tons_ha": carbon.get("biomass_tons_ha"),
            "co2_tons_ha": carbon.get("co2_tons_ha"),
            "co2_tons_total": carbon.get("co2_tons_total"),
            "potential_income_eur": carbon.get("potential_income_eur"),
        }

        price_m3 = 45.0
        total_m3 = tagavara * pindala
        vaartus_result = {
            "total_value_eur": round(total_m3 * price_m3),
            "value_per_ha": round(tagavara * price_m3),
            "price_per_m3": price_m3,
            "tagavara_m3": round(total_m3),
            "log_price": round(price_m3 * 0.6, 2),
            "pulp_price": round(price_m3 * 0.4, 2),
        }

        sinik_result = {
            "co2_tons_total": carbon.get("co2_tons_total"),
            "co2_tons_ha": carbon.get("co2_tons_ha"),
            "total_biomass_tons_ha": carbon.get("biomass_tons_ha"),
            "potential_income_eur": carbon.get("potential_income_eur"),
        }

    kataster_data["mets_pindala_ha"] = pindala if eraldis_data else 0

    natura_2000 = bool(natura_features)
    kaitseala_features = layers_data.get("kaitsealad", [])
    toetus_features = layers_data.get("toetus_mets", [])
    vaariselupaik = bool(kaitseala_features or toetus_features)

    subsidy_data = {
        "natura_2000": natura_2000,
        "vaariselupaik": vaariselupaik,
        "keskm_vanus": eraldis_data.get("vanus", 0) if eraldis_data else 0,
        "peapuuliik_kood": eraldis_data.get("puuliik_kood") if eraldis_data else None,
        "keskm_raievanus": eraldis_data.get("raievanus") if eraldis_data else None,
        "mets_pindala": eraldis_data.get("pindala_ha", 0) if eraldis_data else 0,
        "siht1": kataster_data.get("sihtotstarve", ""),
        "kaitseala": bool(kaitseala_features),
    }
    toetused = check_subsidies(subsidy_data)

    riskid = {}
    if eraldis_data:
        riskid["raievanus"] = raie
        riskid["yrask"] = {
            "score": 2 if yrask_features else 0,
            "label": "Kõrge" if yrask_features else "Madal",
            "official_zone": bool(yrask_features),
        }
        riskid["terviseindeks"] = None
        riskid["karuputk"] = bool(layers_data.get("karuputk"))
        riskid["lageraieala"] = bool(layers_data.get("lageraiealad"))

    teatised = []
    for feat in teatised_features:
        p = feat.get("properties", {})
        teatised.append({"tyyp": p.get("teatise_tyyp", ""), "staatus": p.get("staatus", ""), "kehtiv_kuni": p.get("kehtiv_kuni", ""), "pindala_ha": p.get("pindala", 0)})

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
