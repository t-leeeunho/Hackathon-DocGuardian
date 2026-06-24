---
name: new-endpoint
description: >-
  Scaffold a new DocGuardian API endpoint consistently across all layers — the
  FastAPI route (in the owner's router file), its request/response contracts, the
  mirrored TypeScript type, a fixture, and the frontend client call. USE WHEN the
  user wants to "add an endpoint", "add an API route", "expose <X> over the API", or
  wire a new backend route to the frontend. Keeps ownership and contract rules intact.
---

# New Endpoint (consistent cross-layer route scaffold)

Add a new REST (or WebSocket) endpoint the same way every time, so the API stays
coherent and the ownership/contract rules are never broken.

## When to use

- Adding a new route to one of the existing domain routers, or a genuinely new
  domain router (with director sign-off).

## When NOT to use

- To change an existing data contract — use the `contract-sync` skill instead.
- To add a route in someone else's router file — only the owner edits their router
  (see `docs/team-plan.md` §2.2).

## Procedure

### 1. Confirm ownership & placement

Identify which **domain router** the endpoint belongs to and confirm you own it:

| Router file | Owner | Endpoints |
| --- | --- | --- |
| `api/ingest.py`, `api/search.py` | P2 (retrieval) | ingestion + search |
| `api/documents.py`, `api/chat.py` | P3 (ai-orchestration) | intake/proposals + chat |
| `api/graph.py`, `api/proposals.py`, `api/metrics.py`, `api/stream.py` | P4 (governance) | graph, proposals, metrics, WS |

`app/main.py` already wires every router (director-owned) — do **not** edit it to
add a route inside an existing router.

### 2. Define / reuse the contracts

- If request/response shapes already exist in `backend/app/models/**`, **reuse them**.
- If a **new** shape is needed, that's a contract change → run the `contract-sync`
  skill (Pydantic + mirrored TS together, camelCase). Never inline an ad-hoc dict.

### 3. Add the route in your router file

- Add a typed handler that accepts/returns the contract models; prefer `async def`.
- Keep heavy work off the request path (enqueue to the job queue).
- Enforce ACLs if the route reads or writes governed content.
- Before real services exist, return the matching **fixture** (mock-first), guarded
  so it's easy to swap for the real service call at integration.

### 4. Add a fixture

Add a representative example to `backend/app/fixtures/` (and
`frontend/src/lib/fixtures.ts`) so the mock API and the frontend can render it
before the real implementation lands.

### 5. Wire the frontend client

- Add the typed call in `frontend/src/lib/api.ts` (or `ws.ts` for streams), honoring
  the `VITE_USE_MOCK` flag (fixture in mock mode, real fetch otherwise).
- Type the call with the contract from `src/lib/types.ts` — no `any`.

### 6. Test & verify

- Backend: a `pytest` test that the route returns a schema-valid response.
- Run the `run-checks` skill (backend + frontend) and fix anything red.

## Rules

- Stay within your owned router file; route contract changes through `contract-sync`.
- Match the API surface conventions in `README.md` §8A.5 (method, path, payload).
- Mock-first, then swap to the real service behind the same signature at integration.
