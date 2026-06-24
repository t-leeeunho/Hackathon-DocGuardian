# DocGuardian AI — Team Plan & General TODOs

> Read `general-plan.md` first. This document defines **who owns what**, the
> **parallel execution model**, the **milestones**, and the **general (shared)
> todos**. Each person's detailed todos live in `docs/team/person-N-*.md`.
>
> **As-built note (2026-06-24):** the backend (ingestion → processing →
> embeddings → pgvector retrieval → LangGraph agents → FastAPI) is implemented,
> **plus governance** (ACL, approval/rollback, provenance, conflict detection,
> health, `/metrics`), a **real Docker verification sandbox**, and async ingest +
> `WS /stream`. The frontend is **scaffolded and buildable**. The ownership map below
> reflects the **actual** layout. See
> [`implementation-status.md`](implementation-status.md) for the ground truth.

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

The single most important coordination artifact. Each person works mainly in their
own area; a few **shared** files are changed only by the director.

### 2.1 Shared files (director-coordinated)
- `backend/app/models.py` — core snake_case contracts (`RawDocument`, `DocChunk`, `GraphEdge`).
- `backend/app/main.py` — **all** FastAPI endpoints + camelCase response DTOs live here
  today (a per-domain router split is a future refactor).
- `backend/repos.config.json` — ingestion sources.
- `backend/app/storage/db.py` — the Postgres schema (`init_schema`), touched by P2 + P4.
- `backend/.env.example`, `backend/requirements.txt`, `backend/docker-compose.yml`.
- `frontend/src/lib/types.ts` — the camelCase API mirror (README §8B); **exists**.

### 2.2 Per-person ownership (actual paths; ✅ = exists, ⬜ = to build)

| Person | Owns (directories / files) | API endpoints |
| --- | --- | --- |
| **P1** | `frontend/**` 🟡 (scaffolded: components, hooks, API/WS client, styles) | consumes the API (README §8B) |
| **P2** | `backend/app/ingestion/**` ✅, `backend/app/processing/**` ✅ (incl. `conflicts.py`, `summarize.py`), `backend/app/embeddings/provider.py` ✅, `backend/app/storage/vectorstore.py` ✅, `backend/scripts/**` ✅ | `GET /search` ✅, `POST /documents` ✅, `POST /ingest/refresh` ⬜ |
| **P3** | `backend/app/agents/**` ✅ (`graph.py` LangGraph, `llm.py` Azure, `schemas.py`) | `POST /chat` ✅, `POST /propose` ✅ |
| **P4** | `backend/app/storage/db.py` + `queries.py` ✅, `backend/app/governance/**` ✅, `backend/app/services/**` ✅ (verification/events/jobs) | `GET /graph` ✅, `GET /documents/{id}` ✅, `GET /metrics` ✅, `POST /proposals/:id/approve` ✅, `POST /proposals/:id/rollback` ✅, `POST /verify` ✅, `WS /stream` ✅ |

> **Note:** today the API is one `app/main.py` and `app/storage/` is shared by P2
> (vectors) and P4 (metadata/graph). Splitting into per-domain routers and separate
> service modules is a planned refactor — coordinate it through the director rather
> than racing edits into `main.py`.

---

## 3. Execution Model — what's done, what's next

The backend was built first (foundation → ingestion → processing → embeddings →
retrieval → agents → API). The remaining work can now proceed largely **in
parallel against the live API** (README §8B): the frontend, duplicate/conflict
detection + health scoring, and the governance/metrics/verification layer.

| Track | Status | What's left |
| --- | --- | --- |
| Backend foundation + pipeline + agents | ✅ done | — |
| P2 — duplicate/conflict detection + node health | ✅ done | (tuning thresholds for the demo) |
| P4 — governance / metrics / verification | ✅ done | demo seed data |
| P1 — frontend | 🟡 scaffolded | wire governance panels (approve/metrics/provenance) to live endpoints |
| Demo polish | ⬜ later | planted fixtures, rehearse the 9-step demo |

### What each person builds against (today)
- **P1** → the **real** backend API (README §8B); no mock needed (CORS already allows `localhost:5173`).
- **P2** → real git clones + local fastembed + pgvector (all run offline).
- **P3** → real pgvector retrieval; **Azure OpenAI required** for `/chat` + `/propose`.
- **P4** → the existing Postgres store + real `AgentProposal`s from `/propose`.

---

## 4. Milestones (restated against current status)

| Milestone | Definition | Status |
| --- | --- | --- |
| **M1** | Backend pipeline + retrieval API live (ingest → chunk → embed → pgvector → `/search`) | ✅ reached |
| **M2** | LangGraph Curator/Guardian agents live (`/chat`, `/propose`) | ✅ reached |
| **M3** | Duplicate/conflict detection + node health scoring feed a real `/graph` | ✅ reached |
| **M4** | Governance (ACL/approval/provenance) + `/metrics` + verification + `WS /stream` | ✅ reached |
| **M5** | Frontend on the live API + rehearsed 9-step demo | 🟡 frontend scaffolded; demo wiring next |

---

## 5. GENERAL TODOs (status-aware)

Per-person build todos are in the individual docs. ✅ = done, ⬜ = remaining.

### 5.A Foundation + pipeline — DONE
- [x] **G1.** `backend/` layout + `repos.config.json` (4 repos) + `.env.example` + `requirements.txt` + `docker-compose.yml` (Postgres+pgvector).
- [x] **G2.** Core contracts in `app/models.py` (snake_case `RawDocument`/`DocChunk`/`GraphEdge`) + agent schemas in `app/agents/schemas.py`.
- [x] **G3.** Embedding provider abstraction (`app/embeddings/provider.py`): local fastembed default + Azure option.
- [x] **G4.** Postgres+pgvector store (`app/storage/`): schema, upserts, HNSW cosine search.
- [x] **G5.** Ingestion + processing (`app/ingestion/`, `app/processing/`) + CLI (`scripts/`).
- [x] **G6.** FastAPI API (`app/main.py`): `/health`, `/search`, `/documents`, `/tree`, `/graph`, `/documents/{id}`, `/chat`, `/propose`.
- [x] **G7.** LangGraph Curator/Guardian graphs (`app/agents/graph.py`) + Azure chat factory (`app/agents/llm.py`).

### 5.B Remaining shared work
- [x] **G8.** Duplicate detection (`duplicate-of` at score ≥ 0.92) + conflict seeding (`conflicts-with` at ≥ 0.85) — `app/processing/conflicts.py`.
- [x] **G9.** Node **health/freshness scoring** + importance — `app/governance/health.py` (replaces the old `/graph` placeholders).
- [x] **G10.** Governance: ACL columns + enforcement at retrieval/answer/write — `app/governance/acl.py`.
- [x] **G11.** Approval flow + `POST /proposals/:id/approve`; provenance log + one-click rollback — `app/governance/service.py` + Postgres `proposals`/`provenance`.
- [x] **G12.** Metrics aggregation + `GET /metrics` — `app/governance/metrics.py`.
- [x] **G13.** Verification sandbox (real containerized run) — `app/services/verification.py`.
- [x] **G14.** `WS /stream` live updates + async ingest (`202`+job). `POST /ingest/refresh` still **TODO**.
- [ ] **G15.** Wire the frontend governance panels (approve/metrics/provenance) to the live endpoints + demo seed data.
- [ ] **G15.** Frontend (entire) on the live API; create `frontend/src/lib/types.ts` mirroring README §8B.
- [ ] **G16.** Richer `AgentProposal` (structured `diff{}`, `evidence[]`, `verification{}`) per README §8A.4.

### 5.C Hygiene + demo — TODO
- [ ] **G17.** (Recommended) add dev tooling: ruff + black + pytest (backend), eslint + tsc + vitest (frontend) — *not configured yet*.
- [ ] **G18.** (Optional refactor) split `app/main.py` into per-domain routers + extract `services/`.
- [ ] **G19.** Seed planted stale/duplicate/conflict fixtures; accessibility pass; rehearse the 9-step demo.

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
- It honors the contract shapes (core snake_case models in `app/models.py`; camelCase
  API DTOs in `app/main.py` per README §8B; agent schemas in `app/agents/schemas.py`).
- It runs: today, verify the backend by running the CLI (`python -m scripts.run_ingest`,
  `scripts.load_vectors`, `scripts.search`) and the API (`uvicorn app.main:app --reload`,
  check Swagger at `/docs`). *(ruff/black/pytest and the frontend `eslint`/`tsc`/`vitest`
  gates are recommended but not configured yet — see G17.)*
- Edge cases are handled, not just the happy path (empty results, low confidence /
  weak evidence → needs-human-review, unchanged content, deleted docs).

---

## 8. Communication Protocol

- **Contract change?** → coordinate through the director. Core models live in
  `app/models.py`, agent schemas in `app/agents/schemas.py`, and the camelCase API
  shape in `app/main.py` DTOs (README §8B); when `frontend/src/lib/types.ts` exists
  it must mirror that camelCase shape. Change the relevant places together and announce it.
- **Need another person's output?** → the backend API is live; build against it
  (README §8B) rather than waiting.
- **Blocked?** → mark it, state the assumption you're proceeding with, and keep moving.
- **Before integrating** → run the quality gate (§7) and reconcile against the contracts.
