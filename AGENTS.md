# AGENTS.md

cinerec is a movie recommendation system. See `README.md` for the architecture, full setup,
and the standard lint/test/build/run commands (do not duplicate them here).

## Cursor Cloud specific instructions

The update script (run automatically on VM startup) only refreshes dependencies
(`uv sync` for `backend/`, `npm install` for `frontend/`). Everything below is **not** handled
by the update script and is needed to actually run the app.

### PostgreSQL (not auto-started)

- PostgreSQL 16 + `pgvector` are installed natively (not Docker). The DB server does **not**
  start automatically on a fresh VM. Start it once per session:
  ```bash
  sudo pg_ctlcluster 16 main start
  ```
- Connection: `postgresql+psycopg://cinerec:cinerec@localhost:5432/cinerec` (this is the default
  in `app/config.py`; override with `CINEREC_DATABASE_URL`).
- The `cinerec` role is a **SUPERUSER** on purpose — pgvector's `CREATE EXTENSION vector`
  requires superuser, including for the auto-created `cinerec_test` database used by pytest.
- Loaded data (≈9.7k movies, ≈100k ratings, embeddings, HNSW index) lives in the cluster data
  directory and **persists across VM snapshots**. After starting Postgres, check
  `GET /health`; only re-seed if it reports 0 movies:
  ```bash
  cd backend && uv run python -m scripts.load_data && uv run python -m scripts.build_embeddings
  ```

### Redis cache & background retraining

- Redis is installed natively and, like Postgres, does **not** auto-start on a fresh VM. Start it
  with `sudo service redis-server start` (verify with `redis-cli ping`).
- The recommendation cache uses Redis when `CINEREC_REDIS_URL` is set and reachable; otherwise it
  **transparently falls back to an in-process cache** (so a missing Redis never breaks the app).
  `/health` reports the active `cache_backend`. Only the `cinerec:rec:*` namespace is used/cleared.
- The ALS model is refreshed by a background worker thread (started in the FastAPI lifespan).
  `POST /ratings` marks the model dirty and signals the worker, which retrains off the request
  path and atomically swaps the model — so recommendation requests never block on training. This
  is eventually consistent: a brand-new user's collaborative recommendations appear a moment later
  (typically ~1-2s), not instantly. `/health.als` shows `users`/`items`/`dirty`/`last_trained_at`.
- Tests set `CINEREC_REDIS_URL=""` and `CINEREC_ENABLE_BACKGROUND_RETRAIN=false` for determinism
  (in-process cache + synchronous training); `collaborative.reset()` forces a synchronous rebuild.

### Backend gotchas

- `uv` lives at `~/.local/bin` — add it to `PATH` if `uv` is not found.
- `scripts.build_embeddings` and the live server use `sentence-transformers`
  (`all-MiniLM-L6-v2`); the model is cached under `~/.cache/huggingface` (persists in snapshots,
  so no re-download needed). Set `CINEREC_EMBEDDER=hash` to use the offline hashing embedder
  (no model download) — this is what the test suite uses.
- The collaborative-filtering (ALS) model is trained **lazily in-memory** on the first
  `/recommend/*?method=collaborative` request and cached; it is not persisted, so it retrains
  after each server restart. `POST /ratings` calls `collaborative.invalidate()` to force a
  retrain on the next request.
- Tests require a running PostgreSQL and create/use a separate `cinerec_test` database
  automatically (see `tests/conftest.py`).
- Schema changes use additive, idempotent migrations (`scripts.migrate`, `ADD COLUMN IF NOT
  EXISTS`) rather than a migration framework. After pulling changes that add columns, run
  `uv run python -m scripts.migrate` against an already-populated DB (fresh `load_data` already
  includes them via the ORM).
- Recommendation responses are cached in-process with a short TTL (`app/recsys/cache.py`); the
  cache is cleared by `collaborative.invalidate()` (called on `POST /ratings`). It is per-process,
  so it resets on server restart.
- `scripts.evaluate` reports leave-one-out HR@K / NDCG@K and is the way to compare
  content / collaborative / hybrid quality; it reads embeddings from the DB, so run
  `build_embeddings` first.

### Frontend

- The Vite dev server proxies `/api/*` → `http://localhost:8000`, so the backend must be running
  on port 8000 for the UI to load data. If the catalog shows "0 movies" and the console logs
  `Unexpected token '<' ... is not valid JSON`, the dev server/proxy is down — restart
  `npm run dev` (the proxy only forwards `/api` while Vite is running).
- Avoid running `npm run build` in `frontend/` while `npm run dev` is live in the same directory;
  the build (`tsc -b` + `vite build`) can disrupt the running dev server. Use separate sessions
  or stop the dev server first.
