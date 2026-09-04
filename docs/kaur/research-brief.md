# Keskkonnaportaali metsaotsingu uuring

Uurimiskuupäev: 16.08.2026. Eesmärk oli leida kolmekuulise piloodi jaoks
väikseim arhitektuur, mis parandab loomulikus eesti keeles metsaandmete
leidmist ja tõlgendamist, ilma et asendaks kohe kogu Keskkonnaportaali otsingu.

## Meetod ja piirangud

Kontroll hõlmas Keskkonnaportaali avaliku otsingu renderdatud kasutusvoogu,
avalikku autocomplete-endpointi, HTTP turvapäiseid, 18 lähteülesande FAQ
otsingut, Agent Reachi Jina Readeri ja Exa otsingut ning primaarsete metsa-,
otsingu-, turva- ja ligipääsetavusallikate võrdlust. Portaali sisemist
otsingumootorit, logisid, analüütikat ega Drupal Search API serveripoolset
konfiguratsiooni ei olnud võimalik avalikust vaatest tõendada. Parameetrinimi
`search_api_fulltext` ja autocomplete'i rada tõendavad Drupal Search API
kasutust, kuid mitte konkreetset indekseerimismootorit.

Tulemuste arv mõõdab ainult leitavust, mitte tulemuse asjakohasust või vastuse
õigsust. Nullist suurem tulemus ei tähenda, et kasutaja küsimusele vastati.

## Praeguse otsingu baasjoon

Renderdatud otsing avanes 6056 tulemusega ning aktiivse filtriga „Viimased 5
aastat”. Küsimus „Kas Eestis raiutakse rohkem kui metsa juurde kasvab?” andis
vaikimisi filtriga null tulemust. Kõigi aastate valimisel ilmus üks tulemus;
märksõnapäring „raiemaht juurdekasv” andis kuus tulemust. Seega oskab praegune
otsing leida sõnu, kuid pikk loomuliku keele küsimus, käändevormid ja vaikimisi
ajafilter vähendavad recall'i.

| # | Lähteülesande küsimus | Viimased 5 a | Kõik aastad |
|---:|---|---:|---:|
| 1 | Kui suur osa Eestist on kaetud metsaga? | 10 | 10 |
| 2 | Kas Eestis raiutakse rohkem kui metsa juurde kasvab? | 0 | 1 |
| 3 | Miks annavad eri allikad erinevaid numbreid? | 0 | 0 |
| 4 | Mis vahe on SMI-l ja metsaregistril? | 0 | 0 |
| 5 | Kuidas arvutatakse juurdekasvu? | 2 | 2 |
| 6 | Miks ei võrdu tagavara raiutava puidukogusega? | 0 | 0 |
| 7 | Kust leida konkreetse kinnistu metsaandmeid? | 0 | 0 |
| 8 | Kui suur osa metsadest on kaitse all? | 11 | 13 |
| 9 | Miks erinevad RMK ja SMI numbrid? | 0 | 0 |
| 10 | Kuidas mõjutab kliimamuutus metsi? | 0 | 0 |
| 11 | Mis on metsateatis? | 11 | 13 |
| 12 | Kas Eestis saab mets otsa? | 5 | 6 |
| 13 | Kas praegu raiutakse rohkem kui 20 aastat tagasi? | 0 | 0 |
| 14 | Kas meie metsad muutuvad nooremaks? | 4 | 4 |
| 15 | Kui palju lageraiet on viimase 10 aasta jooksul tehtud? | 0 | 1 |
| 16 | Kas kuusk või mänd domineerib Eestis? | 0 | 0 |
| 17 | Kas kaitsealadel raiutakse? | 1 | 1 |
| 18 | Kui palju metsa on minu koduvallas? | 0 | 0 |

Vaikimisi päringutest 11/18 ja kõigi aastate päringutest 9/18 ei leidnud
ühtegi tulemust. Need arvud on 16.08.2026 hetktõmmis; sisu ja indeks võivad
hiljem muutuda.

## Mida ametlikud metsaallikad nõuavad otsingult

- [Keskkonnaportaali SMI leht](https://keskkonnaportaal.ee/et/teemad/mets/metsastatistika-sh-smi)
  kirjeldab SMI-d üleriigilise valikuuringuna ja hoiatab, et iga hinnanguga
  kaasneb valikust tulenev statistiline viga. Vastus peab seega kandma
  andmeaastat, ühikut, definitsiooni ja veateavet, mitte ainult üht arvu.
- [SMI 2024 tabelid](https://keskkonnaportaal.ee/sites/default/files/Teemad/Mets/SMI2024/SMI_2024.pdf)
  eristavad näiteks metsasuse nimetajaid ja rahvusvahelist FRA definitsiooni.
  Samas dokumendis on juurdekasv märgitud mudelarvutuseks ning raiemahul on
  eraldi aasta ja suhteline viga. Tabeliridu ei tohi ilma päise, joonealuse
  märkuse ja perioodita eraldiseisvateks „faktideks” lõigata.
- [Metsainfo hetkeseis](https://keskkonnaportaal.ee/et/teemad/mets/metsainfo-hetkeseis)
  eristab jooksvalt uuenevaid RMK ja Metsaregistri andmeid SMI hinnangutest.
  Metsateatis kirjeldab kavatsust; kõiki lubava märkega teatisi ei realiseerita.
- [Metsaregistri andmestike leht](https://keskkonnaportaal.ee/et/avaandmed/metsaregistri-andmestikud)
  dokumenteerib WMS/WFS kihid ja nende CC BY 4.0 litsentsid. Kinnistu vastus
  vajab ruumipäringut, mitte riikliku SMI hinnangu jaotamist väikesele alale.
- [Keskkonnaameti kaitsealuste liikide juhis](https://keskkonnaamet.ee/keskkonnateadlikkus-avalikustamised/inventuurid-ja-ekspertiisid/kaitsealuste-liikide-elupaigad)
  ütleb, et osa liigiinfot näeb ainult autentitud maaomanik ning seda ei tohi
  massiteabekanalis avaldada. Üldine RAG-indeks peab seetõttu sisaldama ainult
  avalikku, allikapõhiselt lubatud sisu.
- [Kehtiva Metsaseaduse § 41](https://www.riigiteataja.ee/akt/MS) on
  õigusväidete autoriteetne allikas. Õigusaktide vastused vajavad jõustumise
  kuupäeva ja suunamist ametlikku teenusesse; prototüüp ei anna personaalset
  õigusnõu.

## Otsingumeetodite võrdlus

Üks retrieval-meetod ei ole piisav:

- leksikaalne BM25 säilitab täpsed mõisted, aastad, ühikud ja registrikoodid;
- semantiline retrieval leiab loomuliku küsimuse ka siis, kui lehel kasutatakse
  teisi sõnu või käändevorme;
- Reciprocal Rank Fusion ühendab eri skaalal tulemused järjekoha põhjal.
  [Elasticsearchi RRF dokumentatsioon](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/reciprocal-rank-fusion)
  rõhutab, et lähte-skoorid ei pea olema omavahel võrreldavad;
- [Qdranti hübriidotsingu juhis](https://qdrant.tech/documentation/search/hybrid-queries/)
  soovitab ilma treeningkogumita RRF-i turvalise algvalikuna ja hoiatab
  normaliseerimata dense- ja sparse-skooride liitmise eest;
- [BEIR-i uuring](https://arxiv.org/abs/2104.08663) leidis BM25 tugeva
  baasjoonena ning reranking'u keskmiselt tugeva, kuid kallima variandina.
  Seetõttu mõõdetakse lahendust kohalikul eestikeelsel kuldandmestikul;
  üldbenchmark ei tõenda KAURi kvaliteeti.

Eestikeelse leksikaalse otsingu jaoks on Lucene'il
[EstonianAnalyzer](https://lucene.apache.org/core/9_9_0/analysis/common/org/apache/lucene/analysis/et/EstonianAnalyzer.html)
ning Elasticsearch kirjeldab
[eestikeelse analüsaatori](https://www.elastic.co/docs/reference/text-analysis/analysis-lang-analyzer)
standardset lowercase + stopword + Snowball stemmer ahelat. Dense-kandidaadid
`BAAI/bge-m3` (MIT) ja `intfloat/multilingual-e5-base` (MIT) toetavad üle saja
keele, kuid mudelikaart hoiatab madala ressursiga keelte võimaliku kvaliteedikao
eest. `BAAI/bge-reranker-v2-m3` (Apache-2.0) on mitmekeelne reranker. Ükski
nendest ei lähe tootmisse enne eestikeelset võrdlust.

## Embed'i tehniline reaalsus

Keskkonnaportaal kasutab metsalehtedel juba kolmandate osapoolte Power BI
iframe'e, seega on iframe CMS-is realistlik piloodivorm. 16.08.2026 HTTP
vaatluses saatis Keskkonnaportaal `X-Frame-Options: SAMEORIGIN`; see takistab
Keskkonnaportaali enda raamimist, mitte selle sees teise saidi näitamist.
Terrapointi kõik lehed saatsid seevastu `X-Frame-Options: DENY` ja CSP
`frame-ancestors 'none'`, mistõttu praegust rakendust ei saa embed'ida.

Piloot vajab eraldi `/embed/forest` dokumenti, mille
[`frame-ancestors`](https://www.w3.org/TR/CSP/#directive-frame-ancestors) lubab
ainult Keskkonnaportaali kontrollitud originit. Ülejäänud Terrapoint jääb
`DENY`/`'none'` kaitse alla. Iframe teeb API-kõned Terrapointi enda originile,
seega pole vaja brauserisse mudelivõtit ega laia CORS-i.

## Otsus

Kolmekuuline piloot tuleb teha eraldi metsa-teadmusindeksi ja embeditava
iframe'ina. See vähendab integratsiooniriski, jätab portaali senise otsingu
puutumata ning võimaldab retrieval'i ja vastuste kvaliteeti eraldi mõõta.
Püsiva teenuse otsus tehakse alles pärast kuldandmestiku, sisutoimetajate
kontrolli, kasutajamõõdikute ja halduskoormuse hindamist.

## Prototüübi kontrollkatse

Otsust ei jäetud ainult kirjanduse põhjal oletuseks. Väike deterministlik
referentsmootor ühendab käändevorme arvestava BM25-haru, märgi-trigrammi haru,
auditeeritava metsandusterminite haru, RRF-i ja rerankimise. Ranget sõnavormi
kasutav BM25 on baasjoon.

V1 külmutatud kontroll ei läbinud väravat (Recall@3 `0,8667`, paranemine
`+0,10`), mis paljastas nii retrieval'i servajuhte kui kaks ebatäpset
kuldmärgendit. Tulemus säilitati. Pärast v1 muutmist arendusmaterjaliks loodi
uus v2 kontrollosa ja külmutati see enne esimest jooksu. V2 tulemus 30
vastataval kontrollpäringul:

| Meetod | Recall@3 | nDCG@3 | MRR |
|---|---:|---:|---:|
| range leksikaalne baasjoon | 0,7667 | 0,6762 | 0,6639 |
| hübriid + RRF + rerank | **1,0000** | **0,9139** | **0,8833** |

Recall@3 absoluutne paranemine oli `+0,2333`; kõik viite-,
abstention-/redirect- ja kaitsekriitilise regressiooni kontrollid läbisid.
See tõendab prototüübi arhitektuurisuunda, mitte tootmisvalmis dense-mudelit ega
KAURi kinnitatud kuldandmestikku. Korratav käsk ja detailid on `evaluation/`
kaustas.
