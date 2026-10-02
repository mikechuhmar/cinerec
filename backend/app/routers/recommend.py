"""Recommendation endpoints.

The request handlers are ``async``, but the actual scoring (pgvector similarity queries
feeding the ALS/hybrid blenders) is CPU-bound and uses the sync recsys layer, so it is
offloaded to a worker thread via ``run_in_threadpool`` to keep the event loop responsive.
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.concurrency import run_in_threadpool

from app.db import SessionLocal
from app.models import Movie
from app.recsys import cache, collaborative, content, hybrid
from app.schemas import RecommendationResponse, ScoredMovie

router = APIRouter(prefix="/recommend", tags=["recommend"])

SIMILAR_METHODS = "^(content|collaborative|hybrid)$"
USER_METHODS = "^(collaborative|content|hybrid)$"


def _to_response(source: str, scored: list[tuple[Movie, float]]) -> RecommendationResponse:
    items = [
        ScoredMovie(
            id=m.id,
            title=m.title,
            year=m.year,
            genres=m.genres,
            poster_url=m.poster_url,
            score=round(score, 4),
        )
        for m, score in scored
    ]
    return RecommendationResponse(source=source, items=items)


def _compute_similar(
    movie_id: int, method: str, limit: int, alpha: float
) -> RecommendationResponse:
    with SessionLocal() as db:
        if db.get(Movie, movie_id) is None:
            raise HTTPException(status_code=404, detail="Movie not found")
        if method == "collaborative":
            return _to_response("collaborative", collaborative.similar_items(db, movie_id, limit))
        if method == "hybrid":
            return _to_response("hybrid", hybrid.similar_to_movie(db, movie_id, limit, alpha))
        return _to_response("content", content.similar_to_movie(db, movie_id, limit))


def _compute_user(user_id: int, method: str, limit: int, alpha: float) -> RecommendationResponse:
    with SessionLocal() as db:
        if method == "content":
            return _to_response("content", content.recommend_for_user_by_taste(db, user_id, limit))
        if method == "hybrid":
            return _to_response("hybrid", hybrid.recommend_for_user(db, user_id, limit, alpha))
        return _to_response("collaborative", collaborative.recommend_for_user(db, user_id, limit))


@router.get("/similar/{movie_id}", response_model=RecommendationResponse)
async def similar_movies(
    movie_id: int,
    limit: int = Query(10, ge=1, le=50),
    method: str = Query("content", pattern=SIMILAR_METHODS),
    alpha: float = Query(0.5, ge=0.0, le=1.0, description="Hybrid blend weight (CF share)"),
) -> RecommendationResponse:
    cache_key = f"similar:{movie_id}:{method}:{limit}:{alpha}"
    cached = cache.get(cache_key)
    if cached is not None:
        _count_cache("similar", hit=True)
        return RecommendationResponse.model_validate(cached)

    _count_cache("similar", hit=False)
    resp = await run_in_threadpool(_compute_similar, movie_id, method, limit, alpha)
    cache.set(cache_key, resp.model_dump())
    return resp


@router.get("/user/{user_id}", response_model=RecommendationResponse)
async def recommend_for_user(
    user_id: int,
    limit: int = Query(10, ge=1, le=50),
    method: str = Query("hybrid", pattern=USER_METHODS),
    alpha: float = Query(0.5, ge=0.0, le=1.0, description="Hybrid blend weight (CF share)"),
) -> RecommendationResponse:
    cache_key = f"user:{user_id}:{method}:{limit}:{alpha}"
    cached = cache.get(cache_key)
    if cached is not None:
        _count_cache("user", hit=True)
        return RecommendationResponse.model_validate(cached)

    _count_cache("user", hit=False)
    resp = await run_in_threadpool(_compute_user, user_id, method, limit, alpha)
    cache.set(cache_key, resp.model_dump())
    return resp


def _count_cache(endpoint: str, hit: bool) -> None:
    try:
        from app.observability import CACHE_HITS, CACHE_MISSES

        (CACHE_HITS if hit else CACHE_MISSES).labels(endpoint=endpoint).inc()
    except Exception:  # pragma: no cover - metrics optional
        pass
