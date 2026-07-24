"""Recommendation response cache with a Redis backend and in-process fallback.

If ``settings.redis_url`` is set and reachable, recommendation responses are cached in
Redis (shared across processes/workers). Otherwise the service transparently falls back to
a thread-safe in-process TTL cache, so it always works even without Redis.

Values are JSON-serialisable dicts (``RecommendationResponse.model_dump()``); ``get`` returns
the dict (or ``None``). The cache is cleared via ``clear()`` when new ratings invalidate the
collaborative model.
"""

from __future__ import annotations

import json
import threading
import time
from typing import Any, Protocol

from app.config import get_settings

_KEY_PREFIX = "cinerec:rec:"


class _Backend(Protocol):
    name: str

    def get(self, key: str) -> Any | None: ...
    def set(self, key: str, value: Any, ttl: int) -> None: ...
    def clear(self) -> None: ...


class InProcessBackend:
    name = "in-process"

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        now = time.monotonic()
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            expires_at, value = entry
            if expires_at < now:
                self._store.pop(key, None)
                return None
            return value

    def set(self, key: str, value: Any, ttl: int) -> None:
        with self._lock:
            self._store[key] = (time.monotonic() + ttl, value)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()


class RedisBackend:
    name = "redis"

    def __init__(self, client: Any) -> None:
        self._client = client

    def get(self, key: str) -> Any | None:
        raw = self._client.get(_KEY_PREFIX + key)
        return json.loads(raw) if raw is not None else None

    def set(self, key: str, value: Any, ttl: int) -> None:
        self._client.set(_KEY_PREFIX + key, json.dumps(value), ex=ttl)

    def clear(self) -> None:
        # Only drop our namespace, never the whole Redis instance.
        keys = list(self._client.scan_iter(match=_KEY_PREFIX + "*"))
        if keys:
            self._client.delete(*keys)


def _build_backend() -> _Backend:
    settings = get_settings()
    if settings.redis_url:
        try:
            import redis

            client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
            client.ping()
            return RedisBackend(client)
        except Exception as exc:  # pragma: no cover - depends on runtime env
            print(f"[cache] Redis unavailable ({exc}); falling back to in-process cache.")
    return InProcessBackend()


_backend: _Backend = _build_backend()


def backend_name() -> str:
    return _backend.name


def get(key: str) -> Any | None:
    try:
        return _backend.get(key)
    except Exception as exc:  # pragma: no cover - defensive against transient Redis errors
        print(f"[cache] get failed ({exc}); ignoring cache.")
        return None


def set(key: str, value: Any, ttl: int | None = None) -> None:
    ttl = ttl if ttl is not None else get_settings().cache_ttl_seconds
    try:
        _backend.set(key, value, ttl)
    except Exception as exc:  # pragma: no cover
        print(f"[cache] set failed ({exc}); skipping cache write.")


def clear() -> None:
    try:
        _backend.clear()
    except Exception as exc:  # pragma: no cover
        print(f"[cache] clear failed ({exc}).")
