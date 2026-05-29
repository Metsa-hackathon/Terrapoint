import os

GEOBASE = "https://gsavalik.envir.ee/geoserver"

CACHE_TTL_FULL = 86400
CACHE_TTL_WFS = 21600
CACHE_TTL_PRICES = 604800

TILES_URL = "https://tiles.maaamet.ee/tm/tms/1.0.0/{layer}@GMC/{z}/{x}/{y}.png"

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
