# Changelog

Kõik olulised muudatused Terrapoint repositooriumis.

## [Määramata] - 2026-06-09

### Fixed
- **AI chat endpoint tagastas 500 "AI ei andnud vastust"** — põhjus: Verceli
  deployment'is puudus `NVIDIA_API_KEY` keskkonnamuutuja. Lisatud Verceli
  dashboardi (production) + `NVIDIA_MODEL=stepfun-ai/step-3.7-flash`.
  Kohalik `.env` oli olemas, aga Vercel ei loe kohalikku `.env` — seaded
  tuleb teha dashboardi kaudu.
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
