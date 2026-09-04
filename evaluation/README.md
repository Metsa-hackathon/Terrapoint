# Metsandusotsingu hindamine

## Versioonireegel

Lukustatud päringut ega kuldmärgendit ei muudeta pärast tulemuse vaatamist.
Kui kontrollosa paljastab vea või soovitakse retrieval'it häälestada, muutub
eelmine kogu arendusmaterjaliks ja järgmine kontrollosa saab uue versiooni.

- v1 esimene kontroll ebaõnnestus; tulemus on `history/v1-results.md` ja v1
  JSON on säilitatud `forestry_queries.json` failis;
- v2 kasutab v1 vastatavaid päringuid arendusmaterjalina ja täiesti uut
  kontrollosa failis `forestry_queries_v2.json`;
- v2 kontrollosa käivitati pärast v2 mootori ja päringute külmutamist ning
  läbis esimese jooksu;
- v2 andmestiku SHA-256 on
  `6408f0b29aabbcecb153bd75fe39001e4c32793ae5a59d71a30b5a006be76d79`.

`results.json` sisaldab sama hash'i ja kõigi päringute top-3 detaile. Korratav
käsk:

```bash
python3 scripts/evaluate_forestry_search.py --write --enforce
```

Binaarse `relevant_document_ids` otsuse definitsioon, negatiivsed piirijuhud,
prototüübi märgenduse provenance ja KAURi kahe hindajaga kordusprotokoll on
`relevance-rubric.md` failis. Relevantne tähendab, et teadmuskirje katab
küsimuse peamise intent'i ja annab ametliku tõendi vähemalt ühe sisulise
vastuselõigu jaoks; pelk märksõnakattuvus ei piisa.

See on executor'i prototüübikogum, mitte sõltumatult kinnitatud KAURi
kuldandmestik. Enne avalikku pilooti kopeerib KAUR küsimused oma kontrollitud
protsessi, kinnitab märgendid, arvutab hash'i ning kordab jooksu ilma v2
retrieval'i muutmata.

## Päris portaali hetktõmmis

`live_portal_snapshot_2026-08-16.json` säilitab 18 lähteküsimuse avaliku
otsingu tulemusarvud (SHA-256
`c092f9be36bcecc50231aa1b2aa9d5cb8dd61e6a817fdffb6ca405480c879349`).
See pole relevance-hinnang: nullist suurem tulemus võib olla ebaoluline.

```bash
python3 scripts/compare_live_portal_snapshot.py --write
```

Hetktõmmises oli vaikimisi null tulemust 11/18 ja kõigi aegade vaates 9/18;
prototüübi märgendatud tõend oli top-3-s 18/18. `live_portal_comparison.md`
hoiab küsimusepõhist tulemust ja piirangut.

## Mõõdikud ja värav

- Recall@3 ≥ 0,90;
- Recall@3 absoluutne paranemine range leksikaalse baasjoone suhtes ≥ 0,15;
- nDCG@3 ≥ 0,80;
- 0 kaitse-/õiguskriitilist regressiooni;
- citation integrity, redirect ja abstention kontrollides 100%;
- extractive-vastuse allikaväljade faithfulness 100%: kuvatud summary,
  metoodika, piirangud ja citation ID-d kattuvad valitud teadmuskirjega;
- kõik FAQ-01…18 ja MIS-01…12 kontrollosas.

Lävend on koodis ja `acceptance-matrix.md` failis. Selle muutus nõuab uut
andmestiku-/tulemuse versiooni ja kirjalikku põhjendust.

## Ohutuskäitumise kontroll

Ka ohutuskogum on versioonitud, mitte tagantjärele roheliseks muudetud:

- safety v1: 15/16, kasutaja metadata-URL sai eksliku teemavaste;
- safety v2: 15/18, valdkonnavärav oli liiga nõrk;
- safety v3: esimesel jooksutamisel **20/20**, SHA-256
  `47c71a520221f3988c4facf9006c662ee08f817adc0621147f726e1c5cae85d7`.

V1/v2 tulemused on `history/` kaustas. V3 katab valdkonnavälise, meditsiini-,
finants-, personaalse otsuse, piiratud liigi-/isikuinfo, prompt-injection'i,
SSRF-protokolli, markdown-URL-i, XSS-i ja secret-exfiltration'i ning kaht
positiivset valdkonnakontrolli, turvalist täpsustust ja suunamist.

`forestry_safety_coverage.json` seob kõik 20 juhtumit ühega 12 nõutud
kontrollalast ning põhjendab valimit. Evaluaator nõuab, et kõik v3 ID-d ja tag'id
oleksid maatriksis täpselt kaetud; maatriksi hash lisatakse tulemusfaili.

```bash
python3 scripts/evaluate_forestry_safety.py --write
```

See on deterministlik rakenduskäitumise regressioonitõend, mitte pentest.

## Ligipääsetavuse lokaalne värav

```bash
python3 scripts/audit_forestry_accessibility.py --write
```

`accessibility_results.json` / `.md` kontrollib semantilist DOM-lepingut,
fookuse CSS-i, live-region'e, heading-järjestust, liikuvuseelistust ning 18
kontrastipaari. Klaviatuuri ja accessibility-tree päris brauseri smoke on
`docs/kaur/accessibility-qa.md` failis. Kumbki ei asenda sõltumatut WCAG
auditit ega nimetatud ekraanilugeja testi KAURi staging'us.
