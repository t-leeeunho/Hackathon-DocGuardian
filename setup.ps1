<#
.SYNOPSIS
    One-shot local setup for DocGuardian AI: database, ingestion, embeddings,
    and (optionally) the dev servers.

.DESCRIPTION
    Brings a fresh machine to a populated knowledge graph with one command:
      1. Verifies prerequisites (python, docker, git, node).
      2. Installs backend Python dependencies.
      3. Starts Postgres + pgvector via docker compose and waits for health.
      4. Clones doc repos and processes them into JSONL (run_ingest).
      5. Embeds chunks locally (fastembed) and loads docs/chunks/edges into
         Postgres, creating the schema (load_vectors).
      6. Installs frontend dependencies.

    Everything is local — no Azure key is required (embeddings use fastembed).
    Azure is only needed for /chat and /propose.

.PARAMETER Repo
    Ingest a single repo shortName (e.g. garnet) instead of all of them.

.PARAMETER SkipFrontend
    Skip "npm install" for the frontend.

.PARAMETER StartServers
    After setup, launch the backend (uvicorn) and frontend (vite) dev servers
    in new terminal windows.

.EXAMPLE
    ./setup.ps1
    Full setup for all repos.

.EXAMPLE
    ./setup.ps1 -Repo garnet -StartServers
    Set up just the garnet corpus, then start both dev servers.
#>
[CmdletBinding()]
param(
    [string]$Repo,
    [switch]$SkipFrontend,
    [switch]$StartServers
)

$ErrorActionPreference = 'Stop'
$RepoRoot = $PSScriptRoot
$BackendDir = Join-Path $RepoRoot 'backend'
$FrontendDir = Join-Path $RepoRoot 'frontend'

function Write-Step($msg) { Write-Host "`n=== $msg ===" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "  [ok] $msg" -ForegroundColor Green }

function Assert-Command($name, $hint) {
    if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
        throw "Required command '$name' not found on PATH. $hint"
    }
    Write-Ok "$name found"
}

# --- 1. Prerequisites ----------------------------------------------------- #
Write-Step 'Checking prerequisites'
Assert-Command 'python' 'Install Python 3.11+ from https://www.python.org/downloads/'
Assert-Command 'docker' 'Install Docker Desktop and ensure it is running.'
Assert-Command 'git'    'Install Git from https://git-scm.com/downloads'
if (-not $SkipFrontend) {
    Assert-Command 'node' 'Install Node.js LTS from https://nodejs.org/'
    Assert-Command 'npm'  'npm ships with Node.js.'
}

# Confirm the Docker daemon is actually reachable (not just the CLI).
& docker info *> $null
if ($LASTEXITCODE -ne 0) {
    throw 'Docker is installed but the daemon is not reachable. Start Docker Desktop and retry.'
}
Write-Ok 'Docker daemon reachable'

# --- 2. Backend dependencies --------------------------------------------- #
Write-Step 'Installing backend Python dependencies'
Push-Location $BackendDir
try {
    python -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'pip install failed.' }
    Write-Ok 'Backend dependencies installed'

    # --- 3. Database ------------------------------------------------------ #
    Write-Step 'Starting Postgres + pgvector (docker compose)'
    docker compose up -d
    if ($LASTEXITCODE -ne 0) { throw 'docker compose up failed.' }

    Write-Host '  waiting for the database to become healthy...' -ForegroundColor DarkGray
    $deadline = (Get-Date).AddMinutes(2)
    do {
        Start-Sleep -Seconds 2
        $health = (docker inspect -f '{{.State.Health.Status}}' docguardian-db 2>$null)
        if ($health -eq 'healthy') { break }
    } while ((Get-Date) -lt $deadline)
    if ($health -ne 'healthy') {
        throw "Database did not become healthy in time (last status: '$health')."
    }
    Write-Ok 'Database is healthy'

    # --- 4. Ingest -------------------------------------------------------- #
    Write-Step 'Ingesting documentation repos (clone + process)'
    if ($Repo) {
        python -m scripts.run_ingest --repo $Repo
    } else {
        python -m scripts.run_ingest --all
    }
    if ($LASTEXITCODE -ne 0) { throw 'run_ingest failed.' }
    Write-Ok 'Ingestion complete'

    # --- 5. Embed + load -------------------------------------------------- #
    Write-Step 'Embedding chunks locally + loading into Postgres'
    if ($Repo) {
        python -m scripts.load_vectors --repo $Repo
    } else {
        python -m scripts.load_vectors --all
    }
    if ($LASTEXITCODE -ne 0) { throw 'load_vectors failed.' }
    Write-Ok 'Vectors + graph loaded'
}
finally {
    Pop-Location
}

# --- 6. Frontend dependencies -------------------------------------------- #
if (-not $SkipFrontend) {
    Write-Step 'Installing frontend dependencies'
    Push-Location $FrontendDir
    try {
        npm install
        if ($LASTEXITCODE -ne 0) { throw 'npm install failed.' }
        Write-Ok 'Frontend dependencies installed'
    }
    finally {
        Pop-Location
    }
}

# --- 7. Optionally start the dev servers --------------------------------- #
if ($StartServers) {
    Write-Step 'Starting dev servers'
    Start-Process pwsh -ArgumentList @(
        '-NoExit', '-Command',
        "Set-Location '$BackendDir'; uvicorn app.main:app --reload"
    )
    Write-Ok 'Backend starting at http://localhost:8000 (Swagger at /docs)'
    if (-not $SkipFrontend) {
        Start-Process pwsh -ArgumentList @(
            '-NoExit', '-Command',
            "Set-Location '$FrontendDir'; npm run dev"
        )
        Write-Ok 'Frontend starting at http://localhost:5173'
    }
}

Write-Step 'Setup complete'
Write-Host 'Next steps:' -ForegroundColor Yellow
if (-not $StartServers) {
    Write-Host '  backend : cd backend;  uvicorn app.main:app --reload'
    Write-Host '  frontend: cd frontend; npm run dev'
}
Write-Host '  Then open http://localhost:5173 to see the populated graph.'
Write-Host '  Note: /chat and /propose need Azure; set CHAT_PROVIDER=fake for offline demo.' -ForegroundColor DarkGray
