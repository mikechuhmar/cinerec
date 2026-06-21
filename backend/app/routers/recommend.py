from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Movie
from app.recsys import collaborative, content
from app.schemas import RecommendationResponse, ScoredMovie

router = APIRouter(prefix="/recommend", tags=["recommend"])


def _to_response(source: str, scored: list[tuple[Movie, float]]) -> RecommendationResponse:
    items = [
        ScoredMovie(
            id=m.id, title=m.title, year=m.year, genres=m.genres, score=round(score, 4)
        )
        for m, score in scored
    ]
    return RecommendationResponse(source=source, items=items)


@router.get("/similar/{movie_id}", response_model=RecommendationResponse)
def similar_movies(
    movie_id: int,
    limit: int = Query(10, ge=1, le=50),
    method: str = Query("content", pattern="^(content|collaborative)$"),
    db: Session = Depends(get_db),
) -> RecommendationResponse:
    if db.get(Movie, movie_id) is None:
        raise HTTPException(status_code=404, detail="Movie not found")

    if method == "collaborative":
        return _to_response("collaborative", collaborative.similar_items(db, movie_id, limit))
    return _to_response("content", content.similar_to_movie(db, movie_id, limit))


@router.get("/user/{user_id}", response_model=RecommendationResponse)
def recommend_for_user(
    user_id: int,
    limit: int = Query(10, ge=1, le=50),
    method: str = Query("collaborative", pattern="^(content|collaborative)$"),
    db: Session = Depends(get_db),
) -> RecommendationResponse:
    if method == "content":
        return _to_response("content", content.recommend_for_user_by_taste(db, user_id, limit))
    return _to_response("collaborative", collaborative.recommend_for_user(db, user_id, limit))
