"""Apply database migrations (Alembic) up to the latest revision.

    uv run python -m scripts.migrate            # upgrade to head
    uv run python -m scripts.migrate --down -1  # downgrade one revision

This replaces the previous ad-hoc ``ALTER TABLE`` script: the schema is now fully managed
by the versioned migrations under ``migrations/versions/``.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from alembic import command
from alembic.config import Config

BACKEND_DIR = Path(__file__).resolve().parent.parent


def _alembic_config() -> Config:
    return Config(str(BACKEND_DIR / "alembic.ini"))


def upgrade(revision: str = "head") -> None:
    command.upgrade(_alembic_config(), revision)


def downgrade(revision: str) -> None:
    command.downgrade(_alembic_config(), revision)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run cinerec database migrations")
    parser.add_argument("--down", metavar="REV", help="Downgrade to this revision instead")
    args = parser.parse_args()
    if args.down:
        downgrade(args.down)
        print(f"Downgraded to {args.down}.")
    else:
        upgrade("head")
        print("Migrations applied (head).")


if __name__ == "__main__":
    main()
