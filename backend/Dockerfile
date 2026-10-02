# syntax=docker/dockerfile:1
# Multi-stage build for the cinerec backend (build context: ./backend).
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install dependencies first (cached layer) using the locked versions.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Then the application source.
COPY . .

EXPOSE 8000

# Apply migrations, then serve. Honour $PORT (set by most hosting platforms; default 8000).
# Seed data once with `scripts.load_data` / `scripts.build_embeddings`.
CMD ["sh", "-c", "python -m scripts.migrate && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
