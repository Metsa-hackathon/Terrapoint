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
- **Tootmise domeen**: `terrapoint.ee` (Verceli custom domain, sama projekt
  mis `terrapoint.vercel.app` — mõlemad on sama Vercel deployment, push
  master branchi → mõlemad värskenevad kohe)
- Vercel hostib frontend: `terrapoint.ee` (primary), `terrapoint.vercel.app` (alias)
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
