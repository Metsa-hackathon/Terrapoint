# Terrapoint — Metsaportaal

## Kirjeldus
Metsa väärtuse ja andmete analüüsi veebirakendus. FastAPI backend + HTML/CSS/JS frontend.

## Olulised käsud
- **Backend käivitamine:** `python3 -m uvicorn api.index:app --host 0.0.0.0 --port 8099`
- **Paigaldus:** `pip install -r requirements.txt`

## Git konventsioonid
- Commit tüübid: `feat:` (uus funktsioon), `fix:` (parandus), `style:` (CSS/UI), `refactor:`
- Commit keel: eesti keel
- Alati `git pull --rebase` enne `git push` — remote võib sõbra muudatusi sisaldada
- Push ainult siis kui testid/ehitus töötab

## API struktuur (ülevaade)
- `api/` - API endpointid
- `services/` - äriloogika
- `calculators/` - arvutusmoodulid
- `spatial/` - GeoJSON/ruumilised andmed
- `static/` - staatilised failid (CSS, JS, pildid)
- `logos/` - logo pildid

## Levinud veaolukorrad
- Git push võib ebaõnnestuda kui remote on ees. Tee alati `git pull --rebase` esimesena.
- Kui curl/wget alamkäsk ebaõnnestub, proovi alternatiivset URL-i või meetodit.
- Kui bash käsk tagastab "exit code 1", ära proovi sama käsku uuesti — proovi alternatiivset lahendust.

## Keskkond
- **Tootmise domeen**: `terrapoint.ee` ja `www.terrapoint.ee` (Cloudflare, alates 2026-11-03).
  Registripidaja on Veebimajutus (Elkdata OÜ); nimeserverid on `brady.ns.cloudflare.com` ja
  `elma.ns.cloudflare.com`. Vanad resolverid hoiavad Verceli NS-e vahemälus kuni 6 h (TTL 21600).
- Teekond: Cloudflare (tsoon `terrapoint.ee`) → Cloudflare Tunnel `home-apps` →
  `http://127.0.0.1:8099` (uvicorn, systemd `terrapoint-api`). Ingress: `terrapoint.ee` ja
  `www.terrapoint.ee` otse originisse, catch-all `http_status:404`. Ingressi muudetakse
  Cloudflare'i tunneli konfiguratsioonis (API), mitte kohaliku failina.
- Deploy: push `master` → koduserveri `terrapoint-deploy.timer` (`/root/projects/terrapoint/deploy.sh`).
  Vercel ehitab master'it veel, aga ei teeninda domeeni.
- AI-vestlus (`/api/chat`, SSE) töötab originil: gateway token ja snapshot key loetakse failidest (`TERRAPOINT_CODEX_GATEWAY_TOKEN_FILE`, `TERRAPOINT_CHAT_SNAPSHOT_KEY_FILE`); originil ei ole Vercel'i env-muutujaid.
- Cloudflare'i sätted, mida ära muuda: e-posti kaitse VÄLJAS (muudab `mailto:` lingi),
  Browser Cache TTL = respect existing headers (muidu 4 h, origin 1 h), Always Use HTTPS SEES,
  DNSSEC VÄLJAS (`.ee`-s DS puudub; kui lubad, lisa DS Veebimajutusse),
  Browser Integrity Check VÄLJAS (2026-11-03: `libwww-perl` UA sai 403 error 1010, API skriptid peavad töötama),
  Security level `medium` JÄTA (threat-score challenge kaitseb kodu-originit; kui API klient saab 403 `cf-mitigated: challenge`, langeta `low`-ks).
- Veebimajutuse paneel: `admin.veebimajutus.ee` (Parool, ID-kaart, Mobiil-ID või Smart-ID; Google ei ole valik).
- `terrapoint.vercel.app` suunab `vercel.json` redirectiga (308) terrapoint.ee-le.
- Vercel proxyb `/api/search/` ja `/api/map-context/` päringud `terrapoint.arle.top`-i
  (`DEFAULT_BACKEND_API_URL`; Traefik `coolify-proxy` → `172.20.0.1:8001`). Origin seda teed ei vaja.
- Backendi URL-i saab muuta `TERRAPOINT_BACKEND_API_URL` keskkonnamuutujaga.
- Home-serveri API kuulab ainult `127.0.0.1:8099`; socat ingress on `deploy/home/`.
- **Kaardile joonistatakse ainult krundi sees olev osa kattuvast kihist.** `_map_context_core`
  lõikab iga kattuvuse `_clip_feature_to_parcel`-iga krundi geomeetria piiresse (shapely
  `intersection`), sest kattuvuse mõiste on „mis jääb sellele krundile". Ilma lõikamiseta joonistati
  terve objekt (nt `piirang` #7b2cbf vöönd, mis ulatub üle naaberkinnistute) ja see loeti
  ekslikult krundi alaks. Analüüsirada (`_filter_features_by_geometry_with_status`) ja EUDR
  eksport jäävad tervet objekti kasutama; lõikamine on ainult kaardi vastuses.
- **Satelliitpilt on eemaldatud (kasutaja soov, 2026-11-05).** Välja on võetud
  `services/satellite.py`, `GET /api/satellite/{kataster_nr}`, `satellite_cache`, EstHubi kiht
  (`map-satellite` pane ja olekuriba `#map-satellite-control`), `pillow` sõltuvus ning viited
  allikakaardil ja SEO-lehtedel. Põhjus: pilvelooriga päevapilt kattis ortofoto ja näis
  andmeveana. Tagasi tuues lisa ka `pillow` `requirements.txt`-i. Aluskaart on Maa- ja
  Ruumiameti ortofoto.

## Andmevool: puuduvad eraldise andmed

- Metsaregistris on eraldisi, mille kohta ei ole tagavara-, kõrguse- ega vanuseandmeid
  (nt vastregistreeritud ala). `_search_core`-s jagatakse eraldised `stock_stands` ja
  `stock_missing_stands`; koondnäitajad (tagavara, peapuuliik, rahaline hinnang, süsinik,
  andmepassid) arvutatakse teadaolevate eraldiste põhjal ja nende pindalaga kaalutult.
- Avaldamise tingib katvus: `MIN_STOCK_COVERAGE = 0.75`. Sellest suurem katvus avaldab
  hinnangu koos `stock_coverage_percent`, `stock_known_area_ha`, `stock_missing_area_ha` ja
  `stock_missing_eraldised` väljadega; väiksema katvuse korral jäävad koondnäitajad `null`
  ja `sinik.credit_income_limitation` ütleb, mitme hektari andmed puuduvad.
  Kliendivaates joonistab selle `stockCoverageNote()` hinnangu- ja süsinikukaardile.
- `services/data_passports.build_asset_passports(..., stock_coverage=...)`: ilma selleta
  kehtib range reegel (kõik eraldised või mitte midagi). Passid on katvuse korral saadaval
  ja lisavad piirangutesse katvuse ning puuduvad eraldised.
- Teatised: `TEATIS_LAYER_TIMEOUT_SECONDS = 5.0` + 1 korduskatse ja eraldi allika-eelarve
  `TEATIS_SOURCE_TIMEOUT_SECONDS = 11.0`. GeoServeri `teatis`/`teatis_arhiiv` on külmalt
  kuni ~15 s; varem 3,5 s / 0 kordust märkis arhiivi iga kinnistu juures kättesaamatuks.
  Natura 2000: sisemine 6 s + 1 korduskatse, eelarve 10 s (sisemine aeg peab mahtuma
  välisesse eelarvesse, muidu lõigatakse päring alati ära).

## Olulised reeglid
- Originil (`api/index.py`) on `vercel.json` päiste ja vahemälu peegel (`BROWSER_SECURITY_HEADERS`,
  `CachedStaticFiles`, `/index.html` ja `/api-docs*` redirectid). Muuda mõlemat koos; CSP-räsi ei muuda.
- Pärast `git push` oota kuni 5 min, kuni `/var/lib/terrapoint/.last-deploy-commit` on sama mis
  `git rev-parse --short HEAD`, siis kontrolli brauseris `terrapoint.ee` (cache võib vajada hard refresh: Cmd/Ctrl+Shift+R).
- MD failid: `CLAUDE.md` (agent kontekst), `CHANGELOG.md` (ajalugu).
  Ei ole eraldi `AGENTS.md` / `OPENCODE.md` — kogu agent info on `CLAUDE.md`-s.

## Keel ja kujundus
- **Mõttekriipsu (— või –) kasutajale nähtavas tekstis ei ole** (kasutaja reegel,
  2026-11-04). Asendus: koolon, koma, sulud või punkt. Numbervahemikud jäävad
  en-dashiga (`61–100 a`, `01.12–15.12.2026`). Kehtib meta-kirjeldusele,
  JSON-LD-le, SEO-lehtedele (`seo_pages.py`), riskisiltidele ja app.js-i tekstidele.
- Tühja välja asemel kuvatakse sõna `puudub` (`NO_VALUE` app.js-is), mitte `—`.
- **JSON-LD muutmine nõuab CSP hashi uuendust**: `index.html` JSON-LD ploki
  sha256 peab olema nii `vercel.json`-is kui `api/index.py`-s, muidu blokeerib
  CSP struktuurandmed. Test `test_csp_limits_network_hosts_and_inline_execution`
  püüab vahe kinni.
- Staatiliste failide vahemäluvõti (`?r=jklNNN`) tuleb iga `style.css`/`app.js`
  muudatuse järel tõsta, muidu jääb brauserisse vana fail.
- **Ära päri uut `?r=` võtit enne, kui deploy on maas.** Cloudflare vahemälu
  võti on täis-URL (koos päringuga) ja TTL 1 h, seega esimene päring enne
  deploy'd jätab selle võtme alla vana faili ja brauser saab endiselt vana
  koodi. Oota `.last-deploy-commit` = HEAD ja alles siis ava leht.

## SEO töö käib GSC kaudu
- Kasutaja reegel (2026-11-04): **iga SEO muudatuse kontroll ja lõpetamine käib Google
  Search Console'is** — vaata Performance/Coverage/URL Inspection, esita sitemap ja
  taotle indekseerimist, siis kinnita tulemus GSC-s.
- Ainult lugemine: ADC (`gcloud auth application-default`) annab `webmasters.readonly` —
  `/home/arle/tmp/gsc/gsc.py sites|query --site sc-domain:terrapoint.ee`,
  `/home/arle/tmp/gsc/gsc_inspect.py sc-domain:terrapoint.ee` (URL Inspection).
  Kirjutavad toimingud (sitemapi esitamine) annavad 403; tee need jagatud töölaua
  Chromes CDP kaudu (`search.google.com/search-console/sitemaps?resource_id=sc-domain%3Aterrapoint.ee`,
  sitemapiks täis-URL `https://terrapoint.ee/sitemap.xml`).
- Seis 2026-11-04 (GSC): sitemap uuesti esitatud → loetud samal päeval, 7 lehte;
  "Request indexing" tehtud 5 uuele lehele (metsaandmed-katastritunnuse-jargi,
  metsa-hind, metsatoetused, eudr-geolokatsioon, andmeallikad). **/kkk jäi tegemata:
  GSC päevane "Request indexing" kvoot täis** — taotle järgmisel päeval.
  Baseline: 1 indekseeritud, 6 indekseerimata (2×404 ajalooline, 2×redirect,
  2×canonical); 28 päeva 6 klikki / 121 kuvamist / pos 8.5.
- 404 `/100</strong></div><p>` (GSC „Not found”) võib Googleboti JS-ist URL-i
  otsimise tõttu uuesti tekkida: `static/js/app.js` terviseskoori plokk sisaldab
  sama HTML-fragmenti stringina. See ei ole andmeviga ega vaja parandust.

## SEO ja GEO (sisulehed)
- Indekseeritav sisu ei tohi sõltuda JavaScriptist: AI-kraalerid (GPTBot,
  PerplexityBot jt) ei käivita JS-i. Seepärast on sisulehed serveripoolselt
  renderdatud — sisu `seo_pages.py`, renderdaja `api/seo.py`, marsruudid
  `api/index.py`-s (`for _seo_page in SEO_PAGES`).
- Uue lehe lisamine: lisa `SeoPage` `seo_pages.py`-sse (pealkiri ≤60,
  kirjeldus 50–160, ≥350 sõna, allikad, `related`). Sitemap, footer-lingid ja
  `llms.txt` tulevad samast allikast; avalehe footeris peab link olema
  (`tests/test_seo.py` kontrollib).
- **CSP räsi**: avalehe inline JSON-LD on CSP-s `sha256-…`-ga. Iga
  `index.html` JSON-LD muudatus nõuab uut räsi nii `api/index.py`-s kui
  `vercel.json`-is; `test_csp_limits_network_hosts_and_inline_execution`
  kukub kohe, kui see puudub.
- `meta keywords`, `twitter:site`, `og:locale:alternate` on teadlikult väljas
  (Google ignoreerib; meil ei ole X-kontot ega ingliskeelset lehte).
- robots.txt ja sitemap.xml genereeritakse koodist (`api/seo.py`), mitte
  staatilistest failidest — ära lisa repo juurde `sitemap.xml`-i tagasi.
- FAQPage: Google'i rikkad tulemused on alates 2026. aastast kõigile
  suletud; skeem jääb alles ainult seetõttu, et selle sisu on lehel nähtav.
  Ära lisa uut FAQPage'i lootusega SERP-rikkusele.

## Tulemuste kaartide paigutus
- `.metrics-grid` on kolme veeru ruudustik, mille lapsed on `.metrics-column` virnad
  (`display: flex; flex-direction: column`). `initCardColumns()` (`static/js/app.js`)
  jagab kaardid veergudesse üks kord (lühima veeru reegel, esimesed kaardid üks
  veeru kohta) ja jagab uuesti ainult vaate laiuse muutumisel või
  `refreshCardColumns()` väljakutsel uue otsingu järel.
- **Ära pane `ResizeObserver`-it kaardi kasvamise peale ümber jagama.** Varem
  paigutas JS kaardid ühises `grid-auto-rows: 1px` ruudustikus iga mõõtmise järel
  uuesti: mahuka sektsiooni (nt 12 kaardiga „Muud meetmed”) avamine muutis kõigi
  kõrgusi, kaardid hüppasid teistesse veergudesse ja kadusid ekraanilt.
- Mahukad nimekirjad hoitakse `.toetus-list-scroll` sees (720 px, sisemine
  kerimine); mobiilis on see klass `max-height: none` (test
  `test_subsidy_counts_have_explicit_contrast_and_mobile_avoids_nested_scroll`).
- Kaartidel ei ole sisu loetlevaid alapealkirju (`.section-desc` on eemaldatud,
  2026-11-04): pealkiri ütleb sisu ise. Uut kaarti lisades ära enumerateeri
  välju; pane vajadusel ainult piirang või hoiatus. Pikk tabel (`Metsateatised`)
  on piiratud sisemise kerimisega (460 px), muidu venitab üks kaart veeru
  tuhandete piksliteni.

## UI kontroll brauseris (kasutaja reegel)
- Iga UI muudatus (`index.html`, `static/css/*`, `static/js/*`, UI-nähtav vastus): enne "valmis" ütlemist vaata lehte headless brauseris. Testid ja diff ei tõesta, et leht töötab.
- Brauser: süsteemne `python3` Playwright (1.60.0). Kontrollitud 2026-11-02: `chromium.launch(headless=True, args=["--no-sandbox"])` käivitab Playwrighti Chromiumi (148) ja `chromium.launch(executable_path="/usr/bin/google-chrome", headless=True, args=["--no-sandbox"])` käivitab Chrome'i (153). Repo `.venv`-s Playwrighti ei ole.
- Voog: käivita rakendus (`.venv/bin/python -m uvicorn api.index:app --host 127.0.0.1 --port 8160`, enne seadista `TERRAPOINT_CHAT_SNAPSHOT_KEY_B64` juhusliku 32-baidise võtmega), ava `/`, kirjuta `78404:409:0113` väljale `#kataster-input-landing`, vajuta Enter, oota ~18 s. Tulemuste vaates on päises `#kataster-input`.
- Kontrolli: desktop 1280×800 ja mobiil 390×844; `pageerror` ja konsoolivead 0; ebaõnnestunud päringuid ei tohi olla; mobiilil horisontaalset ülevoolu ei tohi olla. Ekraanipilt tuleb ise vaadata. Kui välimus peab jääma samaks, võrdle teksti ja pikselit eelmise versiooniga.
- Ajutised ekraanipildid ja tekstivõtted jäta `/tmp/` alla, mitte repo sisse. Sulge oma brauserivahelehed ja peata oma serverid.
