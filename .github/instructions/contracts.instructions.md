---
applyTo: "backend/app/models.py,backend/app/agents/schemas.py"
---

# Data Contract Instructions (COORDINATED)

These files are part of the data shapes exchanged between layers. They are not the
only contract surface: the implemented backend has **three model layers**, and a
future frontend must mirror the camelCase API layer.

## Current contract layers

1. `backend/app/models.py` — **snake_case** core Pydantic v2 contracts used by
   ingestion and processing (`RawDocument`, `DocChunk`, `GraphEdge`, `EdgeType`).
   These models do not use a `to_camel` alias generator.
2. `backend/app/main.py` — **camelCase API response DTOs** (`Match`,
   `SearchResponse`, `GraphNode`, `GraphResponse`, `DocumentResponse`, etc.). This
   is the JSON shape the frontend will consume, along with camelCase dictionaries
   from `backend/app/storage/queries.py`.
3. `backend/app/agents/schemas.py` — agent structured outputs (`Citation`,
   `ChatAnswer`, `AgentProposal`) used by LangGraph Curator/Guardian endpoints.

The frontend mirror is `frontend/src/lib/types.ts`: its TypeScript types mirror the
camelCase API responses in README §8B and the actual `/chat` and `/propose`
payloads, not the internal snake_case models directly.

## Before you change anything here

- **Stop and confirm with the `director`.** Ordinary feature work consumes these
  contracts but should not casually reshape them. If your code needs a different
  shape, treat that as a coordinated contract change, not a local patch.
- Identify which layer is changing: core snake_case model, API camelCase DTO, agent
  schema, or future frontend type. Update all affected layers and docs/fixtures together.

## Rules when a contract change is approved

1. Preserve the layer boundary: core models may remain snake_case; API responses must
   remain camelCase (`docId`, `commitSha`, `headingPath`, `riskLevel`).
2. Keep `commit_sha`/`commitSha`, chunk IDs, line ranges, confidence, and citations
   available wherever provenance/evidence is required.
3. Pydantic v2 models should be typed explicitly and validate README examples where
   examples exist. Do not add a `to_camel` alias generator to core models unless the
   director intentionally changes that layer's role.
4. Future TypeScript interfaces should mirror the **API JSON** exactly:
   `str→string`, `int|float→number`, `list[X]→X[]`, `Optional[X]→X | null`, nested
   models → nested interfaces. No `any`.
5. Update matching fixtures when they exist (`frontend/src/lib/fixtures.ts`).
6. Verify with the tooling that exists today: `python -m pytest tests -q` (backend),
   `npm run lint` / `npm run test` (frontend), plus the CLI/API smoke path.
7. Announce the change to the affected engineer agents/people.

## Why this matters

Every answer or proposal must be traceable to exact source chunks and commit SHAs.
The whole parallel build depends on stable shapes at each boundary, especially the
snake_case core contracts and the camelCase API contract the frontend will consume.
Treat them with care.
