"""Hybrid recommendations: a weighted blend of content-based and collaborative scores.

Each source produces scores on a different scale, so scores are min-max normalised to
``[0, 1]`` within each source before blending:

    hybrid = alpha * collaborative + (1 - alpha) * content

A larger candidate pool is pulled from each source so items that only one source knows
about can still surface (this mitigates cold-start for new movies/users).
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Movie
from app.recsys import collaborative, content


def _normalize(scored: list[tuple[Movie, float]]) -> dict[int, tuple[Movie, float]]:
    if not scored:
        return {}
    values = [s for _, s in scored]
    lo, hi = min(values), max(values)
    span = hi - lo
    out: dict[int, tuple[Movie, float]] = {}
    for movie, score in scored:
        norm = (score - lo) / span if span > 0 else 1.0
        out[movie.id] = (movie, norm)
    return out


def _blend(
    content_scored: list[tuple[Movie, float]],
    cf_scored: list[tuple[Movie, float]],
    alpha: float,
    limit: int,
) -> list[tuple[Movie, float]]:
    content_norm = _normalize(content_scored)
    cf_norm = _normalize(cf_scored)

    movies: dict[int, Movie] = {}
    for mid, (movie, _) in {**content_norm, **cf_norm}.items():
        movies[mid] = movie

    blended: list[tuple[Movie, float]] = []
    for mid, movie in movies.items():
        c = content_norm.get(mid, (None, 0.0))[1]
        f = cf_norm.get(mid, (None, 0.0))[1]
        score = alpha * f + (1.0 - alpha) * c
        blended.append((movie, score))

    blended.sort(key=lambda x: x[1], reverse=True)
    return blended[:limit]


def recommend_for_user(
    db: Session, user_id: int, limit: int = 10, alpha: float = 0.5
) -> list[tuple[Movie, float]]:
    pool = max(limit * 3, 30)
    content_scored = content.recommend_for_user_by_taste(db, user_id, limit=pool)
    cf_scored = collaborative.recommend_for_user(db, user_id, limit=pool)
    return _blend(content_scored, cf_scored, alpha, limit)


def similar_to_movie(
    db: Session, movie_id: int, limit: int = 10, alpha: float = 0.5
) -> list[tuple[Movie, float]]:
    pool = max(limit * 3, 30)
    content_scored = content.similar_to_movie(db, movie_id, limit=pool)
    cf_scored = collaborative.similar_items(db, movie_id, limit=pool)
    return _blend(content_scored, cf_scored, alpha, limit)
