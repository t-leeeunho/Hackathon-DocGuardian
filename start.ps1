#!/usr/bin/env pwsh
# DocGuardian AI — one-command dev startup
# Usage (from repo root):  .\start.ps1
#
# What it does:
#   1. Starts Postgres via Docker (auto-seeds DB on first run)
#   2. Waits for Postgres to be healthy
#   3. Starts the FastAPI backend (uvicorn) in a new window
#   4. Starts the Vite frontend in a new window

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Backend = Join-Path $Root 'backend'
$Frontend = Join-Path $Root 'frontend'

Write-Host ""
Write-Host "==> DocGuardian AI startup" -ForegroundColor Cyan

# ── 1. Postgres ────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "[1/4] Starting Postgres..." -ForegroundColor Yellow
Push-Location $Backend
docker compose up -d
Pop-Location

# Wait until healthy (up to 30s)
Write-Host "[2/4] Waiting for Postgres to be healthy..." -ForegroundColor Yellow
$retries = 30
for ($i = 0; $i -lt $retries; $i++) {
    $status = docker inspect --format='{{.State.Health.Status}}' docguardian-db 2>$null
    if ($status -eq 'healthy') { break }
    Start-Sleep -Seconds 1
}
if ($status -ne 'healthy') {
    Write-Host "ERROR: Postgres did not become healthy in time." -ForegroundColor Red
    exit 1
}
Write-Host "    Postgres is ready." -ForegroundColor Green

# ── 2. Backend ─────────────────────────────────────────────────────────────────
Write-Host "[3/4] Starting backend (uvicorn :8000)..." -ForegroundColor Yellow
$uvicorn = Join-Path $Backend '.venv\Scripts\uvicorn'
Start-Process powershell -ArgumentList @(
    '-NoExit',
    '-Command',
    "Set-Location '$Backend'; & '$uvicorn' app.main:app --reload --reload-dir app --port 8000"
) -WindowStyle Normal

# Brief pause so the backend can start before we open the browser
Start-Sleep -Seconds 3

# ── 3. Frontend ────────────────────────────────────────────────────────────────
Write-Host "[4/4] Starting frontend (vite :5173)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList @(
    '-NoExit',
    '-Command',
    "Set-Location '$Frontend'; npm run dev"
) -WindowStyle Normal

Write-Host ""
Write-Host "All services started:" -ForegroundColor Green
Write-Host "  Backend  ->  http://localhost:8000/health"
Write-Host "  Frontend ->  http://localhost:5173"
Write-Host ""
Write-Host "On a fresh machine the DB is pre-seeded automatically from"
Write-Host "backend/docker/init/01-seed.sql (runs only when pgdata volume is empty)."
Write-Host ""
