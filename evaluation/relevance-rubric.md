# Relevantsushinnangu rubriik

## Eesmärk ja piir

Rubriik kirjeldab, kuidas prototüübi binaarne väli `relevant_document_ids`
loodi. See on executor'i sisemine märgendusjuhis, mitte KAURi sõltumatu
kuldstandard. KAURi sisuomanik peab enne pilooti märgenduse pimekorras kordama
ja lahkarvamused lahendama; prototüübi retrieval-tulemust ei kasutata
kuldmärgendi allikana.

Hindamisühik on üks **küsimus–teadmuskirje paar**. Märgend on binaarne:

- `relevant = 1`: teadmuskirje põhivastus või metoodika käsitleb küsimuse
  peamist info- või tõlgendusvajadust otseselt ning selle viidatud ametlik
  tõend võimaldab koostada vähemalt ühe sisulise vastuselõigu ilma välise
  teadmiseta;
- `relevant = 0`: kirje ainult jagab märksõna, käsitleb teist näitajat,
  geograafiat, perioodi või definitsiooni, või ei anna küsimusele vastamiseks
  vajalikku ametlikku tõendit.

`Relevant` ei tähenda, et dokument üksi annab lõpliku haldusotsuse, personaalse
nõu või kõik võimalikud vaatenurgad. Täpsustamist nõudev kirje võib olla
relevantne, kui see selgitab puuduvat mõõdet ja põhjendab, miks arvulist vastust
ei tohi veel anda.

## Märgendamisjuhis

1. Normaliseeri küsimus ainult lugemiseks; ära vaata otsingumootori järjestust.
2. Kirjuta välja peamine intent ning nõutud näitaja, geograafia, periood,
   definitsioon ja küsimuse liik (fakt, metoodika, õigus, väärtushinnang või
   teenusesse suunamine).
3. Loe kandidaatkirje `summary`, `methodology`, `limitations` ja allikate
   locator'eid. Vajaduse korral ava ametlik algallikas.
4. Anna `1` ainult siis, kui kirje vastab peamisele intent'ile ning ükski
   kriitiline mõõde ei ole vastuolus. Märksõnakattuvus üksi ei piisa.
5. Anna `0`, kui vaste on sama teema teine mõõde (näiteks lageraie pindala vs
   kogu raiemaht), sama sõna teine ulatus (riik vs vald) või ajaliselt/
   õiguslikult sobimatu tõend.
6. Mitme sõltumatu intent'i korral võib olla mitu relevantset kirjet. V2
   lukustatud prototüübiküsimused kavandati ühe peamise intent'iga ja neil on
   seetõttu üks positiivne kirje; see ei ole mootori piirang.
7. Suunamis- ja keeldumisjuhtumeid ei hinnata retrieval-relevantsusena. Neil on
   eraldi `expected_status` ning vajaduse korral `expected_document_id`.

## Piirijuhtumite näited

| Küsimuse vajadus | Relevantne | Mitterelevantne põhjus |
|---|---|---|
| riigi metsamaa hektarid ja metsasus | `forest-area` | `municipality-forest-area` vajab KOV-i ja teist andmekihti |
| juurdekasvu ja toimunud raie võrdlus | `harvest-versus-increment` | `harvest-over-time` ei lahenda juurdekasvu võrdlust |
| lageraie pindala aegrida | `clearcut-over-time` | kogu raiemahu aegrida on teine näitaja |
| konkreetse kinnistu puistuandmed | `property-forest-data` | SMI riiklik hinnang ei kirjelda kinnistut |
| miks hinnangud erinevad | `why-numbers-differ` | ühe näitaja arvuline kirje ei selgita definitsiooni/metoodika erinevust |

## Prototüübi provenance ja külmutamine

- 18 FAQ-d ja 12 väärarusaama seoti teadmuskirjetega enne vastava lukustatud
  päringu esimest jooksu; päringud on nende intent'ide uued sõnastused.
- V1 läbikukkumine säilitati ja selle küsimused muutusid v2 arendusmaterjaliks.
- V2 JSON-i SHA-256 ja tulemuste detailid on `results.json` failis; v2 märgendit
  ega retrieval-parameetrit ei muudeta tulemuse parandamiseks.
- Autor ja esimene hindaja on sama prototüübi executor; pime teine hindaja,
  hindajatevaheline kooskõla ja KAURi adjudikatsioon puuduvad. Seetõttu on
  `18/18` portaali võrdlus ja v2 meetrikad sisemine tehniline tõend, mitte
  sõltumatu sisuline kvaliteediväide.

## KAURi kordusmärgenduse protokoll

1. Kopeeri küsimused uude versiooni ja eemalda mootoritulemused hindaja vaatest.
2. Kasuta vähemalt kaht metsaandmete sisuvaldajat; igaüks märgendab iseseisvalt
   selle rubriigi järgi kõik küsimus–kandidaat paarid.
3. Salvesta annotaatori pseudonüüm, kuupäev, rubriigi versioon, otsus ja lühike
   põhjendus; ära salvesta isikuandmeid päringuteksti.
4. Raporteeri protsentuaalne kokkulangevus ja Cohen'i kappa; lahenda erimeelsus
   kolmanda nimetatud adjudikaatoriga.
5. Külmuta uus JSON ja rubriik hash'iga enne KAURi clean-run'i. Kui kuldmärgend
   muutub pärast tulemuse nägemist, loo uus versioon ning säilita eelmine.
