"""
Terrapoint — In-memory TTL Cache
"""
from __future__ import annotations
import time
import threading


class TTLCache:
    """Thread-safe in-memory cache with TTL per key."""

    def __init__(self, default_ttl: int = 300, max_entries: int = 512):
        if max_entries < 1:
            raise ValueError("max_entries must be positive")
        self._data: dict[str, tuple[float, object]] = {}
        self._default_ttl = default_ttl
        self._max_entries = max_entries
        self._lock = threading.Lock()

    def get(self, key: str) -> object | None:
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                return None
            expires_at, value = entry
            if time.monotonic() > expires_at:
                del self._data[key]
                return None
            return value

    def set(self, key: str, value: object, ttl: int | None = None) -> None:
        expires_at = time.monotonic() + (ttl if ttl is not None else self._default_ttl)
        with self._lock:
            # Refreshing an existing key must not evict an unrelated entry.
            # Reinsert it so the insertion-ordered dict keeps FIFO eviction fair.
            self._data.pop(key, None)
            while len(self._data) >= self._max_entries:
                self._data.pop(next(iter(self._data)))
            self._data[key] = (expires_at, value)

    def make_key(self, *parts: str) -> str:
        return ":".join(str(p) for p in parts)

    def invalidate(self, prefix: str) -> int:
        """Remove all keys starting with prefix. Returns count removed."""
        removed = 0
        with self._lock:
            keys = list(self._data.keys())
            for k in keys:
                if k.startswith(prefix):
                    del self._data[k]
                    removed += 1
        return removed

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._data)


# Singleton instances
wfs_cache = TTLCache(default_ttl=7200, max_entries=512)    # 2h for WFS queries
search_cache = TTLCache(default_ttl=300, max_entries=256)  # 5min for search results
