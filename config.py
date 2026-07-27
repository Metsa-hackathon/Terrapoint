import os

GEOBASE = "https://gsavalik.envir.ee/geoserver"

CACHE_TTL_FULL = 86400
CACHE_TTL_WFS = 21600
CACHE_TTL_PRICES = 604800

DEFAULT_CORS_ORIGINS = [
    "https://terrapoint.ee",
    "https://www.terrapoint.ee",
    "https://terrapoint.vercel.app",
    "http://localhost:8099",
    "http://127.0.0.1:8099",
]

DEFAULT_TRUSTED_HOSTS = [
    "terrapoint.ee",
    "www.terrapoint.ee",
    "terrapoint.vercel.app",
    "*.vercel.app",
    "terrapoint.arleserver.cfd",
    "localhost",
    "127.0.0.1",
    "172.20.0.1",
    "testserver",
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


def _parse_trusted_hosts() -> list[str]:
    raw = os.getenv("TRUSTED_HOSTS", "")
    hosts = [host.strip().lower().rstrip(".") for host in raw.split(",") if host.strip()]
    valid_hosts = [
        host
        for host in hosts
        if host != "*"
        and not any(char.isspace() for char in host)
        and all(char.isalnum() or char in ".-*" for char in host)
        and ("*" not in host or (host.startswith("*.") and host.count("*") == 1))
    ]
    return valid_hosts or list(DEFAULT_TRUSTED_HOSTS)


CORS_ORIGINS = _parse_cors_origins()
TRUSTED_HOSTS = _parse_trusted_hosts()
