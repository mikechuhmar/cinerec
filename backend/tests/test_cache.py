"""Tests for the recommendation cache backends (in-process + Redis via fakeredis)."""

import fakeredis

from app.recsys.cache import InProcessBackend, RedisBackend


def test_in_process_set_get_clear():
    backend = InProcessBackend()
    backend.set("user:1", {"source": "hybrid", "items": []}, ttl=100)
    assert backend.get("user:1") == {"source": "hybrid", "items": []}
    backend.clear()
    assert backend.get("user:1") is None


def test_in_process_expiry():
    backend = InProcessBackend()
    backend.set("k", {"v": 1}, ttl=-1)  # already expired
    assert backend.get("k") is None


def test_in_process_missing_key():
    assert InProcessBackend().get("nope") is None


def test_redis_backend_roundtrip():
    client = fakeredis.FakeStrictRedis(decode_responses=True)
    backend = RedisBackend(client)
    backend.set("similar:3:content:10:0.5", {"source": "content", "items": [1, 2]}, ttl=100)
    assert backend.get("similar:3:content:10:0.5") == {"source": "content", "items": [1, 2]}


def test_redis_backend_clear_only_namespace():
    client = fakeredis.FakeStrictRedis(decode_responses=True)
    client.set("unrelated", "keep-me")
    backend = RedisBackend(client)
    backend.set("user:1", {"x": 1}, ttl=100)
    backend.clear()
    assert backend.get("user:1") is None
    assert client.get("unrelated") == "keep-me"  # non-namespaced keys untouched
