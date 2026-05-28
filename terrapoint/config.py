import os
from dotenv import load_dotenv

load_dotenv()

# Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Cache TTLs (seconds)
CACHE_TTL_FULL = int(os.getenv("CACHE_TTL_FULL", "86400"))      # 24h
CACHE_TTL_WFS = int(os.getenv("CACHE_TTL_WFS", "21600"))        # 6h
CACHE_TTL_PRICES = int(os.getenv("CACHE_TTL_PRICES", "604800")) # 7d

# GeoServer
GEOBASE = "https://gsavalik.envir.ee/geoserver"
WFS_BASE = f"{GEOBASE}/wfs"

# REST APIs
CADASTRE_PUBLIC = "https://cadastrepublic.kataster.ee/api/xroad/valid"
HINDAMINE_API = "https://hindamine.kataster.ee/api/x-road/mkhis-detailed"
KOLVIKUD_API = "https://kolvikud.kataster.ee/api/cadastre-unit/find"

# Tiles
TILES_URL = "https://tiles.maaamet.ee/tm/tms/1.0.0/{layer}@GMC/{z}/{x}/{y}.png"

# CORS
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

# OpenRouter
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/owl-alpha")
