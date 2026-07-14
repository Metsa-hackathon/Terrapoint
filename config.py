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
        origins = list(DEFAULT_CORS_ORIGINS)
    for environment_name in ("VERCEL_URL", "VERCEL_BRANCH_URL"):
        preview_host = os.getenv(environment_name, "").strip().lower()
        if (
            preview_host.endswith(".vercel.app")
            and all(char.isalnum() or char in ".-" for char in preview_host)
        ):
            preview_origin = f"https://{preview_host}"
            if preview_origin not in origins:
                origins.append(preview_origin)
    return origins


CORS_ORIGINS = _parse_cors_origins()
