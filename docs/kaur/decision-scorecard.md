# Jätkuotsuse scorecard

## Prototüübi hetkeseis 16.08.2026

| Mõõde | Värav | Praegune tõend | Olek |
|---|---|---|---|
| Leitavus | Recall@3 ≥ 0,90; +0,15 baasjoonest | v2: 1,0000; +0,2333 | prototüübis läbitud |
| Järjestus | nDCG@3 ≥ 0,80 | v2: 0,9139 | prototüübis läbitud |
| Viited | 100% registry/evidence seos | eval + testid | prototüübis läbitud |
| FAQ/väärarusaamad | 18/18 ja 12/12 | katvusmanifest | tehniliselt kaetud, sisu kinnitamata |
| Abstention/kinnistu suund | 100% kontrolljuhtudel | v2 käitumistestid | prototüübis läbitud |
| Ligipääsetavus | WCAG 2.2 AA põhivoog | semantiline leping + brauseri QA | lõplik eksperthinnang ootel |
| Turve/privaatsus | 0 kriitilist leidu, õiguslik alus | scoped CSP, no-text default | KAURi review ootel |
| Latentsus/uptime | piloodi SLA | lokaalne smoke-test ainult | mõõtmata |
| Kasutajakasu | KAURi lävend | piloot pole alanud | mõõtmata |
| Halduskoormus | nimeline omanik ja SLA | juhend/rollback olemas | omanik määramata |
| Kulu | kinnitatud eelarve | extractive fallbackil mudelikulu 0 | tootmismudel otsustamata |
| Bränd/vastutus | kirjalik KAURi otsus | puudub | blokeerib KAURi nimel avaldamise |

V2 tulemus on väikesel prototüübi kontrollkogumil, mille KAURi sisuomanik pole
veel kinnitanud. Seda ei esitata kasutajapiloodi ega tootmiskvaliteedi tõendina.

## Piloodi lõpus täidetav hinnang

Iga mõõde saab hinde 0–3:

- `0` — tõend puudub või stoppreegel rikuti;
- `1` — alla lävendi, vajab sisulist ümbertegemist;
- `2` — lävend täidetud kontrollitud piloodis;
- `3` — lävend täidetud ja KAUR suudab seda iseseisvalt korrata/hallata.

Üks keskmine skoor ei tohi peita stoppreeglit. Turbe-, privaatsus-, viite- või
kriitilise sisuklassi hinne 0 lõpetab piloodi sõltumata muudest tulemustest.

| Mõõde | Hinne 0–3 | Tõendi link/raport | Omaniku kommentaar |
|---|---:|---|---|
| Sisuline õigsus |  |  |  |
| Retrieval ja abstention |  |  |  |
| Viited ja arvude grounding |  |  |  |
| Kasutajakasu |  |  |  |
| Ligipääsetavus |  |  |  |
| Turve ja privaatsus |  |  |  |
| Jõudlus ja töökindlus |  |  |  |
| Kulu |  |  |  |
| Sisuhalduse koormus |  |  |  |
| Tehniline ülevõetavus |  |  |  |

## Otsus

```text
[ ] lõpetada ja eemaldada
[ ] korrata piiratud ulatusega pärast parandusi
[ ] jätkata ajutist pilooti
[ ] võtta KAURi haldusse
[ ] algatada püsiva teenuse eraldi arendus

Põhjendus:
Riskid ja tingimused:
Otsustajad / kuupäev:
```
