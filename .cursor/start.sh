#!/usr/bin/env bash
# Per-boot service startup: PostgreSQL + Redis. Idempotent and safe to re-run.
set -euo pipefail

echo "==> Starting PostgreSQL 16"
if ! sudo pg_lsclusters -h 2>/dev/null | grep -q "online"; then
  sudo pg_ctlcluster 16 main start || true
fi

echo "==> Starting Redis"
if ! redis-cli ping >/dev/null 2>&1; then
  sudo redis-server --daemonize yes || true
fi

# Wait briefly for PostgreSQL to accept connections.
for _ in $(seq 1 15); do
  if pg_isready -h localhost -U cinerec >/dev/null 2>&1; then
    echo "==> PostgreSQL is ready"
    break
  fi
  sleep 1
done

redis-cli ping >/dev/null 2>&1 && echo "==> Redis is ready" || echo "WARN: Redis not responding"
