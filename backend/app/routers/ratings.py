from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Movie, Rating
from app.recsys import collaborative
from app.schemas import RatingIn

router = APIRouter(prefix="/ratings", tags=["ratings"])


@router.post("", status_code=201)
def add_rating(payload: RatingIn, db: Session = Depends(get_db)) -> dict:
    if db.get(Movie, payload.movie_id) is None:
        raise HTTPException(status_code=404, detail="Movie not found")

    db.add(Rating(user_id=payload.user_id, movie_id=payload.movie_id, rating=payload.rating))
    db.commit()
    # New feedback invalidates the cached collaborative-filtering model.
    collaborative.invalidate()
    return {"status": "created"}
