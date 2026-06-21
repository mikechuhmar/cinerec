"""Content-based recommendations using pgvector cosine similarity."""

from __future__ import annotations

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Movie, Rating


def build_movie_text(title: str, year: int | None, genres: list[str], tags: str | None) -> str:
    parts = [title]
    if year:
        parts.append(str(year))
    if genres:
        parts.append(" ".join(genres))
    if tags:
        parts.append(tags)
    return " ".join(parts)


def similar_to_movie(db: Session, movie_id: int, limit: int = 10) -> list[tuple[Movie, float]]:
    """Return movies most similar to the given movie by embedding cosine similarity."""
    target = db.get(Movie, movie_id)
    if target is None or target.embedding is None:
        return []

    distance = Movie.embedding.cosine_distance(target.embedding)
    stmt = (
        select(Movie, distance.label("distance"))
        .where(Movie.id != movie_id)
        .where(Movie.embedding.is_not(None))
        .order_by(distance)
        .limit(limit)
    )
    return [(movie, 1.0 - float(dist)) for movie, dist in db.execute(stmt).all()]


def recommend_for_user_by_taste(
    db: Session, user_id: int, limit: int = 10, like_threshold: float = 4.0
) -> list[tuple[Movie, float]]:
    """Build a taste profile from a user's highly-rated movies and find nearest movies."""
    liked = (
        db.execute(
            select(Movie.embedding, Rating.rating)
            .join(Rating, Rating.movie_id == Movie.id)
            .where(Rating.user_id == user_id)
            .where(Rating.rating >= like_threshold)
            .where(Movie.embedding.is_not(None))
        )
        .all()
    )
    if not liked:
        return []

    vectors = np.array([row[0] for row in liked], dtype=np.float32)
    weights = np.array([row[1] for row in liked], dtype=np.float32).reshape(-1, 1)
    profile = (vectors * weights).sum(axis=0)
    norm = np.linalg.norm(profile)
    if norm == 0:
        return []
    profile = profile / norm

    rated_ids = select(Rating.movie_id).where(Rating.user_id == user_id)
    distance = Movie.embedding.cosine_distance(profile.tolist())
    stmt = (
        select(Movie, distance.label("distance"))
        .where(Movie.embedding.is_not(None))
        .where(Movie.id.not_in(rated_ids))
        .order_by(distance)
        .limit(limit)
    )
    return [(movie, 1.0 - float(dist)) for movie, dist in db.execute(stmt).all()]
