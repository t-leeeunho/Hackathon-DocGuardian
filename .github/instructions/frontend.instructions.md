---
applyTo: "frontend/**"
---

# Frontend Instructions (React + TypeScript)

Applies to all files under `frontend/`. Read alongside `.github/copilot-instructions.md`.

## Language & style

- **TypeScript only**, `strict` mode. **Never use `any` for a contract type** —
  import the type from `src/lib/types.ts`.
- **Function components + hooks** only (no class components).
- Lint with **eslint**, type-check with **tsc** (`npx tsc --noEmit`), test with **vitest**.
- Keep components small and focused; lift shared logic into `src/hooks/**`.

## Contracts

- `src/lib/types.ts` is the **frozen** mirror of the backend Pydantic models — do
  **not** edit it to work around a mismatch. If a real payload differs from the
  type, that's a contract bug for the `director`.
- All API/WS data is typed with these contracts: `GraphDTO`, `ChatAnswer`,
  `AgentProposal`, `MetricsDTO`, `GraphHighlightEvent`.

## Data access (mock-first)

- Use the `VITE_USE_MOCK` flag: when `true`, `src/lib/api.ts` and `src/lib/ws.ts`
  return local fixtures / replay mock events; when `false`, they call the real REST
  API and `WS /stream`. Flipping the flag is the main M3 integration switch —
  component contracts must not change between the two modes.
- Keep fixtures in `src/lib/fixtures.ts`, shaped exactly like the contracts.

## Styling & UI

- Use **Tailwind** utility classes and **shadcn/ui** components for cards, buttons,
  badges, panels, tabs, dialogs, and toasts. Keep a consistent design language.
- Graph rendering uses **React Flow** (`@xyflow/react`). Node IDs equal `docId`.

## Graph & visual semantics (match the spec)

- Node **color** from `health`: green = fresh/verified, yellow = aging, red =
  stale/conflicting/broken, gray/locked = inaccessible (README §7.9).
- Node **size** from `importance`/`size` (§7.10) — normalize in the API adapter, not
  by editing the contract.
- `conflicts-with` edges render as **red dashed** lines (§7.13); keep them the
  strongest warning signal vs calmer `references`/`duplicate-of`/`deprecated-by` edges.
- Inaccessible nodes get **permission fog** (dimmed/blurred/locked), never their content (§7.14).

## "Show your work" & accessibility

- Map `ChatAnswer.citations[]` → `GraphHighlightEvent` and gently pulse/glow cited
  nodes (glow derived from health color; intensity from relevance; auto-fade after `ttlMs`).
- **Respect `prefers-reduced-motion`** — fall back to a static halo, no pulsing.
- Ensure keyboard focus, sufficient contrast, and labels on interactive controls.

## Performance & quality

- Use chunked/lazy rendering so large graphs stay responsive (README §7.3).
- Run `npm run lint`, `npx tsc --noEmit`, `npm run test` before finishing. Handle
  empty/loading/error and low-confidence/needs-review states, not just the happy path.
