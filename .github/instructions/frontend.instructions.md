---
applyTo: "frontend/**"
---

# Frontend Instructions (React + TypeScript)

Applies to all files under `frontend/`. Read alongside `.github/copilot-instructions.md`.

> As of the as-built snapshot in `docs/implementation-status.md`, **no frontend exists yet**.
> The guidance below is the intended frontend convention once it is scaffolded.

## Language & style

- **TypeScript only**, `strict` mode. **Never use `any` for a contract type** — once
  `src/lib/types.ts` exists, import shared API types from there.
- **Function components + hooks** only (no class components).
- When the frontend is set up, lint with **eslint**, type-check with **tsc**
  (`npx tsc --noEmit`), and test with **vitest**.
- Keep components small and focused; lift shared logic into `src/hooks/**`.

## Contracts

- There is currently no `frontend/src/lib/types.ts`. When created, it must mirror the
  **camelCase API responses** implemented by the backend and documented in README §8B
  (`docId`, `chunkId`, `headingPath`, `lineRange`, `commitSha`, etc.).
- Do not mirror the backend's snake_case core models directly into UI payloads. Core
  ingestion/processing models live in `backend/app/models.py`; frontend-facing DTOs
  currently live in `backend/app/main.py` and `backend/app/storage/queries.py`.
- Agent payloads should match `backend/app/agents/schemas.py` plus the runtime fields
  returned by `/chat` and `/propose`.
- If a real payload differs from the frontend type, treat it as a coordinated contract
  issue for the director rather than a local workaround.

## Data access

- Build against the real REST API shape in README §8B and `app/main.py`: `/health`,
  `/search`, `/documents`, `/tree`, `/graph`, `/documents/{docId}`, `/chat`, and
  `/propose`.
- `/chat` and `/propose` require Azure OpenAI chat on the backend and return 503 when
  Azure is unconfigured. The ingestion/search/tree/graph/document paths run locally
  with Postgres + pgvector and local fastembed embeddings.
- Mock fixtures are useful for UI development, but no mock API or WebSocket layer is
  implemented yet. `WS /stream`, metrics, proposal approval, ACL, and provenance UI
  are planned, not current endpoints.

## Styling & UI

- Use **Tailwind** utility classes and **shadcn/ui** components for cards, buttons,
  badges, panels, tabs, dialogs, and toasts. Keep a consistent design language.
- Graph rendering uses **React Flow** (`@xyflow/react`). Node IDs equal `docId`.
- Use **Monaco** for code/diff-style document editing or preview surfaces.

## Graph & visual semantics (match the spec)

- Node **color** from `health`: green = fresh/verified, yellow = aging, red =
  stale/conflicting/broken, gray/locked = inaccessible (README §7.9). Note that
  backend graph health/accessibility are placeholders today.
- Node **size** from `importance`/`size` (§7.10) — normalize in the API adapter, not
  by editing the contract.
- `conflicts-with` edges render as **red dashed** lines (§7.13); keep them the
  strongest warning signal vs calmer `references`/`duplicate-of`/`deprecated-by` edges.
- Inaccessible nodes get **permission fog** (dimmed/blurred/locked), never their content (§7.14).

## "Show your work" & accessibility

- Map `ChatAnswer.citations[]` → graph highlights and gently pulse/glow cited nodes
  (glow derived from health color; intensity from relevance; auto-fade after `ttlMs`).
- **Respect `prefers-reduced-motion`** — fall back to a static halo, no pulsing.
- Ensure keyboard focus, sufficient contrast, and labels on interactive controls.

## Performance & quality

- Use chunked/lazy rendering so large graphs stay responsive (README §7.3).
- Once the frontend exists, run `npm run lint`, `npx tsc --noEmit`, and `npm run test`
  before finishing. Handle empty/loading/error and low-confidence/needs-review states,
  not just the happy path.
