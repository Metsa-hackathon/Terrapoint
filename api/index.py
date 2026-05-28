import os
import time
import asyncio
from contextlib import asynccontextmanager

import orjson
from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, HTMLResponse, FileResponse

import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from services.cache import CacheService
from services.kataster import query_kataster
from services.metsaregister import query_eraldis, query_eraldis_element, query_natura_2000, query_yrask_mke
from services.layers import query_all_layers
from services.valuation import get_valuation
from services.subsidies import check_subsidies
from calculators.carbon import carbon_potential
from calculators.cutting_age import cutting_age_indicator
from calculators.beetle_risk import beetle_risk
from calculators.health_index import health_index as calc_health_index
from spatial.bbox import calculate_bbox, bbox_to_wfs_string
import config


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = None
    yield


app = FastAPI(title="Terrapoint", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok", "timestamp": time.time()}


@app.get("/")
async def root():
    html_path = PROJECT_ROOT / "public" / "index.html"
    if html_path.exists():
        return HTMLResponse(content=html_path.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>Terrapoint</h1><p>index.html not found</p>", status_code=500)


@app.get("/css/{filename:path}")
async def serve_css(filename: str):
    file_path = PROJECT_ROOT / "public" / "css" / filename
    if file_path.exists():
        return FileResponse(str(file_path), media_type="text/css")
    return Response(status_code=404)


@app.get("/js/{filename:path}")
async def serve_js(filename: str):
    file_path = PROJECT_ROOT / "public" / "js" / filename
    if file_path.exists():
        return FileResponse(str(file_path), media_type="application/javascript")
    return Response(status_code=404)


@app.get("/img/{filename:path}")
async def serve_img(filename: str):
    file_path = PROJECT_ROOT / "public" / "img" / filename
    if file_path.exists():
        return FileResponse(str(file_path))
    return Response(status_code=404)


@app.get("/api/search/{kataster_nr}")
async def search(request: Request, kataster_nr: str, refresh: bool = Query(False)):
    start = time.time()
    cache = CacheService(request.app.state.redis)
    cache_key = f"kataster:{kataster_nr}:full"

    if not refresh:
        cached = await cache.get(cache_key)
        if cached:
            cached["meta"]["cached"] = True
            return Response(content=orjson.dumps(cached), media_type="application/json")

    kataster_data = await query_kataster(kataster_nr)
    if not kataster_data:
        return Response(
            content=orjson.dumps({"error": "Katastri numbrit ei leitud", "kataster_nr": kataster_nr}),
            status_code=404,
            media_type="application/json",
        )

    geometry = kataster_data.get("geometry")
    bbox = calculate_bbox(geometry) if geometry else None
    bbox_str = bbox_to_wfs_string(bbox) if bbox else None

    async def _empty_layers():
        return {}

    async def _empty_list():
        return []

    eraldis_task = query_eraldis(kataster_nr)
    layers_task = query_all_layers(bbox_str) if bbox_str else _empty_layers()
    natura_task = query_natura_2000(bbox_str) if bbox_str else _empty_list()
    yrask_task = query_yrask_mke(bbox_str) if bbox_str else _empty_list()

    eraldis_data, layers_data, natura_features, yrask_features = await asyncio.gather(
        eraldis_task, layers_task, natura_task, yrask_task
    )

    liikide_koosseis = []
    mets_result = None
    vaartus_result = None
    sinik_result = None
    riskid = {}
    terviseindeks = None

    if eraldis_data:
        eraldis_id = eraldis_data.get("id")
        if eraldis_id:
            liikide_koosseis = await query_eraldis_element(eraldis_id)

        eraldis_data["liikide_koosseis"] = liikide_koosseis
        mets_result = eraldis_data

        tagavara = eraldis_data.get("tagavara_y_ha") or 0
        pindala = eraldis_data.get("pindala_ha") or 0

        if tagavara == 0 and liikide_koosseis:
            weighted_sum = 0
            total_osakaal = 0
            for elem in liikide_koosseis:
                t = elem.get("tagavara")
                o = elem.get("osakaal", 0)
                if t and t > 0 and o > 0:
                    weighted_sum += t * o
                    total_osakaal += o
            if total_osakaal > 0:
                tagavara = round(weighted_sum / total_osakaal, 1)
                eraldis_data["tagavara_y_ha"] = tagavara
        puuliik = eraldis_data.get("puuliik_kood") or "MA"

        if tagavara > 0 and pindala > 0:
            vaartus_result = await get_valuation(kataster_nr, tagavara, pindala, puuliik)
            sinik_result = carbon_potential(tagavara, pindala, puuliik)

        raievanus = cutting_age_indicator(
            eraldis_data.get("vanus") or 0,
            puuliik,
            eraldis_data.get("boniteedi_kood") or 3,
            eraldis_data.get("raievanus"),
        )

        official_zone = bool(yrask_features)
        yrask = beetle_risk(
            puuliik,
            eraldis_data.get("vanus") or 0,
            eraldis_data.get("kuivendatud", False),
            eraldis_data.get("taius_1") or 0,
            official_zone,
        )

        tervise = calc_health_index(
            eraldis_data.get("boniteedi_kood") or 3,
            eraldis_data.get("kuivendatud", False),
            eraldis_data.get("tuleohu_kood"),
            yrask["score"],
        )
        terviseindeks = tervise["score"]

        riskid = {
            "raievanus": raievanus,
            "yrask": yrask,
            "terviseindeks": terviseindeks,
            "karuputk": bool(layers_data.get("karuputk")),
            "lageraieala": _extract_lageraie(layers_data.get("lageraiealad", [])),
        }

    kitsendused = _extract_kitsendused(layers_data, natura_features)

    subsidy_data = {
        "natura_2000": bool(natura_features) or bool(layers_data.get("toetus_mets")),
        "keskm_vanus": (eraldis_data.get("vanus") or 0) if eraldis_data else 0,
        "peapuuliik_kood": (eraldis_data.get("puuliik_kood") or "") if eraldis_data else "",
        "mets_pindala": kataster_data.get("mets_pindala_ha", 0) or 0,
        "siht1": kataster_data.get("sihtotstarve", ""),
        "keskm_raievanus": (eraldis_data.get("raievanus") or 999) if eraldis_data else 999,
        "kaitseala": bool(layers_data.get("kaitsealad")),
    }
    toetused = check_subsidies(subsidy_data)

    elapsed = int((time.time() - start) * 1000)

    response = {
        "kataster": kataster_data,
        "mets": mets_result,
        "vaartus": vaartus_result,
        "sinik": sinik_result,
        "kitsendused": kitsendused,
        "toetused": toetused,
        "riskid": riskid,
        "meta": {
            "cached": False,
            "cache_ttl": config.CACHE_TTL_FULL,
            "response_time_ms": elapsed,
        },
    }

    await cache.set(cache_key, response, config.CACHE_TTL_FULL)

    return Response(content=orjson.dumps(response), media_type="application/json")


@app.get("/api/export/eudr/{kataster_nr}")
async def export_eudr(kataster_nr: str):
    kataster = await query_kataster(kataster_nr)
    if not kataster or not kataster.get("geometry"):
        return Response(
            content=orjson.dumps({"error": "Geomeetria ei leitud"}),
            status_code=404,
            media_type="application/json",
        )

    geometry = kataster["geometry"]
    _round_coords(geometry)
    _close_ring(geometry)

    feature = {
        "type": "Feature",
        "geometry": geometry,
        "properties": {
            "ProducerName": "",
            "ProducerCountry": "EE",
            "ProductionPlace": kataster.get("ov_nimi", ""),
            "CadastralReference": kataster_nr,
            "AreaHa": kataster.get("pindala_ha"),
        },
    }

    geojson = {"type": "FeatureCollection", "features": [feature]}
    filename = f"terrapoint_eudr_{kataster_nr.replace(':', '_')}.geojson"

    return Response(
        content=orjson.dumps(geojson, option=orjson.OPT_INDENT_2),
        media_type="application/geo+json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _extract_kitsendused(layers_data: dict, natura_features: list) -> list[dict]:
    result = []
    for feat in natura_features:
        p = feat.get("properties", {})
        result.append({"tyyp": "Natura 2000", "kirjeldus": p.get("nimetus", p.get("nimi", "Natura 2000 ala")), "allikas": "metsaregister:natura_2000_alad"})
    for feat in layers_data.get("kaitsealad", []):
        p = feat.get("properties", {})
        result.append({"tyyp": "Kaitseala", "kirjeldus": p.get("nimi", p.get("nimetus", "Kaitseala")), "allikas": "eelis:kr_kaitseala"})
    for feat in layers_data.get("natura_elupaik", []):
        p = feat.get("properties", {})
        result.append({"tyyp": "Natura elupaik", "kirjeldus": p.get("nimetus", p.get("nimi", "Elupaik")), "allikas": "eelis:natura_elupaik"})
    for layer_key in ["veekaitse", "piiranguvoond", "uleujutus"]:
        for feat in layers_data.get(layer_key, []):
            p = feat.get("properties", {})
            result.append({"tyyp": "Veekaitse", "kirjeldus": p.get("nimetus", p.get("nimi", layer_key)), "allikas": f"kitsendused:{layer_key}"})
    for feat in layers_data.get("kotkas", []):
        p = feat.get("properties", {})
        result.append({"tyyp": "Kotka pesitsuspiirang", "kirjeldus": p.get("objekti_nimetus", p.get("voondi_nimetus", "Kotka piirang")), "allikas": "kitsendused:kotkas_kitsendused"})
    for feat in layers_data.get("malestised", []):
        p = feat.get("properties", {})
        result.append({"tyyp": "Muinsuskaitse", "kirjeldus": p.get("nimetus", p.get("nimi", "Kultuurimälestis")), "allikas": "muinsuskaitse:kpo_malestised"})
    return result


def _extract_lageraie(features: list) -> str | None:
    if not features:
        return None
    for feat in features:
        p = feat.get("properties", {})
        a, o = p.get("periood_a"), p.get("periood_o")
        if a and o:
            return f"{a}–{o}"
    return None


def _round_coords(geometry: dict):
    _round_nested(geometry.get("coordinates", []))


def _round_nested(coords):
    if isinstance(coords[0], (int, float)):
        for i in range(len(coords)):
            coords[i] = round(coords[i], 6)
    else:
        for sub in coords:
            _round_nested(sub)


def _close_ring(geometry: dict):
    coords = geometry.get("coordinates", [])
    geom_type = geometry.get("type", "")
    if geom_type == "Polygon":
        for ring in coords:
            if ring and ring[0] != ring[-1]:
                ring.append(ring[0])
    elif geom_type == "MultiPolygon":
        for polygon in coords:
            for ring in polygon:
                if ring and ring[0] != ring[-1]:
                    ring.append(ring[0])
