#!/usr/bin/env bash
# DocGuardian AI — one-command dev startup (Mac / Linux)
# Usage (from repo root):  ./start.sh
#
# What it does:
#   1. Starts Postgres via Docker (auto-seeds DB on first run)
#   2. Waits for Postgres to be healthy
#   3. Starts the FastAPI backend (uvicorn :8000) in background
#   4. Starts the Vite frontend (:5173) in foreground

set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"

echo ""
echo "==> DocGuardian AI startup"

# ── 1. Postgres ────────────────────────────────────────────────────────────────
echo "[1/4] Starting Postgres..."
(cd "$BACKEND" && docker compose up -d)

# Wait until healthy (up to 30s)
echo "[2/4] Waiting for Postgres to be healthy..."
for i in $(seq 1 30); do
    STATUS=$(docker inspect --format='{{.State.Health.Status}}' docguardian-db 2>/dev/null || echo "missing")
    [ "$STATUS" = "healthy" ] && break
    sleep 1
done
if [ "$STATUS" != "healthy" ]; then
    echo "ERROR: Postgres did not become healthy in time." >&2; exit 1
fi
echo "    Postgres is ready."

# ── 2. Backend ─────────────────────────────────────────────────────────────────
echo "[3/4] Starting backend (uvicorn :8000)..."
UVICORN="$BACKEND/.venv/bin/uvicorn"
(cd "$BACKEND" && "$UVICORN" app.main:app --reload --reload-dir app --port 8000 &)
BACKEND_PID=$!
sleep 2

# ── 3. Frontend ────────────────────────────────────────────────────────────────
echo "[4/4] Starting frontend (vite :5173)..."
echo ""
echo "All services started:"
echo "  Backend  ->  http://localhost:8000/health"
echo "  Frontend ->  http://localhost:5173"
echo ""
echo "On a fresh machine the DB is pre-seeded automatically from"
echo "backend/docker/init/01-seed.sql (runs only when pgdata volume is empty)."
echo ""
(cd "$FRONTEND" && npm run dev)
