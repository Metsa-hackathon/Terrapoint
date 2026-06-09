# Terrapoint — Metsaportaal

## Kirjeldus
Metsa väärtuse ja andmete analüüsi veebirakendus. FastAPI backend + HTML/CSS/JS frontend.

## Olulised käsud
- **Backend käivitamine:** `python3 -m uvicorn main:app --host 0.0.0.0 --port 8099`
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
- Vercel hostib frontend: terrapoint.vercel.app
- Traefik proxyb backendi: 10.0.4.1:8099
- Docker võrgud: coolify gateway 10.0.1.1, n8n 10.0.1.9

## Olulised reeglid
- Kõik peab olema Verceliga ühilduv — frontend deployitakse Vercelile
