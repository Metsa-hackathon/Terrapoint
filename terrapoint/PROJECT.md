# terrapoint — Projekti kontekst

## Ülevaade
Katastri numbri järgi kõik metsa- ja kinnisvaraandmed ühes kohas.
Eesmärk: täielik rakendus (kaart + kihid + otsing).
Väljakutse: "Uus toode või teenus metsanduslike avaandmete peal" — luua praktiline tööriist, mis aitab metsaandmeid päriselt ära kasutada.

## Häkatoni väljakutsed (Eventornado)
1. Andmete väärkasutus ja turvariskid
2. **Uus toode või teenus metsanduslike avaandmete peal** ← Terrapoint
3. Metsainfo visualiseerimine ja populariseerimine
4. Metsanduslik kaugseire
5. Teekond tundmatusse (muu)

## Meeskond
- **Backend:** User (Python)
- **Frontend:** Sõber (HTML/CSS/JS)
- **Repo:** `terrapoint` (ühine GitHub organization)

## Stack
- **Backend:** FastAPI (Python)
- **Frontend:** HTML/CSS/JS (sõber teeb)
- **Andmebaas:** Redis cache + PostgreSQL (Dockeris olemas)
- **Vektorandmebaas:** Qdrant (Dockeris olemas)
- **Deployment:** Coolify (Docker-compose)
- **Keeled:** Eesti keel

## Docker teenused (serveris olemas)
- Redis
- PostgreSQL
- Qdrant

## Funktsioonid (kõik)
1. **Põhiandmed** — puuliik, vanus, kubatuur, boniteet, pindala
2. **Väärtus** — puidu turuhinnang (erametsaliit hinnad)
3. **Kitsendused** — kaitsealad, Natura 2000, veekaitse, muinsuskaitse
4. **EUDR** — GeoJSON export
5. **Süsinik** — IPCC valem, potentsiaalne tulu
6. **Toetused** — 12 programmi, loogika põhjal

## API-d (kõik töötavad ilma autentimiseta)
1. **kataster:ky_kehtiv** — põhiandmed + geomeetria (CQL tunnus)
2. **metsaregister:eraldis** — metsaandmed (CQL katastri_nr)
3. **metsaregister:eraldis_element** — puuliikide koosseis
4. **cadastrepublic.kataster.ee** — geomeetria WKT
5. **hindamine.kataster.ee** — maa hindamine (POST)
6. **kolvikud.kataster.ee** — maakasutuse jaotus
7. **eelis:kr_kaitseala** — kaitsealad (BBOX)
8. **eelis:toetus_mets** — toetusalad (BBOX)
9. **eelis:natura_elupaik** — Natura elupaigad (BBOX)
10. **metsaregister:natura_2000_alad** — Natura 2000 (BBOX)
11. **kitsendused:metsakas_kpois_*** — veekaitse (BBOX)
12. **kitsendused:kotkas_kitsendused** — kotka piirangud (BBOX)
13. **muinsuskaitse:kpo_malestised** — muinsuskaitse (BBOX)
14. **kmanahtused:kma_avalik_looduskaitse_*** — looduskaitse tsoonid (BBOX)
15. **veeveeb:mullad_boniteet** — mulla boniteet (BBOX)
16. **pta:msr_vork** — drenaaživõrk (BBOX)
17. **maaamet:karuputk** — invasiivne liik (BBOX)
18. **keskkonnainfo:clc_2018_iii** — Corine Land Cover (BBOX)
19. **maaoksjon:auction** — riigimaade oksjonid (BBOX)
20. **tiles.maaamet.ee** — kaardiplaadid

## Spatial query strateegia
- CQL INTERSECTS EI tööta
- Kasuta BBOX: CQL → bbox arvutada → BBOX päringud
- Kataster CQL: `tunnus%20%3D%20%27{NR_ENCODED}%27`
- Metsaregister CQL: `katastri_nr='{NR}'`

## Failid
- `/root/projects/terrapoint/API_REFERENCE.md` — 19 sektsiooni, kõik API-d
- `/root/projects/terrapoint/PROJECT.md` — see fail
