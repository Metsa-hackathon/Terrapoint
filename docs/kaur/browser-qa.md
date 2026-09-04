# Iframe-widget'i brauseri QA

Kontrollitud 16.08.2026 Playwrighti juhitud Chromiumis lokaalsel FastAPI
serveril. See on funktsionaalne smoke-test, mitte sõltumatu WCAG audit ega
Keskkonnaportaali staging'u vastuvõtt.

Klaviatuuri-, accessibility-tree-, valideerimis- ja kontrastitõend on eraldi
`accessibility-qa.md` ning `evaluation/accessibility_results.md` failides.

## Kontrollitud vood

| Kontroll | Tulemus |
|---|---|
| demo parent → `/embed/forest` iframe | läbitud |
| loomuliku küsimuse submit | läbitud; `answer_rendered`, olekuteade ja fookus vastuse H2-l |
| vastus + metoodika + piirangud + kaks ametlikku linki | läbitud |
| arv, aasta, ühik ja suhteline viga | nähtavad ühes vastuses |
| katastritunnus `52901:001:1234` | ei loonud kinnistuarvu; kuvas Terrapointi ja Metsaportaali toimingud |
| loaderi `postMessage` origin/source kontroll | lepingutest + brauseris kõrguse muutus |
| desktop | frame'i `clientHeight` ja sisu `scrollHeight` võrdsed |
| 320 px viewport (iframe 286 px demo gutter'i tõttu) | parent ja iframe `scrollWidth == clientWidth`; horisontaalset kerimist pole |
| pikk mobiilivastus | pärast parandust frame 2256 px ja sisu 2256 px; nested scroll puudub |
| konsool | 0 viga; same-origin demo kohta 1 Chromiumi sandbox-hoiatus |

Hoiatus tekib, sest lokaalne demo ja iframe on testis sama origin ning sandbox
sisaldab korraga `allow-scripts` ja API jaoks vajalikku `allow-same-origin`.
Päris integratsioonis on Keskkonnaportaal ja Terrapoint eri originid. KAURi
staging'us tuleb kinnitada, et parent'i CSP, reverse proxy ja CMS ei muuda
turvapiiri.

## Visuaalsed tõendid

- `output/playwright/forest-widget-desktop.png`
- `output/playwright/forest-widget-mobile.png`
- `output/playwright/forest-widget-keyboard-focus.png`

Visuaalsel vaatlusel on nähtav prototüübi/sisukinnituse olek, küsimuse label,
klaviatuurifookuse siht, vastuse liik, confidence-silt, ametlike allikate
pealkirjad/ajaseis/locator ning haldusotsuse disclaimer.

## Staging'us veel kohustuslik

- axe või samaväärne automaatkontroll ja käsitsi ekraanilugeja test;
- 200% zoom, Windows High Contrast ja brauserite Firefox/Safari test;
- päris Keskkonnaportaali CMS-i klaviatuuri- ja fookusejärjekord;
- välise parent-origini CSP ja `postMessage` test;
- koormuse, p95 latentsuse ja katkestuse UI test.
