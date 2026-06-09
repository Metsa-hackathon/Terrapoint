# Changelog

Kõik olulised muudatused Terrapoint repositooriumis.

## [Määramata] - 2026-06-09

### Fixed
- **Vercel FastAPI runtime ei käivitunud** — `vercel.json`-is oli
  `framework: null` ja käsitsi `rewrites` `/api/...` -> `/api/index.py`,
  mis pani Verceli serveerima `api/index.py` raw Python failina (Content-Type
  `application/octet-stream`, 405 POST korral). Eemaldatud `framework: null`
  ja rewrites — Verceli fastapi preset avastab nüüd `app.py` juurest
  ise. Lisatud `app.py` shim: `from api.index import app`.
- **API endpoint tagastas 500 FUNCTION_INVOCATION_FAILED** —
  `api/index.py` real 1176 oli sulgemata jutumärk AI fallback tekstis
  (3 × U+201E `„` ilma vastava U+201C lõputa), mis andis `SyntaxError`.
  Parandatud — nüüd import töötab.
- **AI chat endpoint tagastas 500 "AI ei andnud vastust"** — põhjus: Verceli
  deployment'is puudus `NVIDIA_API_KEY` keskkonnamuutuja. Lisatud Verceli
  dashboardi (production) + `NVIDIA_MODEL=meta/llama-3.3-70b-instruct`
  (varem `stepfun-ai/step-3.7-flash` kulus kogu tokeni eelarve sisemisele
  mõttekäigule ega andnud sisulist vastust). Kohalik `.env` oli olemas,
  aga Vercel ei loe kohalikku `.env` — seaded tuleb teha dashboardi kaudu.
- **AI chat input ei ilmunud mobiilis refresh'i järel** —
  `aiAnalyzeKataster` funktsioonis oli `return` short-circuit, mis jättis
  input area `display:none` peale, kui kasutaja navigeeris samale
  kinnistule. Nüüd kuvatakse input area alati enne return-i.
- **AI chat input kaotas pärast esimest sõnumit** —
  `aiLastSendAt` ja `aiRecentSendTimes` kasutati ilma `var` deklareerimiseta,
  mis põhjustas `ReferenceError` ja peitis input area. Deklareeritud
  koos teiste AI muutujatega.
- **Touch targetid olid mobiilis liiga väikesed** (26-36px alla soovitatud
  44px) — search nupp, AI send, zoom nupud, kihi toggle, hint nupud.
  Kõik tõstetud ≥32px (44px eelistatult).
- **Landing title murdus 320px ekraanidel** — vähendatud 38px → 30px
  + lühem line-height.
- **Reposit "muss"** — kohalik oli 9 commit'i taga, logifailid olid
  commititud (`server_err.log`, `server_out.log`). Tehtud `git pull --rebase`,
  logifailid eemaldatud jälgimisest, `.gitignore` täiendatud.

### Added
- `.gitignore`: `server_*.log` ja `*.log` (kohalikud uvicorn logid).
- WFS 400 retry — Estonian WFS annab vahel 400 kehtetutele bbox päringutele,
  nüüd retry ka nende puhul (`services/layers.py`).
- **URL-põhine auto-search** — `?kataster=78404:409:0113` või `?q=Kadaka pst 159`
  query stringi põhjal käivitub search automaatselt lehe laadimisel.
  Kasulik jagamislinkide jaoks ja deep-linking'uks.
  Toetab ka `popstate` (back/forward nupp).

### Changed
- CSS versioon v11 → v12 (cache bust).

### Deployment
- **Vercel**: env vars seadistatud (NVIDIA_API_KEY, NVIDIA_MODEL).
- **GitHub**: master branch on ajakohane, Vercel auto-deploy töötab.
- **Kohalik API** (systemctl terrapoint-api): .env-st tulnud, töötab.

### Mobile UX parandused
- AI chat input nüüd nähtav ja töötav (393px ja 320px ekraanidel).
- Suuremad touch targetid — sõrmega lihtsam tabada.
- Landing page'i pealkiri mahub 320px ekraanile.

### Teadaolevad puudused
- **2 `@app.get("/")` route** FastAPI's — teine varjutab esimest,
  kuid töötab (testitud).

## [Meist/Allikad/Info] - 2026-06-09 (UI uuendus)

### Added
- **Tiimi pilt** (`static/img/team-hackathon-2026.jpg`, allikas aripaev.ee):
  Metsikult andmetes 2026 võit, 5000€ auhind, 3 meeskonnaliiget.
  Kasutatud Meist sektsiooni hero pildina + uues bento layout'is.
- **Victory bento** (Meist sektsioonis) — 2-veeruline grid:
  - Vasakul: tiimi pilt (4:3, object-position center 30%) + "1. koht · 5000 €"
    badge üleval vasakul
  - Paremal üleval: dark "5000€" prize card
  - Paremal keskel: 3-veeruline meta grid (kuupäev, osalejad, tiim)
  - Paremal all: pikk selgitav tekst
  - Mobiilis: stackub üheks veeruks
- **Info sektsioon** (täiesti uus) — 5-kaardine bento grid:
  - Privaatsus, Arvutusmeetod, AI mudel, Tehniline stack
  - Lai dark "Piirangud" kaart full-width all
  - Sama design system: --ink, --blue-900, --paper-2 taust, 16-18px radius,
    11px mono eyebrow, 17px pealkiri
- **about-hero-caption** — label + tekst tiimi pildi allosas
- **about-hero-tag** (victory bento sees) — backdrop-blur badge "1. koht · 5000 €"

### Changed
- `static/img/forest-hero.jpg` asendatud `static/img/team-hackathon-2026.jpg`-ga
  Meist hero pildina.
- Olemasolev `.about-hackathon` plokk asendatud uue `.victory-bento`-ga.
- CSS versioon v13 → v14 (cache bust).

### Mobile UX
- Bento collapse: 880px → 1-veeruline, 520px → meta stack.
- Info grid: 768px → 1-veeruline.
- Tiimi pilt objekt-positsioon 30% (tiimi näod jäävad nähtavaks).
