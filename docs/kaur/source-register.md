# Allikaregister ja provenance

Masinloetav registri allikas on `knowledge/forestry/sources.json` ning
vastuste ja allikate seos on `knowledge/forestry/documents.json`. Failide
Git-versioon ja SHA-256 kuvatakse käsuga:

```bash
python3 scripts/validate_forestry_knowledge.py
```

Kõigi kirjete praegune olek `prototype_research_reviewed` tähendab, et allikas
ja kasutatud koht kontrolliti 16.08.2026 uurimise käigus. See ei tähenda KAURi
sisutoimetaja kinnitust.

## Registreeritud allikad

| ID | Omanik / tüüp | Kasutus prototüübis | Eripiirang |
|---|---|---|---|
| `smi-2024-tables` | KAUR, ametlik statistiline PDF | arvud, aastad, ühikud, suhteline viga | säilita tabeli lehekülg, päis ja definitsioon |
| `kkp-smi-overview` | KAUR, metoodikaleht | valikuuringu ja ebakindluse selgitus | perioodiline leht, kontrolli uuendust |
| `kkp-forest-overview` | KAUR, teemavärav | mõisted ja ametlikud suunad | kiirfakt ei asenda algtabelit |
| `kkp-current-forest` | KAUR, jooksva info juhis | SMI, registri, RMK ja teatise ajaseis | eri vaated pole vahetatavad |
| `kkp-metsaregister-data` | KAUR, andmekataloog | kihid, WMS/WFS ja kinnistu suund | ainult loetletud levitused on märgitud CC BY 4.0 |
| `keskkonnaamet-forest-notice` | Keskkonnaamet, teenusejuhis | metsateatise protsess | menetlus võib muutuda |
| `forest-act` | Riigi Teataja, seadus | § 41 ja õigusraam | kuva kehtivus; ei ole personaalne õigusnõu |
| `keskkonnaamet-protected-species` | Keskkonnaamet, ligipääsujuhis | avaliku/piiratud info piir | I–II kategooria info ei lähe avalikku RAG-i |
| `kkp-forest-environment-review` | KAUR, keskkonnaülevaade | seisund, surve ja kliimariskid | mõju sõltub mõõdikust/perioodist |
| `climate-adaptation-plan` | Kliimaministeerium, poliitika/uuringute värav | kliimariski kontekst | poliitikadokument ei ole üksik prognoos |

Autoriteetsed lähtekohad on
[SMI metoodikaleht](https://keskkonnaportaal.ee/et/teemad/mets/metsastatistika-sh-smi),
[SMI 2024 tabelid](https://keskkonnaportaal.ee/sites/default/files/Teemad/Mets/SMI2024/SMI_2024.pdf),
[Metsainfo hetkeseis](https://keskkonnaportaal.ee/et/teemad/mets/metsainfo-hetkeseis),
[Metsaregistri andmekataloog](https://keskkonnaportaal.ee/et/avaandmed/metsaregistri-andmestikud)
ja [Metsaseadus](https://www.riigiteataja.ee/akt/MS).

## Arvulise väite kohustuslik komplekt

Arvuline teadmusväide avaldatakse ainult koos väljadega:

`väärtus + ühik + andmeaasta/periood + geograafia + definitsioon + veahinnang
(kui avaldatud) + source_id + locator`.

Praeguses väikeses JSON-korpuses on komplekt toimetatud vastusetekstis ja
allikaviites. Tootmisindeksis peab see olema eraldi struktureeritud objekt, et
generaator ei saaks ühikut ega veapiiri arvust lahutada.

## Uuendamise protsess

1. Allika omanik või monitor tuvastab muudatuse; vana kirjet ei kirjutata
   tõendita üle.
2. Kontrollitakse URL-i, avalikkuse taset, litsentsi/kasutusotsust, kuupäeva,
   definitsiooni, tabelipäist ja locator'it.
3. Muudetakse `sources.json` ning kõik mõjutatud `documents.json` kirjed.
4. KAURi sisuomanik kinnitab difi ja uued kuldmärgendid.
5. Läbivad validaator, v2 või uus eval-versioon, testid ja brauseri smoke-test.
6. Avaldatakse uus indeksiversioon; regressiooni korral taastatakse eelmine Git
   commit/deploy.

Õigusallikat kontrollitakse enne iga avaldamist ning vähemalt kord kuus.
Statistikafaili kontrollitakse uue SMI väljaande ilmumisel. Jooksva info lehti
kontrollitakse vähemalt kord kuus. Täpsed SLA-d ja omanikud määrab KAUR.
