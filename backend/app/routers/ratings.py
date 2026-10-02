from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_async_db
from app.models import Movie, Rating
from app.recsys import collaborative
from app.schemas import RatingIn

router = APIRouter(prefix="/ratings", tags=["ratings"])


@router.post("", status_code=201)
async def add_rating(payload: RatingIn, db: AsyncSession = Depends(get_async_db)) -> dict:
    if await db.get(Movie, payload.movie_id) is None:
        raise HTTPException(status_code=404, detail="Movie not found")

    # Upsert: one rating per (user, movie); a repeat rating overwrites the previous value
    # instead of inserting a duplicate row.
    stmt = (
        insert(Rating)
        .values(user_id=payload.user_id, movie_id=payload.movie_id, rating=payload.rating)
        .on_conflict_do_update(
            constraint="uq_ratings_user_movie",
            set_={"rating": payload.rating, "created_at": func.now()},
        )
        .returning(Rating.id)
    )
    await db.execute(stmt)
    await db.commit()

    # New feedback invalidates the cached collaborative-filtering model.
    collaborative.invalidate()
    return {"status": "ok"}


@router.get("/user/{user_id}", response_model=list[dict])
async def list_user_ratings(user_id: int, db: AsyncSession = Depends(get_async_db)) -> list[dict]:
    rows = (
        await db.execute(
            select(Rating.movie_id, Rating.rating)
            .where(Rating.user_id == user_id)
            .order_by(Rating.created_at.desc())
        )
    ).all()
    return [{"movie_id": mid, "rating": r} for mid, r in rows]
