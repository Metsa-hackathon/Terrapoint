"""Ühised pytest-fixture'id kogu testide jaoks.

Vahemälud (otsingutulemus, allikate vahemälu, WFS-i vahemälu) on
protsessiglobaalsed ja elavad kogu testiseansi jooksul. Ilma
puhastuseta võiks ühe testi puhverdatud vastus sattuda teise testi
sisse — eriti kuna kõik testifailid kasutavad sama katastritunnust
("78404:409:0113") ja puhverduse võtmed põhinevad sellel.
"""

import pytest

from api import cache as api_cache
from api import index as api


@pytest.fixture(autouse=True)
def _clear_api_caches():
    """Tühjenda API vahemälud enne ja pärast iga testi."""

    def _clear():
        api_cache.search_cache.clear()
        api_cache.search_source_cache.clear()
        api_cache.wfs_cache.clear()
        api_cache.satellite_cache.clear()
        api._search_in_flight.clear()
        api._search_waiters.clear()

    _clear()
    yield
    _clear()
