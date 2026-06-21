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

### Frontend

- The Vite dev server proxies `/api/*` → `http://localhost:8000`, so the backend must be running
  on port 8000 for the UI to load data.
