# KAURi metsaandmete otsingu- ja RAG-arhitektuur

## Otsus lühidalt

Piloot kasutab eraldi, versioonitud metsanduse teadmusbaasi ja iframe-widget'it.
Päring läbib intent'i ja ulatuse kontrolli, eestikeelse leksikaalse retrieval'i,
semantilise retrieval'i, RRF-fusiooni, rerankimise ja tõendivärava. Vastuse
moodustaja saab kasutada organisatsiooni heakskiidetud keelemudelit, kuid
retrieval, allikad ja vastuse kontroll ei sõltu ühest mudelipakkujast.

Referentsimplementatsioon selles repos on väike ja deterministlik: BM25-laadne
leksikaalne haru, käändevorme taluv märgi-n-grammi haru, RRF ja struktureeritud
extractive vastus. See tõendab API-, viite-, embed- ja hindamislepingut ilma
mudelivõtmeta. Tootmiskandidaat lisab päris dense-embedding'u ja cross-encoder
reranker'i alles pärast eestikeelset A/B-hindamist.

## Arhitektuuri otsustusmaatriks

Hinne on 1–5 ja kaalutud summa maksimaalselt 5. Need on 16.08.2026
prototüübiuuringu hinnangud; KAURi sisemise otsingubackend'i ja meeskonna
võimekuse selgumisel tuleb operatsioonihinne uuesti kinnitada.

| Variant | Eesti küsimuse leidmine 25% | Allika-/sisukontroll 25% | Piloodi pööratavus 20% | Halduskoormus 15% | Turva-/privaatsuspiir 15% | Summa |
|---|---:|---:|---:|---:|---:|---:|
| ainult Drupal Search API leksikaalne häälestus | 2 | 2 | 5 | 4 | 4 | 3,20 |
| kogu portaali site-wide vector search | 4 | 2 | 2 | 2 | 3 | 2,65 |
| eraldi metsakorpus + hybrid/RRF + iframe | 5 | 5 | 5 | 4 | 5 | **4,85** |
| LLM üldteadmisega, ilma retrieval'ita | 2 | 1 | 4 | 3 | 1 | 2,15 |

Valik ei tähenda, et KAUR peab ostma uue vektoriandmebaasi. Piloodi eraldi
loogiline indeks võib asuda olemasolevas Solr/Elasticsearch/OpenSearchi
klastris, kui see toetab versioonimist ja mõõdetavat hübriidretrieval'it.
Otsuse tuum on eraldi kinnitatud korpus, mõõtmisvärav ja pööratav iframe, mitte
konkreetne tootebränd.

## Süsteemipiir

```text
Keskkonnaportaali metsaleht
  └─ sandboxitud iframe /embed/forest
       └─ POST /api/forest-search
            ├─ päringu normaliseerimine ja intent
            ├─ ulatuse/privaatsuse värav
            ├─ BM25 + EstonianAnalyzer ─┐
            ├─ dense embedding ─────────┼─ RRF ─ reranker
            └─ metadatafiltrid ─────────┘
                         └─ tõendikontekst + viite-ID-d
                              └─ provider-neutraalne vastusemoodustaja
                                   └─ väite/viite/ühiku/aja järelkontroll
                                        └─ struktureeritud API-vastus

Versioonitud ingest
  allowlist → fetch → viirus/markup/instruction scan → parser → semantiline
  chunk → metadata/õigused → sisutoimetaja heakskiit → indeksialias
```

## Miks eraldi indeks

Keskkonnaportaali üldotsing teenindab tuhandeid eri tüüpi objekte. Piloodi
eesmärk on metsaandmete tähenduse selgitamine, mitte kogu portaali asendamine.
Eraldi indeks võimaldab:

- hoida ainult sisupoole kinnitatud metsandusallikaid;
- säilitada tabelipäised, metoodika ja veahinnangud koos arvuga;
- lukustada hindamiskogum ja mõõta regressiooni;
- avaldada või eemaldada widget ühe CMS-muudatusega;
- viia teenus hiljem KAURi infrastruktuuri ilma portaali otsinguandmeid
  ümber migreerimata.

KAUR peab enne tootmistehnoloogia valikut avaldama praeguse Drupal Search API
backend'i ja haldusvõimekuse. Kui olemasolev Solr/Elasticsearch/OpenSearchi
klaster toetab vektoreid, aliastega versioonimist ja jälgitavat hübriidotsingut,
kasutatakse seda. Muidu on eelistatud eraldi Lucene-põhine otsinguteenus;
piloodi korpus on liiga väike, et õigustada keerukat hajusklastrit.

## Andmemudel

Igal allikal on vähemalt:

- stabiilne `source_id`, HTTPS URL, pealkiri, väljaandja ja allikatüüp;
- avaldamise/uuendamise/auditimise aeg ning andmeaasta;
- litsents või kasutusotsus;
- checksum, ingest'i versioon ja parseri versioon;
- avalikkuse tase (`public`, `authenticated`, `restricted`);
- sisuline omanik, ülevaatuse olek ja järgmine ülevaatuse tähtaeg.

Igal retrieval-dokumendil on vähemalt:

- stabiilne `document_id`, keel, teema, küsimuse intent ja sisu tüüp;
- pealkiri, aliasküsimused, vastuse väited, metoodika ja piirangud;
- viidatud `source_id`-d koos lehe/tabeli/sektsiooni locator'iga;
- kehtivusperiood, geograafia, näitaja, ühik ja definitsioon;
- `content_hash` ning sisutoimetaja heakskiidu olek.

Arvuline fakt on indeksis tervikobjekt, mitte paljas lause: `value`, `unit`,
`data_year`, `geography`, `definition`, `estimate_error`, `source_locator`.
Nii ei saa generaator ühikut või veapiiri kontekstist eraldada.

## Retrieval

1. **Normaliseerimine.** Unicode NFKC, väiketähed, kirjavahemärkide kontroll,
   eesti keele stoppsõnad ja terminisõnastik. Algtekst säilib auditis; logidesse
   ei kirjutata seda vaikimisi.
2. **Intent ja mõõtmed.** Tuvastatakse SMI/metoodika, riiklik statistika,
   aegrida, piirkond, kinnistu, õigus või väärtushinnang. Võrdluspäringu puhul
   eraldatakse näitaja, periood ja geograafia; puuduva olulise mõõtme korral
   küsitakse täpsustust.
3. **Ulatuse värav.** Katastritunnus suunatakse Terrapointi kinnistuotsingusse
   või Metsaportaali. Autentimist nõudev liigi- või omanikuteave ei lähe üld-RAG-i.
   Personaalne õigus- või raietegevuse soovitus suunatakse ametlikku menetlusse.
4. **Sparse retrieval.** BM25 väljade kaaludega `aliases > title > headings >
   body`; Lucene'i EstonianAnalyzer ning eraldi keyword-väljad aastatele,
   ühikutele, registrikoodidele ja allikatele.
5. **Dense retrieval.** Esmased kandidaadid on `BAAI/bge-m3` ja
   `intfloat/multilingual-e5-base`. Valik tehakse ainult lukustatud eestikeelse
   eval-kogumi kvaliteedi, latentsuse, mälu, litsentsi ja KAURi deploy-nõuete
   põhjal.
6. **Fusion.** Mõlema haru top-N ühendatakse RRF-iga. Toorskoore ei liideta,
   sest BM25 ja cosine pole samal skaalal. Kaalusid tohib muuta ainult
   arendusjaotusel ja muudatus jääb konfiguratsiooni versiooni.
7. **Reranking.** Top 20 kandidaati järjestab eestikeelsel kogumil valideeritud
   cross-encoder; kandidaat on `BAAI/bge-reranker-v2-m3`. Reranker on
   väljalülitatav, et mõõta kvaliteedi/latentsuse suhet.
8. **Tõendivärav.** Vastus koostatakse ainult heakskiidetud, kehtiva ja
   avaliku taseme dokumentidest. Madal recall, vastuoluline periood või puuduv
   locator annab täpsustuse/keeldumise, mitte mudeli üldteadmise.

## Vastuse moodustamine

Generaator saab ainult nummerdatud evidence-objektid ja range JSON-skeemi:

- `answer_sections[]`: tekst + kasutatud `source_ids`;
- `methodology`: kuidas näitaja saadi;
- `limitations[]`: valimiviga, katvus, ajaseis või definitsioon;
- `clarification`: puuduva mõõtme küsimus;
- `related_questions[]`: ainult indeksi katvuse piires.

Järelkontroll lükkab vastuse tagasi, kui viide ei olnud retrieval-kontekstis,
URL pole registris, arvul puudub ühik/aasta, väärtus ei esine struktureeritud
tõendis või mudel püüab anda kinnistupõhist/õiguslikku otsust. UI eristab
`fakt`, `statistiline hinnang`, `metoodiline selgitus` ja `väärtushinnang`.

Praegune DeepSeek ei ole arhitektuuri osa, vaid üks võimalik adapter.
`generator.generate(evidence, question, schema)` leping võimaldab KAURil mudeli
vahetada. API-võti ja süsteemijuhis jäävad serverisse. Ilma mudelita tagastab
teenus kinnitatud extractive vastuse, mis on piloodi fallback ja auditi alus.

## Turve ja privaatsus

- Ingest on ainult allowlist'itud avalikest allikatest; veebisisu on andmed,
  mitte käsk. HTML, peidetud Unicode ja prompt-injection markerid skannitakse.
- Avaliku ja piiratud sisu indeksid/ACL-id on füüsiliselt või loogiliselt
  eraldatud. Widget kasutab ainult avalikku indeksit.
- Generaatoril pole brauserit, shelli, andmebaasi kirjutusõigust ega muid
  agentseid tööriistu. See vähendab prompt injection'i mõju.
- Väljund renderdatakse tekstina; linkide URL-id tulevad allikaregistrist, mitte
  mudelilt. Küsimuse pikkus, päringusagedus, konteksti- ja väljundimaht on piiratud.
- Vaikimisi telemeetria salvestab päringu juhusliku ID, intent'i, latentsuse,
  kasutatud dokumendi-ID-d, mudeli/indeksi versiooni ja tulemuse oleku, mitte
  küsimuse teksti. Tekstipõhine kvaliteedilogimine vajab eraldi õiguslikku alust
  ja kasutajateavitust.
- OWASP-i
  [RAG Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/RAG_Security_Cheat_Sheet.html)
  ning [Prompt Injection risk](https://genai.owasp.org/llmrisk/llm01-prompt-injection/)
  on threat model'i miinimum; RAG ei lahenda prompt injection'it iseenesest.

## Embed

Piloodi dokument `/embed/forest` saab tavarakendusest erineva CSP:
`frame-ancestors 'self' https://keskkonnaportaal.ee` (ja kinnitatud hostid).
Teised Terrapointi lehed säilitavad `frame-ancestors 'none'` ning
`X-Frame-Options: DENY`. Widget:

- ei vaja kolmanda osapoole JavaScripti ega küpsiseid;
- teeb same-origin API-kõne ja hoiab võtmed serveris;
- kasutab semantilist HTML-i, klaviatuurivoogu, nähtavat fookust,
  `role=status` olekuteateid ja `aria-live` vastust;
- töötab 320 px laiusest alates, austab `prefers-reduced-motion` ja saadab
  parent'ile ainult kõrguse muutuse `postMessage` sündmuse;
- märgib selgelt „prototüüp”, allika ajaseisu ja selle, et vastus ei ole
  haldusotsus.

Ligipääsetavuse siht on WCAG 2.2 AA. W3C nõuab muu hulgas täielikku
[klaviatuurikasutust ja programmiliselt tuvastatavaid olekuteateid](https://www.w3.org/TR/WCAG22/).

## Ingest ja avaldamine

1. Fetch salvestab sisu checksum'i ja HTTP metadata; muutus tekitab uue
   versiooni, mitte vaikse ülekirjutuse.
2. Parser säilitab pealkirjahierarhia, tabeli päise, joonealused märkused ja
   lehekülje/sektsiooni locator'i. Chunk on semantiline üksus, tavaliselt
   300-600 sõna; tabeli fakt võib olla väiksem struktureeritud objekt.
3. Automaatkontroll leiab puuduvad URL-id, kuupäevad, ühikud, duplikaadid,
   lubamatud originid ja potentsiaalsed instruktsioonid.
4. Sisutoimetaja kinnitab uue/oluliselt muutunud dokumendi. Indeks ehitatakse
   uue versioonina; smoke- ja retrieval-eval läbivad enne alias swap'i.
5. Eelmise aliaseni saab ühe sammuga tagasi pöörduda. Kustutatud või aegunud
   allikas eemaldatakse aktiivsest indeksist, kuid auditi manifest säilib.

## Mõõtmine

Retrieval-eval sisaldab vähemalt kõiki 18 FAQ-d, 12 väärarusaama, parafraase,
kirjavigu, käändevorme, aastate/ühikute päringuid, kinnistusuunamisi,
väärtushinnanguid ja teadlikult vastamatuid küsimusi. Kuldmärgendid kinnitab
KAURi sisuomanik. Mõõdikud:

- Recall@3 ja nDCG@3: kas õige evidence jõudis generaatorini ja mis kohal;
- MRR: esimese õige tõendi koht;
- citation precision/coverage: kas iga kuvatud viide on päriselt kasutatud;
- numeric grounding: arv + ühik + aasta + locator;
- abstention precision/recall: kas süsteem keeldub õigel ajal;
- p50/p95 latentsus, veamäär ja allikate värskus;
- kasutajalt „vastas / ei vastanud”, täpsustamise määr ja ametliku lingi avamine.

Värav on kirjeldatud `acceptance-matrix.md` failis. Tulemused esitatakse
baasjoone, hübriidi, reranker'i ja generaatori kaupa; üks üldskoor ei tohi peita
kaitsekriitilise intent'i regressiooni.

## Avatud KAURi otsused

- peamine sihtrühm ja keeleline detailsus;
- millised arvud tohib widget'is otse avaldada ja millised vajavad igakordset
  andmeteenuse päringut;
- allikate sisulised omanikud, ülevaatuse SLA ja eemaldamise õigus;
- olemasolev Search API backend ning lubatud infrastruktuur/mudelid;
- küsimuseteksti logimise õiguslik alus ja säilitustähtaeg;
- haldus-, õigus- ja kinnistuküsimuste täpne vastutuspiir;
- piloodi kvaliteedilävendite ametlik kinnitus.
