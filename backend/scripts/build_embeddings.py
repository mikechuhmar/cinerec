"""Compute content embeddings for every movie and store them in pgvector.

Usage:
    uv run python -m scripts.build_embeddings
    CINEREC_EMBEDDER=hash uv run python -m scripts.build_embeddings   # offline backend
"""

from __future__ import annotations

from sqlalchemy import select, text

from app.db import SessionLocal, engine
from app.models import Movie
from app.recsys.content import build_movie_text
from app.recsys.embedder import get_embedder


def _create_vector_index() -> None:
    """Create an HNSW index for fast cosine similarity search (idempotent)."""
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_movies_embedding_hnsw "
                "ON movies USING hnsw (embedding vector_cosine_ops)"
            )
        )


def main(batch_size: int = 256) -> None:
    embedder = get_embedder()
    print(f"Using embedder with dim={embedder.dim}")

    with SessionLocal() as db:
        movies = list(db.execute(select(Movie)).scalars())
        if not movies:
            print("No movies found. Run scripts.load_data first.")
            return

        print(f"Embedding {len(movies)} movies ...")
        for start in range(0, len(movies), batch_size):
            batch = movies[start : start + batch_size]
            texts = [
                build_movie_text(m.title, m.year, m.genres, m.tags, m.overview) for m in batch
            ]
            vectors = embedder.encode(texts)
            for movie, vector in zip(batch, vectors, strict=True):
                movie.embedding = vector.tolist()
            db.commit()
            print(f"  {min(start + batch_size, len(movies))}/{len(movies)}")

    print("Creating HNSW vector index ...")
    _create_vector_index()
    print("Done building embeddings.")


if __name__ == "__main__":
    main()
