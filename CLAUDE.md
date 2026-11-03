# Terrapoint — Metsaportaal

## Kirjeldus
Metsa väärtuse ja andmete analüüsi veebirakendus. FastAPI backend + HTML/CSS/JS frontend.

## Olulised käsud
- **Backend käivitamine:** `python3 -m uvicorn api.index:app --host 0.0.0.0 --port 8099`
- **Paigaldus:** `pip install -r requirements.txt`

## Git konventsioonid
- Commit tüübid: `feat:` (uus funktsioon), `fix:` (parandus), `style:` (CSS/UI), `refactor:`
- Commit keel: eesti keel
- Alati `git pull --rebase` enne `git push` — remote võib sõbra muudatusi sisaldada
- Push ainult siis kui testid/ehitus töötab

## API struktuur (ülevaade)
- `api/` - API endpointid
- `services/` - äriloogika
- `calculators/` - arvutusmoodulid
- `spatial/` - GeoJSON/ruumilised andmed
- `static/` - staatilised failid (CSS, JS, pildid)
- `logos/` - logo pildid

## Levinud veaolukorrad
- Git push võib ebaõnnestuda kui remote on ees. Tee alati `git pull --rebase` esimesena.
- Kui curl/wget alamkäsk ebaõnnestub, proovi alternatiivset URL-i või meetodit.
- Kui bash käsk tagastab "exit code 1", ära proovi sama käsku uuesti — proovi alternatiivset lahendust.

## Keskkond
- **Tootmise domeen**: `terrapoint.ee` (Verceli custom domain). Push master
  branchi → terrapoint.ee värskeneb kohe.
- `terrapoint.vercel.app` suunab `vercel.json` redirectiga (308) terrapoint.ee-le.
- Vercel hostib frontend ainult `terrapoint.ee` all.
- Vercel proxyb pikad päringud `terrapoint.arleserver.cfd` home-serveri API-le
- Backendi URL-i saab muuta `TERRAPOINT_BACKEND_API_URL` keskkonnamuutujaga
- Traefik proxyb backendi Docker bridge'i `172.20.0.1:8001` kaudu
- Home-serveri API kuulab ainult `127.0.0.1:8099`; socat ingress on `deploy/home/`

## Olulised reeglid
- Kõik peab olema Verceliga ühilduv — frontend deployitakse Vercelile
- Pärast `git push` oota ~30s Verceli deploy'ks, siis kontrolli brauseris
  `terrapoint.ee` (cache võib vajada hard refresh: Cmd/Ctrl+Shift+R)
- MD failid: `CLAUDE.md` (agent kontekst), `CHANGELOG.md` (ajalugu).
  Ei ole eraldi `AGENTS.md` / `OPENCODE.md` — kogu agent info on `CLAUDE.md`-s.

## UI kontroll brauseris (kasutaja reegel)
- Iga UI muudatus (`index.html`, `static/css/*`, `static/js/*`, UI-nähtav vastus): enne "valmis" ütlemist vaata lehte headless brauseris. Testid ja diff ei tõesta, et leht töötab.
- Brauser: süsteemne `python3` Playwright (1.60.0). Kontrollitud 2026-11-02: `chromium.launch(headless=True, args=["--no-sandbox"])` käivitab Playwrighti Chromiumi (148) ja `chromium.launch(executable_path="/usr/bin/google-chrome", headless=True, args=["--no-sandbox"])` käivitab Chrome'i (153). Repo `.venv`-s Playwrighti ei ole.
- Voog: käivita rakendus (`.venv/bin/python -m uvicorn api.index:app --host 127.0.0.1 --port 8160`, enne seadista `TERRAPOINT_CHAT_SNAPSHOT_KEY_B64` juhusliku 32-baidise võtmega), ava `/`, kirjuta `78404:409:0113` väljale `#kataster-input-landing`, vajuta Enter, oota ~18 s. Tulemuste vaates on päises `#kataster-input`.
- Kontrolli: desktop 1280×800 ja mobiil 390×844; `pageerror` ja konsoolivead 0; ebaõnnestunud päringuid ei tohi olla; mobiilil horisontaalset ülevoolu ei tohi olla. Ekraanipilt tuleb ise vaadata. Kui välimus peab jääma samaks, võrdle teksti ja pikselit eelmise versiooniga.
- Ajutised ekraanipildid ja tekstivõtted jäta `/tmp/` alla, mitte repo sisse. Sulge oma brauserivahelehed ja peata oma serverid.
