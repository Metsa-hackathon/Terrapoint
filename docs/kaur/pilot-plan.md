# Kolmekuulise kontrollitud piloodi plaan

Piloot algab alles pärast sisulist, turbe-, andmekaitse- ja tehnilist
heakskiitu. Kuupäevad, nimed ja tegelikud lävendid täidetakse
`decision-log-template.md` failis.

## Etapid

| Aeg | Tegevus | Väljapääsuvärav |
|---|---|---|
| enne starti | 18 FAQ ja 12 väärarusaama sisukinnitus; uus KAURi kuldandmestik; DPIA/privaatsusotsus; load-, a11y- ja turvatest | kõik kriitilised read heaks kiidetud |
| nädal 1 | 5–10% kokkulepitud metsalehe liiklusest või sisemine link; igapäevane viite- ja veaaudit | 0 põhjendamata arvulist väidet, 0 turvaintsidenti |
| nädalad 2–4 | avalik piiratud piloot; iganädalane sisuproov ja päringuklasside koond | kvaliteet, uptime ja koormus väravas |
| kuu 2 | ainult arendusjaotusel parandused; uue versiooniga kontrollkogum; valikuline generaatori A/B | muudatused ei halvenda kaitse-/õigusklasse |
| kuu 3 | stabiilsusperiood, kasutajate tagasiside, kulude ja halduskoormuse mõõtmine | otsustusraport ja rollback-valmidus |
| lõpp + 7 päeva | CMS eemaldamine või eraldi jätkuotsus; andmete kustutamine vastavalt tähtajale | kirjalik sulgemis- või jätkuotsus |

## Minimaalne sündmuseskeem

Telemeetria on vaikimisi väljas. Kui KAUR annab õigusliku aluse ja teavituse,
salvestatakse ilma küsimuse tekstita ainult:

```text
event_name: widget_loaded | answer_rendered | clarification_shown |
            redirect_shown | source_opened | helpful_vote
event_time: UTC
anonymous_session_id: juhuslik, lühikese elueaga
service_version, index_version, generator_version
status, intent/document_ids, confidence_bucket
latency_bucket, viewport_bucket, error_code
```

Keelatud väljad on küsimuse/vastuse tekst, katastritunnus, URL querystring,
IP-aadress analüütikakihis, user-agent täiskujul ja omaniku/isikuandmed.
Infrastruktuuri turvalogide IP-käitlus ja säilitustähtaeg otsustatakse eraldi.
Vabatahtliku vabasõnalise tagasiside jaoks on eraldi nõusolek, kanal ja
redaktsiooniprotsess; seda ei ühendata vaikimisi RAG-i treeningandmetega.

## Mõõdikud

### Sisuline kvaliteet

- lukustatud Recall@3 ≥ 0,90 ja paranemine baasjoonest ≥ +0,15;
- nDCG@3 ≥ 0,80;
- citation precision/coverage 100%;
- arvuliste kontrollvastuste aasta + ühik + definitsioon + locator 100%;
- abstention/redirect korrektne kõigil ohutusjuhtudel;
- KAURi toimetajate valimi hinnang: õige, arusaadav, piisavalt piiratud.

### Kasutajakasu

- vastuse kuvamise ja allika avamise määr;
- „vastas küsimusele” jah/ei (mitte ainult üldine rahulolu);
- täpsustamise määr ning mitu täpsustust viib vastuseni;
- kinnistuküsimuse õige suunamise määr;
- ligipääsetavuse probleemid ja kasutajatoe teemad.

### Tehniline ja organisatsiooniline sobivus

- API p95 latentsus ja veamäär kokkulepitud liiklusel;
- uptime, 429 määr ja intsidentide taastumisaeg;
- mudeli/infra kulu 1000 vastuse kohta;
- sisu uuendamiseks kuluv inimtöö ja allika vanus;
- deploy/rollback'i sooritamise aeg KAURi meeskonna poolt.

## Kohe peatamise tingimused

- allikata või vale viitega arvuline/õiguslik väide;
- piiratud liigi-, omaniku- või muu isikuinfo leke;
- prompt-injection või XSS viib juhise, võtme või lubamatu lingi kuvamiseni;
- vale katastriüksuse andmete omistamine;
- kriitilise klassi retrieval-regressioon;
- korduv kättesaamatus üle kokkulepitud veaeelarve;
- KAURi sisu-, turbe- või andmekaitseomaniku peatamisnõue.

Peatamine tähendab CMS-i embed-ploki eemaldamist, endpointi väljalülitamist,
logide säilitamist ainult intsidendi jaoks lubatud tähtajaks ja kirjalikku
järelanalüüsi. Seda saab teha mudelist või indeksist sõltumatult.

## Jätkuotsus

Piloodi edu ei võrdu automaatselt KAURi brändi või püsivastutuse võtmisega.
`decision-scorecard.md` täidetakse sisuomaniku, tehnilise omaniku, turbe,
andmekaitse ja tooteomaniku ühisel review'l. Võimalikud otsused: lõpetada,
teha uus piiratud katse, võtta sisemine haldus üle või alustada püsiva teenuse
eraldi projekti.
