"""A tiny thread-safe in-process TTL cache for recommendation responses.

Avoids an external dependency (e.g. Redis) while still skipping repeated expensive
similarity / ALS lookups. The cache is cleared whenever new ratings invalidate the
collaborative model (see ``collaborative.invalidate``).
"""

from __future__ import annotations

import threading
import time
from typing import Any

_lock = threading.Lock()
_store: dict[str, tuple[float, Any]] = {}
_DEFAULT_TTL = 300.0  # seconds


def get(key: str) -> Any | None:
    now = time.monotonic()
    with _lock:
        entry = _store.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if expires_at < now:
            _store.pop(key, None)
            return None
        return value


def set(key: str, value: Any, ttl: float = _DEFAULT_TTL) -> None:
    with _lock:
        _store[key] = (time.monotonic() + ttl, value)


def clear() -> None:
    with _lock:
        _store.clear()
