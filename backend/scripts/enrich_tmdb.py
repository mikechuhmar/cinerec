"""Enrich movies with posters, overviews and Russian titles/overviews from TMDB.

Requires a TMDB API key via ``CINEREC_TMDB_API_KEY``. Without a key the script exits
gracefully (the rest of the system works fine without posters/overviews). To populate a
handful of popular movies with Russian titles + posters *without* a key, use the offline
fixture instead: ``uv run python -m scripts.seed_localized_demo``.

    CINEREC_TMDB_API_KEY=xxx uv run python -m scripts.enrich_tmdb --limit 200

Each movie needs up to two requests: ``language=en-US`` (English overview, used for the
content embeddings) and ``language=ru-RU`` (Russian title/overview shown in the UI). The
poster is language-agnostic; TMDB returns a localized one when available.

After enriching, rebuild embeddings so overviews contribute to content similarity:
    uv run python -m scripts.build_embeddings
"""

from __future__ import annotations

import argparse
import time

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import SessionLocal
from app.models import Movie

TMDB_URL = "https://api.themoviedb.org/3/movie/{tmdb_id}"
IMAGE_BASE = "https://image.tmdb.org/t/p/w500"


def _fetch(client: httpx.Client, api_key: str, tmdb_id: int, language: str) -> dict | None:
    resp = client.get(
        TMDB_URL.format(tmdb_id=tmdb_id),
        params={"api_key": api_key, "language": language},
    )
    return resp.json() if resp.status_code == 200 else None


def enrich_one(client: httpx.Client, api_key: str, movie: Movie) -> bool:
    en = _fetch(client, api_key, movie.tmdb_id, "en-US")
    if en is None:
        return False
    movie.overview = en.get("overview") or movie.overview
    poster_path = en.get("poster_path")

    ru = _fetch(client, api_key, movie.tmdb_id, "ru-RU")
    if ru is not None:
        # TMDB returns the English title in ``title`` when no localized title exists; only
        # keep a Russian title that actually differs from the original.
        ru_title = ru.get("title")
        if ru_title and ru_title != en.get("title"):
            movie.title_ru = ru_title
        movie.overview_ru = ru.get("overview") or movie.overview_ru
        poster_path = ru.get("poster_path") or poster_path

    if poster_path:
        movie.poster_url = f"{IMAGE_BASE}{poster_path}"
    return True


def run(db: Session, api_key: str, limit: int | None, overwrite: bool) -> None:
    stmt = select(Movie).where(Movie.tmdb_id.is_not(None))
    if not overwrite:
        stmt = stmt.where(Movie.poster_url.is_(None))
    if limit:
        stmt = stmt.limit(limit)
    movies = list(db.execute(stmt).scalars())
    print(f"Enriching {len(movies)} movies from TMDB ...")

    enriched = 0
    with httpx.Client(timeout=30) as client:
        for i, movie in enumerate(movies, 1):
            try:
                if enrich_one(client, api_key, movie):
                    enriched += 1
            except httpx.HTTPError as exc:  # noqa: PERF203
                print(f"  warn: {movie.id} failed: {exc}")
            if i % 50 == 0:
                db.commit()
                print(f"  {i}/{len(movies)} (enriched={enriched})")
            time.sleep(0.05)  # be gentle with the API
    db.commit()
    print(f"Done. Enriched {enriched}/{len(movies)} movies.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Enrich movies with TMDB metadata")
    parser.add_argument("--limit", type=int, default=None, help="Max movies to enrich")
    parser.add_argument(
        "--overwrite", action="store_true", help="Re-enrich movies that already have a poster"
    )
    args = parser.parse_args()

    api_key = get_settings().tmdb_api_key
    if not api_key:
        print(
            "CINEREC_TMDB_API_KEY is not set. Skipping TMDB enrichment.\n"
            "Set it (e.g. in backend/.env) to fetch posters and overviews."
        )
        return

    with SessionLocal() as db:
        run(db, api_key, args.limit, args.overwrite)


if __name__ == "__main__":
    main()
