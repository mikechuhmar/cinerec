#!/usr/bin/env bash
# Idempotent repository bootstrap for the cinerec Cloud Agent environment.
# Installs uv, PostgreSQL 16 + pgvector and Redis, syncs deps, migrates and seeds data.
set -euo pipefail

export PATH="$HOME/.local/bin:$PATH"
export OPENBLAS_NUM_THREADS=1

echo "==> Installing uv (if missing)"
if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi

echo "==> Installing PostgreSQL 16 + pgvector and Redis (if missing)"
if ! command -v pg_ctlcluster >/dev/null 2>&1 || ! command -v redis-server >/dev/null 2>&1; then
  sudo apt-get update -qq
  sudo apt-get install -y -qq postgresql-16 postgresql-16-pgvector redis-server
fi

echo "==> Starting PostgreSQL + Redis"
bash "$(dirname "$0")/start.sh"

echo "==> Ensuring the cinerec role + database exist"
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='cinerec'" | grep -q 1 \
  || sudo -u postgres psql -c "CREATE USER cinerec WITH PASSWORD 'cinerec' SUPERUSER CREATEDB;"
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='cinerec'" | grep -q 1 \
  || sudo -u postgres psql -c "CREATE DATABASE cinerec OWNER cinerec;"
sudo -u postgres psql -d cinerec -c "CREATE EXTENSION IF NOT EXISTS vector;"

echo "==> Installing backend dependencies"
(cd backend && uv sync --extra dev)

echo "==> Applying database migrations"
(cd backend && uv run python -m scripts.migrate)

echo "==> Seeding data (only if the catalogue is empty)"
MOVIE_COUNT=$(sudo -u postgres psql -d cinerec -tAc "SELECT count(*) FROM movies" 2>/dev/null || echo 0)
if [ "${MOVIE_COUNT:-0}" -eq 0 ]; then
  (cd backend && CINEREC_EMBEDDER=hash uv run python -m scripts.load_data \
    && CINEREC_EMBEDDER=hash uv run python -m scripts.build_embeddings)
else
  echo "    catalogue already has ${MOVIE_COUNT} movies; skipping seed"
fi

echo "==> Installing frontend dependencies"
(cd frontend && npm ci)

echo "==> Install complete"
