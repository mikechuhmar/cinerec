from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Movie, Rating
from app.schemas import MovieBase, MovieDetail

router = APIRouter(prefix="/movies", tags=["movies"])


@router.get("", response_model=list[MovieBase])
def list_movies(
    q: str | None = Query(None, description="Case-insensitive title search"),
    genre: str | None = Query(None, description="Filter by genre"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> list[Movie]:
    stmt = select(Movie)
    if q:
        stmt = stmt.where(Movie.title.ilike(f"%{q}%"))
    if genre:
        stmt = stmt.where(Movie.genres.any(genre))
    stmt = stmt.order_by(Movie.title).limit(limit).offset(offset)
    return list(db.execute(stmt).scalars())


@router.get("/{movie_id}", response_model=MovieDetail)
def get_movie(movie_id: int, db: Session = Depends(get_db)) -> MovieDetail:
    movie = db.get(Movie, movie_id)
    if movie is None:
        raise HTTPException(status_code=404, detail="Movie not found")

    stats = db.execute(
        select(func.avg(Rating.rating), func.count(Rating.id)).where(Rating.movie_id == movie_id)
    ).one()
    avg_rating, num_ratings = stats
    return MovieDetail(
        id=movie.id,
        title=movie.title,
        year=movie.year,
        genres=movie.genres,
        tags=movie.tags,
        tmdb_id=movie.tmdb_id,
        imdb_id=movie.imdb_id,
        avg_rating=round(float(avg_rating), 2) if avg_rating is not None else None,
        num_ratings=int(num_ratings),
    )
