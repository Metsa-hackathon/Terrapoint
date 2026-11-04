import io
import unittest
from datetime import date, timedelta
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from PIL import Image

from api import index as api
from services import satellite

KATASTER_NR = "78404:409:0113"
# Tallinna Kadaka pst 159 kinnistu (ligikaudne ristkülik piiri ümber).
PARCEL_GEOMETRY = {
    "type": "Polygon",
    "coordinates": [[
        [24.63385763, 59.39419284],
        [24.63384073, 59.39385064],
        [24.63562891, 59.39377199],
        [24.63562891, 59.39422799],
        [24.63385763, 59.39419284],
    ]],
}


def png(pixels: list[tuple[int, int, int, int]], size: int = 16) -> bytes:
    """Ehita PNG, mille ülaosa on esimene värv ja alumine osa järgmised."""
    image = Image.new("RGBA", (size, size), pixels[0])
    if len(pixels) > 1:
        band = size // len(pixels)
        for index, color in enumerate(pixels[1:], start=1):
            image.paste(color, (0, index * band, size, (index + 1) * band))
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue()


BLANK_PNG = png([(0, 0, 0, 0)])
CLEAR_PNG = png([(41, 68, 39, 255)])
CLOUDY_PNG = png([(246, 248, 252, 255)])
HALF_PNG = png([(41, 68, 39, 255), (0, 0, 0, 0)])


class ProjectionTests(unittest.TestCase):
    def test_matches_published_l_est97_coordinates(self):
        x, y = satellite.wgs84_to_lest97(24.638407, 59.391929)
        self.assertAlmostEqual(x, 536275, delta=2)
        self.assertAlmostEqual(y, 6583948, delta=2)

    def test_round_trips_back_to_wgs84(self):
        for lon, lat in ((24.638407, 59.391929), (26.7225, 58.3776), (22.0, 58.9)):
            restored_lon, restored_lat = satellite.lest97_to_wgs84(
                *satellite.wgs84_to_lest97(lon, lat)
            )
            self.assertAlmostEqual(restored_lon, lon, places=6)
            self.assertAlmostEqual(restored_lat, lat, places=6)


class PatchBoundsTests(unittest.TestCase):
    def test_patch_is_a_square_that_contains_the_parcel(self):
        bounds = satellite.parcel_patch_bounds(PARCEL_GEOMETRY)
        self.assertIsNotNone(bounds)
        west, south, east, north = bounds
        self.assertEqual(east - west, north - south)
        parcel_west, parcel_south = satellite.wgs84_to_lest97(24.63384073, 59.39377199)
        parcel_east, parcel_north = satellite.wgs84_to_lest97(24.63562891, 59.39422799)
        self.assertLessEqual(west, parcel_west)
        self.assertLessEqual(south, parcel_south)
        self.assertGreaterEqual(east, parcel_east)
        self.assertGreaterEqual(north, parcel_north)

    def test_patch_side_uses_configured_limits(self):
        tiny = {"type": "Polygon", "coordinates": [[[24.0, 59.0], [24.0001, 59.0], [24.0001, 59.0001], [24.0, 59.0]]]}
        bounds = satellite.parcel_patch_bounds(tiny)
        self.assertEqual(bounds[2] - bounds[0], satellite.SATELLITE_MIN_SIDE_METRES)
        huge = {"type": "Polygon", "coordinates": [[[21.0, 57.0], [28.0, 57.0], [28.0, 60.0], [21.0, 57.0]]]}
        clamped = satellite.parcel_patch_bounds(huge)
        self.assertEqual(clamped[2] - clamped[0], satellite.SATELLITE_MAX_SIDE_METRES)

    def test_latlon_bounds_are_leaflet_corners(self):
        bounds = satellite.parcel_patch_bounds(PARCEL_GEOMETRY)
        south_west, north_east = satellite._bounds_wgs84(bounds)
        self.assertEqual(len(south_west), 2)
        self.assertEqual(len(north_east), 2)
        self.assertLess(south_west[0], north_east[0])
        self.assertLess(south_west[1], north_east[1])
        # Leaflet ootab [[lõuna, lääs], [põhi, ida]] — laiuskraad esimesena.
        self.assertAlmostEqual(south_west[0], 59.39, delta=0.05)
        self.assertAlmostEqual(south_west[1], 24.64, delta=0.05)

    def test_geometry_without_positions_has_no_bounds(self):
        self.assertIsNone(satellite.parcel_patch_bounds({"type": "Polygon", "coordinates": []}))
        self.assertIsNone(satellite.parcel_patch_bounds(None))


class AssessmentTests(unittest.TestCase):
    def test_transparent_raster_has_no_coverage(self):
        coverage, luminance, _cloud = satellite.png_assessment(BLANK_PNG)
        self.assertEqual(coverage, 0.0)
        self.assertEqual(luminance, 0.0)

    def test_covered_forest_is_dark_and_complete(self):
        coverage, luminance, cloud = satellite.png_assessment(CLEAR_PNG)
        self.assertEqual(coverage, 1.0)
        self.assertLess(luminance, satellite.SATELLITE_MAX_CLEAR_LUMINANCE)

    def test_cloud_fraction_distinguishes_partly_cloudy_from_clear(self):
        _coverage, _luminance, clear_cloud = satellite.png_assessment(CLEAR_PNG)
        _coverage, _luminance, cloudy_cloud = satellite.png_assessment(CLOUDY_PNG)
        self.assertEqual(clear_cloud, 0.0)
        self.assertGreater(cloudy_cloud, satellite.SATELLITE_CLEAR_CLOUD_MAX)

    def test_cloud_cover_exceeds_the_clear_threshold(self):
        coverage, luminance, cloud = satellite.png_assessment(CLOUDY_PNG)
        self.assertEqual(coverage, 1.0)
        self.assertGreater(luminance, satellite.SATELLITE_MAX_CLEAR_LUMINANCE)

    def test_partial_coverage_is_measured_from_alpha(self):
        coverage, _luminance, _cloud = satellite.png_assessment(HALF_PNG)
        self.assertAlmostEqual(coverage, 0.5, delta=0.1)

    def test_webp_keeps_the_raster_size(self):
        webp, width, height = satellite.png_to_webp(CLEAR_PNG)
        self.assertEqual(webp[:4], b"RIFF")
        self.assertEqual((width, height), (16, 16))


class SceneSelectionTests(unittest.IsolatedAsyncioTestCase):
    async def scene(self, images, today=date(2026, 11, 3)):
        async def fake_fetch(_client, day, _bounds, _pixels):
            value = images.get(day)
            if isinstance(value, Exception):
                raise value
            return value if value is not None else BLANK_PNG

        with patch.object(satellite, "_fetch_png", fake_fetch):
            return await satellite.latest_satellite_scene((500000, 6500000, 501000, 6501000), today=today)

    async def test_newest_clear_day_wins(self):
        result = await self.scene({
            "2026-11-03": BLANK_PNG,
            "2026-11-02": BLANK_PNG,
            "2026-11-01": CLEAR_PNG,
            "2026-10-31": CLEAR_PNG,
        })
        self.assertEqual(result, {"date": "2026-11-01", "newest_date": "2026-11-01", "obscured": False, "cloud_fraction": 0.0, "partial_cloud": False})

    async def test_cloudy_newest_day_falls_back_to_older_clear_scene(self):
        result = await self.scene({
            "2026-11-03": CLOUDY_PNG,
            "2026-11-02": BLANK_PNG,
            "2026-11-01": CLEAR_PNG,
        })
        self.assertEqual(result, {"date": "2026-11-01", "newest_date": "2026-11-03", "obscured": False, "cloud_fraction": 0.0, "partial_cloud": False})

    async def test_hazy_days_fall_back_to_the_least_cloudy_scene(self):
        """Kui ükski päev pole päris selge, valitakse väikseima pilveosakaaluga päev."""
        # Hägune päev: keskmine heledus alla pilvelävendi (~85), aga 20% pilti on pilved.
        image = Image.new("RGBA", (16, 16), (30, 30, 30, 255))
        image.paste((200, 200, 200, 255), (0, 0, 16, 9))
        buffer = io.BytesIO()
        image.save(buffer, "PNG")
        hazy = buffer.getvalue()
        overcast = CLOUDY_PNG

        async def fake_fetch(_client, day, _bounds, _pixels):
            return {"2026-11-03": overcast, "2026-11-02": hazy}.get(day, BLANK_PNG)

        with patch.object(satellite, "_fetch_png", fake_fetch):
            result = await satellite.latest_satellite_scene(
                (500000.0, 6580000.0, 500900.0, 6580900.0),
                today=date(2026, 11, 4),
            )
        self.assertEqual(result["date"], "2026-11-02")
        self.assertEqual(result["newest_date"], "2026-11-03")
        self.assertFalse(result["obscured"])
        self.assertTrue(result["partial_cloud"])

    async def test_only_cloudy_scenes_are_still_reported(self):
        result = await self.scene({
            "2026-11-03": CLOUDY_PNG,
            "2026-11-02": BLANK_PNG,
        })
        self.assertEqual(result, {"date": "2026-11-03", "newest_date": "2026-11-03", "obscured": True, "cloud_fraction": 1.0, "partial_cloud": False})

    async def test_no_coverage_returns_no_date(self):
        result = await self.scene({"2026-11-03": BLANK_PNG})
        self.assertEqual(result, {"date": None, "newest_date": None, "obscured": False, "cloud_fraction": None, "partial_cloud": False})

    async def test_every_failed_request_is_an_error_not_an_empty_day(self):
        today = date(2026, 11, 3)
        failures = {
            (today - timedelta(days=offset)).isoformat():
                satellite.SatelliteError("wms")
            for offset in range(satellite.SATELLITE_LOOKBACK_DAYS)
        }
        with self.assertRaises(satellite.SatelliteError):
            await self.scene(failures, today=today)


class SatelliteContextTests(unittest.IsolatedAsyncioTestCase):
    async def test_payload_carries_image_and_leaflet_bounds(self):
        kataster = AsyncMock(return_value={"number": KATASTER_NR, "geometry": PARCEL_GEOMETRY})
        with (
            patch.object(satellite, "query_kataster", kataster),
            patch.object(satellite, "latest_satellite_scene", AsyncMock(return_value={
                "date": "2026-10-27", "newest_date": "2026-10-30", "obscured": False,
                "cloud_fraction": 0.012,
            })),
        ):
            async def fake_fetch(_client, day, _bounds, _pixels):
                self.assertEqual(day, "2026-10-27")
                return CLEAR_PNG

            with patch.object(satellite, "_fetch_png", fake_fetch):
                payload = await satellite.satellite_context(KATASTER_NR)

        self.assertEqual(payload["state"], "available")
        self.assertEqual(payload["date"], "2026-10-27")
        self.assertEqual(payload["newest_date"], "2026-10-30")
        self.assertFalse(payload["obscured"])
        self.assertEqual(payload["cloud_fraction"], 0.012)
        self.assertTrue(payload["image"].startswith("data:image/webp;base64,"))
        self.assertEqual((payload["width"], payload["height"]), (16, 16))
        self.assertGreater(payload["resolution_m"], 1)
        south_west, north_east = payload["bounds"]
        self.assertLess(south_west[0], north_east[0])
        self.assertLess(south_west[1], north_east[1])

    async def test_missing_imagery_reports_empty_without_an_image(self):
        kataster = AsyncMock(return_value={"number": KATASTER_NR, "geometry": PARCEL_GEOMETRY})
        with (
            patch.object(satellite, "query_kataster", kataster),
            patch.object(satellite, "latest_satellite_scene", AsyncMock(return_value={
                "date": None, "newest_date": None, "obscured": False,
            })),
        ):
            payload = await satellite.satellite_context(KATASTER_NR)

        self.assertEqual(payload["state"], "empty")
        self.assertNotIn("image", payload)


class SatelliteEndpointTests(unittest.TestCase):
    def setUp(self):
        from api import cache as api_cache

        api_cache.satellite_cache.clear()

    def test_endpoint_returns_cached_payload(self):
        payload = {
            "parcel_id": KATASTER_NR,
            "state": "available",
            "date": "2026-10-27",
            "image": "data:image/webp;base64,AAAA",
            "bounds": [[59.38, 24.63], [59.39, 24.64]],
        }
        upstream = AsyncMock(return_value=payload)
        with patch.object(api, "satellite_context", upstream):
            client = TestClient(api.app)
            first = client.get(f"/api/satellite/{KATASTER_NR}")
            second = client.get(f"/api/satellite/{KATASTER_NR}")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json()["date"], "2026-10-27")
        self.assertEqual(upstream.await_count, 1)
        self.assertIn("max-age=600", first.headers["cache-control"])

    def test_upstream_failure_is_a_502(self):
        upstream = AsyncMock(side_effect=api.SatelliteError("wms"))
        with patch.object(api, "satellite_context", upstream):
            response = TestClient(api.app).get(f"/api/satellite/{KATASTER_NR}")

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.headers["cache-control"], "private, no-store")

    def test_invalid_kataster_number_is_rejected_before_upstream(self):
        upstream = AsyncMock()
        with patch.object(api, "satellite_context", upstream):
            response = TestClient(api.app).get("/api/satellite/../secret")

        self.assertIn(response.status_code, (400, 404))
        upstream.assert_not_awaited()
