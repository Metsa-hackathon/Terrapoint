# Keskkonnaportaali embed-juhis

## Paigalduskood

Keskkonnaportaali CMS-i sisualasse lisatakse üks sandboxitud iframe ja
kõrgusekuulaja:

```html
<iframe
  data-terrapoint-forest
  src="https://terrapoint.ee/embed/forest"
  title="Terrapointi metsaandmete tõlgendaja"
  loading="lazy"
  referrerpolicy="no-referrer"
  sandbox="allow-scripts allow-forms allow-same-origin"
  style="display:block;width:100%;height:780px;border:0"
></iframe>
<script defer src="https://terrapoint.ee/static/embed/loader.js?v=2"></script>
```

Kui portaali CSP kasutab `frame-src` direktiivi, lisab KAUR sinna
`https://terrapoint.ee`. Kui CMS ei luba välist loader-skripti, võib iframe
jääda fikseeritud kõrgusega (soovitus 900 px) või kopeerida `loader.js` KAURi
enda staatilisse varasse muutmata originikontrolliga.

`allow-same-origin` on vajalik, et iframe saaks teha sama origini API-päringu.
Sandbox on turvaline, sest Keskkonnaportaal ja Terrapoint on eri originid.

## Terrapointi serveripoolne seadistus

Vaikimisi lubatud parent-originid:

```text
'self'
https://keskkonnaportaal.ee
https://www.keskkonnaportaal.ee
https://keskkonnaportaal.envir.ee
```

Neid saab serveris kitsendada:

```bash
EMBED_FRAME_ANCESTORS="https://keskkonnaportaal.ee,https://www.keskkonnaportaal.ee"
```

Parser lubab ainult täpseid HTTPS-origineid; teed, wildcard'id, kasutajainfo ja
CSP-d katkestavad märgid lükatakse tagasi. Kui seadistatud loendis ei jää ühtki
kehtivat kaug-originit, jääb alles ainult `'self'` (fail closed). Muutuja ei laienda CORS-i. Iframe
laeb Terrapointist ning teeb `/api/forest-search` päringu samale originile.

## Päiste piir

`/embed/forest`:

- ei saada `X-Frame-Options` päist;
- saadab CSP `frame-ancestors`, mis lubab ainult eelneva allowlist'i;
- ei luba inline JavaScripti/CSS-i ega kolmanda osapoole võrguühendusi.

Kõik teised lehed, sealhulgas demo, säilitavad `X-Frame-Options: DENY` ja CSP
`frame-ancestors 'none'`. Verceli globaalne päisereegel kasutab ametlikus
konfiguratsioonis toetatud negatiivset gruppi, et täpselt `/embed/forest`
erandisse jätta; Verceli dokumentatsioon kirjeldab nii
[custom response headers](https://vercel.com/docs/project-configuration/vercel-json)
kui ka nõuet panna
[negative lookahead gruppi](https://vercel.com/docs/errors/error-list#invalid-route-source-pattern).

Kontroll:

```bash
curl -sI https://terrapoint.ee/embed/forest
curl -sI https://terrapoint.ee/
```

Esimeses peab olema Keskkonnaportaali originidega `frame-ancestors` ja puuduma
`X-Frame-Options`. Teises peab olema `DENY` ning `'none'`.

## Kõrguse sõnum

Widget saadab parent'ile ainult:

```json
{"type":"terrapoint:forest-resize","height":780}
```

Küsimust, vastust ega kasutajaandmeid `postMessage` kaudu ei saadeta.
`loader.js` kontrollib nii `event.origin` kui ka `event.source`, teisendab
kõrguse arvuks ja piirab selle vahemikku 480–6000 px. Kõrgem piir väldib
kitsal ekraanil pika allikavastuse sees eraldi kerimisala.

## CMS-i vastuvõtukontroll

- 320, 375, 768 ja vähemalt 1024 px laiuses pole horisontaalset kerimist;
- Tab/Shift+Tab jõuab küsimuse, nupu, detailide ja allikalinkideni;
- Enter/submit kuvab olekuteate ning vastuse pealkiri saab fookuse;
- allikas avaneb uuel vahelehel `noopener noreferrer` kaitsega;
- katastritunnus suunab kinnistuotsingusse ega anna SMI-st kinnistuarvu;
- parent'i ja iframe'i konsoolis pole CSP/CORS viga;
- olulise vea korral saab CMS-i ploki ühe avaldamisega eemaldada.

## Kolme kuu eemaldamine

Piloodi lõppkuupäev ja CMS-ploki omanik täidetakse
`decision-log-template.md` failis. Eemaldamiseks kustutab KAUR CMS-ist iframe'i
ja loaderi viite; Terrapoint jätab endpointi 7 päevaks teatega alles, seejärel
sulgeb route'i või taastab üldise `DENY` päise. Telemeetria kustutatakse
kokkulepitud säilitustähtaja järgi.
