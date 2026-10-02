# cinerec

A modern **movie recommendation system**: FastAPI + PostgreSQL/pgvector backend with a
React (Vite) frontend. It combines three recommendation strategies:

- **Content-based** — semantic embeddings of each movie (title + year + genres + tags + overview)
  generated with `sentence-transformers` and stored in **pgvector**; "similar movies" are
  found via cosine similarity (HNSW index).
- **Collaborative filtering** — implicit **ALS** (Alternating Least Squares) trained on the
  user–movie ratings matrix, for "recommended for you" and "users also liked".
- **Hybrid** — a min-max-normalised, weighted blend of the two (tunable `alpha`), which helps
  with cold-start.

Recommendation quality is measured offline with leave-one-out **HR@K / NDCG@K**
(`scripts/evaluate.py`).

Recommendation responses are cached in **Redis** (with a transparent in-process fallback), and
the ALS model is refreshed by a **background worker** (and **persisted to disk** so it
warm-loads on restart) so new ratings are picked up without blocking requests.

The HTTP layer is **async** (`AsyncSession`), with CPU-bound scoring offloaded to a worker
thread. It ships with production concerns built in: **Alembic** migrations, **structlog** JSON
logging, request-id correlation, **Prometheus** metrics (`/metrics`), optional **OpenTelemetry**
tracing, and per-IP **rate limiting**.

Data comes from the [MovieLens](https://grouplens.org/datasets/movielens/) dataset
(no API key required). Optional TMDB enrichment is supported via `CINEREC_TMDB_API_KEY`.

## Architecture

```
frontend/  React + Vite + TS + Tailwind      → http://localhost:5173 (proxies /api → :8000)
           TanStack Query + React Router
backend/   FastAPI (async) + SQLAlchemy       → http://localhost:8000 (docs at /docs, metrics at /metrics)
           recsys/  content-based + ALS + hybrid + cache
           migrations/  Alembic versions
           scripts/ load_data, build_embeddings, migrate, evaluate
PostgreSQL 16 + pgvector                      → localhost:5432  (db/user/pass: cinerec)
Redis                                         → localhost:6379  (optional; in-process fallback)
```

### Run the whole stack with Docker

```bash
docker compose up --build        # db + redis + backend + frontend
# one-time seed (inside the backend container):
docker compose exec backend python -m scripts.load_data
docker compose exec backend python -m scripts.build_embeddings
# UI → http://localhost:5173 · API → http://localhost:8000/docs
```

### Deploy as a website

See [`DEPLOY.md`](DEPLOY.md) for publishing cinerec live — a one-click **Render** blueprint
([`render.yaml`](render.yaml), managed Postgres/pgvector + Redis + TLS) or a **VPS + Docker Compose**
setup with automatic HTTPS via Caddy.

## Tech stack

| Layer        | Tech |
|--------------|------|
| Backend API  | Python 3.12, FastAPI (async), Uvicorn, SQLAlchemy 2.0 async, Pydantic v2 |
| Database     | PostgreSQL 16 + pgvector (HNSW cosine index), Alembic migrations |
| Cache        | Redis (in-process fallback) |
| Embeddings   | sentence-transformers (`all-MiniLM-L6-v2`, 384-dim) |
| Collaborative| `implicit` ALS (background retraining + disk persistence) |
| Observability| structlog (JSON), Prometheus (`/metrics`), OpenTelemetry (opt-in), request-id, slowapi rate limiting |
| Frontend     | React 19, Vite 6, TypeScript, Tailwind CSS v4, TanStack Query, React Router |
| Tooling      | uv, npm, ruff (+ format), mypy, pytest, Vitest, eslint, Prettier, pre-commit |

## Prerequisites

- Python 3.12, [`uv`](https://docs.astral.sh/uv/)
- Node.js 22+
- PostgreSQL 16 with the `pgvector` extension
- Redis (optional — the cache falls back to in-process if unavailable)

## Setup

### 1. Database

```bash
# Create role + database (one-time)
sudo -u postgres psql -c "CREATE USER cinerec WITH PASSWORD 'cinerec' SUPERUSER CREATEDB;"
sudo -u postgres psql -c "CREATE DATABASE cinerec OWNER cinerec;"
sudo -u postgres psql -d cinerec -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

Alternatively use Docker: `docker compose up -d db`.

### 2. Backend

```bash
cd backend
uv sync --extra dev                       # install deps
uv run python -m scripts.migrate          # alembic upgrade head (creates the schema)
uv run python -m scripts.load_data        # download + load MovieLens
uv run python -m scripts.build_embeddings # compute embeddings + HNSW index
uv run uvicorn app.main:app --reload      # http://localhost:8000/docs

# Russian titles + posters for ~60 popular movies (offline, no API key required)
uv run python -m scripts.seed_localized_demo

# Optional: enrich the full catalogue with TMDB posters + English/Russian overviews
# (needs CINEREC_TMDB_API_KEY: fetches language=en-US and language=ru-RU), then re-embed
CINEREC_TMDB_API_KEY=xxx uv run python -m scripts.enrich_tmdb
uv run python -m scripts.build_embeddings

# Optional: evaluate recommendation quality (HR@K / NDCG@K)
uv run python -m scripts.evaluate --k 10 --users 300
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev                               # http://localhost:5173
```

## Useful commands

| Task            | Backend (`cd backend`)            | Frontend (`cd frontend`) |
|-----------------|-----------------------------------|--------------------------|
| Run (dev)       | `uv run uvicorn app.main:app --reload` | `npm run dev`        |
| Lint            | `uv run ruff check .`             | `npm run lint`           |
| Format          | `uv run ruff format .`            | `npm run format`         |
| Type check      | `uv run mypy`                     | `tsc -b` (via build)     |
| Test            | `uv run pytest`                   | `npm run test`           |
| Migrate         | `uv run python -m scripts.migrate`| —                        |
| Build           | —                                 | `npm run build`          |

Install [`pre-commit`](https://pre-commit.com/) and run `pre-commit install` to enable the
ruff/ruff-format/prettier hooks on commit.

## Key API endpoints

- `GET /health` — counts of movies / ratings / embeddings, cache backend and ALS status
- `GET /metrics` — Prometheus metrics (request latency, cache hit/miss, ALS retrains)
- `GET /movies?q=&genre=&year_from=&year_to=&min_rating=&sort=&order=&limit=&offset=` — paginated
  catalog (sort by `popularity|rating|year|title`); returns `{total, limit, offset, items}`
- `GET /movies/genres` — distinct genres
- `GET /movies/{id}` — movie detail + rating stats
- `GET /recommend/similar/{movie_id}?method=content|collaborative|hybrid&alpha=`
- `GET /recommend/user/{user_id}?method=hybrid|collaborative|content&alpha=`
- `POST /ratings` — add/update a rating (upsert; invalidates the ALS model and recommendation cache)
- `GET /ratings/user/{user_id}` — list a user's ratings

Every response carries an `X-Request-ID` header; requests exceeding `CINEREC_RATE_LIMIT`
(default `120/minute` per IP) get `429`.
