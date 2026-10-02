"""initial schema: movies + ratings (pgvector)

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-02

Creates the pgvector extension and the ``movies`` and ``ratings`` tables, including the
``uq_ratings_user_movie`` unique constraint (one rating per user/movie). The HNSW vector
index is built by ``scripts.build_embeddings`` once embeddings exist.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import ARRAY

from app.config import get_settings

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    dim = get_settings().embedding_dim
    op.create_table(
        "movies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("genres", ARRAY(sa.String()), nullable=True),
        sa.Column("tags", sa.Text(), nullable=True),
        sa.Column("overview", sa.Text(), nullable=True),
        sa.Column("poster_url", sa.String(length=512), nullable=True),
        sa.Column("tmdb_id", sa.Integer(), nullable=True),
        sa.Column("imdb_id", sa.String(length=20), nullable=True),
        sa.Column("embedding", Vector(dim), nullable=True),
    )
    op.create_index("ix_movies_title", "movies", ["title"])

    op.create_table(
        "ratings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "movie_id",
            sa.Integer(),
            sa.ForeignKey("movies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("rating", sa.Float(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("user_id", "movie_id", name="uq_ratings_user_movie"),
    )
    op.create_index("ix_ratings_user_id", "ratings", ["user_id"])
    op.create_index("ix_ratings_movie_id", "ratings", ["movie_id"])


def downgrade() -> None:
    op.drop_table("ratings")
    op.drop_index("ix_movies_title", table_name="movies")
    op.drop_table("movies")
