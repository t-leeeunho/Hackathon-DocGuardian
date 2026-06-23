# Contributing to DocGuardian AI

Welcome! This guide explains **how we work** so four people can build DocGuardian AI
in parallel with Copilot without stepping on each other. For the full plan, read
[`docs/`](docs/README.md); for the product spec, read [`README.md`](README.md).

> **Status:** planning complete, build not yet started. The repo currently holds the
> spec, the plans in `docs/`, and the Copilot agents/skills/instructions in `.github/`.

---

## TL;DR — the three rules that make parallel work possible

1. **Contracts-first.** All cross-layer data shapes are frozen as Pydantic models
   (`backend/app/models/`) mirrored as TypeScript (`frontend/src/lib/types.ts`).
   Only the director changes them. Keep camelCase JSON parity on both sides.
2. **Mock-everything.** Build against the mock API and fakes
   (`FakeLLMProvider`, `FakeEmbeddingProvider`, `InMemoryStore`) so nobody blocks on
   Azure or on another person's code. Swap fakes → real behind the same interfaces.
3. **Stay in your lane.** Each person owns specific directories and **their own API
   router file**. Never edit another person's files, the frozen contracts, or
   `backend/app/main.py`. See the ownership map in
   [`docs/team-plan.md`](docs/team-plan.md) §2.

---

## Roles & ownership

| Person | Role | Detailed plan |
| --- | --- | --- |
| P1 | Frontend & Demo Experience | [`docs/team/person-1-frontend.md`](docs/team/person-1-frontend.md) |
| P2 | Retrieval & Document Intelligence | [`docs/team/person-2-retrieval.md`](docs/team/person-2-retrieval.md) |
| P3 | Agent Orchestration & AI Reasoning | [`docs/team/person-3-ai-orchestration.md`](docs/team/person-3-ai-orchestration.md) |
| P4 | Governance, Verification & Metrics | [`docs/team/person-4-governance.md`](docs/team/person-4-governance.md) |

The full file/directory ownership table is in
[`docs/team-plan.md`](docs/team-plan.md) §2.

---

## Workflow

1. **Read** [`docs/general-plan.md`](docs/general-plan.md), then
   [`docs/team-plan.md`](docs/team-plan.md), then your `docs/team/person-N` plan.
2. **Phase 0 (shared):** land the foundation — scaffold, **frozen contracts**,
   provider/store interfaces + fakes, **mock API + fixtures**, tooling. Exit when the
   frontend renders mock graph/chat/diff/metrics end-to-end (**Milestone M1**).
3. **Build in parallel:** each person implements their slice against mocks/fakes.
4. **Integrate:** **M2** swap fakes → real; **M3** wire the SQLite store + real
   routers and flip the frontend from mock → real API.
5. **Demo polish (M4):** seed 1–2 repos with planted stale/duplicate/conflict
   fixtures, wire live metrics over WebSocket, accessibility pass, rehearse.

Milestones are defined in [`docs/team-plan.md`](docs/team-plan.md) §4, and the
shared (general) TODOs in §5.

---

## Tech stack

- **Backend:** Python 3.11+, FastAPI (REST + WebSocket), Pydantic v2.
- **Frontend:** React + TypeScript + Vite + Tailwind + shadcn/ui + React Flow (2D).
- **Storage:** local-first SQLite + a local vector store (Chroma/FAISS), behind interfaces.
- **LLM/embeddings:** provider-abstracted, default Azure OpenAI, with fakes.

Conventions are enforced automatically by Copilot via
[`.github/copilot-instructions.md`](.github/copilot-instructions.md) and the
path-specific files in [`.github/instructions/`](.github/instructions/).

---

## Copilot agents & skills

This repo ships Copilot **agents** and **skills** to speed up and standardize the build.

**Agents** ([`.github/agents/`](.github/agents/)) — invoke with `@<name>`:
- `@director` — architecture, frozen contracts, integration, demo coordination.
- `@frontend`, `@retrieval`, `@ai-orchestration`, `@governance` — the four build roles.

**Skills** ([`.github/skills/`](.github/skills/)):
- `ingest-repo` — sparse/shallow clone a documentation source.
- `run-checks` — run lint + tests for backend **and** frontend in one pass.
- `contract-sync` — change a data contract as Pydantic **and** TypeScript together.
- `seed-demo-fixtures` — generate planted stale/duplicate/conflict docs for the demo.
- `new-endpoint` — scaffold a new API route + contract + TS type + fixture consistently.
- `commit-and-push` — stage, write a Conventional Commit message, and push.

---

## Quality gate (before every PR)

- **Backend:** `ruff check`, `black --check`, `pytest -q`.
- **Frontend:** `npm run lint`, `npx tsc --noEmit`, `npm run test`.
- Or run the **`run-checks`** skill to do both at once.
- Cover edge cases (empty results, low confidence, inaccessible docs, unchanged
  content, deleted docs), not just the happy path.

## Commits & PRs

- **Conventional Commits** (`feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`,
  `style:`); summary ≤72 chars, imperative mood. The `commit-and-push` skill helps.
- Keep PRs scoped to your ownership area. A PR touching a frozen contract or another
  person's files needs director sign-off.
- Never commit secrets. Never force-push shared history without explicit agreement.

## Definition of Done

A slice is done when it honors the frozen contracts exactly, passes the quality
gate, works against mocks **and** (post-integration) the real dependency, and
handles edge cases. See [`docs/team-plan.md`](docs/team-plan.md) §7.

---

## Product invariants (never violate)

- **Evidence-or-silence:** no AI answer/edit without supporting chunk IDs + commit
  SHAs + confidence; `< 0.5` ⇒ human review. Never invent sources.
- **Permissions:** enforce ACLs at retrieval, answer, and write.
- **Provenance:** every governed write is logged and reversible.
- **Idempotency:** unchanged `contentHash` ⇒ no re-processing.
- **Cost:** ≤2 LLM calls per proposal; the orchestrator uses no LLM.
