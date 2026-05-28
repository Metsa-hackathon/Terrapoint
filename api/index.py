import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.responses import HTMLResponse, FileResponse
from main import app

PROJECT_ROOT = Path(__file__).parent.parent

@app.get("/")
async def root():
    html_path = PROJECT_ROOT / "static" / "index.html"
    if html_path.exists():
        return HTMLResponse(html_path.read_text(encoding="utf-8"))
    return {"error": "index.html not found"}

@app.get("/css/{filename:path}")
async def serve_css(filename: str):
    file_path = PROJECT_ROOT / "static" / "css" / filename
    if file_path.exists():
        return FileResponse(file_path, media_type="text/css")
    return {"error": "not found"}

@app.get("/js/{filename:path}")
async def serve_js(filename: str):
    file_path = PROJECT_ROOT / "static" / "js" / filename
    if file_path.exists():
        return FileResponse(file_path, media_type="application/javascript")
    return {"error": "not found"}
