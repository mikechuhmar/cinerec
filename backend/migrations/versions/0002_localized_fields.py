"""localized movie fields: title_ru + overview_ru

Revision ID: 0002_localized
Revises: 0001_initial
Create Date: 2026-10-02

Adds nullable Russian title/overview columns, populated from TMDB (``language=ru-RU``)
by ``scripts.enrich_tmdb`` or the offline ``scripts.seed_localized_demo`` fixture.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_localized"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("movies", sa.Column("title_ru", sa.String(length=512), nullable=True))
    op.add_column("movies", sa.Column("overview_ru", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("movies", "overview_ru")
    op.drop_column("movies", "title_ru")
