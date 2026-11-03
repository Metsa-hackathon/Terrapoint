"""
Terrapoint — EstHubi Sentinel-2 satelliitpilt kinnistu alale.

EstHub (Maa- ja Ruumiameti satelliidiandmete keskus) avaldab Eesti päevase
Sentinel-2 RGB mosaiigi WMS-teenusena aadressil
https://teenus.maaamet.ee/ows/wms-sentinel-2-rgb. Teenus vastab ainult
EPSG:3301 (L-EST97) projektsioonis ja nõuab päeva parameetrit ``date``.
Seepärast pöörame kinnistu piirid siin ise L-EST97-sse ning tagastame pildi
koos WGS84 piirikast, mille peal Leaflet selle kaardile paigutab.

Päevamosaiik ei kata iga päev kogu Eestit: puuduva ala eest tuleb teenusest
täiesti läbipaistev pilt. Seetõttu otsime viimase päeva, mil kinnistu alal on
ka tegelikku pildisisu, ja näitame kasutajale just seda kuupäeva — mitte
tänast, mille kohta pilti veel ei ole.
"""
from __future__ import annotations

import asyncio
import base64
import io
import math
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import httpx
from fastapi import HTTPException
from PIL import Image

from services.kataster import query_kataster

SATELLITE_SERVICE_URL = "https://teenus.maaamet.ee/ows/wms-sentinel-2-rgb"
SATELLITE_REFERENCE_URL = "https://esthub.maaruum.ee/est/satiladu-p1.html"
SATELLITE_SOURCE_LABEL = "Sentinel-2 RGB päevamosaiik (EstHub)"
SATELLITE_PROVIDER = "Maa- ja Ruumiamet"
SATELLITE_TIME_ZONE = ZoneInfo("Europe/Tallinn")

# Kui mitu päeva tagasi otsime. S-2 möödub Eestist iga 2–3 päeva tagant, aga
# mosaiik avaldatakse ainult päevade kohta, mil pilvitus jättis kasutatavaid
# piksleid; kahene nädal katab ka talvise akna.
SATELLITE_LOOKBACK_DAYS = 14
# Katsetused on väikesed ja läbipaistvuse kontroll on odav.
SATELLITE_PROBE_PIXELS = 96
SATELLITE_PROBE_CONCURRENCY = 5
# Lõplik pilt: Sentinel-2 põhieraldusvõime on 10 m, seega 512 px annab
# kinnistu mõõtmetes terava pildi ilma tarbetu üleskaalumiseta.
SATELLITE_IMAGE_PIXELS = 512
SATELLITE_WEBP_QUALITY = 80
# Väljaku külje pikkus: kinnistu piirid + kontekst, aga piiratud, et pilt ei
# muutuks mõttetult suure ala kaardistuseks.
SATELLITE_MIN_SIDE_METRES = 900.0
SATELLITE_MAX_SIDE_METRES = 6000.0
SATELLITE_PADDING_METRES = 120.0
# Pilt loetakse olemasolevaks, kui vähemalt nii suur osa väljakust on kaetud.
SATELLITE_MIN_COVERAGE = 0.1
# Keskmine heledus, millest alates loeme pildi pilve/udu poolt varjatuks.
# Selge mets on Eestis ~60–90, tugev pilveloor 230–253 (mõõdetud 2026-11-03
# Kadaka pst kinnistul 21 päeva jooksul).
SATELLITE_MAX_CLEAR_LUMINANCE = 140.0
SATELLITE_REQUEST_TIMEOUT_SECONDS = 12.0
SATELLITE_MAX_RESPONSE_BYTES = 8 * 1024 * 1024
SATELLITE_MAX_IMAGE_PIXELS = 2048

# L-EST97 (EPSG:3301) — Lamberti konformne kooniline projektsioon GRS80
# ellipsoidil, telgmeridiaan 24°, lõikeparalleelid 58° ja 59°20'.
_GRS80_A = 6378137.0
_GRS80_F = 1 / 298.257222101
_GRS80_E2 = _GRS80_F * (2 - _GRS80_F)
_GRS80_E = math.sqrt(_GRS80_E2)
_LEST97_LAT_0 = math.radians(57 + 31 / 60 + 3.1942 / 3600)
_LEST97_LON_0 = math.radians(24.0)
_LEST97_LAT_1 = math.radians(59 + 20 / 60)
_LEST97_LAT_2 = math.radians(58.0)
_LEST97_FALSE_EASTING = 500000.0
_LEST97_FALSE_NORTHING = 6375000.0


def _lcc_m(phi: float) -> float:
    return math.cos(phi) / math.sqrt(1 - _GRS80_E2 * math.sin(phi) ** 2)


def _lcc_t(phi: float) -> float:
    sin_phi = math.sin(phi)
    return math.tan(math.pi / 4 - phi / 2) / math.pow(
        (1 - _GRS80_E * sin_phi) / (1 + _GRS80_E * sin_phi), _GRS80_E / 2
    )


_LCC_M1 = _lcc_m(_LEST97_LAT_1)
_LCC_M2 = _lcc_m(_LEST97_LAT_2)
_LCC_T1 = _lcc_t(_LEST97_LAT_1)
_LCC_T2 = _lcc_t(_LEST97_LAT_2)
_LCC_T0 = _lcc_t(_LEST97_LAT_0)
_LCC_N = (math.log(_LCC_M1) - math.log(_LCC_M2)) / (math.log(_LCC_T1) - math.log(_LCC_T2))
_LCC_F = _LCC_M1 / (_LCC_N * math.pow(_LCC_T1, _LCC_N))
_LCC_RHO0 = _GRS80_A * _LCC_F * math.pow(_LCC_T0, _LCC_N)


class SatelliteError(Exception):
    """EstHubi WMS ei vastanud või vastas vigase sisuga."""


def wgs84_to_lest97(lon: float, lat: float) -> tuple[float, float]:
    """Pööra WGS84/ETRS89 kraadid L-EST97 meetriteks."""
    phi = math.radians(lat)
    lam = math.radians(lon)
    rho = _GRS80_A * _LCC_F * math.pow(_lcc_t(phi), _LCC_N)
    theta = _LCC_N * (lam - _LEST97_LON_0)
    return (
        _LEST97_FALSE_EASTING + rho * math.sin(theta),
        _LEST97_FALSE_NORTHING + _LCC_RHO0 - rho * math.cos(theta),
    )


def lest97_to_wgs84(x: float, y: float) -> tuple[float, float]:
    """Pööra L-EST97 meetrid tagasi WGS84/ETRS89 kraadideks."""
    dx = x - _LEST97_FALSE_EASTING
    dy = _LCC_RHO0 - (y - _LEST97_FALSE_NORTHING)
    rho = math.hypot(dx, dy)
    if rho == 0:
        return (math.degrees(_LEST97_LON_0), math.degrees(_LEST97_LAT_0))
    theta = math.atan2(dx, dy)
    t = math.pow(rho / (_GRS80_A * _LCC_F), 1 / _LCC_N)
    phi = math.pi / 2 - 2 * math.atan(t)
    for _attempt in range(12):
        sin_phi = math.sin(phi)
        next_phi = math.pi / 2 - 2 * math.atan(
            t * math.pow((1 - _GRS80_E * sin_phi) / (1 + _GRS80_E * sin_phi), _GRS80_E / 2)
        )
        if abs(next_phi - phi) < 1e-12:
            phi = next_phi
            break
        phi = next_phi
    lon = _LEST97_LON_0 + theta / _LCC_N
    return (math.degrees(lon), math.degrees(phi))


def _geometry_positions(geometry: object) -> list[tuple[float, float]]:
    """Kogu GeoJSON-i geomeetria (Polygon/MultiPolygon/GeometryCollection) koordinaadid."""
    positions: list[tuple[float, float]] = []
    if not isinstance(geometry, dict):
        return positions
    geometry_type = geometry.get("type")
    if geometry_type == "GeometryCollection":
        for child in geometry.get("geometries") or []:
            positions.extend(_geometry_positions(child))
        return positions
    coordinates = geometry.get("coordinates")
    stack = [coordinates] if isinstance(coordinates, list) else []
    while stack:
        node = stack.pop()
        if not isinstance(node, list):
            continue
        if (
            len(node) >= 2
            and isinstance(node[0], (int, float))
            and isinstance(node[1], (int, float))
            and not isinstance(node[0], bool)
            and not isinstance(node[1], bool)
        ):
            lon, lat = float(node[0]), float(node[1])
            if math.isfinite(lon) and math.isfinite(lat):
                positions.append((lon, lat))
            continue
        stack.extend(item for item in node if isinstance(item, list))
    return positions


def parcel_patch_bounds(geometry: object) -> tuple[float, float, float, float] | None:
    """Kinnistut katva L-EST97 ruudu piirid (minx, miny, maxx, maxy).

    Ruut hoiab pildi venitamata ja annab igale kinnistule ühesuguse
    kaardistuse nii kitsale kui piklikule krundile.
    """
    positions = _geometry_positions(geometry)
    if not positions:
        return None
    projected = [wgs84_to_lest97(lon, lat) for lon, lat in positions]
    xs = [point[0] for point in projected]
    ys = [point[1] for point in projected]
    center_x = (min(xs) + max(xs)) / 2
    center_y = (min(ys) + max(ys)) / 2
    side = max(max(xs) - min(xs), max(ys) - min(ys)) + 2 * SATELLITE_PADDING_METRES
    side = min(max(side, SATELLITE_MIN_SIDE_METRES), SATELLITE_MAX_SIDE_METRES)
    half = side / 2
    return (
        round(center_x - half),
        round(center_y - half),
        round(center_x + half),
        round(center_y + half),
    )


def _bounds_param(bounds: tuple[float, float, float, float]) -> str:
    return ",".join(f"{value:.0f}" for value in bounds)


def _wms_params(day: str, bounds: tuple[float, float, float, float], pixels: int) -> dict[str, str]:
    return {
        "service": "WMS",
        "request": "GetMap",
        "version": "1.1.1",
        "layers": "sentinel_2_rgb",
        "styles": "",
        "format": "image/png",
        "transparent": "true",
        "tiled": "true",
        "srs": "EPSG:3301",
        "bbox": _bounds_param(bounds),
        "width": str(pixels),
        "height": str(pixels),
        "date": day,
    }


async def _fetch_png(
    client: httpx.AsyncClient,
    day: str,
    bounds: tuple[float, float, float, float],
    pixels: int,
) -> bytes:
    """Küsi WMS-ist üks PNG. Tõsta SatelliteError, kui vastus pole pilt."""
    try:
        response = await client.get(
            SATELLITE_SERVICE_URL,
            params=_wms_params(day, bounds, pixels),
            timeout=SATELLITE_REQUEST_TIMEOUT_SECONDS,
        )
    except httpx.HTTPError as exc:
        raise SatelliteError(f"EstHubi WMS päring ebaõnnestus: {type(exc).__name__}") from exc
    if response.status_code != 200:
        raise SatelliteError(f"EstHubi WMS vastas staatusega {response.status_code}")
    content = response.content
    if len(content) > SATELLITE_MAX_RESPONSE_BYTES:
        raise SatelliteError("EstHubi WMS vastus on liiga suur")
    if not content.startswith(b"\x89PNG\r\n\x1a\n"):
        # MapServer tagastab vea korral ServiceExceptionReport XML-i.
        raise SatelliteError("EstHubi WMS ei tagastanud pilti")
    return content


def png_assessment(png: bytes) -> tuple[float, float]:
    """(kaetus, keskmine heledus) — mitu protsenti pildist on kaetud ja kui valge see on.

    Kaetus tuleb alfa-kanalist: ilma kaugseireta ala on WMS-is läbipaistev.
    Heledus eraldab uduse/pilvese päeva selgest: metsa keskmine heledus on
    Eesti suvel-sügisel umbes 60–90, pilveloor tõstab selle üle 200.
    """
    try:
        with Image.open(io.BytesIO(png)) as image:
            if image.width > SATELLITE_MAX_IMAGE_PIXELS or image.height > SATELLITE_MAX_IMAGE_PIXELS:
                raise SatelliteError("EstHubi WMS tagastas ootamatult suure pildi")
            converted = image.convert("RGBA")
            alpha = converted.getchannel("A")
            if alpha.getbbox() is None:
                return (0.0, 0.0)
            histogram = alpha.histogram()
            visible = sum(histogram[1:]) if len(histogram) > 1 else 0
            coverage = visible / float(alpha.width * alpha.height)
            # Läbipaistmatud pikslid on RGB 0,0,0, seega nende heledus on 0 ja
            # keskmine tuleb jagada ainult kaetud pindalaga.
            luma_sum = sum(
                value * count for value, count in enumerate(converted.convert("L").histogram())
            )
    except SatelliteError:
        raise
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        raise SatelliteError("EstHubi WMS pilt ei ole loetav") from exc
    if not coverage:
        return (0.0, 0.0)
    return (coverage, luma_sum / float(visible))


def png_to_webp(png: bytes) -> tuple[bytes, int, int]:
    """Kodeeri WMS-i PNG väikeseks läbipaistvust hoidvaks WebP-iks."""
    try:
        with Image.open(io.BytesIO(png)) as image:
            converted = image.convert("RGBA")
            if converted.width > SATELLITE_MAX_IMAGE_PIXELS or converted.height > SATELLITE_MAX_IMAGE_PIXELS:
                raise SatelliteError("EstHubi WMS tagastas ootamatult suure pildi")
            buffer = io.BytesIO()
            converted.save(
                buffer,
                "WEBP",
                quality=SATELLITE_WEBP_QUALITY,
                method=4,
                alpha_quality=90,
            )
            return buffer.getvalue(), converted.width, converted.height
    except SatelliteError:
        raise
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        raise SatelliteError("EstHubi WMS pildi teisendus ebaõnnestus") from exc


async def _assess_day(
    client: httpx.AsyncClient,
    day: date,
    bounds: tuple[float, float, float, float],
) -> dict:
    png = await _fetch_png(client, day.isoformat(), bounds, SATELLITE_PROBE_PIXELS)
    coverage, luminance = png_assessment(png)
    return {
        "day": day,
        "covered": coverage >= SATELLITE_MIN_COVERAGE,
        "obscured": luminance >= SATELLITE_MAX_CLEAR_LUMINANCE,
    }


async def latest_satellite_scene(
    bounds: tuple[float, float, float, float],
    today: date | None = None,
) -> dict:
    """Uusim kasutatav päev sellel väljakul.

    ``date`` on uusim päev, mille pilt ei ole pilvega kaetud; kui ükski
    vaadeldud päev ei ole selge, on ``date`` uusim kaetud päev ja
    ``obscured`` True. ``newest_date`` on alati uusim päev, millel on
    üldse kaugseiret — kasutajaliides saab öelda, kui värskem pilt on pilves.
    """
    last_day = today or datetime.now(SATELLITE_TIME_ZONE).date()
    candidates = [last_day - timedelta(days=offset) for offset in range(SATELLITE_LOOKBACK_DAYS)]
    newest_covered: dict | None = None
    attempts = 0
    failures = 0
    async with httpx.AsyncClient() as client:
        for start in range(0, len(candidates), SATELLITE_PROBE_CONCURRENCY):
            wave = candidates[start:start + SATELLITE_PROBE_CONCURRENCY]
            results = await asyncio.gather(
                *(_assess_day(client, day, bounds) for day in wave),
                return_exceptions=True,
            )
            clear_hits: list[dict] = []
            for day, result in zip(wave, results):
                attempts += 1
                if isinstance(result, BaseException):
                    failures += 1
                    continue
                if not result["covered"]:
                    continue
                if newest_covered is None or result["day"] > newest_covered["day"]:
                    newest_covered = result
                if not result["obscured"]:
                    clear_hits.append(result)
            if clear_hits:
                picked = max(clear_hits, key=lambda hit: hit["day"])
                return {
                    "date": picked["day"].isoformat(),
                    "newest_date": newest_covered["day"].isoformat(),
                    "obscured": False,
                }
    if newest_covered is None:
        if attempts and failures == attempts:
            raise SatelliteError("EstHubi satelliiditeenus ei vasta")
        return {"date": None, "newest_date": None, "obscured": False}
    return {
        "date": newest_covered["day"].isoformat(),
        "newest_date": newest_covered["day"].isoformat(),
        "obscured": True,
    }


def _bounds_wgs84(bounds: tuple[float, float, float, float]) -> list[list[float]]:
    """L-EST97 väljaku nurgad Leafleti jaoks [[lõuna, lääs], [põhi, ida]]."""
    west, south = lest97_to_wgs84(bounds[0], bounds[1])
    east, north = lest97_to_wgs84(bounds[2], bounds[3])
    return [
        [round(min(south, north), 6), round(min(west, east), 6)],
        [round(max(south, north), 6), round(max(west, east), 6)],
    ]


def _source_metadata() -> dict:
    return {
        "label": SATELLITE_SOURCE_LABEL,
        "provider": SATELLITE_PROVIDER,
        "url": SATELLITE_REFERENCE_URL,
        "attribution": "Sentinel-2 RGB · EstHub (Maa- ja Ruumiamet)",
    }


async def satellite_context(kataster_nr: str) -> dict:
    """Viimane EstHubi Sentinel-2 pilt kinnistu alale.

    Vorm: ``state`` on ``available`` (pilt olemas), ``empty`` (viimase
    ``SATELLITE_LOOKBACK_DAYS`` päeva jooksul ei ole sellel alal kaugseiret) või
    ``unavailable`` (kinnistu geomeetria puudub). ``image`` on data-URL, mille
    kaart paigutab ``bounds`` piirikasse.
    """
    checked_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    kataster = await query_kataster(kataster_nr)
    if not kataster:
        raise HTTPException(status_code=404, detail="Katastriüksust ei leitud")
    bounds = parcel_patch_bounds(kataster.get("geometry"))
    if bounds is None:
        return {
            "parcel_id": kataster_nr,
            "state": "unavailable",
            "checked_at": checked_at,
            "lookback_days": SATELLITE_LOOKBACK_DAYS,
            "source": _source_metadata(),
        }

    payload = {
        "parcel_id": kataster_nr,
        "checked_at": checked_at,
        "lookback_days": SATELLITE_LOOKBACK_DAYS,
        "bounds": _bounds_wgs84(bounds),
        "source": _source_metadata(),
    }
    scene = await latest_satellite_scene(bounds)
    if scene["date"] is None:
        payload["state"] = "empty"
        return payload
    async with httpx.AsyncClient() as client:
        png = await _fetch_png(client, scene["date"], bounds, SATELLITE_IMAGE_PIXELS)
    webp, width, height = png_to_webp(png)
    side = bounds[2] - bounds[0]
    payload.update({
        "state": "available",
        "date": scene["date"],
        "newest_date": scene["newest_date"],
        "obscured": scene["obscured"],
        "image": "data:image/webp;base64," + base64.b64encode(webp).decode("ascii"),
        "width": width,
        "height": height,
        "resolution_m": round(side / width, 1) if width else None,
    })
    return payload
