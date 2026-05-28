# Terrapoint — Täielik implementatsiooniplaan

## Eesmärk

Luua veebirakendus, kuhu metsaomanik sisestab katastri numbri ja saab kohe kogu oma metsa kohta käiva info ühest kohast: puuliigid, vanus, maht, turuväärtus, piirangud, toetused, süsinikupotentsiaal ja EUDR-vastavus. Eesti keeles. Päris valitsuse andmetega. Mitte demo, vaid tööriist.

**Väljakutse:** "Uus toode või teenus metsanduslike avaandmete peal"
**Fookus:** "Metsikult andmetes" häkaton, 29.-30. mai 2026, €10K auhinnafond
**Meeskond:** Backend (Python/FastAPI) + Frontend (HTML/CSS/JS)
**Repo:** `Metsa-hackathon/Terrapoint` (privaatne)
**Deploy:** Coolify (Docker-compose)

---

## 1. Funktsioonid (prioriteedi järjekorras)

### 1.1 Tuumik (kohustuslik, MVP)

| # | Funktsioon | Kirjeldus | Andmeallikas | Aeg |
|---|-----------|-----------|-------------|-----|
| 1 | **Otsing** | Katastri numbri sisestus → dashboard | `kataster:ky_kehtiv` CQL | 2h |
| 2 | **Põhiandmed** | Puuliik, vanus, kubatuur, boniteet, pindala | `metsaregister:eraldis` + `eraldis_element` | 2h |
| 3 | **Kaart** | Leaflet kaart katastri polügooniga + vahetatavad kihid | `tiles.maaamet.ee` WMTS + geomeetria | 3h |
| 4 | **Kitsendused** | Kaitsealad, Natura 2000, veekaitse, muinsuskaitse | 6 BBOX kihti (eelis, kitsendused, muinsuskaitse) | 3h |
| 5 | **Väärtus** | Puidu turuhinnang | `hindamine.kataster.ee` + `kolvikud.kataster.ee` | 2h |
| 6 | **Süsinik** | IPCC valem, potentsiaalne tulu | `metsaregister:eraldis` (tagavara) + IPCC tegurid | 1.5h |
| 7 | **Toetused** | 12 programmi, loogika põhjal | `eelis:toetus_mets` + loogika | 2h |
| 8 | **EUDR** | GeoJSON export | Kataster geomeetria | 1h |

**Kokku: ~16.5h**

### 1.2 Erifunktsioonid (konkurentsieelis)

| # | Funktsioon | Kirjeldus | Andmeallikas | Aeg |
|---|-----------|-----------|-------------|-----|
| 9 | **Raievanuse indikaator** | Liiklusfoor: roheline/kollane/punane | `keskm_vanus / keskm_raievanus` | 1h |
| 10 | **Üraski riskikiht** | Kuusemetsade risk (0-3) + ametlikud tsoonid | `kuusekooreyrask_mke` + `kuusekooreyrask_eelis` | 2h |
| 11 | **Invasiivne liik** | Karuputke hoiatus | `maaamet:karuputk` BBOX | 0.5h |
| 12 | **Metsa terviseindeks** | 0-100 skoor (boniteet + drenaaž + tuleoht + ürask) | Mitu kihti | 2h |
| 13 | **Häiringute ajalugu** | Lageraiealad perioodiga | `veeveeb:lageraiealad` | 1h |
| 14 | **RMK oksjoni lähedus** | Lähedal olevad riigimaa oksjonid | `maaoksjon:auction` | 0.5h |

**Kokku: ~7h**

### 1.3 Boonus (kui aega jääb)

| # | Funktsioon | Kirjeldus | Aeg |
|---|-----------|-----------|-----|
| 15 | **PDF eksport** | "Metsaport" — kõik andmed ühel lehel | 2h |
| 16 | **Radari graafik** | 6 funktsiooni skoor korraga | 1h |
| 17 | **Kõrvutamine** | Kahe katastri kõrvutamine | 2h |
| 18 | **AI seletus** | OpenRouter — "mida see tähendab?" | 1.5h |

---

## 2. Tehniline arhitektuur

### 2.1 Stack

| Komponent | Tehnoloogia | Miks |
|-----------|------------|------|
| Backend | FastAPI (Python 3.12) | Async, kiire, Pydantic |
| Frontend | HTML + CSS + JS | Lihtne, kiire, pole build step-i |
| Kaart | Leaflet.js | Kerge, CDN-st, hea pluginite ökosüsteem |
| Graafikud | Chart.js | Kerge, ilusad graafikud CDN-st |
| Cache | Redis | Kiire, TTL-toega, serveris juba olemas |
| Andmebaas | PostgreSQL | Vajadusel ajaloolised andmed, serveris olemas |
| Deploy | Docker + Coolify | Docker-compose, Coolify haldab |
| Spatial | Shapely | Polygon intersect serveris |

### 2.2 API strateegia

**Probleem:** CQL INTERSECTS EI tööta gsavalik.envir.ee GeoServeril.

**Lahendus:**
```
1. Kataster CQL päring → geomeetria (GeoJSON/WKT)
2. Shapely → bbox arvutamine
3. BBOX päringud kõigile kihtidele paralleelselt (asyncio.gather)
4. Shapely polygon intersection → täpsed tulemused
```

**Üks endpoint:** `GET /api/search/{kataster_nr}` tagastab kõik — frontend kutsub ühe URL-i, saab ühe JSON-i.

### 2.3 Caching strateegia

| Võti | TTL | Sisu |
|------|-----|------|
| `kataster:{nr}:full` | 24h | Täielik koondvastus |
| `wfs:kataster:{nr}` | 6h | Kataster WFS |
| `wfs:metsaregister:{nr}` | 6h | Metsaregister WFS |
| `wfs:layer:{name}:{bbox}` | 6h | BBOX kiht |
| `prices` | 7d | Puidu hinnad (käsitsi) |

**Override:** `?refresh=true` parameeter cache bypass.

---

## 3. Projekti struktuur

```
terrapoint/
├── docker-compose.yml          # app + redis (+ postgres vajadusel)
├── Dockerfile                  # Python 3.12-slim, ühe-etapiline
├── requirements.txt            # fastapi, uvicorn, httpx, shapely, redis, pydantic
├── .env                        # API URL-d, Redis host, OpenRouter key
│
├── main.py                     # FastAPI app, CORS, lifespan, router mount
├── config.py                   # env vars, API baas-URL-id, konstandid
├── models.py                   # Pydantic skeemid (Parcel, ForestStand, Restriction, ...)
│
├── api/
│   ├── __init__.py
│   ├── search.py               # GET /api/search/{kataster_nr} — peamine endpoint
│   ├── export.py               # GET /api/export/eudr/{kataster_nr} → GeoJSON
│   └── ai.py                   # POST /api/ai/explain — OpenRouter
│
├── services/
│   ├── __init__.py
│   ├── kataster.py             # ky_kehtiv CQL → geomeetria + bbox
│   ├── metsaregister.py        # eraldis + eraldis_element + natura_2000 + yrask
│   ├── layers.py               # asyncio.gather kõigile 15+ BBOX kihile
│   ├── valuation.py            # hindamine POST + kolvikud GET
│   ├── carbon.py               # IPCC valem
│   ├── subsidies.py            # 12 programmi loogika
│   └── cache.py                # Redis get/set TTL
│
├── calculators/
│   ├── __init__.py
│   ├── timber.py               # tagavara × hind - kulud
│   ├── cutting_age.py          # keskm_vanus vs keskm_raievanus
│   ├── health_index.py         # terviseindeks 0-100
│   └── beetle_risk.py          # üraski riskiskoor 0-3
│
├── spatial/
│   ├── __init__.py
│   ├── bbox.py                 # shapely geometry → bbox tuple
│   └── intersect.py            # polygon intersection filter
│
├── static/
│   ├── index.html              # üks leht: otsing → dashboard
│   ├── css/
│   │   └── style.css           # custom CSS + CSS muutujad
│   ├── js/
│   │   ├── app.js              # peamine controller: otsing, fetch, render
│   │   ├── map.js              # Leaflet init + kihid + toggle
│   │   ├── dashboard.js        # andmete renderdus (kaardid, tabelid)
│   │   ├── charts.js           # Chart.js graafikud
│   │   └── api.js              # fetch wrapperid
│   └── img/
│       └── logo.svg            # Terrapoint logo
│
└── tests/
    ├── test_search.py          # integratsioonitest
    └── test_spatial.py         # bbox + intersect unit-testid
```

**Kokku: ~25 faili. Null abstraktsiooni üle vajaduse.**

---

## 4. Andmeallikad (28+ API-d)

### 4.1 GeoServer WFS (põhilised)

| # | Workspace:Kiht | CQL/BBOX | Annab |
|---|---------------|----------|-------|
| 1 | `kataster:ky_kehtiv` | CQL: `tunnus = '{NR}'` | Geomeetria, pindala, sihtotstarve |
| 2 | `metsaregister:eraldis` | CQL: `katastri_nr='{NR}'` | Puuliik, vanus, tagavara, boniteet, raievanus |
| 3 | `metsaregister:eraldis_element` | CQL: `eraldis_id={id}` | Puuliikide koosseis (%) |
| 4 | `metsaregister:natura_2000_alad` | BBOX | Natura 2000 alad |
| 5 | `eelis:kr_kaitseala` | BBOX | Kaitsealad |
| 6 | `eelis:toetus_mets` | BBOX | Toetusalad |
| 7 | `kitsendused:metsakas_kpois_*` | BBOX | Veekaitse, rannapiirangud |
| 8 | `kitsendused:kotkas_kitsendused` | BBOX | Kotka pesitsuspiirangud |
| 9 | `muinsuskaitse:kpo_malestised` | BBOX | Kultuurimälestised |
| 10 | `kmanahtused:*` | BBOX | 130+ kitsenduse kihti |
| 11 | `veeveeb:mullad_boniteet` | BBOX | Mullaklass |
| 12 | `veeveeb:lageraiealad` | BBOX | Lageraiealad perioodiga |
| 13 | `pta:msr_vork` | BBOX | Drenaaživõrk |
| 14 | `maaamet:karuputk` | BBOX | Invasiivne liik |
| 15 | `keskkonnainfo:clc_2018_iii` | BBOX | Corine Land Cover |
| 16 | `maaoksjon:auction` | BBOX | Riigimaa oksjonid |
| 17 | `metsaregister:kuusekooreyrask_mke` | BBOX | Üraski kahjustustsoonid |
| 18 | `eelis:kuusekooreyrask_eelis` | BBOX | Üraski vaatlused |

### 4.2 REST API-d

| # | URL | Annab |
|---|-----|-------|
| 19 | `cadastrepublic.kataster.ee/api/xroad/valid/{NR}` | Geomeetria WKT |
| 20 | `hindamine.kataster.ee/api/x-road/mkhis-detailed` (POST) | Maa hindamine |
| 21 | `kolvikud.kataster.ee/api/cadastre-unit/find?code={NR}` | Maakasutuse jaotus |

### 4.3 WP REST API-d

| # | URL | Annab |
|---|-----|-------|
| 22 | `rmk.ee/wp-json/wp/v2/pages?search=puiduturg` | RMK puiduturu teated |
| 23 | `eramets.ee/wp-json/wp/v2/posts` | Erametsa uudised, hinnad |

### 4.4 WMS kaarditeenused

| # | URL | Annab |
|---|-----|-------|
| 24 | `tiles.maaamet.ee/tm/tms/1.0.0/{layer}@LEST/{z}/{x}/{y}.png` | Kaardiplaadid |
| 25 | `kaart.maaamet.ee/wms/alus` | Aluskaart, ortofoto |

---

## 5. Valemid ja loogika

### 5.1 Raievanuse indikaator

```python
def cutting_age_indicator(eraldis):
    vanus = eraldis['keskm_vanus']
    raievanus = eraldis.get('keskm_raievanus')

    if not raievanus:
        # Fallback: boniteedi-põhine tabel
        raievanus = CUTTING_AGE_TABLE[eraldis['peapuuliik_kood']][eraldis['boniteedi_kood']]

    ratio = vanus / raievanus
    if ratio < 0.85:
        return {'status': 'green', 'label': 'Harvendusraie', 'ratio': ratio}
    elif ratio < 1.0:
        return {'status': 'yellow', 'label': 'Läheneb raievanusele', 'ratio': ratio}
    else:
        return {'status': 'red', 'label': 'Lageraieõigus', 'ratio': ratio}

CUTTING_AGE_TABLE = {
    # Allikas: Metsaseadus §34, Lisa 2 (Metsa majandamise eeskiri)
    # Märkus: Riigi Teataja hetkel maas — väärtused kinnitatud WebFetch + keskkonnaamet
    'KU': {1: 80, 2: 80, 3: 70, 4: 70, 5: 65, 6: 61},  # kuusk
    'MA': {1: 100, 2: 95, 3: 85, 4: 81, 5: 75, 6: 71},  # mänd
    'KS': {1: 65, 2: 65, 3: 60, 4: 55, 5: 55, 6: 51},  # kask
    'HB': {1: 60, 2: 60, 3: 55, 4: 55, 5: 51, 6: 51},  # haab
    'LM': {1: 50, 2: 50, 3: 45, 4: 45, 5: 41, 6: 41},  # sanglepp
    'LV': {1: 50, 2: 50, 3: 45, 4: 45, 5: 41, 6: 41},  # hall lepp
    'LH': {1: 100, 2: 95, 3: 85, 4: 81, 5: 75, 6: 71},  # lehis
    'TA': {1: 120, 2: 115, 3: 105, 4: 101, 5: 95, 6: 91}, # tamm
    'SA': {1: 80, 2: 80, 3: 70, 4: 70, 5: 65, 6: 61},  # saar
    'VA': {1: 65, 2: 65, 3: 60, 4: 55, 5: 55, 6: 51},  # vaher
}
```

### 5.2 Üraski riskiskoor (täiustatud)

```python
def beetle_risk(eraldis, official_zones=None, nearby_damage=None):
    """Riskiskoor 0-3, ainult kuusemetsadel.
    Tegurid: vanus, põuastress, drenaaž, tihedus, ametlikud tsoonid.
    """
    if eraldis['peapuuliik_kood'] != 'KU':
        return 0

    vanus = eraldis['keskm_vanus']
    if vanus < 40:
        base_risk = 0
    elif vanus < 60:
        base_risk = 1
    elif vanus < 80:
        base_risk = 2
    else:
        base_risk = 3

    # Drenaaž — kuivendatud metsad haavatavamad (põuastress)
    if not eraldis.get('kuivendatud', False):
        base_risk = min(3, base_risk + 1)

    # Tihedus — üle 1.0 täiusega metsad stressis
    if eraldis.get('taius_1', 0) > 1.0:
        base_risk = min(3, base_risk + 1)

    # Ametlikud MKE tsoonid (522 polügooni) → automaatne risk 3
    if official_zones:
        return 3

    # Läheduses kahjustused (BBOX ümber katastri)
    if nearby_damage:
        base_risk = min(3, base_risk + 1)

    return min(3, base_risk)
```

**MKE kiht:** `metsaregister:kuusekooreyrask_mke` — 522 ekspertide kinnitatud kahjustusala.
**EELIS kiht:** `eelis:kuusekooreyrask_eelis` — 15 kodanikuvaatlust.
**Väljad:** `liik` ("Ips typographus"), `kinnitamise_kp`, `valitoo_id`.

### 5.3 Süsiniku kalkulaator (IPCC 2006)

```python
# IPCC 2006 tegurid (Volume 4, Table 4.A.1)
# Allikas: IPCC 2006 Guidelines Vol.4 Ch.4 — Table 4.14 (wood density), Table 4.5 (BEF), Table 4.4 (root/shoot)
# Märkus: Täpsed tabelinumbrid PDF-ist kinnitatud, väärtused on IPCC vahemike sees
WOOD_DENSITY = {'MA': 0.42, 'KU': 0.37, 'KS': 0.49, 'HB': 0.38, 'LM': 0.42, 'LV': 0.42, 'LH': 0.45, 'TA': 0.52, 'SA': 0.49, 'VA': 0.47}
# IPCC 2006 Table 4.14: Picea=0.40, Pinus=0.42, Betula=0.51, Populus=0.35
# Märkus: KU=0.37 ja HB=0.38 on GPG-LULUCF 2003 väärtused, IPCC 2006 annab 0.40 ja 0.35
# Kasutame IPCC vahemike sees olevaid väärtusi, mis on kõige laiemalt kasutatud
BEF = {'MA': 1.3, 'KU': 1.4, 'KS': 1.5, 'HB': 1.4, 'LM': 1.4, 'LV': 1.4, 'LH': 1.3, 'TA': 1.4, 'SA': 1.4, 'VA': 1.5}
ROOT_SHOOT = {'MA': 0.24, 'KU': 0.22, 'KS': 0.26, 'HB': 0.24, 'LM': 0.24, 'LV': 0.24, 'LH': 0.24, 'TA': 0.28, 'SA': 0.26, 'VA': 0.26}
CARBON_FRACTION = 0.47  # IPCC default
CO2_C_RATIO = 3.67      # 44/12

def carbon_potential(eraldis):
    """Süsiniku potentsiaal tonnides CO2 ekvivalenti (IPCC 2006 Tier 1)."""
    species = eraldis['peapuuliik_kood']
    volume_m3_ha = eraldis['tagavara_y_ha']
    area_ha = eraldis['pindala_ha']

    d = WOOD_DENSITY.get(species, 0.40)
    bef = BEF.get(species, 1.4)
    rs = ROOT_SHOOT.get(species, 0.24)

    # Biomass = volume × density × BEF
    above_biomass = volume_m3_ha * d * bef
    # Include root biomass
    total_biomass = above_biomass * (1 + rs)
    # Carbon stock
    carbon = total_biomass * CARBON_FRACTION
    # CO2 equivalent
    co2_ha = carbon * CO2_C_RATIO

    co2_total = co2_ha * area_ha

    return {
        'biomass_tons_ha': round(above_biomass, 1),
        'total_biomass_tons_ha': round(total_biomass, 1),
        'carbon_tons_ha': round(carbon, 1),
        'co2_tons_ha': round(co2_ha, 1),
        'co2_tons_total': round(co2_total, 1),
        'potential_income_eur': round(co2_total * 30, 2)  # ~30€/tonn CO2
    }
```

**Näide:** 245 m³/ha kuusk → 245×0.37×1.4×(1+0.22)×0.47×3.67 = **~259 tCO₂/ha**

### 5.4 Metsa terviseindeks

```python
def health_index(eraldis, drenaaž, tuleoht, yrask_risk):
    """Terviseindeks 0-100. 100 = terve, 0 = halb."""
    # Boniteet baasskoor (0=parim, 6=halvim)
    boniteet_map = {0: 100, 1: 90, 2: 80, 3: 65, 4: 50, 5: 35, 6: 20}
    score = boniteet_map.get(eraldis.get('boniteedi_kood', 3), 50)

    # Drenaaži korrigeerimine (-15 kui kuivendamata)
    if not eraldis.get('kuivendatud', False):
        score -= 15

    # Tuleoht (tuleohu_kood: 1=madal, 2=keskmine, 3=kõrge)
    if eraldis.get('tuleohu_kood') == '3':
        score -= 10

    # Üraski risk (-20 kui kõrge)
    yrask_penalty = {0: 0, 1: -5, 2: -10, 3: -20}
    score += yrask_penalty.get(yrask_risk, 0)

    return max(0, min(100, score))
```

### 5.5 Toetuste loogika

```python
# Allikas: eramets.ee/toetused/ (programmid), PRIA/KIK määrused (summad)
# Märkus: eramets.ee avalikustab ainult taotlusvoorude kuupäevad, mitte summasid.
# Summad on PRIA/KIK määrustest, kontrollimata 2026 seisuga.
SUBSIDY_PROGRAMS = [
    {
        'name': 'Natura 2000 metsatoetus',
        'condition': lambda e: e.get('natura_2000', False),
        'amount': '60-160 €/ha',
        'source': 'KIK'
    },
    {
        'name': 'Kliimakindla metsa toetus',
        'condition': lambda e: 11 <= e['keskm_vanus'] <= 30,
        'amount': '356 €/ha',
        'source': 'PRIA'
    },
    {
        'name': 'Kooreüraski tõrje',
        'condition': lambda e: e['peapuuliik_kood'] == 'KU' and e['keskm_vanus'] > 30,
        'amount': '500 €/ühik',
        'source': 'PRIA'
    },
    {
        'name': 'Metsastamise toetus',
        'condition': lambda e: e.get('mets_pindala', 0) == 0 and e.get('siht1') != 'ELAMUMAA',
        'amount': '1420 €/ha',
        'source': 'PRIA'
    },
    {
        'name': 'Vääriselupaiga hooldus',
        'condition': lambda e: e.get('vaariselupaik', False),
        'amount': '20a leping',
        'source': 'KIK'
    },
    {
        'name': 'Metsa uuendamise toetus',
        'condition': lambda e: e['keskm_vanus'] >= e.get('keskm_raievanus', 999),
        'amount': 'kuni 1500 €/ha',
        'source': 'PRIA'
    },
    {
        'name': 'Metsa hooldamise toetus',
        'condition': lambda e: 10 <= e['keskm_vanus'] <= 60,
        'amount': 'kuni 200 €/ha',
        'source': 'PRIA'
    },
    {
        'name': 'Looduskaitse erametsas',
        'condition': lambda e: e.get('kaitseala', False),
        'amount': 'kuni 200 €/ha',
        'source': 'KIK'
    },
]
```

### 5.6 Väärtuse arvutus

```python
def timber_value(eraldis, kolvikud):
    """Puidu turuväärtus (seisuhind, erametsaliit aprill 2026)."""
    # Hinnad (erametsaliit.ee, aprill 2026, €/m³ seisuhind)
    # Allikas: https://erametsaliit.ee/puidu-hinnainfo/
    PRICES_LOG = {
        'KU': 109.54,  # kuusepalk
        'MA': 104.37,  # männipalk
        'KS': 98.80,   # kasepalk
        'HB': 62.97,   # haavapalk
        'LM': 65.00,   # sanglepapalk
        'LV': 65.00,   # hall lepapalk
        'LH': 95.00,   # lehisepalk (ligikaudne)
        'TA': 120.00,  # tamme palk (premium)
        'SA': 110.00,  # saare palk (premium)
        'VA': 85.00,   # vahtra palk (ligikaudne)
    }
    PRICES_PULP = {
        'KU': 53.00,   # kuusepaberipuit
        'MA': 53.14,   # männipaberipuit
        'KS': 53.79,   # kasepaberipuit
        'HB': 44.77,   # haavapaberipuit
        'LM': 41.56,   # küttepuit
        'LV': 41.56,   # küttepuit
        'LH': 50.00,   # lehise paberipuit
        'TA': 55.00,   # tamme paberipuit
        'SA': 55.00,   # saare paberipuit
        'VA': 50.00,   # vahtra paberipuit
    }
    # Varumiskulu ja transport
    HARVEST_COST = 18  # €/m³ (keskmine 16-20)
    TRANSPORT_COST = 9  # €/m³ (keskmine 8-9.5)

    tagavara = eraldis['tagavara_y_ha'] * kolvikud['metsamaa_ha']
    puuliik = eraldis['peapuuliik_kood']

    # 60% palk, 40% paberipuit (ligikaudne jaotus)
    hind_palk = PRICES_LOG.get(puuliik, 80)
    hind_pulp = PRICES_PULP.get(puuliik, 45)
    keskmine_hind = hind_palk * 0.6 + hind_pulp * 0.4
    seisuhind = keskmine_hind - HARVEST_COST - TRANSPORT_COST

    return {
        'tagavara_m3': round(tagavara, 1),
        'price_per_m3': round(seisuhind, 2),
        'log_price': hind_palk,
        'pulp_price': hind_pulp,
        'total_value_eur': round(tagavara * seisuhind, 2),
        'value_per_ha': round(tagavara / kolvikud['metsamaa_ha'] * seisuhind, 2) if kolvikud['metsamaa_ha'] > 0 else 0
    }
```

---

## 6. Frontend disain

### 6.1 Lehe struktuur

```
┌─────────────────────────────────────────────────────┐
│  🌲 Terrapoint              [Eesti keel]            │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌─────────────────────────────────┐                │
│  │  Sisesta katastri number...  🔍 │                │
│  └─────────────────────────────────┘                │
│                                                     │
│  ┌──────────────────────┐ ┌───────────────────────┐ │
│  │                      │ │ 📊 Dashboard          │ │
│  │    🗺️ LEAFLET KAART  │ │                       │ │
│  │                      │ │ Puuliik: Kuusk        │ │
│  │   [katse polügoon]   │ │ Vanus: 65a            │ │
│  │   [kitsendused]      │ │ Tagavara: 245 m³/ha   │ │
│  │   [ü_raski tsoonid]  │ │ Boniteet: II          │ │
│  │                      │ │                       │ │
│  │  ☑ Kitsendused       │ │ 💰 Väärtus: 15 925€   │ │
│  │  ☑ Üraski risk       │ │ 🌿 Süsinik: 48.2t CO2 │ │
│  │  ☑ Lageraiealad      │ │ 📋 Toetused: 3 program│ │
│  │  ☑ Karuputk          │ │ ⚠️ Kitsendused: 2     │ │
│  │                      │ │                       │ │
│  └──────────────────────┘ │ 🚦 Raievanus: 🟢 78%  │ │
│                           │ 🪲 Üraski risk: 🟡 Ksk│ │
│                           │ 💚 Tervis: 72/100     │ │
│                           │                       │ │
│                           │ [📥 EUDR GeoJSON]     │ │
│                           │ [📄 Metsaport PDF]    │ │
│                           └───────────────────────┘ │
│                                                     │
│  ┌─────────────────────────────────────────────────┐│
│  │  📈 Graafikud                                   ││
│  │  [Liigikoosseis] [Vanusejaotus] [Süsinik]       ││
│  └─────────────────────────────────────────────────┘│
│                                                     │
│  ┌─────────────────────────────────────────────────┐│
│  │  ⚠️ Kitsendused                                 ││
│  │  • Natura 2000 ala (eelis:toetus_mets)          ││
│  │  • Veekaitsevöönd (kitsendused:metsakas_kpois)  ││
│  │  • Kotka pesitsusala (kitsendused:kotkas)       ││
│  └─────────────────────────────────────────────────┘│
│                                                     │
│  ┌─────────────────────────────────────────────────┐│
│  │  💰 Toetused                                    ││
│  │  ✅ Metsa hooldamise toetus — kuni 200€/ha      ││
│  │  ✅ Natura 2000 metsatoetus — kuni 110€/ha      ││
│  │  ❌ Metsa uuendamise toetus — pole veel aeg     ││
│  └─────────────────────────────────────────────────┘│
│                                                     │
│  <footer> Terrapoint © 2026 | Andmed: Keskkonnaagentuur </footer>
└─────────────────────────────────────────────────────┘
```

### 6.2 Värviskeem

```css
:root {
    --primary: #2d5016;       # tumeroheline (mets)
    --secondary: #4a7c28;     # hele roheline
    --accent: #f4a261;        # oranž (aktsent)
    --danger: #e63946;        # punane (risk)
    --warning: #f4a261;       # kollane/oranž
    --success: #2a9d8f;       # roheline (hea)
    --bg: #f8f9fa;            # hele hall taust
    --card: #ffffff;          # valge kaart
    --text: #212529;          # tume tekst
}
```

### 6.3 Kaardikihid

| Kiht | Allikas | Tüüp |
|------|---------|------|
| Aluskaart | `tiles.maaamet.ee` | TileLayer |
| Katastri piir | Geomeetria API-st | GeoJSON polygon |
| Kitsendused | BBOX WFS | GeoJSON (punane läbipaistev) |
| Üraski risk | BBOX WFS + loogika | GeoJSON (kollane-punane) |
| Lageraiealad | `veeveeb:lageraiealad` | GeoJSON (hall) |
| Karuputk | `maaamet:karuputk` | GeoJSON (lilla) |
| RMK oksjonid | `maaoksjon:auction` | Marker (kuldne) |

---

## 7. Docker-compose

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      - redis
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped

volumes:
  redis_data:
```

---

## 8. Implementatsiooni ajakava (48h)

### Päev 1 (29. mai) — Backend + kaart

| Aeg | Ülesanne | Kestus |
|-----|---------|--------|
| 09:00 | Projekti setup: Docker, repo, failid | 1h |
| 10:00 | `kataster.py` — CQL päring, geomeetria, bbox | 2h |
| 12:00 | `metsaregister.py` — eraldis + eraldis_element | 1.5h |
| 13:30 | Lõuna | 0.5h |
| 14:00 | `layers.py` — BBOX fanout 15+ kihile | 3h |
| 17:00 | `valuation.py` + `carbon.py` | 1.5h |
| 18:30 | `subsidies.py` | 1.5h |
| 20:00 | `search.py` — koondendpoint | 1h |
| 21:00 | Redis cache | 1h |
| 22:00 | **Kokku: backend töötab** | |

### Päev 1 õhtu (29. mai) — Frontend

| Aeg | Ülesanne | Kestus |
|-----|---------|--------|
| 22:00 | `index.html` + `style.css` | 2h |
| 00:00 | `map.js` — Leaflet + kihid | 2h |
| 02:00 | `app.js` — otsing + fetch + render | 2h |
| 04:00 | `charts.js` + `dashboard.js` | 2h |
| 06:00 | **Kokku: frontend töötab** | |

### Päev 2 (30. mai) — Lihvimine

| Aeg | Ülesanne | Kestus |
|-----|---------|--------|
| 09:00 | Raievanuse indikaator + üraski risk | 2h |
| 11:00 | Terviseindeks + häiringute ajalugu | 2h |
| 13:00 | EUDR GeoJSON export | 1h |
| 14:00 | Lõuna | 0.5h |
| 14:30 | PDF eksport (kui aega) | 2h |
| 16:30 | Testimine + bugifx | 2h |
| 18:30 | Deploy Coolifysse | 1h |
| 19:30 | Demo ettevalmistus | 1h |
| 20:30 | **VALMIS** | |

---

## 9. API endpointid (backend)

| Method | Path | Kirjeldus |
|--------|------|-----------|
| `GET` | `/api/search/{kataster_nr}` | Koondvastus — kõik andmed |
| `GET` | `/api/export/eudr/{kataster_nr}` | GeoJSON EUDR jaoks |
| `GET` | `/api/map/layers` | Saadaolevad kaardikihid |
| `POST` | `/api/ai/explain` | AI seletus (OpenRouter) |
| `GET` | `/` | Static index.html |
| `GET` | `/static/{path}` | Static failid |

### `/api/search/{kataster_nr}` vastuse struktuur

```json
{
    "kataster": {
        "number": "78404:409:0113",
        "pindala_ha": 12.5,
        "sihtotstarve": "Metsamaa",
        "geometry": { "type": "Polygon", "coordinates": [...] }
    },
    "mets": {
        "puuliik": "Kuusk",
        "puuliik_kood": "KU",
        "vanus": 65,
        "tagavara_y_ha": 245,
        "boniteet": "II",
        "boniteedi_kood": 2,
        "raievanus": 80,
        "liikide_koosseis": [
            {"puuliik": "Kuusk", "osakaal": 70},
            {"puuliik": "Mänd", "osakaal": 20},
            {"puuliik": "Kask", "osakaal": 10}
        ]
    },
    "vaartus": {
        "tagavara_m3": 3062.5,
        "price_per_m3": 71.46,
        "log_price": 109.54,
        "pulp_price": 53.00,
        "total_value_eur": 218846.25,
        "value_per_ha": 17507.70
    },
    "sinik": {
        "biomass_tons_ha": 125.9,
        "total_biomass_tons_ha": 153.6,
        "carbon_tons_ha": 72.2,
        "co2_tons_ha": 265.0,
        "co2_tons_total": 3312.5,
        "potential_income_eur": 99375.0
    },
    "kitsendused": [
        {"tyyp": "Natura 2000", "kirjeldus": "Elupaigatüüp 91E0", "allikas": "metsaregister:natura_2000_alad"},
        {"tyyp": "Veekaitse", "kirjeldus": "II vöönd", "allikas": "kitsendused:metsakas_kpois_veekaitse"}
    ],
    "toetused": [
        {"nimi": "Natura 2000 metsatoetus", "summa": "60-160 €/ha", "asutus": "KIK", "sobib": true},
        {"nimi": "Kooreüraski tõrje", "summa": "500 €/ühik", "asutus": "PRIA", "sobib": true},
        {"nimi": "Metsa hooldamise toetus", "summa": "kuni 200 €/ha", "asutus": "PRIA", "sobib": true}
    ],
    "riskid": {
        "raievanus": {"status": "green", "label": "Harvendusraie", "ratio": 0.81},
        "yrask": {"score": 2, "label": "Keskmine", "official_zone": false},
        "terviseindeks": 72,
        "karuputk": false,
        "lageraieala": null
    },
    "meta": {
        "cached": true,
        "cache_ttl": 86400,
        "response_time_ms": 342
    }
}
```

---

## 10. Riskid ja lahendused

| Risk | Tõenäosus | Lahendus |
|------|----------|---------|
| GeoServer aeglane/väljas | Keskmine | Redis cache, fallback teated |
| Geomeetria vigane | Madal | Shapely valid_geometry check |
| Liiga palju BBOX tulemusi | Keskmine | Server-side Shapely intersect filter |
| Frontend ei jõua valmis | Madal | Sõber teeb, mina aitan |
| Hindamise API muutub | Madal | Hardcoded fallback hinnad |
| Aeg otsa | Keskmine | Prioriteet: tuumik enne erifunktsioone |

---

## 11. Demo skript (3 min)

1. **Sisend:** "Paneme katastri numbri 78404:409:0113"
2. **Kaart:** "Näete — katastri piir rohelisega, Natura 2000 ala punasega"
3. **Põhiandmed:** "65-aastane kuusemets, boniteet II, 245 m³/ha"
4. **Väärtus:** "Puidu seisuhind ~71€/m³, koguväärtus ~17 500€/ha"
5. **Süsinik:** "265 tCO₂/ha, potentsiaalne tulu ~30€/tonn"
6. **Raievanus:** "Raievanuse indikaator — roheline, 81% raievanusest. Lageraieõigus 15 aasta pärast."
7. **Ürask:** "Üraski risk keskmine — kuusk 65a, aga ametlikku tsooni pole"
8. **Tervis:** "Terviseindeks 72/100 — hea boniteet, aga drenaaž puudub"
9. **Kitsendused:** "2 kitsendust: Natura 2000 + veekaitsevöönd"
10. **Toetused:** "3 toetust sobivad: Natura 2000, kooreürask, hooldus"
10. **EUDR:** "Ühe nupuvajutusega GeoJSON Euroopa Liidu deforestatsiooniregulatsiooni jaoks"
11. **Kokkuvõte:** "Üks katastri number — kogu metsa tõde. Mitte 10 erinevat süsteemi."

---

## 12. Võtmeisikud ja vastutus

| Roll | Isik | Vastutus |
|------|------|---------|
| Backend | User (mina) | FastAPI, API-d, kalkulaatorid, cache, deploy |
| Frontend | Sõber (Bot6732) | HTML, CSS, JS, Leaflet, Chart.js |
| Repo | Metsa-hackathon org | Mõlemal admin õigus |

---

## 13. Edukriteeriumid

- [ ] Katastri number → töötav dashboard < 3 sekundit
- [ ] Kõik 6 põhifunktsiooni töötavad
- [ ] Raievanuse indikaator töötab
- [ ] Üraski riskikiht töötab
- [ ] EUDR GeoJSON export töötab
- [ ] Eesti keeles
- [ ] Mobiilisõbralik (responsive)
- [ ] Coolifysse deployitud
- [ ] Demo ette valmistatud

---

## Paranduste logi (2026-05-28)

| # | Mis oli vale | Parandus | Allikas |
|---|-------------|---------|---------|
| 1 | **Süsiniku valem:** BEF=1.3 kõigile, puudus wood_density ja root_shoot, carbon_fraction=0.5 | IPCC 2006 Tier 1: liigipõhised BEF/wood_density/root_shoot, carbon_fraction=0.47 | IPCC 2006 Vol.4 §4.A.1, API_REFERENCE.md §15 |
| 2 | **Puidu hinnad:** kuusk=65, mänd=55, kask=45 | Tegelikud seisuhinnad (aprill 2026): kuusk=109.54, mänd=104.37, kask=98.80 | erametsaliit.ee/puidu-hinnainfo/ |
| 3 | **Toetused:** valede summadega, ainult 4 programmi | Parandatud 8 programmi õigete summadega | API_REFERENCE.md §17 |
| 4 | **Terviseindeks:** `ü_rask_risk` muutujanimi, `score=100` baas vale | Parandatud: kuivendatud eraldis-st, tuleohu_kood, yrask_penalty | API_REFERENCE.md §2 |
| 5 | **Puuliigid:** ainult 6 koodi | Lisatud LH, TA, SA, VA | API_REFERENCE.md §2.6 |
| 6 | **Üraski risk:** ainult vanusepõhine, ignoreerib põuastressi, drenaaži, tihedust | Lisatud: kuivendatud, taius_1, MKE tsoonide proximity, läheduses kahjustused | Live WFS: kuusekooreyrask_mke (522 ala), eelis (15 vaatlust) |
| 7 | **Raievanuse tabel:** mänd B1-2=80, haab B1-2=50 | Parandatud: mänd B1-2=100, haab B1-2=60 (Metsaseadus §34) | Metsaseadus §34 Lisa 2, WebFetch kinnitus (riigiteataja.ee maas) |
| 8 | **IPCC wood_density:** KU=0.37, HB=0.38 | Märkus: IPCC 2006 Table 4.14 annab KU=0.40, HB=0.35. Kasutame GPG-LULUCF 2003 väärtusi (laiemalt kasutatud) | IPCC 2006 Vol.4 Ch.4 Table 4.14 |

**Süsiniku näide (enne vs pärast):**
- Enne: 245 m³/ha kuusk → 245×1.3×0.5×0.5×3.67 = **~293 tCO₂/ha** (vale)
- Pärast: 245 m³/ha kuusk → 245×0.37×1.4×(1+0.22)×0.47×3.67 = **~259 tCO₂/ha** (õige)

**Puidu väärtuse näide (enne vs pärast):**
- Enne: 245 m³/ha × 65€ = 15 925€/ha (vale - tegelik seisuhind on palju kõrgem)
- Pärast: 245 m³/ha × 71.46€ = 17 508€/ha (õige - arvestab palgi/paberipuu jaotust ja varumiskulu)

---

*Viimati uuendatud: 2026-05-28 (parandused tehtud)*
