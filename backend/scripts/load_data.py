"""Download the MovieLens dataset and load it into PostgreSQL.

Usage:
    uv run python -m scripts.load_data            # ml-latest-small (default)
    uv run python -m scripts.load_data --ratings-limit 20000

The dataset is fetched from grouplens.org and cached under ``data/``.
"""

from __future__ import annotations

import argparse
import io
import re
import zipfile
from pathlib import Path

import httpx
import pandas as pd
from sqlalchemy import delete, text

from app.db import Base, SessionLocal, engine
from app.models import Movie, Rating

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATASETS = {
    "ml-latest-small": "https://files.grouplens.org/datasets/movielens/ml-latest-small.zip",
    "ml-25m": "https://files.grouplens.org/datasets/movielens/ml-25m.zip",
}
YEAR_RE = re.compile(r"\((\d{4})\)\s*$")


def download_dataset(name: str) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    target = DATA_DIR / name
    if target.exists():
        print(f"Using cached dataset at {target}")
        return target

    url = DATASETS[name]
    print(f"Downloading {url} ...")
    with httpx.Client(timeout=120, follow_redirects=True) as client:
        resp = client.get(url)
        resp.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        zf.extractall(DATA_DIR)
    print(f"Extracted to {target}")
    return target


def parse_year(title: str) -> tuple[str, int | None]:
    match = YEAR_RE.search(title.strip())
    if match:
        year = int(match.group(1))
        clean = YEAR_RE.sub("", title).strip()
        return clean, year
    return title.strip(), None


def load(name: str, ratings_limit: int | None) -> None:
    path = download_dataset(name)

    movies_df = pd.read_csv(path / "movies.csv")
    ratings_df = pd.read_csv(path / "ratings.csv")
    links_path = path / "links.csv"
    tags_path = path / "tags.csv"
    links_df = pd.read_csv(links_path) if links_path.exists() else None
    tags_df = pd.read_csv(tags_path) if tags_path.exists() else None

    if ratings_limit:
        ratings_df = ratings_df.head(ratings_limit)
        keep_ids = set(ratings_df["movieId"]).union(set(movies_df["movieId"]))
        movies_df = movies_df[movies_df["movieId"].isin(keep_ids)]

    tags_by_movie: dict[int, str] = {}
    if tags_df is not None:
        grouped = tags_df.groupby("movieId")["tag"].apply(
            lambda s: " ".join(sorted({str(t) for t in s})[:30])
        )
        tags_by_movie = grouped.to_dict()

    links_by_movie: dict[int, tuple[str | None, int | None]] = {}
    if links_df is not None:
        for _, row in links_df.iterrows():
            imdb = f"tt{int(row['imdbId']):07d}" if pd.notna(row["imdbId"]) else None
            tmdb = int(row["tmdbId"]) if pd.notna(row["tmdbId"]) else None
            links_by_movie[int(row["movieId"])] = (imdb, tmdb)

    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        print("Clearing existing data ...")
        db.execute(delete(Rating))
        db.execute(delete(Movie))
        db.commit()

        print(f"Inserting {len(movies_df)} movies ...")
        movie_rows = []
        for _, row in movies_df.iterrows():
            title, year = parse_year(str(row["title"]))
            raw_genres = str(row["genres"])
            genres = [] if raw_genres == "(no genres listed)" else raw_genres.split("|")
            imdb_id, tmdb_id = links_by_movie.get(int(row["movieId"]), (None, None))
            movie_rows.append(
                {
                    "id": int(row["movieId"]),
                    "title": title,
                    "year": year,
                    "genres": genres,
                    "tags": tags_by_movie.get(int(row["movieId"])),
                    "imdb_id": imdb_id,
                    "tmdb_id": tmdb_id,
                }
            )
        db.bulk_insert_mappings(Movie, movie_rows)
        db.commit()

        print(f"Inserting {len(ratings_df)} ratings ...")
        rating_rows = [
            {
                "user_id": int(r.userId),
                "movie_id": int(r.movieId),
                "rating": float(r.rating),
            }
            for r in ratings_df.itertuples()
        ]
        db.bulk_insert_mappings(Rating, rating_rows)
        db.commit()

    # Refresh table statistics for the planner.
    with engine.begin() as conn:
        conn.execute(text("ANALYZE movies"))
        conn.execute(text("ANALYZE ratings"))
    print("Done loading data.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Load MovieLens data into PostgreSQL")
    parser.add_argument("--dataset", choices=list(DATASETS), default="ml-latest-small")
    parser.add_argument(
        "--ratings-limit", type=int, default=None, help="Cap number of ratings (for speed)"
    )
    args = parser.parse_args()
    load(args.dataset, args.ratings_limit)


if __name__ == "__main__":
    main()
