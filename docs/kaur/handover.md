# Tehniline üleandmisjuhend

## 1. Eeldused

- Python 3.12;
- Git;
- tootmises HTTPS reverse proxy;
- testimiseks Node.js ainult JavaScripti süntaksikontrolli ja Playwrighti jaoks;
- ükski mudelivõti pole extractive prototüübi käivitamiseks vajalik.

## 2. Puhas paigaldus

```bash
git clone <KAURi-repo-URL> terrapoint
cd terrapoint
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python scripts/validate_forestry_knowledge.py
python scripts/evaluate_forestry_search.py --write --enforce
python scripts/evaluate_forestry_safety.py --write
python scripts/compare_live_portal_snapshot.py --write
python -m pytest -q
python -m uvicorn api.index:app --host 127.0.0.1 --port 8099
```

Kontrolli:

```bash
curl -fsS http://127.0.0.1:8099/api/forest-search/meta
curl -fsS -H 'Content-Type: application/json' \
  -d '{"question":"Mis vahe on SMI-l ja metsaregistril?"}' \
  http://127.0.0.1:8099/api/forest-search
```

Brauseri integratsiooninäide on
`http://127.0.0.1:8099/embed/forest/demo`.

## 3. Koodi ja andmete kaart

Praeguse üleantava prototüübi ulatus on **retrieval + tõendipõhine vastuse
moodustamine**. `extractive-v1` väljastab valitud sisutoimetatud teadmuskirje
väljad muutmata kujul; runtime-keelemudel ja vaba parafraseerimine ei ole selle
versiooni ulatuses. Seetõttu tähendab praegune answer-faithfulness valitud
kirje tekstiväljade ning viidete täpset vastavust. Uus generatiivne adapter
laiendab ulatust ja vajab enne kasutust eraldi claim-level faithfulness'i,
arvulise grounding'u ning inimhindamise väravat.

| Tee | Vastutus |
|---|---|
| `services/forestry_search.py` | valideeritud korpus, analüüs, hübriidretrieval, RRF ja vastuse orkestreerimine |
| `services/forestry_generator.py` | provider-neutraalne generaator ja väljundi viitevärav |
| `knowledge/forestry/sources.json` | URL-i/provenance'i allowlist |
| `knowledge/forestry/documents.json` | sisutoimetatud vastused, meetod, piirangud ja katvus |
| `knowledge/forestry/telemetry.schema.json` | vaikimisi väljas oleva privaatsust hoidva analüütika leping |
| `evaluation/forestry_queries_v2.json` | praegune külmutatud prototüübi kontrollkogum |
| `evaluation/relevance-rubric.md` | binaarse relevantsusmärgendi definitsioon ja KAURi kordusmärgendus |
| `evaluation/forestry_safety_coverage.json` | v3 ohutustestide kontrollalade masinloetav katvus |
| `evaluation/results.json` / `results.md` | korratav v2 tulemus |
| `evaluation/accessibility_results.json` / `.md` | lokaalne semantika- ja kontrastivärav |
| `static/embed/` | isoleeritud widget, loader ja demo |
| `api/index.py` | endpointid, body/rate piirid ja route'i CSP |
| `config.py` | parent-originide, CORS-i ja trusted hostide validatsioon |
| `vercel.json` | edge-päiste täpne iframe-erand |
| `docs/kaur/` | uuring, arhitektuur, ulatus, piloot ja otsus |

JSON-korpus kompileeritakse protsessi käivitamisel valideeritud mäluregistriks;
eraldi binaarset indeksifaili prototüübis pole. Tootmise Lucene/Qdrant/
OpenSearch indeks on sihtarhitektuuri valik pärast KAURi infrastruktuuriotsust.

## 4. Teadmusvastuse muutmine

1. Ava autoriteetne allikas ja kontrolli ajaseisu, tabelipäist, definitsiooni,
   ühikut, perioodi ning veahinnangut.
2. Lisa/muuda allikas `sources.json` failis. Avalikku indeksisse ei lisata
   autentimist nõudvat kirjet.
3. Muuda `documents.json` vastust, meetodit, piiranguid, locator'it ja
   aliasküsimusi. Ära kopeeri uut arvu ilma kogu arvulise komplektita.
4. Lase KAURi sisuomanikul diff kinnitada.
5. Käivita validaator, testid ja eval. Kui uus küsimus muudab ulatust, tee uus
   eval-andmestiku versioon; vana lukustatud kogumit ei häälestata ümber.
6. Uuenda otsuselogi hash'id ja avalda uus deploy.

## 5. Uue generaatori lisamine

1. Rakenda `ForestryAnswerGenerator` adapter eraldi failis.
2. Anna mudelile ainult heakskiidetud dokument ja `allowed_source_ids`; URL-id
   liidetakse pärast mudelit registrist.
3. Käivita väljund läbi `validate_generated_answer` kontrolli.
4. Lisa timeout, maksimaalne tokeni-/kulupiir ja eksplitsiitne provider'i
   seadistus. Tundmatu või maas provider ei tohi vaikselt asenduda.
5. Lisa viite-, arvu-, prompt-injection-, abstention- ja provider outage testid.
6. Võrdle KAURi uuel lukustatud kogumil; hoia `extractive` rollback alles.

## 6. Deploy

Minimaalne keskkond:

```text
EMBED_FRAME_ANCESTORS=https://keskkonnaportaal.ee,https://www.keskkonnaportaal.ee
FORESTRY_GENERATOR_PROVIDER=extractive
TRUSTED_HOSTS=<KAURi host>,localhost,127.0.0.1
CORS_ORIGINS=<Terrapointi/KAURi top-level UI originid>
```

Kui host või Keskkonnaportaali origin muutub, uuenda nii serveri muutujat kui
ka `vercel.json` täpset embed-CSP-d. Deploy järel kontrolli mõlema route'i
päiseid `embed-guide.md` järgi. Reverse proxy ei tohi `/embed/forest` vastusele
uuesti globaalset `X-Frame-Options: DENY` lisada.

## 7. Monitooring ja logid

- endpoint ei logi rakenduse tasemel küsimuse teksti;
- logi status, latentsus, indeks/generaatori versioon ja veakood;
- hoia ligipääsu-/turvalogid analüütikast eraldi;
- häire: 5xx, p95 latentsus, 429 osakaal, allikakontrolli aegumine ja
  teadmuskorpuse hash'i ootamatu muutus;
- tekstiline tagasiside vajab eraldi õiguslikku alust ja redaktsiooni.

## 8. Rollback ja taastamine

1. Kriitilise vea korral eemalda iframe Keskkonnaportaali CMS-ist.
2. Taasta viimane roheline Git commit/deploy ja extractive provider.
3. Kontrolli `meta`, eval, testid ning `/embed/forest` ja `/` päised.
4. Ära muuda läbikukkunud eval-tulemust; arhiveeri see `evaluation/history/`
   alla ja tee paranduse jaoks uus versioon.
5. Dokumenteeri mõju, küsimuseklass, allikad, aeg, omanik ja järeltegevus.

## 9. Üleandmise kontrollnimekiri

- [ ] repo ja deploy-õigus on KAURil;
- [ ] secret'id on KAURi secret-store'is ning Terrapointi võtmed eemaldatud;
- [ ] sisu-, tehniline-, turbe-, andmekaitse- ja piloodiomnik määratud;
- [ ] kõik 30 teemat ja kuldmärgendid sisuliselt kinnitatud;
- [ ] allikate SLA ja eemaldamisõigus kinnitatud;
- [ ] clean install, test, eval, browser smoke ja rollback KAURi poolt korratud;
- [ ] CSP/proxy päised tootmishostis kontrollitud;
- [ ] privaatsusteade, säilitustähtajad ja kasutajatugi avaldatud;
- [ ] kolm kuud algus/lõpp ning eemaldamise kalendriomanik määratud;
- [ ] jätkuotsus ei ole enne piloodit eeldatud.
