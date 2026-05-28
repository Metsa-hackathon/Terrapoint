import os
import time
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import CORS_ORIGINS, REDIS_URL
from api.search import router as search_router
from api.export import router as export_router

ON_VERCEL = os.environ.get("VERCEL") == "1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not ON_VERCEL:
        try:
            app.state.redis = aioredis.from_url(REDIS_URL, decode_responses=True)
            await app.state.redis.ping()
        except Exception:
            app.state.redis = None
    else:
        app.state.redis = None
    yield
    if getattr(app.state, "redis", None):
        await app.state.redis.aclose()


app = FastAPI(
    title="Terrapoint",
    description="Metsaomaniku tööriist — sisesta katastri number, saa kogu metsa tõde.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search_router, prefix="/api")
app.include_router(export_router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok", "timestamp": time.time()}


if not ON_VERCEL:
    from fastapi.staticfiles import StaticFiles

    app.mount("/", StaticFiles(directory="static", html=True), name="static")
