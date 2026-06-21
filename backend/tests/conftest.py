import os

# Configure the app to use an offline embedder and a dedicated test database
# BEFORE any app module (which reads settings at import time) is imported.
os.environ["CINEREC_EMBEDDER"] = "hash"
os.environ.setdefault(
    "CINEREC_DATABASE_URL",
    "postgresql+psycopg://cinerec:cinerec@localhost:5432/cinerec_test",
)

import psycopg  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


def _ensure_test_database() -> None:
    """Create the test database (and pgvector extension) if missing."""
    admin_dsn = "postgresql://cinerec:cinerec@localhost:5432/cinerec"
    with psycopg.connect(admin_dsn, autocommit=True) as conn:
        exists = conn.execute(
            "SELECT 1 FROM pg_database WHERE datname = 'cinerec_test'"
        ).fetchone()
        if not exists:
            conn.execute("CREATE DATABASE cinerec_test")

    test_dsn = "postgresql://cinerec:cinerec@localhost:5432/cinerec_test"
    with psycopg.connect(test_dsn, autocommit=True) as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")


@pytest.fixture(scope="session", autouse=True)
def _db_setup():
    _ensure_test_database()

    from app.db import Base, engine

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(_db_setup):
    from app.db import Base, SessionLocal, engine
    from app.models import Movie, Rating
    from app.recsys import collaborative
    from app.recsys.content import build_movie_text
    from app.recsys.embedder import get_embedder

    # Reset state between tests.
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    collaborative.invalidate()

    embedder = get_embedder()
    seed_movies = [
        (1, "Toy Story", 1995, ["Animation", "Children", "Comedy"], "pixar toys"),
        (2, "A Bug's Life", 1998, ["Animation", "Children", "Comedy"], "pixar bugs"),
        (3, "The Matrix", 1999, ["Action", "Sci-Fi"], "cyberpunk hacker"),
        (4, "Terminator 2", 1991, ["Action", "Sci-Fi"], "robot future"),
        (5, "Pride and Prejudice", 2005, ["Drama", "Romance"], "classic love"),
    ]
    with SessionLocal() as db:
        for mid, title, year, genres, tags in seed_movies:
            vector = embedder.encode([build_movie_text(title, year, genres, tags)])[0]
            db.add(
                Movie(
                    id=mid,
                    title=title,
                    year=year,
                    genres=genres,
                    tags=tags,
                    embedding=vector.tolist(),
                )
            )
        # User 1 loves animated kids movies; user 2 loves sci-fi action.
        ratings = [
            (1, 1, 5.0), (1, 2, 4.5), (1, 5, 2.0),
            (2, 3, 5.0), (2, 4, 4.5), (2, 1, 2.5),
        ]
        for uid, mid, r in ratings:
            db.add(Rating(user_id=uid, movie_id=mid, rating=r))
        db.commit()

    from app.main import app

    with TestClient(app) as c:
        yield c
