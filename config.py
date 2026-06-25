import os

GEOBASE = "https://gsavalik.envir.ee/geoserver"

CACHE_TTL_FULL = 86400
CACHE_TTL_WFS = 21600
CACHE_TTL_PRICES = 604800

TILES_URL = "https://tiles.maaamet.ee/tm/tms/1.0.0/{layer}@GMC/{z}/{x}/{y}.png"

DEFAULT_CORS_ORIGINS = [
    "https://terrapoint.ee",
    "https://www.terrapoint.ee",
    "https://terrapoint.vercel.app",
    "http://localhost:8099",
    "http://127.0.0.1:8099",
]


def _parse_cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "")
    origins = [origin.strip().rstrip("/") for origin in raw.split(",") if origin.strip()]
    if not origins or "*" in origins:
        return DEFAULT_CORS_ORIGINS
    return origins


CORS_ORIGINS = _parse_cors_origins()
