"""Unit tests for the TMDB enrichment logic (no network — the fetch is stubbed)."""

from __future__ import annotations

from app.models import Movie
from scripts import enrich_tmdb


def _stub_fetch(responses: dict[str, dict | None]):
    def _fetch(client, api_key, tmdb_id, language):  # noqa: ANN001, ARG001
        return responses.get(language)

    return _fetch


def test_enrich_populates_russian_fields(monkeypatch):
    monkeypatch.setattr(
        enrich_tmdb,
        "_fetch",
        _stub_fetch(
            {
                "en-US": {
                    "title": "The Matrix",
                    "overview": "A hacker learns the truth.",
                    "poster_path": "/en.jpg",
                },
                "ru-RU": {
                    "title": "Матрица",
                    "overview": "Хакер узнаёт правду.",
                    "poster_path": "/ru.jpg",
                },
            }
        ),
    )
    movie = Movie(id=1, title="The Matrix", tmdb_id=603)
    assert enrich_tmdb.enrich_one(client=None, api_key="x", movie=movie) is True
    assert movie.title_ru == "Матрица"
    assert movie.overview == "A hacker learns the truth."
    assert movie.overview_ru == "Хакер узнаёт правду."
    # Russian poster is preferred when present.
    assert movie.poster_url.endswith("/ru.jpg")


def test_enrich_keeps_title_ru_empty_when_not_localized(monkeypatch):
    # TMDB echoes the English title in ``ru-RU`` when no localized title exists.
    monkeypatch.setattr(
        enrich_tmdb,
        "_fetch",
        _stub_fetch(
            {
                "en-US": {"title": "Obscure Film", "overview": "En.", "poster_path": "/p.jpg"},
                "ru-RU": {"title": "Obscure Film", "overview": "", "poster_path": None},
            }
        ),
    )
    movie = Movie(id=2, title="Obscure Film", tmdb_id=999)
    assert enrich_tmdb.enrich_one(client=None, api_key="x", movie=movie) is True
    assert movie.title_ru is None
    assert movie.poster_url.endswith("/p.jpg")


def test_enrich_returns_false_when_movie_missing(monkeypatch):
    monkeypatch.setattr(enrich_tmdb, "_fetch", _stub_fetch({"en-US": None, "ru-RU": None}))
    movie = Movie(id=3, title="Gone", tmdb_id=123)
    assert enrich_tmdb.enrich_one(client=None, api_key="x", movie=movie) is False
