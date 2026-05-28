# Metsa Pass — API Referents

## Ülevaade

Kõik API-d töötavad **ilma autentimiseta** (CC BY 4.0 litsents). Baas-URL: `gsavalik.envir.ee/geoserver`

## 1. KATASTER WFS — Põhiandmed + geomeetria

**Workspace:** `kataster`
**Layer:** `kataster:ky_kehtiv`
**CRS:** EPSG:4326 (WGS84)

### Päring katastri numbri järgi:
```
GET https://gsavalik.envir.ee/geoserver/kataster/wfs
  ?service=WFS
  &request=GetFeature
  &typeName=kataster:ky_kehtiv
  &srsName=EPSG:4326
  &outputFormat=application/json
  &CQL_FILTER=tunnus%20%3D%20%2778404%3A409%3A0113%27
```

**CQL filteri trikk:** Koolonid peavad olema URL-encoded (`%3A`), `=` peab olema `%20%3D%20`

### Väljundväljad:
| Väli | Tüüp | Kirjeldus |
|------|------|-----------|
| tunnus | string | Katastri number (nt "78404:409:0113") |
| pindala | int | Kogupindala m² |
| mets | int/null | Metsamaa pindala m² |
| haritav | int/null | Haritav maa m² |
| rohumaa | int/null | Looduslik rohumaa m² |
| ouemaa | int/null | Õuemaa m² |
| muumaa | int/null | Muu maa m² |
| siht1 | string | Sihtotstarbe: ELAMUMAA, MAATULUNDUSMAA, TRANSPORDIMAA jne |
| maks_hind | int | Maksustamishind EUR |
| omvorm | string | Omandivorm: Eraomand, Riigiomand, Munitsipaalomand |
| mk_nimi | string | Maakond |
| ov_nimi | string | Omavalitsus |
| l_aadress | string | Aadress |
| kinnistu | string | Kinnistu number |
| geom | GeoJSON | Geomeetria (Polygon, EPSG:4326) |

---

## 2. METSAREGISTER WFS — Metsaandmed

**Workspace:** `metsaregister`
**CRS:** EPSG:4326

### 2.1 Eraldised (põhikiht)

```
GET https://gsavalik.envir.ee/geoserver/metsaregister/wfs
  ?service=WFS
  &request=GetFeature
  &typeName=metsaregister:eraldis
  &srsName=EPSG:4326
  &outputFormat=application/json
  &CQL_FILTER=katastri_nr='78404:409:0113'
```

### Väljundväljad (35 välja):
| Väli | Tüüp | Kirjeldus |
|------|------|-----------|
| id | long | Eraldise ID (võti eraldis_element jaoks) |
| katastri_nr | string | Katastri number |
| kvartali_nr | string | Kvartali number |
| eraldise_nr | int | Eraldise number |
| pindala | double | Pindala hektarites |
| peapuuliik_kood | string | Peapuuliik (MA=mänd, KU=kuusk, KS=kask, HB=haab) |
| keskm_vanus | int | Keskmine vanus (aastat) |
| korgus | double | Keskmine kõrgus (meetrit) |
| boniteedi_kood | string | Boniteet (0=parim, 6=halvim) |
| tagavara_1_ha | double | 1. rinde tagavara m³/ha |
| tagavara_y_ha | double | Kogutagavara m³/ha |
| keskm_raievanus | double | Keskmine raievanus |
| juurdekasv | double | Aastane juurdekasv |
| taius_1 | double | 1. rinde täius |
| kasvukoht_kood | string | Kasvukoha tüüp (FK kl_kasvukoht) |
| omandivorm_kood | string | Omandivorm (F=eraisik, J=juriidiline, R=riik) |
| tuleohu_kood | string | Tuleohu klass |
| kuivendatud | boolean | Kas kuivendatud |
| invent_kp | date | Inventeerimise kuupäev |

### 2.2 Eraldise koosseis (puuliigid)

```
GET ...&typeName=metsaregister:eraldis_element
  &CQL_FILTER=eraldis_id=10713755
```

| Väli | Tüüp | Kirjeldus |
|------|------|-----------|
| eraldis_id | long | FK eraldis.id |
| rinne_kood | string | Rind (1=I rinne, 2=II rinne, J=noorendik) |
| puuliik_kood | string | Puuliik |
| osakaal | int | Osakaal % |
| vanus | int | Vanus |
| korgus | double | Kõrgus (m) |
| diameeter | double | Diameeter (cm) |
| rinnaspindala | double | Rinnaspindala m²/ha |
| tagavara | double | Tagavara m³/ha |

### 2.3 Natura 2000 alad

```
GET ...&typeName=metsaregister:natura_2000_alad
  &bbox=24.5,59.3,25.0,59.5,EPSG:4326
```

### 2.4 Kehtivad raie teatised

```
GET ...&typeName=metsaregister:teatis
  &CQL_FILTER=katastri_nr='78404:409:0113'
```

### 2.5 Kooreüraski kahjustusalad

```
GET ...&typeName=metsaregister:kuusekooreyrask_mke
  &bbox=24.5,59.3,25.0,59.5,EPSG:4326
```

### 2.6 Kahjustuste kirjed (eraldis_id-ga)

```
GET ...&typeName=metsaregister:kahjustused
  &CQL_FILTER=eraldis_id=10713755
```

### Klassifikaatorid:

**Puuliigid (kl_puuliik):**
| Kood | Eesti | English |
|------|-------|---------|
| MA | Mänd | Pine |
| KU | Kuusk | Spruce |
| KS | Kask | Birch |
| HB | Haab | Aspen |
| LH | Lehis | Larch |
| LM | Sanglepp | Black alder |
| LV | Hall lepp | Grey alder |
| TA | Tamm | Oak |
| SA | Saar | Ash |
| VA | Vaher | Maple |

**Omandivorm (kl_omandivorm):**
| Kood | Kirjeldus |
|------|-----------|
| F | Eraisik |
| J | Juriidiline isik |
| R | Riik |
| M | Omavalitsus |

---

## 3. CADASTREPUBLIC API — Geomeetria + põhiandmed

```
GET https://cadastrepublic.kataster.ee/api/xroad/valid/78404%3A409%3A0113
```

**URL encoding:** Koolonid → `%3A`

### Väljund:
| Väli | Tüüp | Kirjeldus |
|------|------|-----------|
| tunnus | string | Katastri number |
| geom | WKT | Geomeetria (POLYGON, EPSG:3301) |
| pindala | int | Pindala m² |
| siht1 | string | Sihtotstarbe |
| omvorm | string | Omandivorm |
| maks_hind | int | Maksustamishind EUR |
| aadress | string | Aadress |
| tais_aadress | string | Täisaadress |
| registreeritud | date | Registreerimise kp |

---

## 4. HINDAMINE API — Maa hindamine

```
POST https://hindamine.kataster.ee/api/x-road/mkhis-detailed
Content-Type: application/json

{"cadastreId": "78404:409:0113"}
```

### Väljund:
```json
{
  "data": {
    "cadastralUnit": {
      "validValue": 2210985,
      "area": 216544,
      "acquisitionType": "Riigiomand",
      "validFrom": "2025-12-11"
    },
    "calculation": [
      {
        "year": 2022,
        "usageCode": "811",        // 811 = metsamaa
        "habitatCode": 3,          // elupaiga tüüp
        "area": 190588,
        "unitValue": 10.0,         // €/m²
        "partValue": 1905880.0     // koguväärtus
      }
    ]
  }
}
```

**usageCode 811 = metsamaa**
**unitValue × 10000 = €/hektar**

---

## 5. KOLVIKUD API — Maakasutuse jaotus

```
GET https://kolvikud.kataster.ee/api/cadastre-unit/find
  ?date=2025-01-01
  &code=78404:409:0113
```

### Väljund:
```json
[{
  "landParcelSummary": [
    {"type": {"code": "forest", "name": "Metsamaa"}, "computedArea": 190322.0},
    {"type": {"code": "yard", "name": "Õuemaa"}, "computedArea": 1420.0},
    {"type": {"code": "other", "name": "Muu maa"}, "computedArea": 22618.0}
  ],
  "geometry": "{\"type\":\"Polygon\",\"coordinates\":[...],\"crs\":{\"type\":\"name\",\"properties\":{\"name\":\"EPSG:3301\"}}}"
}]
```

---

## 6. EELIS WFS — Looduskaitse

**Workspace:** `eelis`

### 6.1 Kaitsealad
```
GET https://gsavalik.envir.ee/geoserver/eelis/wfs
  ?service=WFS&request=GetFeature
  &typeName=eelis:kr_kaitseala
  &srsName=EPSG:4326
  &outputFormat=application/json
  &bbox=24.5,59.3,25.0,59.5,EPSG:4326
```

**Väljad:** nimi, tyyp (KMKA=maastikukaitseala, KLKA=looduskaitseala, KRP=rahvuspark), kr_kood, valitseja

### 6.2 Metsatoetuste alad
```
GET ...&typeName=eelis:toetus_mets
```

**Väljad:** kr_kood, tunnus, tyyp, ala_tyyp, voond_liik, pindala_ha

### 6.3 Natura elupaigad
```
GET ...&typeName=eelis:natura_elupaik
```

### 6.4 Liigi vaatlused
```
GET ...&typeName=eelis:liigi_alamkirjed_avalik
```

### 6.5 Metsa pärandobjektid
```
GET ...&typeName=eelis:pk_objekt_metsas
```

### 6.6 Kooreüraski vaatlused
```
GET ...&typeName=eelis:kuusekooreyrask_eelis
```

---

## 7. KITSENDUSED WFS — Kitsendused

**Workspace:** `kitsendused`

```
GET https://gsavalik.envir.ee/geoserver/kitsendused/wfs
  ?service=WFS&request=GetFeature
  &typeName=kitsendused:metsakas_kpois_RANNA_VOI_KALDA_VEEKAITSEVOOND
  &srsName=EPSG:4326
  &outputFormat=application/json
  &bbox=24.5,59.3,25.0,59.5,EPSG:4326
```

**Kitsenduse tüübid:**
- `metsakas_kpois_RANNA_VOI_KALDA_VEEKAITSEVOOND` — ranna/kalda veekaitsevöönd
- `metsakas_kpois_RANNA_VOI_KALDA_PIIRANGUVOOND` — ranna/kalda piiranguvöönd
- `metsakas_kpois_KORDUV_ULEUJUTUSALA` — korduv üleujutusala
- `metsakas_kpois_VAETISTE_JA_TAIMEKAITSEV_KEELD` — väetiste keeld

---

## 8. MUINSUSKAITSE WFS

**Workspace:** `muinsuskaitse`

```
GET https://gsavalik.envir.ee/geoserver/muinsuskaitse/wfs
  ?service=WFS&request=GetFeature
  &typeName=muinsuskaitse:kpo_malestised
  &srsName=EPSG:4326
  &outputFormat=application/json
  &bbox=24.5,59.3,25.0,59.5,EPSG:4326
```

---

## 9. LISAKIHIID GeoServeris

### Riigivara (katri workspace)
```
GET https://gsavalik.envir.ee/geoserver/katri/wfs
  ?service=WFS&request=GetFeature
  &typeName=katri:state_property_ownership
  &srsName=EPSG:4326&outputFormat=application/json
  &bbox=24.5,59.3,25.0,59.5,EPSG:4326
```
**71K riigivarad.** Väljad: `katastritunnus`, `riigivara_valitseja`, `volitatud_asutus` (RMK metsade puhul), `vara_liik`

### Kaitsealad (ps workspace — INSPIRE)
```
GET https://gsavalik.envir.ee/geoserver/ps/wfs
  ?service=WFS&request=GetFeature
  &typeName=ps:ProtectedSite
  &count=5&srsName=EPSG:4326&outputFormat=application/json
  &bbox=24.5,59.3,25.0,59.5,EPSG:3035
```
**4,648 kaitseala.** CRS: EPSG:3035 (ETRS89-LAEA)

### Veemajandus (vmk workspace)
```
GET https://gsavalik.envir.ee/geoserver/vmk/wfs
```
**25 kihti:** reostus, pohjavesi, kraavid, paisud, vesikonnad, seisund

### Metsamuutused (LiDAR)
- Allalaadimine: `https://geoportaal.maaruum.ee/docs/Avaandmed/Metsamuutused_*.zip`
- Kaart: `https://xgis.maaamet.ee/xgis2/page/app/metsamuutused`

### Lageraiealad
```
GET ...workspace=veeveeb&typeName=veeveeb:lageraiealad
```

### Mullad ja boniteet
```
GET ...workspace=veeveeb&typeName=veeveeb:mullad_boniteet
GET ...workspace=veeveeb&typeName=veeveeb:liht_mullakaart
```

### Jahipiirkonnad
```
GET ...workspace=eelis&typeName=eelis:kr_jahipiirkond
```

### Metsise elupaigad
```
GET ...workspace=piiratud&typeName=piiratud:metsisemang
```

### Ristipuud
```
GET ...workspace=keskkonnainfo&typeName=keskkonnainfo:ristipuud
```

### Kotka pesitsuspiirangud
```
GET https://gsavalik.envir.ee/geoserver/kitsendused/wfs
  ?service=WFS&request=GetFeature
  &typeName=kitsendused:kotkas_kitsendused
  &srsName=EPSG:4326&outputFormat=application/json
  &bbox={BBOX},EPSG:4326
```
**336 piirangut.** Väljad: kma_kood, voondi_nimetus, objekti_nimetus, nahtus_kood, ulatus_m

### Kmanahtused (looduskaitse tsoonid)
```
GET https://gsavalik.envir.ee/geoserver/kmanahtused/wfs
  ?service=WFS&request=GetFeature
  &typeName=kmanahtused:kma_avalik_looduskaitse_211_3001
  &srsName=EPSG:4326&outputFormat=application/json
  &bbox={BBOX},EPSG:4326
```
**130+ kihti.** Tüübid:
- `kma_avalik_looduskaitse_211_*` — kaitsealad (reservaadid, sihtkaitsevööndid, piiranguvööndid)
- `kma_avalik_veekogu_221_*` — veekogu kaitsevööndid
- `kma_avalik_maaparandus_231` — maaparandussüsteemid (nimi, maksusoodustus, reegel, ulatus)
- `kma_avalik_reostusoht_261*` — reostusohtlikud alad

### Etak (topograafia)
```
GET https://gsavalik.envir.ee/geoserver/etak/wfs
  ?service=WFS&request=GetFeature
  &typeName=etak:e_305_puittaimestik_a
  &srsName=EPSG:4326&outputFormat=application/json
  &bbox={BBOX},EPSG:4326
```
**39 kihti.** Tähtsamad:
- `e_305_puittaimestik_a` — puittaimestik (mets). Väljad: kood, tyyp (10=Mets), tyyp_tekst
- `e_303_haritav_maa_a` — haritav maa
- `e_306_margala_a` — märgala (tyyp: 20=Raba)
- `e_307_turbavali_a` — turba kaevandamine

### Mullad ja põhjavesi (veeveeb)
```
GET https://gsavalik.envir.ee/geoserver/veeveeb/wfs
  ?service=WFS&request=GetFeature
  &typeName=veeveeb:mullad_boniteet
  &srsName=EPSG:4326&outputFormat=application/json
  &bbox={BBOX},EPSG:4326
```
**8 kihti.** Väljad:
- `mullad_boniteet` — mullaklass (hea/keskmine/halb)
- `liht_mullakaart` — mullatüüp (loimis_1, morfsus_1)
- `pohjavesi_kaitstus` — põhjavee kaitstus (tase 1-5)
- `lageraiealad` — lageraiealad (periood_a, periood_o)

### Drenaaživõrk (pta)
```
GET https://gsavalik.envir.ee/geoserver/pta/wfs
  ?service=WFS&request=GetFeature
  &typeName=pta:msr_vork
  &srsName=EPSG:4326&outputFormat=application/json
  &bbox={BBOX},EPSG:4326
```
**5 kihti.** Väljad: ms_kood, ehitise_nimi, nahtuse_liik, pind_ha, aasta

### Karuputk (invasiivne liik)
```
GET https://gsavalik.envir.ee/geoserver/maaamet/wfs
  ?service=WFS&request=GetFeature
  &typeName=maaamet:karuputk
  &srsName=EPSG:4326&outputFormat=application/json
  &bbox={BBOX},EPSG:4326
```
Väljad: koloonia_id, torjeyksus, pindala, seisund, torjemeetod, raskusaste

### Corine Land Cover
```
GET https://gsavalik.envir.ee/geoserver/keskkonnainfo/wfs
  ?service=WFS&request=GetFeature
  &typeName=keskkonnainfo:clc_2018_iii
  &srsName=EPSG:4326&outputFormat=application/json
  &bbox={BBOX},EPSG:4326
```
Väljad: maakate_kood, maakate_selgitus. Ajalugu: 1990, 2000, 2006, 2012

### Riigimaade oksjonid
```
GET https://gsavalik.envir.ee/geoserver/maaoksjon/wfs
  ?service=WFS&request=GetFeature
  &typeName=maaoksjon:auction
  &srsName=EPSG:4326&outputFormat=application/json
  &bbox={BBOX},EPSG:4326
```
Väljad: purpose, starting_price, offer_deadline, status, url

### WMS-only kihid (401 WFS-il):
- `mr_piiratud:metsisemang` — metsise elupaigad
- `mr_piiratud:pesitsusrahu_maatriks` — pesitsusrahu
- `piiratud:metsaelupaigad` — metsaelupaigad
- `piiratud:jahipiiranguga_alad` — jahipiirangud

---

## 10. SPATIAL QUERY STRATEEGIA

**TÄHTIS:** CQL INTERSECTS EI tööta sellel GeoServeril. Peab kasutama BBOX.

### Töövoog:
```
1. CQL päring: kataster:ky_kehtiv WHERE tunnus='{NR}' → saame geomeetria
2. Arvuta bbox geomeetriast (EPSG:4326)
3. BBOX päring kõigile teistele kihtidele
4. (Valikuline) Kliendipoolne INTERSECTS täpsuse jaoks
```

### BBOX arvutamine:
```python
from shapely.geometry import shape
geom = shape(feature['geometry'])
bbox = geom.bounds  # (minx, miny, maxx, maxy)
```

### Kihtide päringu järjekord:
1. `kataster:ky_kehtiv` — CQL tunnus → geomeetria
2. `metsaregister:eraldis` — CQL katastri_nr → metsaandmed
3. `metsaregister:eraldis_element` — CQL eraldis_id → puuliikide koosseis
4. BBOX päringud (kõik paralleelselt):
   - `eelis:kr_kaitseala` — kaitsealad
   - `eelis:natura_elupaik` — Natura elupaigad
   - `eelis:toetus_mets` — toetusalad
   - `metsaregister:natura_2000_alad` — Natura 2000
   - `kitsendused:metsakas_kpois_*` — veekaitse
   - `kitsendused:kotkas_kitsendused` — kotka piirangud
   - `muinsuskaitse:kpo_malestised` — muinsuskaitse
   - `kmanahtused:kma_avalik_looduskaitse_*` — looduskaitse tsoonid
   - `veeveeb:mullad_boniteet` — mulla boniteet
   - `pta:msr_vork` — drenaaž
   - `maaamet:karuputk` — invasiivne liik
   - `maaoksjon:auction` — oksjonid

---

## 11. WORDPRESS API'd

### RMK (riigimets)
```
GET https://www.rmk.ee/wp-json/wp/v2/pages?search=puit&per_page=5
```
Annab puiduturu teated HTML-na.

### Erametsakeskus
```
GET https://www.eramets.ee/wp-json/wp/v2/posts?search=mets&per_page=5
```
Kategooriad: metsandusuudised, puiduturg-ja-toostus, toetuste-info-ja-teated

### Metsainfo.ee
```
GET https://metsainfo.ee/wp-json/wp/v2/posts?per_page=5
```
Metsanduse teadusartiklid.

---

## 12. KAARDIPLAADID (tiles.maaamet.ee)

**TMS:** `https://tiles.maaamet.ee/tm/tms/1.0.0/{layer}@{crs}/{z}/{x}/{y}.png`
**WMTS:** `https://tiles.maaamet.ee/tm/wmts?`

| Kiht | Kirjeldus |
|------|-----------|
| `kaart@LEST` / `kaart@GMC` | Eesti aluskaart |
| `foto@LEST` / `foto@GMC` | Ortofoto |
| `hybriid@LEST` / `hybriid@GMC` | Foto + sildid |
| `hallkaart@LEST` | Hallkaart |
| `epk_v@LEST` | Värviline aluskaart |
| `topo@LEST` | Kõrgusandmed |

CRS: `@LEST` = EPSG:3301, `@GMC` = EPSG:3857

---

## 13. AADRESSI API (inaadress)

```
GET https://inaadress.maaamet.ee/inaadress/gazetteer?request=layers
```
Tagastab kaardikihid. Aadressiotsing: `?request=search&address=...`

---

## 14. RMK PUIDUTURG (WordPress API)

```
GET https://www.rmk.ee/wp-json/wp/v2/pages?search=puit
```
Tagastab RMK puiduturu teated (HTML sisuga).

---

## 15. SÜSINIKU ARVUTUSE VALEM

```python
# IPCC 2006 tegurid
WOOD_DENSITY = {'MA': 0.42, 'KU': 0.37, 'KS': 0.49, 'HB': 0.38}
BEF = {'MA': 1.3, 'KU': 1.4, 'KS': 1.5, 'HB': 1.4}  # Biomass Expansion Factor
ROOT_SHOOT = {'MA': 0.24, 'KU': 0.22, 'KS': 0.26, 'HB': 0.24}
CARBON_FRACTION = 0.47
CO2_C_RATIO = 3.67

def carbon_stock(species, volume_m3_ha):
    d = WOOD_DENSITY.get(species, 0.40)
    bef = BEF.get(species, 1.4)
    rs = ROOT_SHOOT.get(species, 0.24)
    biomass = volume_m3_ha * d * bef
    total_biomass = biomass * (1 + rs)
    carbon = total_biomass * CARBON_FRACTION
    co2 = carbon * CO2_C_RATIO
    return round(co2, 1)  # tCO₂e/ha
```

---

## 16. PUIDUHINNAD (Erametsaliit)

Allikas: `https://erametsaliit.ee/puidu-hinnainfo/`

Q1 2026 hinnad (ligikaudsed):
- Männipalk: ~104 €/m³
- Kuusepalk: ~110 €/m³
- Kasepalk: ~95 €/m³
- Paberipuit: ~53 €/m³
- Küttepuit: ~41 €/tm
- Varumiskulu: 16-20 €/m³
- Transport: 8-9.5 €/m³

---

## 17. TOETUSED (loogika põhjal)

| Toetus | Summa | Tingimus (Metsaregisterist) |
|--------|-------|-----------------------------|
| Natura 2000 mets | 60-160 €/ha | EELIS:toetus_mets kattuvus |
| Kliimakindla mets | 356 €/ha | 11 ≤ keskm_vanus ≤ 30 |
| Kooreürask | 500 €/ühik | peapuuliik_kood='KU' AND keskm_vanus>30 |
| Metsastamine | 1420 €/ha | mets=0 AND siht1≠ELAMUMAA |
| Vääriselupaik | 20a leping | EELIS:kr_looduslik_skv kattuvus |

---

## 18. AI INTEGRATSIOON (OpenRouter)

API: `https://openrouter.ai/api/v1/chat/completions`
Model: `openrouter/owl-alpha` (Hermes configis)

### Kasutuskohad:
1. **Kitsenduste tõlgendus** — toores andmed → inimkeelne selgitus
2. **Metsa soovitused** — vanus, liik, boniteet → hooldussoovitused
3. **Müügianalüüs** — hinnatrendid + metsaandmed → müügisoovitus
4. **EUDR tõend** — geopolygon → täidetud deklaratsioon
5. **Süsiniku potentsiaal** — metsaandmed → sobivushinnang

---

## 19. TEHNILINE ARHITEKTUUR

```
Sisend: katastri number (nt "78404:409:0113")
    │
    ├─→ kataster:ky_kehtiv (WFS)     → pindala, mets, siht1, maks_hind, geom
    ├─→ metsaregister:eraldis (WFS)  → puuliik, vanus, tagavara, boniteet
    ├─→ metsaregister:eraldis_element→ puuliikide täpne koosseis
    ├─→ hindamine API (POST)         → validValue, unitValue
    ├─→ kolvikud API (GET)           → metsamaa pindala
    └─→ eelis:toetus_mets (WFS)      → toetusõiguslikkus
         │
         ▼
    Python kalkulaator
    ├─→ Puidu väärtus = tagavara × pindala × hind - kulud
    ├─→ Süsinik = tagavara × wood_density × BEF × (1+rs) × 0.47 × 3.67
    ├─→ Toetused = loogika kitsenduste põhjal
    └─→ Raievanus = keskm_vanus vs keskm_raievanus
         │
         ▼
    OpenRouter AI
    ├─→ Kitsenduste tõlgendus (eelis andmed)
    ├─→ Metsa soovitused (eraldis andmed)
    └─→ Müügianalüüs (hinnatrendid)
         │
         ▼
    Metsa Pass (HTML/CSS/JS)
```
