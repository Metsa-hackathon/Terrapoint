import orjson
from fastapi import APIRouter
from fastapi.responses import Response

from services.kataster import query_kataster

router = APIRouter()


@router.get("/export/eudr/{kataster_nr}")
async def export_eudr(kataster_nr: str):
    """Export parcel geometry as EUDR-compliant GeoJSON."""
    kataster = await query_kataster(kataster_nr)
    if not kataster or not kataster.get("geometry"):
        return Response(
            content=orjson.dumps({"error": "Geomeetria ei leitud"}),
            status_code=404,
            media_type="application/json",
        )

    geometry = kataster["geometry"]

    # Round coordinates to 6 decimal places
    _round_coords(geometry)

    # Ensure ring is closed
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

    geojson = {
        "type": "FeatureCollection",
        "features": [feature],
    }

    filename = f"terrapoint_eudr_{kataster_nr.replace(':', '_')}.geojson"

    return Response(
        content=orjson.dumps(geojson, option=orjson.OPT_INDENT_2),
        media_type="application/geo+json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _round_coords(geometry: dict):
    """Round all coordinates to 6 decimal places."""
    coords = geometry.get("coordinates", [])
    _round_nested(coords)


def _round_nested(coords):
    if isinstance(coords[0], (int, float)):
        for i in range(len(coords)):
            coords[i] = round(coords[i], 6)
    else:
        for sub in coords:
            _round_nested(sub)


def _close_ring(geometry: dict):
    """Ensure polygon rings are closed (first == last)."""
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
