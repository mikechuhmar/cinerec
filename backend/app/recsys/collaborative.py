"""Collaborative filtering via implicit ALS, trained from the ratings table.

The model is trained lazily and cached in-memory. Call ``invalidate()`` after
ingesting new ratings to force a retrain on the next request.
"""

from __future__ import annotations

import threading

import scipy.sparse as sp
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Movie, Rating

_lock = threading.Lock()
_model_state: _ALSState | None = None


class _ALSState:
    def __init__(self) -> None:
        self.model = None
        self.user_items = None  # csr: user x item (confidence)
        self.user_index: dict[int, int] = {}
        self.item_index: dict[int, int] = {}
        self.index_item: list[int] = []


def _train(db: Session) -> _ALSState:
    from implicit.als import AlternatingLeastSquares

    settings = get_settings()
    rows = db.execute(select(Rating.user_id, Rating.movie_id, Rating.rating)).all()

    state = _ALSState()
    if not rows:
        return state

    user_ids = sorted({r[0] for r in rows})
    item_ids = sorted({r[1] for r in rows})
    state.user_index = {uid: i for i, uid in enumerate(user_ids)}
    state.item_index = {iid: i for i, iid in enumerate(item_ids)}
    state.index_item = item_ids

    rows_idx = [state.user_index[r[0]] for r in rows]
    cols_idx = [state.item_index[r[1]] for r in rows]
    # Treat ratings as confidence weights (implicit-feedback style).
    data = [float(r[2]) for r in rows]
    user_items = sp.csr_matrix(
        (data, (rows_idx, cols_idx)), shape=(len(user_ids), len(item_ids))
    )

    model = AlternatingLeastSquares(
        factors=settings.als_factors,
        iterations=settings.als_iterations,
        regularization=settings.als_regularization,
        random_state=42,
    )
    model.fit(user_items, show_progress=False)

    state.model = model
    state.user_items = user_items
    return state


def get_state(db: Session) -> _ALSState:
    global _model_state
    with _lock:
        if _model_state is None:
            _model_state = _train(db)
        return _model_state


def invalidate() -> None:
    global _model_state
    with _lock:
        _model_state = None


def recommend_for_user(
    db: Session, user_id: int, limit: int = 10
) -> list[tuple[Movie, float]]:
    state = get_state(db)
    if state.model is None or user_id not in state.user_index:
        return []

    uidx = state.user_index[user_id]
    ids, scores = state.model.recommend(
        uidx, state.user_items[uidx], N=limit, filter_already_liked_items=True
    )
    movie_ids = [state.index_item[i] for i in ids]
    movies = {m.id: m for m in db.execute(select(Movie).where(Movie.id.in_(movie_ids))).scalars()}
    out: list[tuple[Movie, float]] = []
    for i, score in zip(ids, scores, strict=True):
        movie = movies.get(state.index_item[i])
        if movie is not None:
            out.append((movie, float(score)))
    return out


def similar_items(db: Session, movie_id: int, limit: int = 10) -> list[tuple[Movie, float]]:
    state = get_state(db)
    if state.model is None or movie_id not in state.item_index:
        return []

    iidx = state.item_index[movie_id]
    ids, scores = state.model.similar_items(iidx, N=limit + 1)
    movie_ids = [state.index_item[i] for i in ids]
    movies = {m.id: m for m in db.execute(select(Movie).where(Movie.id.in_(movie_ids))).scalars()}
    out: list[tuple[Movie, float]] = []
    for i, score in zip(ids, scores, strict=True):
        mid = state.index_item[i]
        if mid == movie_id:
            continue
        movie = movies.get(mid)
        if movie is not None:
            out.append((movie, float(score)))
    return out[:limit]
