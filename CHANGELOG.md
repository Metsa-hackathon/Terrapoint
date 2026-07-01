# Changelog

Kõik olulised muudatused Terrapoint repositooriumis.

> **Domeen**: tootmine töötab aadressil **terrapoint.ee** (Vercel custom
> domain). `terrapoint.vercel.app` on sama projekti alias — push master
> branchi uuendab mõlemat korraga.

## [Määramata] - 2026-07-01

### Added
- **Metsateatiste tabel: uus veerg "Eraldis"** — iga metsateatise juures
  on nüüd näidatud, millisele konkreetsele eraldisele teatis käib
  (andmed pärinevad Metsaregistri WFS-i `eraldise_nr` väljast). Number
  on tabelis eraldi veerus "Eraldis" (tooltip näitab täisteksti
  "Eraldis N"). Mobiilil näitab ainult numbrit, et ei läheks kärbitud.
  Uuendatud ka `grid-template-columns` (desktop + mobiil) ja veergude
  joondusreeglid: Tüüp/Eraldis/Staatus vasakule, Kehtiv kuni/Pindala
  paremale.
- **Toetused: "Sobib eraldistele" plokk** — iga sobiva toetuse juures
  on nüüd näidatud, millistele konkreetsetele eraldistele toetust
  saab taotleda. Väljund:
  1. Rohelised eraldise-numbrite "chip-id" (nt 1, 16, 5, 12, …).
  2. Kogupindala "X,XX ha kokku".
  3. Seletav silt, mis kirjeldab filtrit (nt "Eraldised vanusega
     10–60 aastat", "Kuivendatud eraldised", "Raieküpsed eraldised
     (vanus ≥ raievanus)").
  Iga toetuse jaoks on `services/subsidies.py`-s uus `eraldised_filter`
  lambda, mis tagastab sobivate eraldiste nimekirja. Filtreid on 13
  toetuse jaoks: looduskaitse, metsameede, kliimakindla metsa
  kujundamine, metsastamine, metsa uuendamine, kooreüraski tõrje,
  inventeerimine, maaparandus, pärandkultuur, metsaühistu, metssigade
  küttimine jt. Tagastatakse ka `eraldised_match_count` (sobivate arv),
  `eraldised_match_ha` (kogupindala) ja `eraldised_filter_label`
  (inimloetav filter). Lisatud 12 testi `tests/test_subsidy_eraldised.py`
  (kõik vanad + uued 18 testi läbivad).

### Fixed
- **Liikide koosseis: "Ainuroheline kask" → "Harilik kask"** —
  vana nimi oli AI-hallutsinatsioon (sellist puuliiki ei eksisteeri
  Eesti metsanduses). Kask (KS) on õige nimetusega "harilik kask"
  (*Betula pendula*). Parandatud kolmes kohas:
  - `api/index.py` riskiskoori label ("Peapuuliik: …").
  - `index.html` frontend `SPECIES_NAMES` map.
  - `index.html` SPECIES_COLORS legendi kommentaar.
  Tagasihoidlik "Kask" (ilma "harilik" eesliiteta) jääb alles
  backendi `services/metsaregister.py` lühinimeks ja chart-i
  legendis.

## [Määramata] - 2026-06-29

### Fixed
- **Eraldiste tabel: kõik 7 veergu nähtavad ka 3-veerulise Mac kaardi
  laiuse juures** — eraldiste tabeli kõige olulisem veerg "Väärtus"
  (kus on raha) lõigati ära Mac 3-veerulise paigutuse juures (eraldiste kaart
  ~357px laiune, 28px sisemise veerisega → eraldiste paneel ~299px).
  Puuliigi veergu ("Kask", "Haab", "Kuusk") oli näha ainult 1 täht ("K",
  "H"). Parandused:
  1. `.metric-card:has(.eraldised-table-panel)` sai kitsama sisemise
     veerise (28px → 14px), mis annab tabelile ~28px rohkem ruumi.
  2. `.eraldised-table-header` / `.eraldised-row` said kitsamad veerud
     (22px → 18px, 80px → minmax(0, 1fr) Puuliigile, 42px → 30px Vanusele,
     56px → 38px Tagavarale, 48px → 32px Boniteedile, 56px → 40px
     Pindalale, 76px → 72px Väärtusele).
  3. Rakkude padding 8px → 6px, gap 10px → 8px.
  4. `.er-value` font 0.92em + `white-space: nowrap` (pikad väärtused
     nagu "12 074 €" mahuvad).
  5. `.eraldised-panel` sai nähtava õhukese kerimisriba
     (`scrollbar-width: thin`, `scrollbar-color: rgba(0,0,0,0.25)`,
     webkit thumb 8px) — macOS peidab kerimisribad vaikimisi, mis
     jättis mulje, et väärtuse veerg on "kadunud".
  Testitud Mac 1440px, Windows 1920px, iPhone 390px, iPad 1024px,
  Android 412px. Nüüd näitab iga seade kõiki 7 veergu koos
  puuliiginime ja väärtusega (NBSP-tuhandelise eraldajaga numbrid
  nagu "12 074 €" mahuvad ilma kärpimiseta).

## [Määramata] - 2026-06-13

### Fixed
- **Vasakus ülanurgas rippus juhuslik `-->` tekst** —
  `index.html` `<head>`-is oli pesastatud HTML kommentaar
  (`<!--     <!-- ... -->\n -->`), mille teine sulgev `-->` jäi
  kommentaarist välja ja renderdus body esimese tekstisõlmena
  (väikese noolena lehe ülaservas, päise kohal). Asendatud
  ühe puhta `<!-- ... -->` reaga.

### Removed
- **Lehe suurenduse slider eemaldatud** (`#zoom-slider`,
  `.zoom-controls`, `.page-zoom` wrapper, kogu zoom JS IIFE
  ja umbes 170 rida zoom CSS-i). Brauseri natiivne `Ctrl/Cmd +`
  / `Ctrl/Cmd -` (ja `Ctrl/Cmd + 0` reset) teevad sama tööd
  paremini, ei varjuta kaarti vasakus alanurgas ega ei sega
  legendi/atribuuti.
  - HTML: kustutatud `<div class="page-zoom">` wrapper,
    `<div class="zoom-controls">` plokk koos `<input type="range"
    class="zoom-slider">` ja kõik tema kommentaarid.
  - JS: kustutatud `// ═══ Zoom Controls ═══` IIFE
    (`scheduleZoom`, `snapToMagnet`, `localStorage` salvestus
    `terrapoint-zoom` võtmega — vana väärtus jääb brauserisse,
    aga seda ei loeta enam, nii et see on kahjutu).
  - CSS: kustutatud `.zoom-controls`, `.zoom-stack`,
    `.zoom-tick-labels`, `.zoom-track`, `.zoom-track-wrap`,
    `.zoom-slider` (kõik vendor pseudo-elemendid kaasa
    arvatud), `.page-zoom` (sh `@supports not (zoom: 1)` fallback
    ja `.is-zooming` overrride) ning `@media (max-width: 768px)`
    sees olnud zoom-i mobile overrride-d.
  - Cache buster: `?r=jkl029` → `?r=jkl030`.

## [Määramata] - 2026-06-11

### Changed
- **Kaart: kihid eristatavamad + kihtide legend** —
  Ürask, Vooluveed, Järved jt 11 kihti on nüüd kaardil selgelt
  nähtavad ja omavahel eristatavad:
  - Värvid uuendatud (backend `LAYER_MAP`, api/index.py): iga kiht
    sai unikaalse värvitooni + joone stiili (solid/dashed/dotted)
    ja paksuse (weight 1-4). Sarnased värvid (järved vs vooluveed,
    kaitsealad vs natura_elupaik) on nüüd selgelt eristatavad —
    järved hele täidisega, vooluveed paks tume joon ilma täidise
    täidiseta; kaitsealad tume metsaroheline, natura_elupaik
    hele salvei-roheline.
  - Vaikimisi weight 2 → 3, opacity 0.7 → 0.9, fillOpacity
    0.15 → 0.30.
  - Per-layer stiil salvestatakse backendi `map_layers` payloadi
    (color, dash, weight, fillOpacity) — frontend rakendab
    `L.geoJSON` style objektile.
  - Uus `updateKihtLegend()` funktsioon jälgib aktiivseid
    kihte ja joonistab nende värvid/jooned legendi alumisse
    vasakusse nurka (eraldiste legend on paremas nurgas, atribuut
    kokkupanduna). Legend peidab end automaatselt kui ühtegi
    kihti pole sisse lülitatud või neil pole andmeid. Kuvab
    iga kihi värvi + soolid/dashed/dotted mustri + nime.
  CSS versioon v28 → v29 (cache bust).
- **Kaart: atribuut kokkupanduna** — Esri/Maa-ameti atribuut (Esri ToS +
  CC-BY 4.0 nõutav) on nüüd vaikimisi väike "i" ikoon nurgas
  (26×23px), hover/klõpsuga avaneb täistekst. "Leaflet" prefiks
  eemaldatud (pole nõutav). CSS versioon v27 → v28 (cache bust).
- **Kaart: alustusest uus — Web Mercator + 2 satelliidikihti** —
  eemaldatud LCC (EPSG:3301) CRS, proj4/proj4leaflet sõltuvused
  ja kõik 5 Maa-ameti X-GIS aluskaarti (CIR-NGR, ametlik ortofoto,
  põhikaart, reljeef, hallkaart). Kaart on nüüd Web Mercator
  (EPSG:3857) ja kasutab kahte Esri satelliidikihti:
  - **Esri satelliit (värskeim)** — vaikimisi
    `https://server.arcgisonline.com/.../World_Imagery/MapServer/tile/{z}/{y}/{x}`
  - **Esri Wayback 2026-02-26** (timeId 64001) — uusim talvine
    väljalase. NB! Esri World Imagery baaspilt on Eesti jaoks
    valdavalt suvised aerofotod, mistõttu 2026-02-26 pildil ei
    pruugi lund näha olla. Päris talvise sat-pildi jaoks oleks
    vaja NASA GIBS MODIS/VIIRS daily (250-375m, pilvine) või
    Sentinel-2 (talve mosaiiki pole vaba tile-teenusena).
  Katastri WMS (`gsavalik.envir.ee`) on uuendatud Web Mercatorile
  (`crs=EPSG:3857`, WMS 1.3.0). Kliki-otsing, otsingukast ja
  kõik 12 KIHID kihti (GeoJSON WFS päringutest) töötavad
  muutumatult — Leaflet reprojseerib GeoJSON automaatselt.
  `proj4` ja `proj4leaflet` script-id eemaldatud HTML head-ist.

### Fixed
- **Kaart: aluskaardi vahetaja kokkupanduna vaikimisi** —
  `L.control.layers(..., { collapsed: false })` puhul kuvas Leaflet
  7 aluskaardi nimekirja kogu aeg lahti (võttis ~30% kaardi pindalast
  desktopil, ~50% mobiilil, lõikas mobiilil "OpenStreetMap" rea
  välja). Nüüd `collapsed: true` — näidatakse ainult kihtide
  ikooni, avaneb klõpsuga.

- **Kaart: eemaldatud Esri satelliit ja OpenStreetMap valikust** —
  mõlemad on Web-Mercatori põhised tile-teenused, mis ei tööta
  LCC (EPSG:3301) projektsiooniga: Leaflet arvutab LCC-s
  y-tile koordinaadid väljaspool Web-Mercatori `[0..2^z-1]`
  vahemikku (nt z=7 vaates y=-62), Maa-ameti/Esmi/OSM server
  tagastab "Map data not yet available" placeholder'i. Kõik 5
  allesjäänud Maa-ameti aluskaarti (CIR-NGR, ametlik ortofoto,
  põhikaart, reljeef, hallkaart) töötavad LCC-proxy
  (`/api/tiles/xgis`) kaudu kõigil suumidel.

### Changed
- **Zoom nuppude asemel slider** — alumise vasakpoolse `1x / 0.75x`
  kahe-nupu toggle'i asemel nüüd pidev `<input type="range">` slider
  vahemikus 0.5–1.0 (samm 0.05, 11 astet). Vana `.zoom-btn` stiilid
  asendatud `.zoom-slider` reeglitega, slideri thumb 18px (desktop)
  / 22px (mobiil) WCAG 2.5.5 puutepunkti jaoks. Slideri kohal on
  3 skaala-märget (50 / 75 / 100) koos tikksümbolitega raja peal,
  et kasutaja näeks kohe millised astmed on valitavad. Märgete
  x-positsioonid on joondatud thumb'i tsentritega (0% / 50% / 100%
  väärtusvahemikust, insettitud `thumbWidth/2` võrra) — näitavad
  täpselt kuhu thumb maandub valitud väärtuse korral. Zoom
  rakendatakse `--zoom-level` CSS muutujaga, mis on seatud
  `.page-zoom` elemendile (uus wrapper ümber kogu lehe sisu).
  **Lehe sisu on nüüd mähitud `<div class="page-zoom">`-i** —
  kogu leht (header, sidebar, loading, sektsioonid, footer) on
  selle sees, ja `.zoom-controls` on tema õde-vend (sama taseme
  `<body>` laps, mitte wrapperi järglane). Tulemus: zoom
  rakendatakse ainult wrapperile, juhtnupp jääb väljapoole
  zoom-konteksti ja tema suurus + asukoht on täiesti
  konstantsed sõltumata valitud suumist (native range input
  ei vaja enam `transform: scale` counter-pole, sest ta pole
  üldse zoom'i mõjualas). Firefox < 126 fallback on sama
  loogikaga, kuid kasutab `transform: scale()` asemel.
  localStorage võti `terrapoint-zoom` salvestab nüüd arvu
  (nt `"0.85"`) Stringina, taastamisel valideeritakse vahemik
  0.5–1.0. CSS versioon v19 → v25 (cache bust).

## [Määramata] - 2026-06-10

### Fixed
- **Desktop: sektsioonid täidavad terve ekraani** — landing ja dashboard
  olid `max-width: 960px` / `var(--max-w)` piiratud, mistõttu 1920px
  ekraanil jäi ~192px valget ala mõlemale poole. Eemaldatud max-width
  piirangud mõlemalt sektsioonilt, lisatud täislaiuses taustad (landing:
  sinine gradient, dashboard: paper-2 → paper gradient), sisu tsentreeritud
  `.section > *` kaudu. `.about` vahetatud `paper` → `paper-3` (tumedam
  sinine, eraldub dashboard'ist). `.contact` sai tugevama `border-top`.
  Mobiilil jääb laste max-width 100% — sisu täidab ekraani nagu varem.

### Reverted
- **Kaart ja sektsioonid tagasi lehe algusesse** — eemaldatud `hidden`
  atribuut `<section id="dashboard">` pealt, et kaart (Leaflet) ja 8
  sektsiooni (Kataster, Eraldised, Väärtus, Süsinik, Teatised, Riskid,
  EUDR, Toetused, Kitsendused) oleksid nähtavad kohe lehe laadimisel,
  mitte peidetud otsingu taha. Varasem `40034f2` fix (`.dashboard[hidden]`
  reegel) jääb alles defensiivseks — kui tulevikus lisatakse `hidden`
  tagasi, ei leki tühi dashboard enam layouti sisse.

### Fixed
- **Mobiil: dashboard ei leki landing vaatesse** — `.dashboard` klassi
  `display: flex` kaotas `[hidden]` atribuudi efekti (UA vaikimisi
  `[hidden] { display: none }` on madalama spetsiifikaga), mistõttu
  kõik 8 tühja placeholder kaarti ("Otsi krunti, et näha…") koos AI
  chat'i ja kaardiga olid mobiilis nähtavad juba enne otsingut.
  Lisatud `.dashboard[hidden] { display: none; }` — landing → meist →
  kontakt → allikad järjestus taastatud, lehe pikkus ~6000 px → 3719 px.

### Changed
- **Kaardi aluskaardid: CIR-NGR vaikimisi, X-GIS 1r03lgo** — vana
  `EESTIFOTO` / `HYBRID` / `nCHM2017` WMS läksid tühjaks (kaart.maaamet.ee
  ei teeninda enam neid kihte). Asendatud X-GIS teenusega `1r03lgo`
  (töötab 256×256 juures). Vaikimisi aluskaardiks `cir_ngr` (Metsanduslik
  ortofoto, CIR-NGR valevärv) — ainuke kiht mis töötab kõigil
  suumitasemetel. Lisatud `of10000` (Ametlik ortofoto), `pohi_vr2`
  (Põhikaart), `pohi_vv` (Reljeef), `pohi_mvr2` (Hallkaart) — töötavad
  ainult z≥15 sest Maa-ameti allika ScaleHint max=8.98 (1:8984). Labelid
  viimased lõpus "(Maa-amet, z≥15)" et kasutaja teaks miks tühi pilt
  väljasurnud alal. Eemaldatud `HYBRID` ja `talvFoto` duplikaat.
- **X-GIS CORS proxy `/api/tiles/xgis`** — Maa-amet ei saada CORS
  päiseid, mistõttu brauser blokeeris WMS päringud (net::ERR_BLOCKED_BY_ORB).
  Lisatud backend proxy `api/index.py:1356` mis vahendab GetMap päringuid
  X-GIS serverile, lisab `Access-Control-Allow-Origin: *` ja cache'dab
  tulemuse 24h. Kasutab L.GridLayer.extend() patternit (L.tileLayer
  ignoreerib getTileUrl override'i).
- **CSS versioon v19 → v20** (cache bust jkl019 → jkl020).

### Reverted
- **Lehe suurendamise slider (50/75/100) eemaldatud** — commit
  218756f lisas bottom-left valge pilli koos noolega (slider thumb).
  Kasutajad ei oodanud sellist lehe-skaala juhtnuppu ja see jäi
  segadust tekitavaks. Eemaldatud HTML (.zoom-controls, .page-zoom
  wrapper), JS init ja kõik sellega seotud CSS reeglid.
- **Põhikaart kaart.maaamet.ee WMS** — eelnev revert (3e56d8b) tõi
  tagasi katkise WMS lahenduse. Reapply (e8f15e8) taastas X-GIS
  1r03lgo proxy + CIR-NGR vaikimisi aluskaardiks.

### Changed
- **Zoom 0.75x / 1x nupp viidud kaardist välja** — vana `position: absolute` — vana `position: absolute`
  `.map-wrapper` sees asendatud `position: fixed` `bottom: 12px; left: 12px`
  poolt, nüüd on nupp kogu lehe vasakus alumises nurgas, mitte kaardi
  sees. Z-index 600 → 1500 (jääb alla nav-header'ile 2000, kuid kõrgem
  kui muu lehe sisu). JS ei muutunud — `setZoom` töötab endiselt
  `html.zoom-75` klassiga ja localStorage võti `terrapoint-zoom` säilib.

### Docs
- `CLAUDE.md` uuendatud: `terrapoint.ee` märgitud primaarse domeenina,
  selgitatud et `terrapoint.vercel.app` on sama Vercel projekti alias.
  Lisatud juhised hard refreshi kohta pärast deploy't.

### Changed
- **Eraldiste "kokku" tabel tihedamaks** — `.eraldised-table-header` ja
  `.eraldised-row` said kitsamad veerud (`24 / 38 / 48 / 42 / 48 / 64px` +
  `minmax(70px, 1fr)` puuliigile), padding 8 → 6px, eemaldatud
  `min-width: 460px` desktopil ja 380px mobiilil. Tabel mahub nüüd
  ühe vaate sisse ilma kerimiseta (sõltumata sõbra `9403439`/`114b789`
  fontide suurendamisest — eraldiste tabel jäi 11/10px, sest see on
  ainus viis saada kõik 7 veergu korraga nähtavaks). Eemaldatud ka
  `text-transform: uppercase` ja `letter-spacing` päiselt — väiksemal
  fondil pole suurtähtedest lugemisel kasu.

## [Määramata] - 2026-06-09

### Fixed
- **Sektsioonide placeholder'id ühtlaseks** — kõik 9 kaarti (Katastriüksuse
  andmed, Metsaeraldised, Metsa majanduslik väärtus, Süsinikuvaru,
  Metsateatised, Ohutegurid, EL deforestatsioonikontroll, Toetused ja
  hüvitised, Kitsendused ja piirangud) kasutavad nüüd sama
  `.card-placeholder` plokki: 40px ringikujuline SVG ikoon + pealkiri
  + vihje. Varasemad probleemid:
  - Mõnedel kaartidel üldse placeholder puudus (tühi ala)
  - Toetuste kaardil oli emoji 💰 (rikkus "No emoji as icons" reeglit)
  - EUDR kaardil oli staatiline "Laadi alla EUDR GeoJSON" nupp
  - Toetused ja Kitsendused kasutasid legacy `.initial-info` plokki
  - Toetused ja Kitsendused kasutasid teiste ikoonide värve (vaartus
    sinine / risk punane)
  Iga kaart sai nüüd unikaalse ikooni värvi: kataster sinine, mets
  roheline, vaartus kollane, süsinik teal, teatised indigo, risk
  punane, EUDR lilla, toetused roheline, kitsendused oranž.

### Changed
- **Mobiili optimeerimine (8 kriitilist viga)** — pärast põhjalikku auditeid
  Playwright + vision abil kõikidel kolmel vaatel (320×568 iPhone SE,
  360×800 Android, 390×844 iPhone 14):
  - **Sticky header blur**: `.hero` sai `backdrop-filter: saturate(180%) blur(8px)`
    ja `scroll-margin-top: 72px` kõikidele sektsioonidele (`.metric-card`,
    `.source-card`, `.fact`, `.section-head`, `.landing`) — sisu
    jääb nähtavaks ka scrollimise ajal.
  - **Zoom pill ankurdatud kaardile**: vana `position: fixed` põhjustas
    kattumist iga mitte-kaardi sektsiooniga. Nüüd `position: absolute`
    `.map-wrapper` sees — kaob koos kaardiga vaatest.
  - **Zoom 0.5x nupp lisatud** + `html.zoom-50 { zoom: 0.5 }` stiil. Nupp
    duplicate eemaldatud (oli kaks `.zoom-controls` plokki).
  - **AI chat input → textarea**: pikad küsimused kasvavad vertikaalselt
    (max 120px / 4 rida) selle asemel, et horisontaalselt üle voolata.
    Auto-grow input handler. Enter saadab, Shift+Enter lisab rea.
  - **Touch targets ≥ 44px (WCAG 2.5.5)**:
    - Leaflet +/− zoom: 32×32 → 44×44
    - Map legend `−` close: 28×28 → 44×44
    - Map controls "Kihid" toggle: 40px → 44px
    - Search submit nupp: 26×26 → 44×44
    - AI chat send nupp: 36×36 → 44×44
  - **Search input laiem**: `flex: 1`, kõrgus 34px → 44px, font 13px → 15px,
    placeholder enam ei lõika teksti maha.
  - **Landing search box**: 38px → 52px, font 14px → 16px, submit 30px → 44px.
  - **Brand ikoon kitsastel ekraanidel** (<380px): "TerraPoint" tekst
    peidetud, näidatakse ainult 22×22 svg kujundust — vabastab ruumi
    otsingu sisendile.
  - **`-webkit-tap-highlight-color: transparent`** kõikidele interaktiivsetele
    elementidele (zoom, layer, legend, AI button) — eemaldab sinise
    välke iOS Safari'l.

### Changed
- **Toetuste sektsiooni ümberkujundus** — vana struktuur oli kitsas ja
  murdus mobiilis (kaardid olid `min-width: 400px` laiused, summa tekst
  lõigati paremast servast maha, CTA lingid olid tekstiviited ilma
  piisava puutepunktita). Uus struktuur:
  - Ülemine rida: pealkiri + staatuse badge (Avatud / Tulemas / Lõppenud)
  - Kategooria + asutus (väiksemad caps)
  - Kirjeldus
  - "Toetuse suurus" silt + summad eraldi pillidena (roheline
    eligible, hall ineligible) — toimib ka komadega eraldatud
    loeteluga nagu "püünispuud 500 €/üksus, feromoonpüünised 40
    €/komplekt"
  - Ineligible puhul: punane "✗ Ei vasta tingimustele" plokk põhjendusega
  - Footer: Taotlusvoor (label + väärtus) + ÜKS suur CTA nupp
    ("Kandideeri eramets.ee lehel" roheline / "Vaata tingimusi" sinine)
  - Mob CTA nupu kõrgus 44px (WCAG 2.5.5 puutepunkt)
  - Eemaldatud `min-width: 400px` toetus-kaartidelt ja JS-i
    `<div style="min-width:400px">` mähkijalt
- **AI pakkuja vahetatud: NVIDIA → OpenCode Zen** — kasutab mudelit
  `deepseek-v4-flash-free`. OpenAI-ühilduv `/v1/chat/completions` endpoint
  aadressil `https://opencode.ai/zen/v1`. Env var nimed:
  `OPENCODE_ZEN_API_KEY`, `OPENCODE_ZEN_MODEL`. Vana `NVIDIA_API_KEY` ja
  `NVIDIA_MODEL` eemaldatud Vercel dashboardist. CSP `connect-src`
  uuendatud: `integrate.api.nvidia.com` → `opencode.ai`. DeepSeek V4 Flash
  on samuti reasoning-mudel, mistõttu `max_tokens` tõstetud 2048 → 4096,
  httpx read-timeout 120s → 180s, frontend safety-timer 120s → 180s.
  Frontend `.ai-thinking-block` kuvab mõttekäiku eraldi, lõplik vastus
  tuleb alati eraldi `content` delta voona.

### Fixed
- **Vercel FastAPI runtime ei käivitunud** — `vercel.json`-is oli
  `framework: null` ja käsitsi `rewrites` `/api/...` -> `/api/index.py`,
  mis pani Verceli serveerima `api/index.py` raw Python failina (Content-Type
  `application/octet-stream`, 405 POST korral). Eemaldatud `framework: null`
  ja rewrites — Verceli fastapi preset avastab nüüd `app.py` juurest
  ise. Lisatud `app.py` shim: `from api.index import app`.
- **API endpoint tagastas 500 FUNCTION_INVOCATION_FAILED** —
  `api/index.py` real 1176 oli sulgemata jutumärk AI fallback tekstis
  (3 × U+201E `„` ilma vastava U+201C lõputa), mis andis `SyntaxError`.
  Parandatud — nüüd import töötab.
- **AI chat endpoint tagastas 500 "AI ei andnud vastust"** — põhjus: Verceli
  deployment'is puudus `NVIDIA_API_KEY` keskkonnamuutuja. Lisatud Verceli
  dashboardi (production) + `NVIDIA_MODEL=meta/llama-3.3-70b-instruct`
  (varem `stepfun-ai/step-3.7-flash` kulus kogu tokeni eelarve sisemisele
  mõttekäigule ega andnud sisulist vastust). Kohalik `.env` oli olemas,
  aga Vercel ei loe kohalikku `.env` — seaded tuleb teha dashboardi kaudu.
- **AI chat input ei ilmunud mobiilis refresh'i järel** —
  `aiAnalyzeKataster` funktsioonis oli `return` short-circuit, mis jättis
  input area `display:none` peale, kui kasutaja navigeeris samale
  kinnistule. Nüüd kuvatakse input area alati enne return-i.
- **AI chat input kaotas pärast esimest sõnumit** —
  `aiLastSendAt` ja `aiRecentSendTimes` kasutati ilma `var` deklareerimiseta,
  mis põhjustas `ReferenceError` ja peitis input area. Deklareeritud
  koos teiste AI muutujatega.
- **Touch targetid olid mobiilis liiga väikesed** (26-36px alla soovitatud
  44px) — search nupp, AI send, zoom nupud, kihi toggle, hint nupud.
  Kõik tõstetud ≥32px (44px eelistatult).
- **Landing title murdus 320px ekraanidel** — vähendatud 38px → 30px
  + lühem line-height.
- **Reposit "muss"** — kohalik oli 9 commit'i taga, logifailid olid
  commititud (`server_err.log`, `server_out.log`). Tehtud `git pull --rebase`,
  logifailid eemaldatud jälgimisest, `.gitignore` täiendatud.

### Added
- `.gitignore`: `server_*.log` ja `*.log` (kohalikud uvicorn logid).
- WFS 400 retry — Estonian WFS annab vahel 400 kehtetutele bbox päringutele,
  nüüd retry ka nende puhul (`services/layers.py`).
- **URL-põhine auto-search** — `?kataster=78404:409:0113` või `?q=Kadaka pst 159`
  query stringi põhjal käivitub search automaatselt lehe laadimisel.
  Kasulik jagamislinkide jaoks ja deep-linking'uks.
  Toetab ka `popstate` (back/forward nupp).

### Changed
- CSS versioon v11 → v12 (cache bust).

### Deployment
- **Vercel**: env vars seadistatud (OPENCODE_ZEN_API_KEY, OPENCODE_ZEN_MODEL).
- **GitHub**: master branch on ajakohane, Vercel auto-deploy töötab.
- **Kohalik API** (systemctl terrapoint-api): .env-st tulnud, töötab.

### Mobile UX parandused
- AI chat input nüüd nähtav ja töötav (393px ja 320px ekraanidel).
- Suuremad touch targetid — sõrmega lihtsam tabada.
- Landing page'i pealkiri mahub 320px ekraanile.

### Teadaolevad puudused
- **2 `@app.get("/")` route** FastAPI's — teine varjutab esimest,
  kuid töötab (testitud).

## [Meist/Allikad/Info] - 2026-06-09 (UI uuendus)

### Added
- **Tiimi pilt** (`static/img/team-hackathon-2026.jpg`, allikas aripaev.ee):
  Metsikult andmetes 2026 võit, 5000€ auhind, 3 meeskonnaliiget.
  Kasutatud Meist sektsiooni hero pildina + uues bento layout'is.
- **Victory bento** (Meist sektsioonis) — 2-veeruline grid:
  - Vasakul: tiimi pilt (4:3, object-position center 30%) + "1. koht · 5000 €"
    badge üleval vasakul
  - Paremal üleval: dark "5000€" prize card
  - Paremal keskel: 3-veeruline meta grid (kuupäev, osalejad, tiim)
  - Paremal all: pikk selgitav tekst
  - Mobiilis: stackub üheks veeruks
- **Info sektsioon** (täiesti uus) — 5-kaardine bento grid:
  - Privaatsus, Arvutusmeetod, AI mudel, Tehniline stack
  - Lai dark "Piirangud" kaart full-width all
  - Sama design system: --ink, --blue-900, --paper-2 taust, 16-18px radius,
    11px mono eyebrow, 17px pealkiri
- **about-hero-caption** — label + tekst tiimi pildi allosas
- **about-hero-tag** (victory bento sees) — backdrop-blur badge "1. koht · 5000 €"

### Changed
- `static/img/forest-hero.jpg` asendatud `static/img/team-hackathon-2026.jpg`-ga
  Meist hero pildina.
- Olemasolev `.about-hackathon` plokk asendatud uue `.victory-bento`-ga.
- CSS versioon v13 → v14 (cache bust).

### Mobile UX
- Bento collapse: 880px → 1-veeruline, 520px → meta stack.
- Info grid: 768px → 1-veeruline.
- Tiimi pilt objekt-positsioon 30% (tiimi näod jäävad nähtavaks).
