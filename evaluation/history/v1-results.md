# V1 külmutatud kontrollmõõtmine

Mõõtmine tehti 2026-08-16 pärast v1 mootori ja kontrollpäringute külmutamist.
Tulemust ei kasutata üleandmisvärava läbimise tõendina.

| Jaotus | Päringuid | Meetod | Recall@3 | nDCG@3 | MRR |
|---|---:|---|---:|---:|---:|
| development | 42 | baseline | 0,8095 | 0,7474 | 0,7440 |
| development | 42 | hybrid | 1,0000 | 0,9617 | 0,9484 |
| locked | 30 | baseline | 0,7667 | 0,7421 | 0,7567 |
| locked | 30 | hybrid | 0,8667 | 0,8298 | 0,8358 |

Värav jäi läbimata: hübriidi Recall@3 oli alla `0,90` ning absoluutne
paranemine baasjoonest oli `+0,10`, mitte nõutud `+0,15`.

Retrieval'i möödalasud olid `locked-faq-03`, `locked-faq-04`,
`locked-mis-08` ja `locked-mis-12`. Järelkontroll tuvastas, et kahe viimase
kuldmärgend ei vastanud lähteülesande tegelikule väärarusaamale:

- `locked-mis-08` küsis metsateatise kavandatud ja tegeliku mahu erinevust,
  kuigi MIS-08 lähteväide on „raiutakse rohkem kui juurde kasvab”;
- `locked-mis-12` küsis metsasuse protsenti, kuigi MIS-12 lähteväide on
  „metsa tagavara on üks kindel vaieldamatu number”.

Neid v1 kirjeid ega tulemust tagantjärele ei muudeta. V1 kogu on v2
arendusmaterjal. V2 kasutab uut kontrollosa ning eraldi tulemusefaili.
