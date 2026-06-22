from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import Base, engine
from app.routers import health, movies, ratings, recommend


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure the pgvector extension and tables exist on startup.
    from sqlalchemy import text

    from app.recsys import collaborative

    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(bind=engine)

    # Start the background ALS retrainer (no-op if disabled).
    collaborative.start_retrainer()
    try:
        yield
    finally:
        collaborative.stop_retrainer()


app = FastAPI(
    title="cinerec API",
    version="0.1.0",
    description="Movie recommendation system (content-based via pgvector + collaborative ALS).",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(movies.router)
app.include_router(recommend.router)
app.include_router(ratings.router)


@app.get("/", tags=["health"])
def root() -> dict:
    return {"name": "cinerec", "docs": "/docs", "health": "/health"}
