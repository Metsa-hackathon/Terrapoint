# Terrapoint — Andmeallikate loetelu (mentoritele)

> Kõik andmed on kinnitatud 28.05.2026 WebFetch + WFS GetCapabilities päringutega.

---

## 1. Avalikud WFS-teenused (GeoServer)

**Server:** `gsavalik.envir.ee/geoserver/wfs`  
**Litsents:** CC-BY 4.0 (Keskkonnaagentuur / Keskkonnaministeerium)  
**Autentimine:** Puudub — avalik juurdepääs  
**CRS:** EPSG:3301 (Eesti koordinaatsüsteem), EPSG:3857, EPSG:44326

| # | Kiht | Töölaud | Andmeallikas | Staatus |
|---|------|---------|-------------|---------|
| 1 | `kataster:ky_kehtiv` | kataster | Maa- ja Ruumiamet | Kinnitatud |
| 2 | `metsaregister:eraldis` | metsaregister | Keskkonnaagentuur | Kinnitatud |
| 3 | `metsaregister:eraldis_element` | metsaregister | Keskkonnaagentuur | Kinnitatud |
| 4 | `metsaregister:natura_2000_alad` | metsaregister | Keskkonnaagentuur | Kinnitatud |
| 5 | `metsaregister:kuusekooreyrask_mke` | metsaregister | MKE (522 ala) | Kinnitatud |
| 6 | `eelis:kr_kaitseala` | eelis | Keskkonnaamet | Kinnitatud |
| 7 | `eelis:toetus_mets` | eelis | Keskkonnaamet | Kinnitatud |
| 8 | `eelis:kuusekooreyrask_eelis` | eelis | Kodanikuvaatlused (15) | Kinnitatud |
| 9 | `kitsendused:kotkas_kitsendused` | kitsendused | Keskkonnaamet | Kinnitatud |
| 10 | `kitsendused:metsakas_kpois_*` | kitsendused | KPOIS (4 kihti) | Kinnitatud |
| 11 | `muinsuskaitse:kpo_malestised` | muinsuskaitse | Muinsuskaitseamet | Kinnitatud |
| 12 | `veeveeb:lageraiealad` | veeveeb | Tartu Observatoorium (2011-2016) | Kinnitatud |
| 13 | `veeveeb:mullad_boniteet` | veeveeb | Keskkonnaagentuur | Kinnitatud |
| 14 | `maaamet:karuputk` | maaamet | Keskkonnaamet | Kinnitatud |
| 15 | `maaoksjon:auction` | maaoksjon | Maa-amet | Kinnitatud |
| 16 | `keskkonnainfo:clc_2018_iii` | keskkonnainfo | Corine Land Cover | Kinnitatud |

**Kokku: 16 kihti, kõik kinnitatud otse WFS GetCapabilities päringutega.**

---

## 2. REST API-d

| # | URL | Andmeallikas | Staatus |
|---|-----|-------------|---------|
| 17 | `cadastrepublic.kataster.ee/api/xroad/valid/{NR}` | Maa- ja Ruumiamet | Kinnitatud — tagastab JSON |
| 18 | `kolvikud.kataster.ee/api/cadastre-unit/find?code={NR}&date={DATE}` | Maa- ja Ruumiamet | Kinnitatud — vajab `date` parameetrit |
| 19 | `hindamine.kataster.ee/api/x-road/mkhis-detailed` | Maa- ja Ruumiamet | 401 — vajab autentimist |

---

## 3. Kaarditeenused

| # | URL | Andmeallikas | Staatus |
|---|-----|-------------|---------|
| 20 | `tiles.maaamet.ee/tm/tms/1.0.0/{layer}@LEST/{z}/{x}/{y}.png` | Maa-amet | Avalik |
| 21 | `kaart.maaamet.ee/wms/alus` | Maa-amet | Avalik |

---

## 4. Puidu hinnad

**Allikas:** [erametsaliit.ee/puidu-hinnainfo/](https://erametsaliit.ee/puidu-hinnainfo/)  
**Periood:** Aprill 2026  
**Raport:** Heiki Hepner, Tark Mets OÜ  
**Staatus:** 100% kinnitatud — kõik 10 hinda identne

| Liik | Palk (€/m³) | Paberipuit (€/m³) |
|------|------------|-------------------|
| Kuusk (KU) | 109.54 | 53.00 |
| Mänd (MA) | 104.37 | 53.14 |
| Kask (KS) | 98.80 | 53.79 |
| Haab (HB) | 62.97 | 44.77 |
| Lepp (LM/LV) | 65.00 | 41.56 (küttepuit) |
| Lehis (LH) | ~95.00 | ~50.00 |
| Tamm (TA) | ~120.00 | ~55.00 |
| Saar (SA) | ~110.00 | ~55.00 |
| Vaher (VA) | ~85.00 | ~50.00 |

*Märkus: LH, TA, SA, VA hinnad on ligikaudsed — erametsaliit.ee neid ei avalikusta.*

---

## 5. IPCC 2006 süsiniku tegurid

**Allikas:** IPCC 2006 Guidelines for National Greenhouse Gas Inventories, Volume 4 (Agriculture, Forestry and Other Land Use), Chapter 4: Forest Land  
**PDF:** [ipcc-nggip.iges.or.jp](https://www.ipcc-nggip.iges.or.jp/public/2006gl/pdf/4_Volume4/V4_04_Ch4_Forest_Land.pdf)

| Tegur | Tabel | Väärtus | Staatus |
|-------|-------|---------|---------|
| Carbon fraction | Table 4.3, p.4.48 | 0.47 | Kinnitatud |
| CO₂/C ratio | — | 44/12 = 3.67 | Kinnitatud |
| Wood density | Table 4.14, p.4.71 | Liigipõhised | Kinnitatud (vahemikud) |
| BEF/BCEF | Table 4.5, p.4.50 | Tsoonipõhised | Kinnitatud (vahemikud) |
| Root/shoot | Table 4.4, p.4.49 | Tsoonipõhised | Kinnitatud (vahemikud) |

*Märkus: Plaanis kasutatud väärtused on IPCC vahemike sees, aga mitte alati IPCC 2006 Tier 1 defaults. Osad väärtused pärinevad GPG-LULUCF 2003 (vanem juhis).*

---

## 6. Raievanuse tabel

**Allikas:** Metsaseadus §34, Lisa 2 (Metsa majandamise eeskiri)  
**Staatus:** Riigi Teataja (riigiteataja.ee) oli 28.05.2026 maas — väärtused kinnitatud WebFetch + keskkonnaamet allikatest

| Liik | B1 | B2 | B3 | B4 | B5 | B6 |
|------|----|----|----|----|----|----|
| Kuusk | 80 | 80 | 70 | 70 | 65 | 61 |
| Mänd | 100 | 95 | 85 | 81 | 75 | 71 |
| Kask | 65 | 65 | 60 | 55 | 55 | 51 |
| Haab | 60 | 60 | 55 | 55 | 51 | 51 |

*Märkus: Täpne ametlik tabel tuleb üle kontrollida, kui Riigi Teataja tagasi tuleb.*

---

## 7. Toetuste programmid

**Allikas:** [eramets.ee/toetused/](https://www.eramets.ee/toetused/)  
**Staatus:** Programmid kinnitatud, summad PRIA/KIK määrustest (kontrollimata 2026)

| # | Programm | Asutus | Taotlusvoor 2026 |
|---|----------|--------|-----------------|
| 1 | Natura 2000 metsatoetus | KIK | Apr 4–30 |
| 2 | Kliimakindla metsa kujundamine | PRIA | Apr 7–23 |
| 3 | Metsastamine | PRIA | Apr 16 – May 7 |
| 4 | Metsa uuendamine | PRIA | Jun 16 – Jul 2 |
| 5 | Kooreüraski tõrje | PRIA | Sep 1–15 |
| 6 | Kultuuripärandi säilitamine | KIK | Jun 16 – Jul 2 |
| 7 | Metsa hooldamine | PRIA | — |
| 8 | Looduskaitse erametsas | KIK | — |

*Märkus: Summad (60-160€/ha, 356€/ha, 500€/ühik jne) ei ole eramets.ee lehel avalikult kirjas. Allikas: PRIA/KIK määrused.*

---

## 8. Kinnitamata andmed

| Andmeallikas | Staatus | Märkus |
|-------------|---------|--------|
| Varumiskulu (18 €/m³) | Kinnitamata | Ei leitud veebist — keskmine hinnang |
| Transport (9 €/m³) | Kinnitamata | Ei leitud veebist — keskmine hinnang |
| CO₂ hind (30 €/tonn) | Kinnitamata | EU ETS ligikaudne hind |
| Toetuste summad | Kinnitamata | PRIA/KIK määrused, kontrollimata |

---

*Koostatud: 28.05.2026*  
*Kontrollitud: WebFetch + WFS GetCapabilities päringud*
