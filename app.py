"""Terrapoint FastAPI entrypoint for Vercel.

Verceli fastapi runtime eeldab, et juurikaustas on app.py või main.py,
mis ekspordib ASGI rakenduse nimega 'app'.
"""
from api.index import app  # noqa: F401 -- ASGI entrypoint re-export
