from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import Movie, Rating
from app.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(db: Session = Depends(get_db)) -> HealthResponse:
    movies = db.scalar(select(func.count()).select_from(Movie)) or 0
    ratings = db.scalar(select(func.count()).select_from(Rating)) or 0
    embeddings = (
        db.scalar(select(func.count()).select_from(Movie).where(Movie.embedding.is_not(None))) or 0
    )
    return HealthResponse(
        status="ok",
        movies=movies,
        ratings=ratings,
        embeddings=embeddings,
        embedder=get_settings().embedder,
    )
