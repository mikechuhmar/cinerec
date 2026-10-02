"""Seed Russian titles, overviews and posters for popular movies — no API key required.

This applies a small curated fixture (``scripts/localized_demo.json``) of ~60 popular
MovieLens movies, so the UI shows Russian titles and real posters out of the box. The data
was collected from TMDB's public pages (``language=ru-RU``); for the full catalogue use
``scripts.enrich_tmdb`` with a ``CINEREC_TMDB_API_KEY``.

    uv run python -m scripts.seed_localized_demo
"""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Movie

FIXTURE = Path(__file__).resolve().parent / "localized_demo.json"


def run(db: Session) -> None:
    records = json.loads(FIXTURE.read_text(encoding="utf-8"))
    updated = 0
    for rec in records:
        movie = db.get(Movie, rec["id"])
        if movie is None:
            continue
        if rec.get("title_ru"):
            movie.title_ru = rec["title_ru"]
        if rec.get("overview_ru"):
            movie.overview_ru = rec["overview_ru"]
            movie.overview = movie.overview or rec["overview_ru"]
        if rec.get("poster_url"):
            movie.poster_url = rec["poster_url"]
        updated += 1
    db.commit()
    print(f"Seeded localized data for {updated}/{len(records)} movies.")


def main() -> None:
    with SessionLocal() as db:
        run(db)


if __name__ == "__main__":
    main()
