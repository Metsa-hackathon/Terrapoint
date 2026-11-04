"""SEO/GEO lepingud: metaandmed, struktuurne info ja sisulehtede kvaliteet.

Need testid hoiavad ära kõige tavalisemad regressioonid, mis SEO-d vaikselt
rikkuvad: liiga pikk pealkiri, kanoonilise ja og:url lahkuminek, JSON-LD, mis
ei ole päris JSON, sitemap, mis unustab lehe, ja tekst, mis on liiga lühike,
et seda üldse indekseerida.
"""

import json
import re
import unittest
from pathlib import Path

from api import seo as seo_site
from seo_pages import PAGES

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INDEX_DOCUMENT = (PROJECT_ROOT / "index.html").read_text(encoding="utf-8")


def _ld_blocks(document: str) -> list[dict]:
    blocks = re.findall(
        r'<script type="application/ld\+json">([\s\S]*?)</script>', document
    )
    return [json.loads(block) for block in blocks]


def _visible_text(document: str) -> str:
    body = document.split("<body", 1)[1] if "<body" in document else document
    body = re.sub(r"<script[\s\S]*?</script>", " ", body)
    body = re.sub(r"<style[\s\S]*?</style>", " ", body)
    body = re.sub(r"<[^>]+>", " ", body)
    return re.sub(r"\s+", " ", body).strip()


class SeoPageContractTests(unittest.TestCase):
    def test_every_page_has_a_short_unique_title_and_description(self):
        titles = [page.title for page in PAGES]
        descriptions = [page.description for page in PAGES]
        self.assertEqual(len(set(titles)), len(titles), "pealkirjad peavad olema unikaalsed")
        self.assertEqual(len(set(descriptions)), len(descriptions))
        for page in PAGES:
            with self.subTest(slug=page.slug):
                self.assertLessEqual(len(page.title), 60, page.title)
                self.assertGreaterEqual(len(page.description), 50)
                self.assertLessEqual(len(page.description), 160, page.description)
                self.assertIn("Terrapoint", page.title)
                self.assertTrue(page.h1)
                self.assertTrue(page.lede)

    def test_pages_are_long_enough_to_index(self):
        for page in PAGES:
            with self.subTest(slug=page.slug):
                words = len(_visible_text(seo_site.render_page(page)).split())
                self.assertGreaterEqual(words, 350, f"{page.slug}: {words} sõna")
                self.assertTrue(page.sections, "lehel peab olema sisu")
                self.assertTrue(page.sources, "lehel peavad olema allikad")

    def test_head_tags_agree_with_each_other(self):
        for page in PAGES:
            document = seo_site.render_page(page)
            url = f"https://terrapoint.ee/{page.slug}"
            with self.subTest(slug=page.slug):
                self.assertEqual(document.count("<title>"), 1)
                self.assertEqual(document.count('name="description"'), 1)
                self.assertEqual(document.count('rel="canonical"'), 1)
                self.assertIn(f'<link rel="canonical" href="{url}">', document)
                self.assertIn(f'<meta property="og:url" content="{url}">', document)
                self.assertIn(f'<meta property="og:title" content="{page.title}">', document)
                self.assertIn(f'<meta name="twitter:title" content="{page.title}">', document)
                self.assertNotIn('name="keywords"', document)
                self.assertNotIn("twitter:site", document)
                self.assertIn('<html lang="et">', document)

    def test_json_ld_is_valid_and_matches_the_page(self):
        for page in PAGES:
            document = seo_site.render_page(page)
            blocks = _ld_blocks(document)
            with self.subTest(slug=page.slug):
                self.assertEqual(len(blocks), 1)
                graph = blocks[0]["@graph"]
                types = [node["@type"] for node in graph]
                self.assertIn("WebPage", types)
                self.assertIn("BreadcrumbList", types)
                webpage = next(node for node in graph if node["@type"] == "WebPage")
                self.assertEqual(webpage["url"], f"https://terrapoint.ee/{page.slug}")
                self.assertEqual(webpage["name"], page.title)
                self.assertEqual(webpage["dateModified"], page.updated)
                self.assertIn(page.h1, document, "headline peab olema lehel nähtav")

    def test_visible_faq_matches_the_schema_answers(self):
        for page in PAGES:
            if not page.faq:
                continue
            document = seo_site.render_page(page)
            text = _visible_text(document)
            for item in page.faq:
                with self.subTest(slug=page.slug, question=item.question):
                    self.assertIn(item.question, document)
                    self.assertIn(item.answer, text)

    def test_pages_link_to_each_other(self):
        for page in PAGES:
            document = seo_site.render_page(page)
            with self.subTest(slug=page.slug):
                self.assertGreaterEqual(document.count('href="/'), 8, "sisemised lingid puuduvad")
                for slug, _label in page.related:
                    self.assertIn(f'href="/{slug}"', document)
                self.assertIn('href="/"', document)


class SiteLevelSeoContractTests(unittest.TestCase):
    def test_index_html_head_limits_and_no_duplicates(self):
        title = re.search(r"<title>([^<]+)</title>", INDEX_DOCUMENT).group(1)
        description = re.search(
            r'<meta name="description" content="([^"]+)"', INDEX_DOCUMENT
        ).group(1)
        self.assertLessEqual(len(title), 60, title)
        self.assertLessEqual(len(description), 160, description)
        self.assertEqual(INDEX_DOCUMENT.count("<title>"), 1)
        self.assertEqual(INDEX_DOCUMENT.count('name="description"'), 1)
        self.assertEqual(INDEX_DOCUMENT.count('rel="canonical"'), 1)
        self.assertNotIn('name="keywords"', INDEX_DOCUMENT)
        self.assertNotIn("twitter:site", INDEX_DOCUMENT)
        self.assertNotIn('hreflang="en"', INDEX_DOCUMENT)
        # üks nähtav h1; tulemusvaate pealkiri on h2
        self.assertEqual(INDEX_DOCUMENT.count("<h1"), 1)

    def test_index_json_ld_is_valid_json_with_dates(self):
        blocks = _ld_blocks(INDEX_DOCUMENT)
        self.assertEqual(len(blocks), 1)
        graph = blocks[0]["@graph"]
        types = {node["@type"] for node in graph}
        self.assertEqual(types, {"WebSite", "Organization", "WebApplication", "FAQPage"})
        app = next(node for node in graph if node["@type"] == "WebApplication")
        self.assertIn("dateModified", app)
        self.assertIn("datePublished", app)

    def test_index_visible_faq_covers_every_schema_question(self):
        """Google nõuab, et FAQPage vastaks lehel nähtavale tekstile."""
        graph = _ld_blocks(INDEX_DOCUMENT)[0]["@graph"]
        faq = next(node for node in graph if node["@type"] == "FAQPage")
        text = _visible_text(INDEX_DOCUMENT)
        for item in faq["mainEntity"]:
            with self.subTest(question=item["name"]):
                self.assertIn(item["name"], text)
                self.assertIn(item["acceptedAnswer"]["text"], text)

    def test_robots_allows_ai_search_crawlers_and_blocks_api(self):
        robots = seo_site.robots_txt()
        for agent in (
            "OAI-SearchBot",
            "Claude-SearchBot",
            "PerplexityBot",
            "GPTBot",
            "Bingbot",
            "Google-Extended",
        ):
            with self.subTest(agent=agent):
                self.assertIn(f"User-agent: {agent}", robots)
        self.assertIn("Disallow: /api/", robots)
        self.assertIn("Sitemap: https://terrapoint.ee/sitemap.xml", robots)

    def test_llms_txt_lists_every_page(self):
        llms = seo_site.llms_txt()
        self.assertTrue(llms.startswith("# Terrapoint"))
        for page in PAGES:
            self.assertIn(f"https://terrapoint.ee/{page.slug}", llms)

    def test_every_page_is_reachable_from_the_homepage(self):
        for page in PAGES:
            with self.subTest(slug=page.slug):
                self.assertIn(f'href="/{page.slug}"', INDEX_DOCUMENT)


if __name__ == "__main__":
    unittest.main()
