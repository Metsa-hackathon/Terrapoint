import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from main import app

PROJECT_ROOT = Path(__file__).parent.parent

@app.get("/")
async def root():
    html_path = PROJECT_ROOT / "public" / "index.html"
    if html_path.exists():
        return HTMLResponse(html_path.read_text(encoding="utf-8"))
    # Debug: list what we can see
    try:
        files = os.listdir(PROJECT_ROOT)
        pub_files = os.listdir(PROJECT_ROOT / "public") if (PROJECT_ROOT / "public").exists() else []
    except Exception as e:
        files = [str(e)]
        pub_files = []
    return JSONResponse({
        "error": "index.html not found",
        "project_root": str(PROJECT_ROOT),
        "root_files": files,
        "public_files": pub_files,
        "cwd": os.getcwd()
    })

@app.get("/css/{filename:path}")
async def serve_css(filename: str):
    file_path = PROJECT_ROOT / "public" / "css" / filename
    if file_path.exists():
        return FileResponse(file_path, media_type="text/css")
    return JSONResponse({"error": "not found", "path": str(file_path)}), 404

@app.get("/js/{filename:path}")
async def serve_js(filename: str):
    file_path = PROJECT_ROOT / "public" / "js" / filename
    if file_path.exists():
        return FileResponse(file_path, media_type="application/javascript")
    return JSONResponse({"error": "not found", "path": str(file_path)}), 404
