"""Lightweight, idempotent schema migrations for existing databases.

This project uses SQLAlchemy ``create_all`` for first-time setup, which does not add
columns to pre-existing tables. Run this after pulling changes that introduce new
columns on an already-populated database:

    uv run python -m scripts.migrate
"""

from __future__ import annotations

from sqlalchemy import text

from app.db import Base, engine

# Columns added after the initial schema. Postgres supports ADD COLUMN IF NOT EXISTS.
ADD_COLUMNS = [
    "ALTER TABLE movies ADD COLUMN IF NOT EXISTS overview TEXT",
    "ALTER TABLE movies ADD COLUMN IF NOT EXISTS poster_url VARCHAR(512)",
]


def main() -> None:
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        for stmt in ADD_COLUMNS:
            conn.execute(text(stmt))
    print("Migrations applied.")


if __name__ == "__main__":
    main()
