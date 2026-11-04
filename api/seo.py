"""Serveripoolne renderdaja Terrapointi sisulehtedele, sitemapile ja llms.txt-le.

Miks see olemas on: rakenduse tulemusvaade tekib alles JavaScriptiga, seega
otsingumootor ja AI-kraaler nägid varem ainult turundusteksti. Sisu tuleb
serverist HTML-ina — üks fail, ühed metaandmed, üks JSON-LD plokk lehe kohta.
"""

from __future__ import annotations

import html as _html
import json

from seo_pages import PAGES, SITE_NAME, SITE_TAGLINE, SITE_URL, CONTACT_EMAIL, SeoPage

# Kohatäitja, mida asendab deploy-skript (või jääb vaikimisi): staatiliste
# failide vahemäluvõti.
CSS_REVISION = "1"

ASSET_CSS = ("/static/css/fonts.css", "/static/css/content.css")
FONT_PRELOADS = (
    "/static/fonts/bricolage-grotesque-latin.woff2",
    "/static/fonts/geist-latin.woff2",
)

ORG_ID = f"{SITE_URL}/#organization"
WEBSITE_ID = f"{SITE_URL}/#website"


def esc(value: str) -> str:
    return _html.escape(value, quote=True)


def page_url(page: SeoPage) -> str:
    return f"{SITE_URL}/{page.slug}"


def _head(page: SeoPage) -> str:
    url = page_url(page)
    og_image = f"{SITE_URL}{page.og_image}"
    parts = [
        "<!DOCTYPE html>",
        '<html lang="et">',
        "<head>",
        '    <meta charset="UTF-8">',
        '    <meta name="viewport" content="width=device-width, initial-scale=1.0">',
        f"    <title>{esc(page.title)}</title>",
        f'    <meta name="description" content="{esc(page.description)}">',
        '    <meta name="robots" content="index, follow, max-image-preview:large, '
        'max-snippet:-1, max-video-preview:-1">',
        f'    <meta name="author" content="{esc(SITE_NAME)}">',
        '    <meta name="theme-color" content="#f3f4f6">',
        '    <meta name="color-scheme" content="light">',
        f'    <link rel="canonical" href="{url}">',
        f'    <link rel="alternate" hreflang="et" href="{url}">',
        f'    <link rel="alternate" hreflang="x-default" href="{url}">',
        '    <link rel="icon" type="image/svg+xml" href="/static/favicon.svg">',
        '    <link rel="apple-touch-icon" href="/static/favicon.svg">',
        '    <link rel="manifest" href="/site.webmanifest">',
        f'    <meta property="og:type" content="article">',
        f'    <meta property="og:site_name" content="{esc(SITE_NAME)}">',
        '    <meta property="og:locale" content="et_EE">',
        f'    <meta property="og:title" content="{esc(page.title)}">',
        f'    <meta property="og:description" content="{esc(page.description)}">',
        f'    <meta property="og:url" content="{url}">',
        f'    <meta property="og:image" content="{og_image}">',
        f'    <meta property="og:image:secure_url" content="{og_image}">',
        '    <meta property="og:image:type" content="image/png">',
        '    <meta property="og:image:width" content="1200">',
        '    <meta property="og:image:height" content="630">',
        f'    <meta property="og:image:alt" content="{esc(page.h1 + ": " + SITE_NAME)}">',
        '    <meta property="article:published_time" content="' + page.published + 'T09:00:00+02:00">',
        '    <meta property="article:modified_time" content="' + page.updated + 'T09:00:00+02:00">',
        '    <meta name="twitter:card" content="summary_large_image">',
        f'    <meta name="twitter:title" content="{esc(page.title)}">',
        f'    <meta name="twitter:description" content="{esc(page.description)}">',
        f'    <meta name="twitter:image" content="{og_image}">',
        f'    <meta name="twitter:image:alt" content="{esc(page.h1)}">',
    ]
    for href in FONT_PRELOADS:
        parts.append(
            f'    <link rel="preload" href="{href}" as="font" type="font/woff2" crossorigin>'
        )
    for href in ASSET_CSS:
        parts.append(f'    <link rel="stylesheet" href="{href}?r={CSS_REVISION}">')
    parts.append("    " + _json_ld(page))
    parts.append("</head>")
    return "\n".join(parts)


def _json_ld(page: SeoPage) -> str:
    url = page_url(page)
    graph: list[dict] = [
        {
            "@type": "WebPage",
            "@id": f"{url}#webpage",
            "url": url,
            "name": page.title,
            "headline": page.h1,
            "description": page.description,
            "inLanguage": "et",
            "datePublished": page.published,
            "dateModified": page.updated,
            "isPartOf": {"@id": WEBSITE_ID},
            "publisher": {"@id": ORG_ID},
            "about": {"@type": "Thing", "name": page.h1},
            "breadcrumb": {"@id": f"{url}#breadcrumb"},
            "primaryImageOfPage": {
                "@type": "ImageObject",
                "url": f"{SITE_URL}{page.og_image}",
                "width": 1200,
                "height": 630,
            },
        },
        {
            "@type": "BreadcrumbList",
            "@id": f"{url}#breadcrumb",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": 1,
                    "name": "Terrapoint",
                    "item": f"{SITE_URL}/",
                },
                {
                    "@type": "ListItem",
                    "position": 2,
                    "name": page.h1,
                    "item": url,
                },
            ],
        },
    ]
    if page.slug == "andmeallikad":
        graph.append(
            {
                "@type": "Dataset",
                "@id": f"{url}#dataset",
                "name": "Terrapointi koondatud metsa- ja kinnistuandmed",
                "description": (
                    "Avalikest registritest (Maa- ja Ruumiamet, Metsaregister, EELIS, "
                    "Kultuurimälestiste register, EstHub) päritud andmed, mis "
                    "koondatakse katastriüksuse kaupa ühte vaatesse."
                ),
                "creator": {"@id": ORG_ID},
                "isAccessibleForFree": True,
                "inLanguage": "et",
                "keywords": ["metsaandmed", "kataster", "metsaregister", "eraldised"],
                "variableMeasured": [
                    "elus puistutagavara",
                    "puidu hinnavahemik",
                    "süsinikuvaru",
                    "metsateatised",
                    "kitsendused",
                ],
            }
        )
    payload = {"@context": "https://schema.org", "@graph": graph}
    return (
        '<script type="application/ld+json">\n'
        + json.dumps(payload, ensure_ascii=False, indent=2)
        + "\n    </script>"
    )


def _header() -> str:
    nav = "".join(
        f'<a href="/{page.slug}">{esc(_nav_label(page))}</a>' for page in PAGES
    )
    return (
        '<header class="site-header">'
        '<a class="brand" href="/" aria-label="Terrapoint, avaleht">Terra<span>Point</span></a>'
        f'<nav class="site-nav" aria-label="Sisu">{nav}</nav>'
        "</header>"
    )


def _nav_label(page: SeoPage) -> str:
    labels = {
        "metsaandmed-katastritunnuse-jargi": "Metsaandmed",
        "metsa-hind": "Metsa hind",
        "metsatoetused": "Toetused",
        "eudr-geolokatsioon": "EUDR",
        "andmeallikad": "Andmeallikad",
        "kkk": "KKK",
    }
    return labels.get(page.slug, page.h1)


def _footer(page: SeoPage) -> str:
    links = "".join(
        f'<li><a href="/{other.slug}">{esc(other.h1)}</a></li>'
        for other in PAGES
        if other.slug != page.slug
    )
    return (
        '<footer class="site-footer">'
        f'<p><strong>{esc(SITE_NAME)}</strong>: {esc(SITE_TAGLINE)}. '
        "Andmed pärinevad avalikest registritest; Terrapoint ei asenda ametlikku "
        "väljavõtet ega hinnangut.</p>"
        f'<nav aria-label="Terrapointi teised juhendid"><ul class="footer-links">{links}</ul></nav>'
        f'<p class="footer-links-extra"><a href="/">Ava tööriist</a> · '
        f'<a href="/api/docs">API dokumentatsioon</a> · '
        f'<a href="/humans.txt">Meist ja allikatest</a> · '
        f'<a href="mailto:{esc(CONTACT_EMAIL)}">{esc(CONTACT_EMAIL)}</a></p>'
        f'<p class="footer-meta">Avaldatud {esc(_et_date(page.published))} · '
        f"uuendatud {esc(_et_date(page.updated))}</p>"
        "</footer>"
    )


def _et_date(iso: str) -> str:
    parts = iso.split("-")
    if len(parts) != 3:
        return iso
    return f"{parts[2]}.{parts[1]}.{parts[0]}"


def _breadcrumbs(page: SeoPage) -> str:
    return (
        '<nav class="breadcrumbs" aria-label="Leivapuru">'
        '<ol>'
        '<li><a href="/">Terrapoint</a></li>'
        f'<li aria-current="page">{esc(page.h1)}</li>'
        "</ol>"
        "</nav>"
    )


def _section(section) -> str:
    out = [f"<h2>{esc(section.heading)}</h2>"]
    for paragraph in section.paragraphs:
        out.append(f"<p>{esc(paragraph)}</p>")
    if section.bullets:
        out.append("<ul>")
        out.extend(f"<li>{esc(item)}</li>" for item in section.bullets)
        out.append("</ul>")
    if section.table_head:
        out.append('<div class="table-wrap"><table>')
        out.append(
            "<thead><tr>"
            + "".join(f"<th scope=\"col\">{esc(cell)}</th>" for cell in section.table_head)
            + "</tr></thead>"
        )
        out.append("<tbody>")
        for row in section.table_rows:
            out.append(
                "<tr>"
                + "".join(f"<td>{esc(cell)}</td>" for cell in row)
                + "</tr>"
            )
        out.append("</tbody></table></div>")
    return "\n".join(out)


def render_page(page: SeoPage) -> str:
    """Täielik HTML-dokument ühe sisulehe kohta."""
    body: list[str] = [
        _header(),
        '<main id="sisu">',
        _breadcrumbs(page),
        f"<h1>{esc(page.h1)}</h1>",
        f'<p class="lede">{esc(page.lede)}</p>',
        '<aside class="answer-box" aria-label="Lühivastus">',
        '<p class="answer-label">Lühivastus</p>',
        f"<p>{esc(page.summary)}</p>",
        "</aside>",
    ]
    for section in page.sections:
        body.append(_section(section))

    if page.faq:
        body.append("<h2>Korduma kippuvad küsimused</h2>")
        body.append('<div class="faq">')
        for item in page.faq:
            body.append("<details>")
            body.append(f"<summary>{esc(item.question)}</summary>")
            body.append(f"<p>{esc(item.answer)}</p>")
            body.append("</details>")
        body.append("</div>")

    if page.sources:
        body.append("<h2>Allikad</h2>")
        body.append('<ul class="sources">')
        for source in page.sources:
            note = f": {esc(source.note)}" if source.note else ""
            body.append(
                f'<li><a href="{esc(source.url)}" target="_blank" rel="noopener noreferrer">'
                f"{esc(source.label)}</a>{note}</li>"
            )
        body.append("</ul>")

    if page.related:
        body.append("<h2>Loe edasi</h2>")
        body.append('<ul class="related">')
        for slug, label in page.related:
            body.append(f'<li><a href="/{esc(slug)}">{esc(label)}</a></li>')
        body.append("</ul>")

    body.append(
        '<aside class="cta" aria-label="Terrapointi proovimine">'
        "<h2>Proovi oma kinnistut</h2>"
        "<p>Sisesta katastritunnus või aadress ja vaata, mida registrid selle "
        "kinnistu kohta ütlevad, koos allikate ja ajaseisuga.</p>"
        '<p><a class="cta-button" href="/">Ava Terrapoint</a></p>'
        "</aside>"
    )
    body.append(
        f'<p class="page-dates">Avaldatud {esc(_et_date(page.published))} · '
        f"uuendatud {esc(_et_date(page.updated))}</p>"
    )
    body.append("</main>")
    body.append(_footer(page))

    return "\n".join([_head(page), "<body>", *body, "</body>", "</html>", ""])


def sitemap_xml() -> str:
    """Sitemap kõigist indekseeritavatest URL-idest, uusima lastmod'iga."""
    updated = max(page.updated for page in PAGES)
    entries = [
        f"""  <url>
    <loc>{SITE_URL}/</loc>
    <lastmod>{updated}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
    <image:image>
      <image:loc>{SITE_URL}/static/og-image.png</image:loc>
      <image:title>Terrapoint: Eesti metsaandmete analüüs</image:title>
    </image:image>
  </url>"""
    ]
    for page in PAGES:
        entries.append(
            f"""  <url>
    <loc>{page_url(page)}</loc>
    <lastmod>{page.updated}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>"""
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n'
        '        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n'
        + "\n".join(entries)
        + "\n</urlset>\n"
    )


def llms_txt() -> str:
    """llms.txt: kokkuvõte masinloetaval kujul (Google'ile kaalu ei anna)."""
    lines = [
        f"# {SITE_NAME}",
        f"> {SITE_TAGLINE}. Avalikest registritest koondatud metsa- ja kinnistuandmed, "
        "iga näitaja juures allikas, ajaseis ja piirangud.",
        "",
        "Terrapoint is a free Estonian web tool that aggregates public forest and "
        "cadastral registry data (Maa- ja Ruumiamet, Metsaregister, EELIS, "
        "Kultuurimälestiste register, EstHub Sentinel-2) for a single cadastral "
        "unit, with source and freshness metadata per figure.",
        "",
        "## Key facts",
        f"- Tool: {SITE_URL}/ (free, no login)",
        "- Coverage: all Estonian cadastral units present in public registries",
        "- Data: cadastral parcel, forest stands, growing stock, indicative timber "
        "price range, carbon stock, restrictions, forest notices, subsidies, "
        "EUDR geolocation export",
        "- Limits: indicative ranges only; not an official valuation, not a "
        "forest notice, not an EUDR due-diligence statement",
        f"- Contact: {CONTACT_EMAIL}",
        "- Award: „Metsikult andmetes 2026” hackathon winner (Keskkonnaagentuur)",
        "",
        "## Pages",
    ]
    for page in PAGES:
        lines.append(f"- [{page.h1}]({page_url(page)}): {page.description}")
    lines += [
        "",
        "## Machine-readable",
        f"- API docs: {SITE_URL}/api/docs",
        f"- Sitemap: {SITE_URL}/sitemap.xml",
        f"- Security contact: {SITE_URL}/.well-known/security.txt",
        "",
    ]
    return "\n".join(lines)


def robots_txt() -> str:
    """robots.txt: otsingumootorid + AI-otsingu kraalerid eraldi gruppidena.

    AI-kraalerite nimetamine on dokumenteerimise mõte: `OAI-SearchBot`,
    `Claude-SearchBot` ja `PerplexityBot` otsustavad, kas sisu saab AI-otsingus
    viidata; treeningkraalerid (GPTBot, ClaudeBot, CCBot) on eraldi rida, sest
    need puudutavad litsentsi, mitte nähtavust.
    """
    groups = [
        ("*", ["Allow: /", "Disallow: /api/"]),
        ("GPTBot", ["Allow: /"]),
        ("OAI-SearchBot", ["Allow: /"]),
        ("ChatGPT-User", ["Allow: /"]),
        ("ClaudeBot", ["Allow: /"]),
        ("Claude-SearchBot", ["Allow: /"]),
        ("Claude-User", ["Allow: /"]),
        ("PerplexityBot", ["Allow: /"]),
        ("Perplexity-User", ["Allow: /"]),
        ("Google-Extended", ["Allow: /"]),
        ("Applebot", ["Allow: /"]),
        ("Bingbot", ["Allow: /"]),
        ("CCBot", ["Allow: /"]),
    ]
    lines = ["# terrapoint.ee robots.txt", "# Eesti metsaandmete analüüsi tööriist", ""]
    for agent, rules in groups:
        lines.append(f"User-agent: {agent}")
        lines.extend(rules)
        lines.append("")
    lines += [
        f"Sitemap: {SITE_URL}/sitemap.xml",
        f"# llms.txt: {SITE_URL}/llms.txt",
        f"Security: {SITE_URL}/.well-known/security.txt",
        "",
    ]
    return "\n".join(lines)
