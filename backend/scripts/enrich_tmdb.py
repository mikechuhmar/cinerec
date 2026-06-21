"""Enrich movies with posters and overviews from TMDB.

Requires a TMDB API key via ``CINEREC_TMDB_API_KEY``. Without a key the script exits
gracefully (the rest of the system works fine without posters/overviews).

    CINEREC_TMDB_API_KEY=xxx uv run python -m scripts.enrich_tmdb --limit 200

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


def enrich_one(client: httpx.Client, api_key: str, movie: Movie) -> bool:
    resp = client.get(
        TMDB_URL.format(tmdb_id=movie.tmdb_id),
        params={"api_key": api_key, "language": "en-US"},
    )
    if resp.status_code != 200:
        return False
    data = resp.json()
    movie.overview = data.get("overview") or movie.overview
    poster_path = data.get("poster_path")
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
