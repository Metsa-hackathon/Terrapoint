"""Staatilise sisu kohaletoimetamise lepingud.

Leht, manifest ja ikoon peavad olema kätte saadavad ilma 404-ta (brauser
logis iga lehelaadimisel viga) ning lehe HTML peab olema servivahemälus,
et iga külastus ei käivitaks uut serverifunktsiooni.
"""

import json
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from api.index import app

PROJECT_ROOT = Path(__file__).parent.parent
VERCEL_CONFIG = json.loads((PROJECT_ROOT / "vercel.json").read_text(encoding="utf-8"))


def _cache_rule(source: str) -> str:
    rule = next(rule for rule in VERCEL_CONFIG["headers"] if rule["source"] == source)
    return next(
        header["value"]
        for header in rule["headers"]
        if header["key"] == "Cache-Control"
    )


class StaticDeliveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def test_index_document_is_cacheable_at_the_edge(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        cache_control = response.headers["cache-control"]
        self.assertIn("s-maxage=60", cache_control)
        self.assertIn("stale-while-revalidate=600", cache_control)
        # Brauser kinnitab dokumenti alati, et deploy kohe nähtavaks muutuks.
        self.assertIn("max-age=0", cache_control)
        self.assertIn(
            "s-maxage=60",
            response.headers.get("cdn-cache-control", ""),
            "Verceli serv vahemälu juhitakse CDN-Cache-Control'iga",
        )

    def test_webmanifest_is_served_with_manifest_content_type(self):
        response = self.client.get("/site.webmanifest")

        self.assertEqual(response.status_code, 200)
        self.assertIn("manifest+json", response.headers["content-type"])
        self.assertEqual(response.json()["short_name"], "Terrapoint")

    def test_favicon_request_redirects_to_the_svg_icon(self):
        response = self.client.get("/favicon.ico", follow_redirects=False)

        self.assertEqual(response.status_code, 307)
        self.assertEqual(response.headers["location"], "/static/favicon.svg")

    def test_static_font_and_vendor_assets_are_cached_for_long(self):
        # Fontide URL-id pole versioneeritud, seega neid ei muudeta immutabelks.
        self.assertIn("max-age=2592000", _cache_rule("/static/fonts/(.*)"))
        self.assertNotIn("immutable", _cache_rule("/static/fonts/(.*)"))
        # Vendor-failid on versiooniga URL-is, seega võivad olla immutabelsed.
        self.assertIn("immutable", _cache_rule("/static/vendor/(.*)"))

    def test_historical_api_docs_urls_still_reach_the_documentation(self):
        # `cleanUrls` lõikab .html-laienduse, nii et /api-docs.html jõuab
        # /api-docs aadressile — ilma marsruudita lõppes see 404-na.
        for path in ("/api-docs", "/api-docs.html", "/static/api-docs"):
            with self.subTest(path=path):
                response = self.client.get(path, follow_redirects=False)

                self.assertEqual(response.status_code, 308)
                self.assertEqual(response.headers["location"], "/api/docs")

        redirect_sources = {
            rule["source"] for rule in VERCEL_CONFIG.get("redirects", [])
        }
        self.assertIn("/api-docs", redirect_sources)
        self.assertIn("/static/api-docs", redirect_sources)

    def test_unversioned_static_assets_still_revalidate(self):
        cache_control = _cache_rule("/static/(.*)")

        self.assertNotIn("immutable", cache_control)
        self.assertIn("must-revalidate", cache_control)


if __name__ == "__main__":
    unittest.main()
