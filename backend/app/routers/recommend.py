from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_db
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


@router.get("/similar/{movie_id}", response_model=RecommendationResponse)
def similar_movies(
    movie_id: int,
    limit: int = Query(10, ge=1, le=50),
    method: str = Query("content", pattern=SIMILAR_METHODS),
    alpha: float = Query(0.5, ge=0.0, le=1.0, description="Hybrid blend weight (CF share)"),
    db: Session = Depends(get_db),
) -> RecommendationResponse:
    if db.get(Movie, movie_id) is None:
        raise HTTPException(status_code=404, detail="Movie not found")

    cache_key = f"similar:{movie_id}:{method}:{limit}:{alpha}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    if method == "collaborative":
        resp = _to_response("collaborative", collaborative.similar_items(db, movie_id, limit))
    elif method == "hybrid":
        resp = _to_response("hybrid", hybrid.similar_to_movie(db, movie_id, limit, alpha))
    else:
        resp = _to_response("content", content.similar_to_movie(db, movie_id, limit))

    cache.set(cache_key, resp)
    return resp


@router.get("/user/{user_id}", response_model=RecommendationResponse)
def recommend_for_user(
    user_id: int,
    limit: int = Query(10, ge=1, le=50),
    method: str = Query("hybrid", pattern=USER_METHODS),
    alpha: float = Query(0.5, ge=0.0, le=1.0, description="Hybrid blend weight (CF share)"),
    db: Session = Depends(get_db),
) -> RecommendationResponse:
    cache_key = f"user:{user_id}:{method}:{limit}:{alpha}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    if method == "content":
        resp = _to_response("content", content.recommend_for_user_by_taste(db, user_id, limit))
    elif method == "hybrid":
        resp = _to_response("hybrid", hybrid.recommend_for_user(db, user_id, limit, alpha))
    else:
        resp = _to_response("collaborative", collaborative.recommend_for_user(db, user_id, limit))

    cache.set(cache_key, resp)
    return resp
