"""Collaborative filtering via implicit ALS, trained from the ratings table.

The fitted model is cached in-memory and refreshed by a background worker thread so that
requests never block on training:

* ``invalidate()`` (called on new ratings) marks the model dirty and signals the worker,
  while the current model keeps serving requests (eventual consistency).
* ``start_retrainer()`` / ``stop_retrainer()`` manage the worker lifecycle (wired into the
  FastAPI lifespan). When background retraining is disabled (e.g. in tests), ``invalidate()``
  resets the model so the next request retrains synchronously, keeping behaviour deterministic.
"""

from __future__ import annotations

import threading
import time

import numpy as np
import scipy.sparse as sp
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Movie, Rating


class _ALSState:
    def __init__(self) -> None:
        self.model = None
        self.user_items = None  # csr: user x item (confidence)
        self.user_index: dict[int, int] = {}
        self.item_index: dict[int, int] = {}
        self.index_item: list[int] = []


_lock = threading.Lock()
_model_state: _ALSState | None = None
_dirty = threading.Event()
_stop = threading.Event()
_thread: threading.Thread | None = None
_last_trained_at: float | None = None


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
    """Return the cached model, training synchronously if none exists yet."""
    global _model_state, _last_trained_at
    if _model_state is not None:
        return _model_state
    with _lock:
        if _model_state is None:
            _model_state = _train(db)
            _last_trained_at = time.time()
        return _model_state


def _set_state(state: _ALSState) -> None:
    global _model_state, _last_trained_at
    with _lock:
        _model_state = state
        _last_trained_at = time.time()


def reset() -> None:
    """Hard reset: drop the model so the next request retrains synchronously."""
    global _model_state, _last_trained_at
    with _lock:
        _model_state = None
        _last_trained_at = None
    _dirty.clear()
    from app.recsys import cache

    cache.clear()


def invalidate() -> None:
    """Mark the model stale after new ratings and clear the recommendation cache."""
    from app.recsys import cache

    cache.clear()
    if get_settings().enable_background_retrain:
        # Keep serving the current model; the worker rebuilds off the request path.
        _dirty.set()
    else:
        reset()


def _retrain_once() -> None:
    from app.db import SessionLocal

    with SessionLocal() as db:
        new_state = _train(db)
    _set_state(new_state)


def _retrain_loop() -> None:
    interval = get_settings().retrain_interval_seconds
    if _model_state is None:
        try:
            _retrain_once()
        except Exception as exc:  # pragma: no cover - defensive
            print(f"[retrain] initial training failed: {exc}")

    while not _stop.is_set():
        triggered = _dirty.wait(timeout=interval)
        if _stop.is_set():
            break
        if triggered or _model_state is None:
            _dirty.clear()
            try:
                _retrain_once()
            except Exception as exc:  # pragma: no cover - defensive
                print(f"[retrain] training failed: {exc}")


def start_retrainer() -> None:
    global _thread
    if not get_settings().enable_background_retrain:
        return
    if _thread is not None and _thread.is_alive():
        return
    _stop.clear()
    _thread = threading.Thread(target=_retrain_loop, name="als-retrainer", daemon=True)
    _thread.start()


def stop_retrainer() -> None:
    global _thread
    _stop.set()
    _dirty.set()
    if _thread is not None:
        _thread.join(timeout=10)
        _thread = None
    _stop.clear()
    _dirty.clear()


def status() -> dict:
    state = _model_state
    return {
        "trained": state is not None and state.model is not None,
        "users": len(state.user_index) if state else 0,
        "items": len(state.item_index) if state else 0,
        "last_trained_at": _last_trained_at,
        "background_retrain": get_settings().enable_background_retrain,
        "dirty": _dirty.is_set(),
    }


def recommend_for_user(
    db: Session, user_id: int, limit: int = 10
) -> list[tuple[Movie, float]]:
    state = get_state(db)
    if state.model is None or user_id not in state.user_index:
        return []

    uidx = state.user_index[user_id]
    # implicit pads the result with filler items when N exceeds the number of
    # recommendable items; cap N so we never request more than are available.
    liked = state.user_items[uidx].nnz
    n = min(limit, max(0, len(state.index_item) - liked))
    if n == 0:
        return []

    ids, scores = state.model.recommend(
        uidx, state.user_items[uidx], N=n, filter_already_liked_items=True
    )
    movie_ids = [state.index_item[i] for i in ids]
    movies = {m.id: m for m in db.execute(select(Movie).where(Movie.id.in_(movie_ids))).scalars()}
    out: list[tuple[Movie, float]] = []
    seen: set[int] = set()
    for i, score in zip(ids, scores, strict=True):
        if not np.isfinite(score):
            continue
        mid = state.index_item[i]
        if mid in seen:
            continue
        movie = movies.get(mid)
        if movie is not None:
            seen.add(mid)
            out.append((movie, float(score)))
    return out


def similar_items(db: Session, movie_id: int, limit: int = 10) -> list[tuple[Movie, float]]:
    state = get_state(db)
    if state.model is None or movie_id not in state.item_index:
        return []

    iidx = state.item_index[movie_id]
    n = min(limit + 1, len(state.index_item))
    ids, scores = state.model.similar_items(iidx, N=n)
    movie_ids = [state.index_item[i] for i in ids]
    movies = {m.id: m for m in db.execute(select(Movie).where(Movie.id.in_(movie_ids))).scalars()}
    out: list[tuple[Movie, float]] = []
    seen: set[int] = set()
    for i, score in zip(ids, scores, strict=True):
        if not np.isfinite(score):
            continue
        mid = state.index_item[i]
        if mid == movie_id or mid in seen:
            continue
        movie = movies.get(mid)
        if movie is not None:
            seen.add(mid)
            out.append((movie, float(score)))
    return out[:limit]
