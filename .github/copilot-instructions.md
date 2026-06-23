# DocGuardian AI — Copilot Instructions

These instructions apply to **all** Copilot work in this repository. Follow them
unless a more specific `.github/instructions/*.instructions.md` file overrides them
for a path.

## Project context

**DocGuardian AI** is an AI-powered documentation governance platform: it ingests
real engineering docs, detects stale / duplicate / conflicting content, proposes
**evidence-backed** fixes via two LLM agents (Curator + Guardian), and presents
everything in an interactive knowledge graph with human approval, provenance, and
rollback.

- Product spec: `README.md` (architecture + data-contract JSON schemas in §8A).
- Implementation plan: `docs/general-plan.md`, `docs/team-plan.md`, `docs/team/person-1..4-*.md`.
- This is a 4-person hackathon build organized for **parallel work** (see below).

## Golden rules (non-negotiable)

1. **Contracts are frozen.** The data contracts live once as Pydantic models in
   `backend/app/models/**` and are mirrored as TypeScript in
   `frontend/src/lib/types.ts`. **Do not edit either** outside a director-led
   contract change. Both sides must stay identical with **camelCase JSON** field
   names (`docId`, `commitSha`, `headingPath`, `riskLevel`). To change a contract,
   use the `contract-sync` skill and update both sides + fixtures together.
2. **Stay in your lane.** Each person owns specific directories and **their own API
   router file** (see `docs/team-plan.md` §2). Never edit another person's files,
   the frozen contract files, or `backend/app/main.py` (router wiring is set once in
   Phase 0). This is what keeps four people conflict-free.
3. **Mock-first.** Develop against the mock API and fakes (`FakeLLMProvider`,
   `FakeEmbeddingProvider`, `InMemoryStore`); never block on Azure or on another
   person's code. Swap fakes → real behind the same interface at integration.

## Stack & versions

- **Backend:** Python **3.11+**, FastAPI (REST + WebSocket), Pydantic **v2**.
- **Frontend:** React + TypeScript + Vite + Tailwind + shadcn/ui + React Flow (`@xyflow/react`), 2D graph for MVP.
- **Storage:** local-first SQLite + a local vector store, behind `Store`/`VectorIndex` interfaces (Azure-ready).
- **LLM/embeddings:** provider-abstracted (`LLMProvider`/`EmbeddingProvider`), default Azure OpenAI, with fakes.

## Naming & style

- Contract JSON fields are **camelCase**; Python internals are **snake_case**
  (Pydantic models map via `alias_generator=to_camel` + `populate_by_name=True`).
- TypeScript interfaces mirror the Pydantic models **exactly** (names + types).
- Prefer clear, typed code. **No `any`** for a contract type in TypeScript. Use
  type hints in Python. Only comment code that genuinely needs clarification.

## Product invariants (always uphold)

- **Evidence-or-silence.** No AI answer or proposed edit without supporting
  `chunkId`s + `commitSha`s + a `confidence` score. `confidence < 0.5` or no
  supporting chunk ⇒ the explicit "needs human review" path. Never invent sources.
- **Permissions.** Enforce ACLs at retrieval, answer, **and** write. Never surface
  content the user cannot access to any layer.
- **Provenance.** Every governed write records a `ProvenanceEntry` (what / who /
  which agent / why / sources / previous version) and supports rollback.
- **Idempotency.** Re-processing an unchanged `contentHash` is a no-op.
- **Cost.** ≤2 LLM calls per proposal (Curator + Guardian); the orchestrator itself
  uses **no** LLM. Everything deterministic (search, dedup, git, ACL, sandbox) is a service.

## Quality gate (run before declaring work done)

- **Backend:** `ruff check`, `black --check`, `pytest -q`.
- **Frontend:** `npm run lint`, `npx tsc --noEmit`, `npm run test`.
- Use the `run-checks` skill to run both at once. Handle edge cases (empty results,
  low confidence, inaccessible docs, unchanged content, deleted docs), not just the
  happy path.

## Commits

- Use **Conventional Commits** (`feat:`, `fix:`, `docs:`, `chore:`, `refactor:`,
  `test:`, `style:`). Keep the summary ≤72 chars, imperative mood.
- Use the `commit-and-push` skill to stage, message, and push.
- Never commit secrets. Never force-push or rewrite published history without
  explicit confirmation.

## Agents & skills available

- **Agents** (`.github/agents/`): `director` (architecture, contracts, integration),
  `frontend`, `retrieval`, `ai-orchestration`, `governance` (the four build roles).
- **Skills** (`.github/skills/`): `commit-and-push`, `ingest-repo` (sparse-clone a
  doc source), `run-checks` (lint+test both stacks), `contract-sync` (Pydantic ⇄ TS),
  `seed-demo-fixtures` (planted stale/dup/conflict docs), `new-endpoint` (scaffold a
  router + contract + TS type + fixture consistently).

> When in doubt about scope, ownership, or a contract shape, consult the relevant
> `docs/` plan or ask the `director` — do not guess and edit a frozen or
> other-owned file.
