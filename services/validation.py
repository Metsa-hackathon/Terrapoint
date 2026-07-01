"""Jagatud sisendi valideerimise abilised."""
from __future__ import annotations
import re
from fastapi import HTTPException

# Eesti katastritunnuse formaat: 1-5 numbrit, 1-4 numbrit, 1-5 numbrit,
# valikuliselt 4. grupp 1-4 numbrit (nt "78404:409:0113" või "78404:409:0113:0001").
KATASTER_RE = re.compile(r'^\d{1,5}:\d{1,4}:\d{1,5}(:\d{1,4})?$')


def _validate_kataster_nr_or_400(kataster_nr: str) -> str:
    """Kinnita, et katastritunnus vastab formaadile. Vastasel korral 400.

    Kasutame nii Vercel→VPS proxy's kui ka otse-päringutes, et vältida
    path-traversal SSRF-i (nt '/api/search/../api/chat').
    """
    if not kataster_nr or not KATASTER_RE.match(kataster_nr):
        raise HTTPException(status_code=400, detail="Vigane katastritunnus")
    return kataster_nr
