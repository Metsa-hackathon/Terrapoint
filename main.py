import os

from fastapi.staticfiles import StaticFiles

from api.index import app

# Serve static files for local dev (Vercel serves from public/ instead)
if not os.environ.get("VERCEL"):
    app.mount("/", StaticFiles(directory="static", html=True), name="static")
