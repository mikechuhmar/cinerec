# Deploying cinerec as a website

This guide publishes cinerec as a live site: a React SPA (the page users visit) talking to the
FastAPI backend, backed by PostgreSQL + pgvector and (optionally) Redis.

Two paths are described:

- **A. Render (PaaS)** — lowest friction, managed TLS + managed Postgres/Redis, free tier. Uses
  the committed [`render.yaml`](render.yaml) blueprint.
- **B. Any VPS with Docker** — full control, one box, automatic HTTPS via Caddy. Uses
  [`docker-compose.yml`](docker-compose.yml).

---

## A. Render (recommended)

### 1. Create the services

1. Push this repository to GitHub (or GitLab).
2. In Render: **New → Blueprint**, pick the repo. Render reads [`render.yaml`](render.yaml) and
   provisions four resources: `cinerec-db` (Postgres 16), `cinerec-redis` (Key Value),
   `cinerec-backend` (Docker web service) and `cinerec-frontend` (static site).
3. Click **Apply** and wait for the first build. The backend runs its Alembic migrations
   automatically on boot (`scripts.migrate`), so the schema and the `vector` extension are created
   for you.

The blueprint wires everything up:

- `CINEREC_DATABASE_URL` ← the managed database connection string (the app rewrites the
  `postgresql://` scheme to the psycopg3 driver automatically).
- `CINEREC_REDIS_URL` ← the managed Key Value instance.
- `CINEREC_CORS_ORIGINS` ← the frontend's hostname (so the browser's cross-origin calls pass CORS).
- `VITE_API_BASE` ← the backend's hostname, baked into the SPA at build time.

### 2. Seed the data (one time)

The database starts empty. Open **cinerec-backend → Shell** in the Render dashboard and run:

```bash
python -m scripts.load_data        # download + load MovieLens (~9.7k movies, ~100k ratings)
python -m scripts.build_embeddings # compute embeddings + build the HNSW index
```

The blueprint sets `CINEREC_EMBEDDER=hash` so no ML model is downloaded (keeps the build within the
free tier). Verify with `GET https://<backend>.onrender.com/health` — it should report non-zero
movie / embedding counts.

### 3. Visit the site

Open the `cinerec-frontend` URL (e.g. `https://cinerec-frontend.onrender.com`). The API lives at
the `cinerec-backend` URL (`/docs`, `/health`, `/metrics`).

### Notes & tuning

- **Free tier**: services spin down when idle (first request after a pause is slow), and the free
  database expires after ~30 days. Upgrade the plans for an always-on, persistent site.
- **Semantic embeddings**: on a paid backend instance with more memory, set
  `CINEREC_EMBEDDER=sentence-transformers` and re-run `scripts.build_embeddings` for higher-quality
  content-based recommendations.
- **pgvector**: Render's managed Postgres supports the `vector` extension; the app enables it on
  startup, so no manual step is needed.

---

## B. VPS with Docker Compose + HTTPS

Good if you already have a server (any provider) and a domain.

### 1. Prerequisites

- A VM with Docker + the Compose plugin.
- A domain's `A` record pointing at the VM's IP (needed for automatic TLS).

### 2. Bring up the stack

```bash
git clone <your-repo> && cd cinerec
docker compose up -d --build        # db + redis + backend + frontend
# one-time seed:
docker compose exec backend python -m scripts.load_data
docker compose exec backend python -m scripts.build_embeddings
```

This exposes the frontend (nginx, proxying `/api` → backend) on port `5173`. For a public site put
a TLS-terminating reverse proxy in front. The simplest is **Caddy** (automatic Let's Encrypt):

`Caddyfile`:

```
your-domain.com {
    reverse_proxy localhost:5173
}
```

```bash
# install Caddy, then:
sudo caddy run --config ./Caddyfile
```

Caddy obtains and renews certificates automatically; your site is live at
`https://your-domain.com`.

### Hardening for production

- Change the default database password (`CINEREC_DATABASE_URL` in `docker-compose.yml`).
- Keep `CINEREC_RATE_LIMIT` enabled (default `120/minute` per IP) and review `CINEREC_CORS_ORIGINS`.
- Point monitoring at `/metrics` (Prometheus) and scrape structured JSON logs from the containers.

---

## Environment variables reference

| Variable | Purpose | Example |
|----------|---------|---------|
| `CINEREC_DATABASE_URL` | Postgres DSN (`postgresql://` is auto-upgraded to psycopg3) | `postgresql://user:pass@host/db` |
| `CINEREC_REDIS_URL` | Cache backend (omit to use the in-process fallback) | `redis://host:6379/0` |
| `CINEREC_EMBEDDER` | `hash` (offline) or `sentence-transformers` (semantic) | `hash` |
| `CINEREC_CORS_ORIGINS` | Comma-separated allowed origins (`*` for any; bare host → https) | `cinerec-frontend.onrender.com` |
| `CINEREC_RATE_LIMIT` | Per-IP rate limit (empty disables) | `120/minute` |
| `CINEREC_LOG_JSON` | Structured JSON logs | `true` |
| `VITE_API_BASE` | **Build-time** backend base URL for the SPA (empty = same-origin `/api`) | `cinerec-backend.onrender.com` |
