# Iframe-widget'i lokaalne ligipääsetavuse QA

Kontrollitud 16.08.2026 Playwrighti juhitud Chromiumis otse
`/embed/forest` route'il ning deterministliku staatilise auditiga. Tulemus on
prototüübi **kohalik põhivoo tõend**, mitte WCAG vastavusdeklaratsioon.

## Automaatne leping ja kontrast

Käsk:

```bash
python scripts/audit_forestry_accessibility.py --write
```

`evaluation/accessibility_results.json` ja `.md` säilitavad tulemuse. Värav
läbis 13 struktuuri-/käitumiskontrolli ja 18 tekstilise või mittetekstilise
kontrastipaari:

- dokumendi keel, üks nimega `main`, seostatud label/juhis, lahenevad
  `aria-labelledby` viited ja loogiline H1→H2→H3 järjestus;
- `status` ja `alert` live-region, programmiliselt fokuseeritav vastuse H2,
  `aria-busy` ning valideerimisvea `aria-invalid`;
- positiivse `tabindex` puudumine, 3 px nähtav fookusrõngas,
  `prefers-reduced-motion` ja mobiilipaigutuse leping;
- tavateksti kontrast vähemalt 4,5:1 ning komponendi/fookuse piir vähemalt
  3:1. Madala kontrastiga placeholder, sisendipiir ja algne kollane
  fookusrõngas parandati enne rohelist jooksu.

Kõige väiksem läbitud tekstisuhe on footeri `4,61:1`; placeholder on `4,91:1`,
sisendi piir `3,42:1`, chip'i piir `3,10:1` ja fookusrõngas valgel `7,48:1`.

## Klaviatuuripõhine Chromiumi smoke

Hiirt kasutamata kontrollitud põhivoog:

| Samm | Brauseritõend | Tulemus |
|---|---|---|
| esimene `Tab` | aktiivne `TEXTAREA#question`, accessible name „Sinu küsimus” | läbitud |
| teine `Tab` | aktiivne `BUTTON#submit-button` | läbitud |
| kolmas `Tab` | esimene näidisküsimuse nupp | läbitud |
| nähtav fookus | computed outline `rgb(122, 74, 0) solid 3px`, offset `3px` kõigil kolmel | läbitud |
| küsimuse täitmine, `Tab`, `Enter` | POST 200; aktiivne `H2#result-title`, status „Vastus leitud.” | läbitud |
| tühi küsimus, `Enter` | fookus tagasi textarea'l, `aria-invalid=true`, nähtav/loetav alert | läbitud |
| pärast tulemust järgmised sihid | piirangute summary, ametlikud allikalingid ja seotud küsimused on DOM-i loomulikus järjestuses | läbitud |

Fookuse ja vea visuaalne tõend on
`output/playwright/forest-widget-keyboard-focus.png`. Chromiumi konsoolis oli
0 viga.

## Accessibility API / ekraanilugeja proxy

Playwrighti accessibility snapshot näitas enne vastust järgmisi rolle ja
nimesid: `main`; region „Esita küsimus”; heading level 1 ja level 2; textbox
„Sinu küsimus”; button „Küsi”; kolm nimega näidisnuppu; `status`.

Pärast vastust olid puus lisaks aktiivne heading „Vastus”, kaks level 3
vastuse/metoodika pealkirja, piirangute `group`, region „Kasutatud allikad”,
kaks nimega HTTPS-linki ning region „Seotud küsimused”. Valideerimisvea
snapshot märkis textbox'i `[active] [invalid]` ning teksti eraldi `alert`
rollis. See kinnitab brauseri accessibility API-le jõudva semantika, kuid ei
asenda NVDA, JAWS-i ega VoiceOveri tegelikku kasutajatesti.

## Reflow

- varasemas põhivoo testis ei tekkinud 320 px viewport'is horisontaalset
  kerimist;
- 1280 px baasvaate 200% reflow-proxy 640 px CSS viewport'is andis
  `scrollWidth == clientWidth == 640`;
- pikk mobiilivastus kasvatas iframe'i sisukõrguseni ilma nested scroll'ita.

## Teadlikult välised avaldamisväravad

KAURi staging'us peab sõltumatu spetsialist tegema axe/samaväärse kontrolli,
NVDA või VoiceOveri käsitesti, 200%/400% zoom'i, Windows Forced Colorsi,
Firefoxi/Safari ning päris CMS parent→iframe fookusejärjekorra. Põhjus on see,
et headless Chromiumi accessibility tree ei tõenda OS-i accessibility stack'i,
KAURi CMS-i ega abitehnoloogia kombinatsiooni. Need on acceptance-matrix'is
publitseerimiseelsed väravad, mitte käesoleva prototüübi kohta tehtud
vastavusväide.
