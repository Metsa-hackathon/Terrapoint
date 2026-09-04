# Ulatus, vastutuspiir ja sisupoole otsused

## Prototüübi tööeeldus

Kuni KAUR otsustab teisiti, on sihtrühm Keskkonnaportaali eestikeelne
tavakasutaja, kes soovib mõista riiklikku metsastatistikat. Vastus alustab
lühiselgitusest, nimetab kasutatud mõõdiku definitsiooni, aasta ja ühiku,
eristab hinnangut registrikirjest ning avab metoodika ja piirangud.

See on tehniline tööeeldus, mitte KAURi heakskiit.

## Toetatud ulatus

- lähteülesande 18 FAQ-d ja 12 väärarusaama;
- SMI, Metsaregistri ja RMK eesmärgi, katvuse ning ajaseisu erinevus;
- metsamaa, tagavara, juurdekasvu, raiemahu, vanuse, puuliikide ja lageraie
  avaldatud riiklikud näitajad;
- valikuuring, suhteline viga, definitsioon, nimetaja ja metoodiline piirang;
- fakti ja väärtushinnangu eristamine;
- ametliku allika, Metsaportaali või Terrapointi kinnistuotsingu leidmine;
- piirkonna, perioodi või näitaja täpsustamine, kui vastamiseks puudub mõõde.

## Teadlikult väljaspool ulatust

- individuaalne raie-, investeerimis-, maksu-, õigus- või toetuse otsus;
- raiet lubav või keelav haldusotsus ja kaitse-eeskirja lõplik tõlgendus;
- konkreetse kinnistu SMI-põhine arvuline hinnang; katastritunnus suunatakse
  registripäringusse;
- I ja II kaitsekategooria liigiandmete või muu autentimist/piirangut nõudva
  info avaldamine massiteabekanalis;
- isiku-, omaniku-, kontakt- või autentimisandmete kogumine;
- metsahinna, tulevase raiemahu, kliima või poliitika prognoos;
- avatud veebi põhjal vastamine, loominguline sisu ja muu valdkond;
- väide, et prototüübi vastus on KAURi seisukoht.

[Keskkonnaameti liigiandmete juhis](https://keskkonnaamet.ee/keskkonnateadlikkus-avalikustamised/inventuurid-ja-ekspertiisid/kaitsealuste-liikide-elupaigad)
kirjeldab piiratud liigiinfo ligipääsu. Õigusküsimuse lõplik allikas on
[Riigi Teataja konsolideeritud Metsaseadus](https://www.riigiteataja.ee/akt/MS)
ja konkreetne menetlus Keskkonnaametis.

## Vastuse stoppreeglid

Süsteem ei koosta faktivastust, kui:

- retrieval'i parim vaste jääb tõendilävendist allapoole;
- viide puudub registrist või URL ei kuulu HTTPS allowlist'i;
- arvul puudub definitsioon, aasta, ühik või allika locator;
- allikad kirjeldavad eri perioodi/üldkogumit ning erinevust ei saa selgitada;
- küsitakse piiratud, isiklikku või kinnistupõhist infot;
- generaator lisab viite, mida retrieval-kontekstis ei olnud.

Sel juhul küsitakse näitajat, geograafiat, perioodi või allikat; vajadusel
suunatakse ametlikku teenusesse. „Ma ei leidnud piisavat tõendit” on korrektne
prototüübitulemus.

## Fakt ja väärtushinnang

Faktiosa võib kirjeldada mõõdetud/hinnatud raiepindala, õiguslikku režiimi või
allikas avaldatud mõjuindikaatorit. „Hea”, „halb”, „jätkusuutlik” ja
„keskkonnavastane” vajavad hindamiskriteeriumi. UI märgib väite liigi ega
teisenda õiguslikku lubatavust automaatselt keskkonnahinnanguks.

## Sisuhaldusrollid

| Roll | Vastutus | Prototüübis |
|---|---|---|
| KAURi sisuomanik | ulatus, faktid, kuldmärgendid, avaldamisotsus | määramata |
| Allika omanik | allika ajakohasus ja definitsioon | määramata |
| Tehniline omanik | deploy, indeks, monitooring, rollback | Terrapoint kuni üleandmiseni |
| Andmekaitse/turve | logimine, säilitamine, intsident | vajab KAURi otsust |
| Piloodi tooteomanik | mõõdikud, tagasiside, jätkuotsus | määramata |

## Avaldamise eeltingimus

`decision-log-template.md` peab sisaldama nimelisi omanikke, kuupäevi ja
heakskiite. Puuduv otsus ei muutu vaikimisi tehniliseks valikuks.
