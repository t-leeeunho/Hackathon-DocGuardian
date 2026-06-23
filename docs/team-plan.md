# DocGuardian AI — Team Plan & General TODOs

> Read `general-plan.md` first. This document defines **who owns what**, the
> **parallel execution model**, the **milestones**, and the **general (shared)
> todos**. Each person's detailed todos live in `docs/team/person-N-*.md`.

---

## 1. The Team (4 people + a shared foundation)

Roles mirror the README §15 split. The four workstreams map 1:1 to the four
engineers; everyone collaborates on the shared **Phase 0** foundation and on
integration/demo.

| Person | Role | Primary domain | Detailed plan |
| --- | --- | --- | --- |
| **P1** | Frontend & Demo Experience | The React UI: graph, chat, diff/review, drop-off, metrics, provenance, "show your work" | `docs/team/person-1-frontend.md` |
| **P2** | Retrieval & Document Intelligence | Ingestion, processing, embeddings, search, duplicate/conflict detection | `docs/team/person-2-retrieval.md` |
| **P3** | Agent Orchestration & AI Reasoning | Orchestrator, Curator & Guardian agents, provider abstraction, evidence/confidence, chat RAG | `docs/team/person-3-ai-orchestration.md` |
| **P4** | Governance, Verification & Metrics | ACL, approval flow, provenance, rollback, store, metrics, sandbox, API plumbing | `docs/team/person-4-governance.md` |

> **Fewer than 4 people?** Merge adjacent roles: P2+P3 (the AI/retrieval backend)
> and P1+P4 (UI + governance/API) are the natural pairs. The plan still holds —
> the contracts and milestones don't change.

---

## 2. Ownership Map (guarantees no merge conflicts)

The single most important coordination artifact. Each person edits only their own
directories and their own API router file. The **shared/frozen** files are changed
only by the director (whoever is driving Phase 0 / integration).

### 2.1 Shared & frozen (director-only after M1)
- `backend/app/models/**` — Pydantic data contracts.
- `frontend/src/lib/types.ts` — mirrored TypeScript contracts.
- `backend/app/main.py` — router wiring (one line per router, set in Phase 0).
- `repos.config.json` — ingestion sources.
- `.env.example`, root tooling configs.

### 2.2 Per-person ownership

| Person | Owns (directories) | Owns (API router file) |
| --- | --- | --- |
| **P1** | `frontend/src/**` (components, hooks, `lib/api.ts`, `lib/ws.ts`, styles) | — (consumes the API) |
| **P2** | `backend/app/ingestion/**`, `backend/app/processing/**`, `backend/app/ai/embeddings.py`, `backend/app/services/retrieval.py`, `backend/app/services/dedup_conflict.py`, `backend/app/store/vector_*.py` | `backend/app/api/ingest.py`, `backend/app/api/search.py` |
| **P3** | `backend/app/ai/orchestrator.py`, `backend/app/ai/agents/**`, `backend/app/ai/providers/**` | `backend/app/api/documents.py`, `backend/app/api/chat.py` |
| **P4** | `backend/app/services/governance.py`, `backend/app/services/verification.py`, `backend/app/store/sqlite_*.py`, job queue | `backend/app/api/graph.py`, `backend/app/api/proposals.py`, `backend/app/api/metrics.py`, `backend/app/api/stream.py` |

> **Rule:** if you need a change to a frozen file, ask the director. Never edit
> another person's directory or router file. Talk to services through their
> interfaces, not their source files.

---

## 3. Parallel Execution Model

| Phase | Who | What |
| --- | --- | --- |
| **Phase 0 — Foundation** | All (one driver) | Scaffold layout; **freeze contracts** (Pydantic + TS); provider/store interfaces + **fakes**; **mock API + fixtures**; tooling; `repos.config.json`. |
| **Build (parallel)** | P1 ‖ P2 ‖ P3 ‖ P4 | Each builds their slice against mocks/fakes — see per-person docs. |
| **Integration** | All | Swap fakes → real; wire SQLite store + real routers; flip frontend mock → real. |
| **Demo polish** | All | Seed repos + planted fixtures; live metrics over WS; accessibility; rehearse. |

### What each person develops against (before integration)
- **P1** → mock API + local fixtures (`GraphDTO`, `ChatAnswer`, `AgentProposal`, `MetricsDTO`).
- **P2** → `FakeEmbeddingProvider` + real git clones (clones are independent, start immediately).
- **P3** → sample `SearchResult` fixtures + `FakeLLMProvider`.
- **P4** → sample `AgentProposal` fixtures.

---

## 4. Milestones (definition + owner)

| Milestone | Definition | Gate for |
| --- | --- | --- |
| **M1** | Contracts frozen; mock API live; frontend renders mocks end-to-end | Unblocks all parallel work |
| **M2** | P2 real retrieval + P3 real Curator/Guardian replace fakes (still local store) | Real reasoning over real chunks |
| **M3** | P4 SQLite store + governance + real routers replace mock API; P1 flips client mock→real | Real end-to-end pipeline |
| **M4** | Seeded planted stale/duplicate/conflict fixtures; live metrics over WS; reduced-motion; rehearsed 9-step demo | Demo-ready |

---

## 5. GENERAL TODOs (shared / sequenced)

These are the cross-team todos. Per-person build todos are in the individual docs.

### 5.A Phase 0 — Foundation (must complete first → M1)
- [ ] **G1.** Create monorepo layout: `backend/` (FastAPI), `frontend/` (Vite+React), `data/` (gitignored), `repos.config.json`, `.env.example`.
- [ ] **G2.** **Freeze data contracts** — author every contract in §7 of the general plan as Pydantic v2 models (`backend/app/models/`), camelCase JSON, accepting snake/camel input.
- [ ] **G3.** **Mirror contracts to TypeScript** — `frontend/src/lib/types.ts`, identical camelCase shape.
- [ ] **G4.** Define provider interfaces `LLMProvider` / `EmbeddingProvider` + Azure stubs + working fakes.
- [ ] **G5.** Define `Store` / `VectorIndex` interfaces + `InMemoryStore` + fake vector index.
- [ ] **G6.** **Mock API**: one router file per domain, each returning fixture JSON; wire all routers once in `main.py`. Endpoints: `POST /ingest/refresh`, `GET /graph`, `GET /search`, `POST /documents`, `GET /proposals/:id`, `POST /proposals/:id/approve`, `GET /metrics`, `WS /stream`.
- [ ] **G7.** Fixtures for `GraphDTO`, `ChatAnswer`, `AgentProposal`, `MetricsDTO`, `SearchResult`, `DocChunk`, `RawDocument` (reuse README §8A examples so they validate).
- [ ] **G8.** Tooling: backend ruff + black + pytest; frontend eslint + tsc + vitest; `.env.example`; update `.gitignore` (node_modules, dist, data, *.db, .env).
- [ ] **G9.** Smoke tests: app imports, `GET /graph` returns a valid `GraphDTO`, each model validates its README example.
- [ ] **M1 GATE:** frontend renders the mock graph/chat/diff/metrics end-to-end.

### 5.B Integration (after parallel build → M2/M3)
- [ ] **G10.** Replace `FakeEmbeddingProvider`/`FakeLLMProvider` with real Azure-backed providers behind the same interfaces (config-switched).
- [ ] **G11.** Replace `InMemoryStore` with the SQLite `Store`; keep the interface identical.
- [ ] **G12.** Replace each mock router body with the real service call (P2/P3/P4 each own their routers).
- [ ] **G13.** Flip the frontend client from `VITE_USE_MOCK` to the real API + WS.
- [ ] **G14.** End-to-end test of the drop-off → proposal → approve → provenance → metrics flow.

### 5.C Demo polish (→ M4)
- [ ] **G15.** Configure 1–2 seed repos in `repos.config.json`; run ingestion (sparse/shallow clone).
- [ ] **G16.** **Seed planted fixtures** — obvious stale, duplicate, and conflicting docs that reliably trigger detection/proposal/approval.
- [ ] **G17.** Wire live updates: proposals/graph/health/metrics over `WS /stream`.
- [ ] **G18.** Accessibility pass: `prefers-reduced-motion` fallback for graph highlight.
- [ ] **G19.** Rehearse the 9-step demo; prepare a fallback recording.

---

## 6. Cross-Cutting Rules (everyone, always)

- **Provenance everywhere** — every chunk/edge/proposal/record carries its originating `commitSha`.
- **Idempotency** — re-processing an unchanged `contentHash` is a no-op.
- **Permission propagation** — ACLs enforced at retrieval, answer, and write; the frontend never receives inaccessible content.
- **Evidence or silence** — no answer/edit without supporting chunk IDs + commit SHAs + a confidence score; weak evidence ⇒ explicit "needs human review."
- **Config-driven sources** — onboarding a repo is a `repos.config.json` change only.
- **Contracts are sacred** — match the README field names exactly; mismatches silently break serialization between layers.

---

## 7. Definition of Done / Quality Gates

A slice is "done" when:
- It honors the frozen contracts exactly (names + types).
- Backend: `ruff check` + `black --check` + `pytest -q` pass for the touched modules.
- Frontend: `npm run lint` + `npx tsc --noEmit` + `npm run test` pass.
- It works against mocks **and** (post-integration) against the real dependency.
- Edge cases are handled, not just the happy path (empty results, low confidence,
  inaccessible docs, unchanged content, deleted docs).

---

## 8. Communication Protocol

- **Contract change?** → director updates `models/` + `types.ts` together, keeps the
  camelCase JSON shape, and announces it. No one else edits those files.
- **Need another person's output before integration?** → use the fixtures/fakes;
  don't wait.
- **Blocked?** → mark it, state the assumption you're proceeding with, and keep moving.
- **Before integrating** → run the quality gate (§7) and reconcile against the contracts.
