# Rakendustaseme turvapiiri ülevaade

Kontrollitud 16.08.2026. See on prototüübi threat-model'i ja automaattestide
raport, mitte sõltumatu penetratsioonitest ega KAURi infoturbe heakskiit.

## Ründeala ja tõendid

| Risk | Kontroll | Tõend |
|---|---|---|
| Clickjacking / liiga lai embed | ainult `/embed/forest` ei saada XFO-d; täpne HTTPS `frame-ancestors` allowlist; kõik muu `DENY/'none'` | middleware-, Vercel- ja endpointitestid |
| Cross-origin API kuritarvitus | JSON-only; `Sec-Fetch-Site: cross-site` ning tundmatu `Origin` → 403; CORS ei peegelda ründaja originit | API integratsioonitest |
| Ressursikurnamine | 16 KiB body, küsimus 3–500, top_k 1–5, 30 päringut/min/IP, 429 + Retry-After | body- ja rate-limit test |
| SSRF allika kaudu | ainult HTTPS ja nimeline ametlike hostide allowlist; localhost, metadata IP, HTTP ja tundmatu host lükatakse laadimisel tagasi | allikaregistri negatiivtest |
| Prompt injection / mudeliviide | ingest'i sisu ei ole juhis; extractive fallback; generaatori viide peab olema retrieval-kontekstis | adversariaalne eval + generaatori test |
| XSS vastuses | brauser kasutab ainult `textContent`/DOM elemente; puudub `innerHTML`, inline script/event ja eval | frontend lepingutest + range CSP |
| Võtmeleke | extractive provider ei vaja võtit; provider'i seade/võtmenimi puudub HTML/JS-ist; serveriliides ei tagasta konfiguratsiooni | staatiline test + meta API |
| Kinnistu-/piiratud info | katastritunnus suunatakse; SMI-st kinnistuarvu ei looda; piiratud liigiandmeid korpuses pole | intent-, brauseri- ja allikapiiri test |
| Privaatsus | küsimuseteksti ei logita rakenduse tasemel; telemeetria vaikimisi väljas; skeem keelab tundmatud/tekstiväljad | meta API + `telemetry.schema.json` test |
| Kahjulik postMessage | child saadab ainult kõrguse; parent kontrollib `event.origin` ja `event.source`, kõrgus arvuline ja 480–6000 | loaderi lepingutest + Chromium QA |

## Käivitatud kontrollid

```bash
python3 -m pytest -q
ruff check config.py services/forestry_search.py services/forestry_generator.py \
  scripts/evaluate_forestry_search.py scripts/validate_forestry_knowledge.py \
  scripts/compare_live_portal_snapshot.py tests/test_forestry_search.py
node --check static/embed/widget.js
node --check static/embed/loader.js
python3 scripts/evaluate_forestry_safety.py --write
python3 scripts/compare_live_portal_snapshot.py --write
bandit -q services/forestry_search.py services/forestry_generator.py \
  scripts/evaluate_forestry_search.py scripts/validate_forestry_knowledge.py
pip-audit -r requirements.txt
```

Tulemus: testid, sihitud lint/JS süntaks ja Bandit läbisid; `pip-audit` teatas
„No known vulnerabilities found”.

Külmutatud ohutuskogumites säilitati kaks ebaõnnestunud iteratsiooni (v1
15/16, v2 15/18). Pärast URL-i/valdkonna/markup'i algpõhjuse parandusi läbis
uute sõnastustega v3 esimese jooksu **20/20**. Detailid ja hash'id on
`evaluation/README.md` ning `evaluation/safety_results.json` failis.
Masinloetav `evaluation/forestry_safety_coverage.json` seob kõik 20 juhtu 12
nõutud kontrollalaga; evaluaator kontrollib ID-de/tag'ide täielikkust ja lisab
maatriksi hash'i raportisse. Valim on boundary-partition regressioonikogum,
mitte fuzzing ega tõend kogu ründeruumi ammendamisest.

## Teadlikud piirid enne pilooti

- teha sõltumatu app-level pentest staging'us, sh reverse proxy/Vercel edge,
  cache, CORS preflight, request smugglingu asjakohasus ja tegelik rate-limit
  mitme instantsi korral;
- in-memory rate limiter ei ole mitme protsessi/regioni ühine — tootmises vaja
  edge/WAF või jagatud atomaarset limiterit;
- kontrollida, et proxy ei lisa embed-route'ile globaalset XFO `DENY` päist;
- uue mudeliadapteri puhul testida provider outage, tokeni-/kulupiir,
  secret-store, andmete asukoht, säilitamine ja mudelipoolne prompt injection;
- teha KAURi DPIA/infoturbe otsus ning sõltumatu WCAG 2.2 AA audit;
- logide ja kasutajate vabasõnalise tagasiside õiguslik alus on otsustamata.

Nende puudumine ei blokeeri lokaalse otsustusprototüübi üleandmist, kuid
blokeerib avaliku tootmis-iframe'i.
