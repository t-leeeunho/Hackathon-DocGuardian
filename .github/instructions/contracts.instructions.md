---
applyTo: "backend/app/models/**,frontend/src/lib/types.ts"
---

# Data Contract Instructions (FROZEN)

These files are the **single source of truth** for the data shapes exchanged
between every layer (README §8A). They are **frozen**: changing them is a
director-level decision because a mismatch silently breaks serialization between
the backend and frontend.

## Before you change anything here

- **Stop and confirm with the `director`.** Ordinary feature work *consumes* these
  contracts but never edits them. If your code needs a different shape, that's a
  contract change, not a local patch.
- Never edit only one side. A change to a Pydantic model in `backend/app/models/**`
  **must** be mirrored in `frontend/src/lib/types.ts`, and vice versa.

## Rules when a contract change is approved

1. Use the **`contract-sync` skill** — it changes the Pydantic model and the TS
   interface together and updates fixtures.
2. Field names are **camelCase** in JSON on both sides (`docId`, `commitSha`,
   `headingPath`, `riskLevel`). The README §8A examples are authoritative.
3. Pydantic models use `ConfigDict(alias_generator=to_camel, populate_by_name=True)`
   so they serialize camelCase and accept snake_case or camelCase input.
4. TypeScript interfaces mirror the Pydantic model **exactly**: `str→string`,
   `int|float→number`, `list[X]→X[]`, `Optional[X]→X | null`, nested models →
   nested interfaces. No `any`.
5. Update the matching fixtures (`backend/app/fixtures/**`, `frontend/src/lib/fixtures.ts`).
6. Verify both sides: `cd backend && pytest -q` (a model must validate its README
   example) and `cd frontend && npx tsc --noEmit`.
7. Announce the change to the affected engineer agents/people.

## Why this matters

Every node in the graph can be traced to an exact commit because `commitSha` is
propagated through every contract. The whole "four people in parallel" model
depends on these shapes being stable and identical on both sides. Treat them with
care.
