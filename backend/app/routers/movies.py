from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Float, cast, func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Movie, Rating
from app.schemas import MovieBase, MovieDetail, MoviePage

router = APIRouter(prefix="/movies", tags=["movies"])

SORT_FIELDS = {"title", "year", "rating", "popularity"}


@router.get("", response_model=MoviePage)
def list_movies(
    q: str | None = Query(None, description="Case-insensitive title search"),
    genre: str | None = Query(None, description="Filter by genre"),
    year_from: int | None = Query(None, description="Minimum release year"),
    year_to: int | None = Query(None, description="Maximum release year"),
    min_rating: float | None = Query(None, ge=0, le=5, description="Minimum average rating"),
    sort: str = Query("popularity", description="title | year | rating | popularity"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> MoviePage:
    if sort not in SORT_FIELDS:
        raise HTTPException(status_code=422, detail=f"sort must be one of {sorted(SORT_FIELDS)}")

    avg_rating = func.avg(Rating.rating)
    num_ratings = func.count(Rating.id)

    stmt = (
        select(
            Movie,
            cast(avg_rating, Float).label("avg_rating"),
            num_ratings.label("num_ratings"),
        )
        .outerjoin(Rating, Rating.movie_id == Movie.id)
        .group_by(Movie.id)
    )

    if q:
        stmt = stmt.where(Movie.title.ilike(f"%{q}%"))
    if genre:
        stmt = stmt.where(Movie.genres.any(genre))
    if year_from is not None:
        stmt = stmt.where(Movie.year >= year_from)
    if year_to is not None:
        stmt = stmt.where(Movie.year <= year_to)
    if min_rating is not None:
        stmt = stmt.having(func.coalesce(avg_rating, 0) >= min_rating)

    direction = (lambda c: c.desc()) if order == "desc" else (lambda c: c.asc())
    if sort == "title":
        stmt = stmt.order_by(direction(Movie.title))
    elif sort == "year":
        stmt = stmt.order_by(direction(func.coalesce(Movie.year, 0)), Movie.title)
    elif sort == "rating":
        stmt = stmt.order_by(direction(func.coalesce(avg_rating, 0)), num_ratings.desc())
    else:  # popularity
        stmt = stmt.order_by(direction(num_ratings), Movie.title)

    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0

    rows = db.execute(stmt.limit(limit).offset(offset)).all()
    items = [
        MovieBase(
            id=m.id,
            title=m.title,
            year=m.year,
            genres=m.genres,
            poster_url=m.poster_url,
            avg_rating=round(float(avg), 2) if avg is not None else None,
            num_ratings=int(cnt),
        )
        for m, avg, cnt in rows
    ]
    return MoviePage(total=total, limit=limit, offset=offset, items=items)


@router.get("/genres", response_model=list[str])
def list_genres(db: Session = Depends(get_db)) -> list[str]:
    rows = db.execute(select(func.unnest(Movie.genres)).distinct()).scalars()
    return sorted({g for g in rows if g})


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
        poster_url=movie.poster_url,
        tags=movie.tags,
        overview=movie.overview,
        tmdb_id=movie.tmdb_id,
        imdb_id=movie.imdb_id,
        avg_rating=round(float(avg_rating), 2) if avg_rating is not None else None,
        num_ratings=int(num_ratings),
    )
