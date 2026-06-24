---
name: run-checks
description: >-
  Run the full DocGuardian quality gate — backend (ruff, black, pytest) and
  frontend (eslint, tsc, vitest) — in one pass. USE WHEN the user asks to "run
  checks", "lint", "run the tests", "verify my changes", "is it green?", or before
  committing/integrating work. Reports a concise pass/fail summary per stack.
---

# Run Checks (backend + frontend quality gate)

One command surface to confirm a change is green before commit or integration.
Run from the repo root.

## When to use

- Before committing, before opening a PR, or at an integration milestone.
- After an engineer finishes a slice, to verify nothing regressed.

## When NOT to use

- As a substitute for writing tests — it only runs what already exists.

## Procedure

Run backend and frontend checks; report which passed and the full output of any
that fail. Do not stop at the first failure — collect results from both stacks.

### Backend (Python + FastAPI)

```powershell
cd backend
ruff check .
black --check .
pytest -q
```

- `ruff check .` — lint (auto-fix with `ruff check --fix .` only if asked).
- `black --check .` — formatting check (apply with `black .` if asked).
- `pytest -q` — unit + smoke tests (model validation, mock API endpoints).

### Frontend (React + TS + Vite)

```powershell
cd frontend
npm run lint
npx tsc --noEmit
npm run test --silent
```

- `npm run lint` — eslint.
- `npx tsc --noEmit` — type-check against the frozen `src/lib/types.ts` contracts.
- `npm run test` — vitest (skip gracefully if no tests yet).

## Reporting

Summarize like: `backend: ruff OK, black OK, pytest 12 passed` /
`frontend: eslint OK, tsc OK, vitest 3 passed`. On failure, show the failing
command's output (stack trace / compiler error) so it can be fixed, then re-run.

## Safety

- Never bypass a failing check by deleting or skipping a test without explicit approval.
- If a dependency is missing, install it with the project's package manager
  (`pip install -e .` / `npm install`) rather than editing lockfiles by hand.
