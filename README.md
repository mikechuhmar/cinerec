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
the ALS model is refreshed by a **background worker** so new ratings are picked up without
blocking requests.

Data comes from the [MovieLens](https://grouplens.org/datasets/movielens/) dataset
(no API key required). Optional TMDB enrichment is supported via `CINEREC_TMDB_API_KEY`.

## Architecture

```
frontend/  React + Vite + TS + Tailwind      → http://localhost:5173 (proxies /api → :8000)
backend/   FastAPI + SQLAlchemy + pgvector    → http://localhost:8000 (docs at /docs)
           recsys/  content-based + ALS
           scripts/ load_data, build_embeddings
PostgreSQL 16 + pgvector                      → localhost:5432  (db/user/pass: cinerec)
```

## Tech stack

| Layer        | Tech |
|--------------|------|
| Backend API  | Python 3.12, FastAPI, Uvicorn, SQLAlchemy 2.0, Pydantic v2 |
| Database     | PostgreSQL 16 + pgvector (HNSW cosine index) |
| Cache        | Redis (in-process fallback) |
| Embeddings   | sentence-transformers (`all-MiniLM-L6-v2`, 384-dim) |
| Collaborative| `implicit` ALS (background retraining) |
| Frontend     | React 19, Vite 6, TypeScript, Tailwind CSS v4 |
| Tooling      | uv (Python), npm (JS), ruff, pytest, eslint |

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
uv run python -m scripts.migrate          # apply additive schema migrations (idempotent)
uv run python -m scripts.load_data        # download + load MovieLens
uv run python -m scripts.build_embeddings # compute embeddings + HNSW index
uv run uvicorn app.main:app --reload      # http://localhost:8000/docs

# Optional: enrich with TMDB posters/overviews (needs CINEREC_TMDB_API_KEY), then re-embed
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
| Test            | `uv run pytest`                   | —                        |
| Build           | —                                 | `npm run build`          |

## Key API endpoints

- `GET /health` — counts of movies / ratings / embeddings, cache backend and ALS status
- `GET /movies?q=&genre=&year_from=&year_to=&min_rating=&sort=&order=&limit=&offset=` — paginated
  catalog (sort by `popularity|rating|year|title`); returns `{total, limit, offset, items}`
- `GET /movies/genres` — distinct genres
- `GET /movies/{id}` — movie detail + rating stats
- `GET /recommend/similar/{movie_id}?method=content|collaborative|hybrid&alpha=`
- `GET /recommend/user/{user_id}?method=hybrid|collaborative|content&alpha=`
- `POST /ratings` — add a rating (invalidates the cached ALS model and recommendation cache)
