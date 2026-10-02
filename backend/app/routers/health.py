from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_async_db
from app.models import Movie, Rating
from app.recsys import cache, collaborative
from app.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health(db: AsyncSession = Depends(get_async_db)) -> HealthResponse:
    movies = await db.scalar(select(func.count()).select_from(Movie)) or 0
    ratings = await db.scalar(select(func.count()).select_from(Rating)) or 0
    embeddings = (
        await db.scalar(
            select(func.count()).select_from(Movie).where(Movie.embedding.is_not(None))
        )
        or 0
    )
    return HealthResponse(
        status="ok",
        movies=movies,
        ratings=ratings,
        embeddings=embeddings,
        embedder=get_settings().embedder,
        cache_backend=cache.backend_name(),
        als=collaborative.status(),
    )
