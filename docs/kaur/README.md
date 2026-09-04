# KAURi metsaandmete tõlgendaja prototüüp

See kaust on Terrapointi praktikakontseptsiooni tehniline ja sisuline
üleandmispakett. Lahendus on **otsustusprototüüp**, mitte KAURi kinnitatud ega
KAURi nimel avaldatav teenus.

## Tulemus

- `/embed/forest` on eraldi ligipääsetav iframe-dokument; ainult selle CSP
  lubab kinnitatud Keskkonnaportaali origineid.
- `/api/forest-search` vastab 3–500 tähemärgi pikkusele küsimusele
  struktureeritud vastuse, metoodika, piirangute ja registrist pärit viidetega.
- `knowledge/forestry/` katab kõik lähteülesande 18 FAQ-d ja 12
  väärarusaama. Sisu on uurimisel kontrollitud, kuid KAURi sisutoimetaja pole
  seda veel kinnitanud.
- Deterministlik v2 hübriidotsing läbis külmutatud prototüübikogumi värava:
  Recall@3 `1,0000`, nDCG@3 `0,9139`, Recall@3 paranemine leksikaalsest
  baasjoonest `+0,2333`. V1 läbikukkumine on säilitatud failis
  `evaluation/history/v1-results.md`.
- Vastuse moodustamine on ulatuses: auditeeritav `extractive-v1` generaator
  kopeerib valitud sisutoimetatud väljad. Lukustatud answer-faithfulness on
  30/30; vaba teksti loov runtime-keelemudel pole sellesse versiooni seotud.
- Ligipääsetavuse kohalik värav läbis 13 semantika- ja 18 kontrastikontrolli;
  klaviatuuri ning Chromiumi accessibility-tree smoke läbis.

## Dokumentide kaart

- `acceptance-matrix.md` — nõue → tõend → olek;
- `research-brief.md` — 16.08.2026 portaali baasjoon ja tehnoloogiauuring;
- `search-architecture.md` — sihtarhitektuur ja threat model;
- `scope-and-guardrails.md` — prototüübi eeldatud ulatus ja KAURi otsused;
- `source-register.md` — allikate omanikud, kasutus ja uuendamine;
- `model-card-and-prompt-contract.md` — generaatori vahetamise leping;
- `embed-guide.md` — CMS-i paigaldus, turvapäised ja eemaldamine;
- `browser-qa.md` — Chromiumi desktopi/mobiili funktsionaalne tõend;
- `accessibility-qa.md` — klaviatuuri, fookuse, semantika ja kontrasti tõend;
- `security-review.md` — app-taseme ründepind, kontrollid ja tootmispiirid;
- `pilot-plan.md` — kolm kuud, mõõdikud, privaatsus ja stoppreeglid;
- `decision-scorecard.md` — jätkuotsuse raam;
- `handover.md` — paigaldus, testimine, sisu uuendamine ja rollback;
- `decision-log-template.md` — täidetav sisupoole heakskiiduleht.

## Kiirkontroll

```bash
python3 scripts/validate_forestry_knowledge.py
python3 scripts/evaluate_forestry_search.py --write --enforce
python3 scripts/evaluate_forestry_safety.py --write
python3 scripts/audit_forestry_accessibility.py --write
python3 -m pytest -q
python3 -m uvicorn api.index:app --host 127.0.0.1 --port 8099
```

Seejärel ava `http://127.0.0.1:8099/embed/forest/demo`.

## Enne avalikku pilooti

KAUR peab kinnitama vähemalt sihtrühma, vastutuspiiri, kõik teadmusvastused ja
kuldmärgendid, allikate omanikud/ülevaatuse SLA, logimise õigusliku aluse,
tehnilise hosti, mudeli ning piloodi peatamiskriteeriumid. Täidetud
`decision-log-template.md` on avaldamise eeltingimus.
