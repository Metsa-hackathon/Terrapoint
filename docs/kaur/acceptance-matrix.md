# KAURi metsaandmete tõlgendaja vastuvõtumaatriks

See maatriks tõlgendab 2026. aasta Terrapointi praktikakontseptsiooni
kontrollitavateks prototüübinõueteks. Tehniline audit tehti 16.08.2026.
`Tõendatud prototüübis` ei tähenda KAURi sisulist heakskiitu ega piloodi
avaldamisotsust.

## Stoppreegel

Tehniline pakett on üleandmiseks kontrollitud, kuid avalik piloot ei ole valmis
enne, kui KAURi otsust nõudvad read on nimeliselt heaks kiidetud. Puuduvat
sisupoole otsust ei tohi tehnilise eeldusega lõpetatuks märkida.

| ID | Lähteülesande nõue | Vastuvõtukriteerium | Autoriteetne tõend | Olek |
|---|---|---|---|---|
| KAUR-01 | Terrapoint on kolm kuud Keskkonnaportaali metsa alalehel embeditav. | Olemas on isoleeritud, responsiivne iframe-widget, kopeeritav paigaldusnäide, lubatud hostide seadistus, CSP/CORS-juhis ja eemaldamisplaan. | `static/embed/`, embed-endpointide integratsioonitestid, `docs/kaur/embed-guide.md`, `docs/kaur/pilot-plan.md` | **tõendatud prototüübis** |
| KAUR-02 | Prototüüp kasutab KAURi metsandusandmeid. | Teadmusbaasi iga kirje viitab lubatud ametlikule allikale, omab allika identiteeti, ajaseisu, teemat ja sisu kontrolli olekut. | `knowledge/forestry/`, skeemi- ja provenance-testid, `docs/kaur/source-register.md` | **tõendatud prototüübis; KAURi sisukinnitus ootel** |
| KAUR-03 | Fookus, sihtrühm, küsimusetüübid, allikad, detailsus ja keelatud teemad lepitakse sisupoolega kokku. | Prototüübi eeldatud ulatus on dokumenteeritud; avatud valikud on eraldi otsuselogi mallis ning neid ei esitata KAURi heakskiiduna. | `docs/kaur/scope-and-guardrails.md`, `decision-log-template.md` | **artefakt valmis; väline KAURi otsus ootel** |
| KAUR-04 | Loomuliku keele päringud annavad vastuse koos allikaviidetega. | API aktsepteerib eestikeelset küsimust; vastus sisaldab vähemalt üht retrieval-tulemusega seotud allikakirjet või ütleb ausalt, et tõendit ei leitud. | API leping, retrieval-/API-testid, brauseri küsimus → vastus → viide funktsionaaltest | **tõendatud prototüübis** |
| KAUR-05 | FAQ-de ja väärarusaamade teadmusbaas. | Kõik lähteülesande 12 väärarusaama ja 18 FAQ-teemat on eraldi kaetud või märgitud sisulisele kinnitamisele; duplikaadid on jälgitavad. | Teadmuskirjete manifest ja katvustest | **30/30 tehniliselt kaetud; KAURi sisukinnitus ootel** |
| KAUR-06 | Mõistete, metoodika ja piirangute selgitamine. | Vastuse leping eristab põhivastuse, metoodika, ebakindluse/piirangu ja allikad; arvul ei tohi puududa aasta, ühik ega allika ajaseis. | Vastuseskeem, kvaliteedireeglite testid, näidispäringud | **tõendatud prototüübis** |
| KAUR-07 | Faktid eristatakse väärtushinnangutest. | Süsteem ei vasta tõendita normatiivsele väitele faktina; vaieldava küsimuse korral märgib vastus väite liigi ja kirjeldab allika mõõdetavat osa. | Guardrail-testid ja `scope-and-guardrails.md` | **tõendatud prototüübis** |
| KAUR-08 | Piirkondade, perioodide ja näitajate võrdlus. | Päringuplaan tuvastab vähemalt näitaja, geograafia ja perioodi; puuduva mõõtme korral pakub täpsustavat küsimust. Prototüübi toetatud võrdluste piir on dokumenteeritud. | Query-planner-testid, API `query_plan`/`clarification`, ulatusdokument | **tõendatud dokumenteeritud prototüübipiiris; live-vallavõrdlus ei ole toetatud** |
| KAUR-09 | Otsing on praegusest parem. | Fikseeritud, allikastatud eestikeelsel hindamiskogumil ületab hübriidotsing leksikaalset baasjoont eelnevalt määratud lävendiga Recall@3-s ja nDCG@3-s; extractive-vastus peab täpselt kattuma valitud allikaväljadega; regressioon blokeerib üleandmise. | `evaluation/`, `relevance-rubric.md`, korratav hindamiskäsk ja tulemuste JSON/Markdown | **v2 värav ja 30/30 extractive-faithfulness läbitud; KAURi kuldmärgendid ootel** |
| KAUR-10 | Arhitektuur, andmeallikad, mudelijuhised ja konfiguratsioon dokumenteeritakse. | Dokumentatsioon kirjeldab ingestiooni, versioonimist, hübriidretrieval'it, rerankimist, vastuse moodustamist, viidete kontrolli, turvapiire, observability't ja taastamist. | `docs/kaur/search-architecture.md`, allikaregister, mudelikaart, konfiguratsioon | **tõendatud** |
| KAUR-11 | Keelemudel peab olema asendatav. | Retrieval ja vastuse moodustamine töötavad providerist sõltumatu liidese kaudu; ilma mudelivõtmeta on auditeeritav extractive fallback; võti ei jõua brauserisse. | `forestry_generator.py`, adapteri-/viitetestid, mudelikaart | **tõendatud prototüübis** |
| KAUR-12 | Lähtekood, dokumentatsioon ja teadmised antakse KAURile üle. | Uus paigaldus puhtas keskkonnas, indeksi ehitus, testid ja smoke-test on ühe juhendi järgi korratavad; litsentsi- ja allikapiirangud on kirjas. | `docs/kaur/README.md`, `handover.md`, validaator ja testid | **pakett valmis; KAURi enda clean-run ootel** |
| KAUR-13 | Kontrollitud piloot kogub tagasisidet ja toetab jätkuotsust. | Kolme kuu plaan määrab etapid, omanikud, mõõdikud, sündmuste minimaalse andmestiku, privaatsuspiirid, katkestuskriteeriumid ning teenuse eemaldamise. | `pilot-plan.md`, `telemetry.schema.json`, privaatsustest | **plaan/skeem tõendatud; piloot pole alanud** |
| KAUR-14 | Edukust hinnatakse sisulise kasu, teostatavuse ja hallatavuse järgi. | Lõppraport seob retrieval-kvaliteedi, vastuse tõendatuse, UX-i, jõudluse, kulud, hoolduskoormuse ja kasutajate tagasiside otsustusväravatega. | `decision-scorecard.md`, tehniline audit | **raamistik valmis; kasutajapiloodi väljad mõõtmata** |
| KAUR-15 | Konkreetse kinnistu andmed suunatakse õigesse teenusesse. | Üldine tõlgendaja ei leiuta kinnistuandmeid; tuvastatud katastri-/kinnistupäring suunab Metsaportaali/Terrapointi kinnistuotsingusse ja selgitab andmeallika erinevust. | Intent-testid ja widget'i suunamisvoog | **tõendatud prototüübis** |
| KAUR-16 | Ligipääsetav ja privaatsust hoidev avalik teenus. | Klaviatuuri-, fookuse-, accessibility-tree- ja responsiivne põhivoog on kontrollitud; semantika/kontrast läbivad lokaalse värava; logidesse ei saadeta küsimuse teksti vaikimisi ning analüütika nõuab teadlikku konfiguratsiooni. | testid, `accessibility-qa.md`, `accessibility_results.md`, `browser-qa.md`, sündmuseskeem, turvadokument | **kohalik põhivoog ja kontrast tõendatud; sõltumatu WCAG/nimetatud ekraanilugeja/DPIA ootel** |

## Esialgne kvaliteedilävend

Hindamiskogum jagatakse enne lõplikku mõõtmist arendus- ja lukustatud
kontrollosaks. Esialgne värav on:

- hübriidotsingu Recall@3 vähemalt `0,90` ja vähemalt `+0,15` absoluutne
  paranemine leksikaalse baasjoone suhtes;
- hübriidotsingu nDCG@3 vähemalt `0,80` ja mitte ühegi kaitsekriitilise
  päringuklassi Recall@3 langust;
- 100% kuvatud viidetest peab vastama retrieval-kontekstis olnud dokumendi
  identifikaatorile ja lubatud HTTPS-allikale;
- 100% extractive-vastuse tekstidest ja piirangutest peab kattuma valitud
  sisutoimetatud teadmuskirjaga;
- teadmata või ulatusest väljas päringu korral peab süsteem keelduma
  arvulisest faktiväitest ning pakkuma täpsustamist või ametlikku sihtlinki.

Lävend kinnitatakse või muudetakse koos KAURi sisupoolega enne piloodi
hindamiskogumi lukustamist. Muudatus peab jääma otsuselogisse; seda ei tohi
teha pärast tulemuste nägemist ilma põhjenduseta.

## Mõõdetud tulemus

V1 kontrollmõõtmine jäi ausalt väravast välja (Recall@3 `0,8667`, paranemine
`+0,10`) ja on säilitatud `evaluation/history/v1-results.md` failis. V1 muudeti
v2 arendusmaterjaliks ning uus v2 kontrollosa külmutati enne esimest jooksu.
V2 esimene kontrolljooks läbis värava:

- leksikaalne baasjoon Recall@3 `0,7667`, nDCG@3 `0,6762`;
- hübriid Recall@3 `1,0000`, nDCG@3 `0,9139`;
- Recall@3 absoluutne paranemine `+0,2333`;
- viite-, abstention-/redirect- ja kriitilise regressiooni kontrollid 100%.
- extractive-vastuse allikaväljade faithfulness 30/30 ehk `1,0000`;
- rakenduse ohutuskogumi v1/v2 läbikukkumised on arhiveeritud; uute
  sõnastustega v3 läbis esimesel jooksutamisel 20/20 ja kõik juhtumid on
  kaetud 12 kontrollala katvusmaatriksiga;
- lokaalne ligipääsetavuse audit läbis 13 struktuuri- ja 18 kontrastikontrolli;
  klaviatuuri ning accessibility-tree Chromiumi smoke läbis.

Tegu on prototüübi kogumiga; KAUR peab enne avalikku pilooti kinnitama uue
sisulise kuldandmestiku ja lävendid.
