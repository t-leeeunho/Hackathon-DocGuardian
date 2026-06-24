# DocGuardian AI — General Implementation Plan

> **Status (2026-06-24):** the **backend is implemented end-to-end** (ingestion →
> processing → embeddings → pgvector retrieval → LangGraph Curator/Guardian agents
> → FastAPI) **plus the governance slice** (ACL, approval/rollback, append-only
> provenance, duplicate/conflict detection, derived health, `MetricsDTO`), a **real
> Docker verification sandbox**, atomic intake with AI summaries, and async ingest +
> `WS /stream`. The **frontend is scaffolded and buildable** (consumes the API, live
> WS refresh); remaining work is wiring its governance panels to the live endpoints.
> For the precise as-built snapshot, see
> [`implementation-status.md`](implementation-status.md) — when this plan and the
> code disagree, that file reflects reality.
> **Audience:** the whole team. Read this first, then `team-plan.md`, then your
> personal plan under `docs/team/`.

---

## 1. Executive Summary

**DocGuardian AI** is an AI-powered documentation governance platform. It ingests
real engineering documentation, continuously validates it against source-of-truth
signals (commits, PRs, config, build/test instructions), detects stale / duplicate
/ conflicting content, proposes **evidence-backed** fixes through two LLM agents,
and surfaces everything in an interactive knowledge graph with human-in-the-loop
approval, provenance, and rollback.

For the hackathon we build a **believable end-to-end demo slice**, not the full
vision: ingest → detect duplicate/conflict → graph → AI-proposed update →
evidence/confidence → human approve → provenance + metrics, scoped to **1–2 repos**.

The work is structured so **four engineers build fully in parallel** after a short
shared foundation phase. The mechanism that makes that possible is the heart of
this plan (see §8, *Contracts-First Parallelism*).

---

## 2. Problem & Solution

**Problem (README §2).** Documentation goes stale after code/config/process
changes, duplicates itself with subtle differences, scatters across repos and
wikis, and erodes trust. Onboarding is slow; teams can't tell whether a doc still
reflects reality; updates are manual and inconsistent.

**Solution (README §3).** An intelligent documentation layer that connects docs to
source-of-truth signals via a thin orchestrator routing to specialized agents and
deterministic services. Documents are presented as an interactive graph showing
relationships, conflicts, freshness, ownership, and access level — making docs
**trustworthy, discoverable, permission-aware, and easy to maintain.**

---

## 3. Goals, Non-Goals & MVP Scope

### 3.1 Goals (the demo slice — README §13–14 "Must Have")
- Upload/paste documentation (drop-off intake).
- Search existing documents; detect related / duplicate docs.
- Show a document graph with health coloring.
- Identify stale / conflicting content.
- Generate an AI-proposed update with **evidence + confidence**.
- Human approve/reject flow with a before/after diff.

### 3.2 Should Have
- Color-coded document health, diff side panel, provenance log, basic metrics
  dashboard, scope toggle.

### 3.3 Non-Goals for the hackathon (README §14 "Nice to Have" — explicitly deferred)
- 3D document map, real sandbox verification (use a mock), permission-aware fog as
  a polished feature, learning-from-accept/reject, glossary generation, Teams/ticket
  integration, full Entra ID auth (ACLs are stubbed with hardcoded roles).

### 3.4 Guiding principle
> Don't build every feature fully. Build a **believable slice** that demonstrates
> the narrative: detection → evidence-backed proposal → human approval → provenance
> → measurable impact.

---

## 4. Architecture Overview (5 Layers)

Data flows **upward** (ingestion → UI); control/approvals flow **downward**
(UI → governed writes). Each boundary carries a specific, versioned payload whose
schema is frozen in §7. (Full detail in README §8A.)

```text
5 · FRONTEND   [Graph View] [Chat] [Diff/Review] [Metrics + Provenance]
                 ^ GraphDTO   ^ ChatAnswer  ^ AgentProposal  ^ MetricsDTO
4 · BACKEND/API [REST + WebSocket] [Job Queue] [Metadata+Graph Store] [Sandbox]
                 ^ AgentProposal   ^ DocChunk[]   ^ SandboxResult
3 · AI/EMBEDDING [Embeddings] -> [Vector Index] -> [Orchestrator -> Curator/Guardian]
                 ^ DocChunk        ^ GraphEdge[]
2 · PROCESSING  [Normalizer] -> [Heading-Aware Chunker] -> [Link Extractor]
                 ^ RawDocument / Document{Added,Changed,Deleted}
1 · INGESTION   [Sparse/Shallow git clone] -> [Commit Metadata Extractor] -> [Refresh Watcher]
                 Sources: microsoft/{playwright, vscode, onnxruntime, garnet}
```

A document is **born** at Layer 1 as a `RawDocument`, becomes `DocChunk` + `GraphEdge`
records at Layer 2, gains a vector embedding and (when acted on) an `AgentProposal`
at Layer 3, is persisted/served by Layer 4, and is rendered for human review at
Layer 5.

---

## 5. Runtime Agent Design (cost-conscious — README §8)

The product uses a **thin orchestrator plus exactly two LLM agents**, and pushes
all deterministic work into plain services that cost no model quota. **As built,**
the orchestrator + agents are two compiled **LangGraph** graphs (`app/agents/graph.py`):
`/chat` = `retrieve → curator` and `/propose` = `retrieve → curator → guardian`.

| Component | Type | Responsibility | Built? |
| --- | --- | --- | --- |
| **Orchestrator** | LangGraph graph (NO LLM in the retrieve node) | Wires retrieve → agent(s); the retrieve node does an in-process pgvector search | ✅ |
| **Curator Agent** | LLM (Azure OpenAI) | Reasons over retrieved docs, decides the action (create/update/merge/link/deprecate/flag), drafts the change with citations + confidence | ✅ |
| **Guardian Agent** | LLM (Azure OpenAI) | Judges safety: reviews the draft + evidence → approve / needs-review / reject | ✅ |
| Retrieval service | Deterministic | pgvector cosine similarity search | ✅ |
| Ingestion service | Deterministic | Sparse clone, commit metadata, refresh | ✅ |
| Duplicate/conflict detection | Deterministic | similarity-threshold edges (`duplicate-of`/`conflicts-with`) | ❌ pending |
| Verification sandbox | Deterministic | Runs build/test/doc command at a commit → pass/fail | ❌ pending (README §10.6 targets a real container) |
| Governance/ACL service | Deterministic | Read/write permissions, provenance, rollback | ❌ pending |

**Budget:** ~2 LLM calls per proposal (Curator + Guardian); 1 call for a simple
chat answer (RAG). Everything else is free deterministic work. Embeddings default
to **local fastembed** (no Azure); **only the agents require Azure OpenAI** (the
`/chat` and `/propose` endpoints return 503 if Azure is unconfigured).

---

## 6. Tech Stack (Locked Decisions)

| Area | Decision | Notes |
| --- | --- | --- |
| Backend | **Python 3.11+ + FastAPI** | Pydantic v2; REST today, WebSocket planned |
| Frontend | **React + TypeScript + Vite + Tailwind + React Flow (2D) + Monaco** | Monaco for the diff/editor views (README §10.1); *scaffolded & buildable (Radix + lucide, no shadcn/ui yet)* |
| Storage | **Single PostgreSQL + pgvector** | One instance = metadata + graph edges + the vector index; run locally via `docker compose` (`pgvector/pgvector:pg16`); managed Azure storage intentionally not used for the MVP (README §10.4) |
| Embeddings | **Provider-abstracted; local fastembed default** | `BAAI/bge-small-en-v1.5` (384-dim, ONNX) by default; swappable to Azure via `EMBEDDING_PROVIDER=azure` |
| LLM agents | **Azure OpenAI chat (required)** | Curator + Guardian via **LangGraph**; `/chat` + `/propose` return 503 if Azure is unset; no local/fake chat fallback |
| Verification | **Real containerized sandbox** | README §10.6; *implemented (`app/services/verification.py`, real Docker; `available:false` without Docker)* |
| Auth/ACL | **Mocked roles/users** | Governance backed by Postgres; Entra ID deferred; *ACL/approval/provenance/rollback implemented* |

These are **locked** (README §10). Changing them is a director-level decision
because they ripple across every layer.

---

## 7. Data Contracts (the interface between everyone)

Every arrow between layers is a typed payload. **As built**, contracts live in
three places rather than one frozen camelCase package (full target schemas: README §8A):

- **Core internal contracts** — `backend/app/models.py`, **snake_case** Pydantic v2
  (`RawDocument`, `DocChunk`, `GraphEdge`, `EdgeType`). Cover Layers 1–2.
- **API response DTOs** — `backend/app/main.py`, **camelCase** Pydantic models
  (`Match`, `GraphNode`, `GraphResponse`, `DocumentResponse`, …) + camelCase dicts
  in `app/storage/queries.py`. This is the camelCase shape the frontend consumes (README §8B).
- **Agent structured outputs** — `backend/app/agents/schemas.py`: `Citation`,
  `ChatAnswer`, `AgentProposal` (aligned with README §8A.4).
- **Governance + frontend contracts** — `backend/app/governance/` (`Principal`,
  `MetricsDTO`, persisted `proposals`/`provenance`), `app/services/verification.py`
  (`SandboxRequest`/`SandboxResult`), and the frontend mirror
  `frontend/src/lib/types.ts` (camelCase, README §8B).

The frontend `frontend/src/lib/types.ts` mirrors the camelCase API; the API client
and `governance/serialize.py` deep-convert the snake_case agent payloads. There is
no `to_camel` alias generator on the core models. Contract changes still flow
through the director.

| Contract | Where it lives today | Status |
| --- | --- | --- |
| `RawDocument`, `DocChunk`, `GraphEdge` | `app/models.py` (snake_case) | ✅ implemented |
| `references` graph edges | `app/processing/processor.py` | ✅ implemented |
| `duplicate-of` / `conflicts-with` edges | `app/processing/conflicts.py` | ✅ implemented (≥0.92 / ≥0.85) |
| `Match` / search response, `GraphDTO`, document DTO | `app/main.py`, `app/storage/queries.py` (camelCase) | ✅ implemented |
| `ChatAnswer`, `AgentProposal`, `Citation` | `app/agents/schemas.py` (snake_case) | ✅ implemented (README §8A.4 shape) |
| `ProvenanceEntry`, `MetricsDTO`, `SandboxRequest/Result` | `app/governance/`, `app/services/verification.py` | ✅ implemented |
| `DocumentRecord` (full governance record), `GraphHighlightEvent` | partial (governance cols on `documents`); `GraphHighlightEvent` client-side | 🟡 partial |

**Cross-cutting rules (upheld where built):**
- **Provenance** — every record carries its originating `commit_sha`; agent
  citations have their `commit_sha` overwritten with the authoritative retrieved value.
- **Idempotent ingestion** — unchanged `content_hash` ⇒ no re-processing (`ON CONFLICT` upserts).
- **Permission propagation** — ACLs at retrieval/answer/write — *implemented (`app/governance/acl.py`, fail-closed)*.
- **Configuration-driven sources** — onboarding a repo is a `repos.config.json` edit.

---

## 8. Execution Model — Contracts-First Parallelism

This is **how four engineers work at the same time without blocking each other.**
Three rules:

1. **Contracts-first.** A short shared **Phase 0** freezes every data contract (§7)
   as Pydantic + mirrored TS. After the freeze, contracts only change via the director.
2. **Run real, locally, where cheap.** The locked local-first stack means most of
   the pipeline runs **for real with no Azure**: fastembed does embeddings locally
   and Postgres+pgvector is one `docker compose up`. The backend API is already
   live, so the frontend builds against the **real** endpoints (README §8B), not a
   mock. **Only the agents** (`/chat`, `/propose`) need Azure OpenAI. *(The original
   plan called for a mock API + `FakeLLMProvider`; in practice only a chat fallback
   would still be useful, and it is not built.)*
3. **Disjoint file ownership.** Each engineer owns separate areas so they don't
   collide. **As built**, the backend is currently a single `app/main.py` (all
   endpoints) + `app/models.py` (core contracts) + `repos.config.json`; splitting
   into per-domain routers / a `models/` package and adding `frontend/src/lib/types.ts`
   are part of the remaining work, coordinated through the director.

```text
                  ┌──────────────── PHASE 0 (shared foundation) ────────────────┐
                  │  freeze contracts · mock API · fakes · fixtures · tooling    │
                  └───────┬───────────┬───────────────┬───────────────┬─────────┘
                          │ M1 unblocked               │               │
              ┌───────────▼──┐ ┌──────▼───────┐ ┌──────▼───────┐ ┌─────▼────────┐
              │ P1 FRONTEND  │ │ P2 RETRIEVAL │ │ P3 AI/AGENTS │ │ P4 GOVERNANCE│
              │ vs mock API  │ │ vs fake embed│ │ vs sample    │ │ vs sample    │
              │ + fixtures   │ │ + real clones│ │ SearchResult │ │ AgentProposal│
              └──────┬───────┘ └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
                     └────────┬───────┴───────┬────────┴───────┬────────┘
                              ▼ M2 fakes→real ▼ M3 wire store  ▼ M4 e2e demo
```

The four workstreams map 1:1 to the four people; ownership detail and the general
shared todos are in **`team-plan.md`**; each person's detailed todos are in
**`docs/team/person-N-*.md`**.

---

## 9. Phases & Milestones

> **Where we are (2026-06-24):** the backend foundation, the retrieval/agent
> pipeline, **and the governance/conflict/verification slice** are built (ingestion,
> processing, embeddings, pgvector search, LangGraph Curator/Guardian, FastAPI, ACL,
> approval/rollback, provenance, duplicate/conflict detection, health scoring,
> `/metrics`, real Docker sandbox, async ingest + `WS /stream`). The frontend is
> scaffolded and buildable. Remaining: wiring the frontend governance panels to the
> live endpoints, `POST /ingest/refresh`, and demo seed data. See
> `implementation-status.md`.

| Phase | Status | Deliverable |
| --- | --- | --- |
| **Foundation** | ✅ done | `backend/` layout, `repos.config.json`, `.env.example`, Postgres+pgvector via `docker-compose`, `requirements.txt` |
| **Ingestion + Processing** | ✅ done | sparse/shallow clone + commit metadata → `RawDocument`; heading-aware chunking + `references` edges |
| **Embeddings + Retrieval** | ✅ done | fastembed/Azure providers, pgvector store + HNSW cosine search, `/search`, CLI |
| **Agents** | ✅ done | LangGraph `/chat` (1 LLM call) + `/propose` (2 LLM calls); evidence/confidence guardrails |
| **Duplicate/conflict detection** | ✅ done | `duplicate-of` (≥0.92) + `conflicts-with` (≥0.85) edges; derived node health scoring |
| **Governance / Metrics / Verification** | ✅ done | ACL, approval, provenance + rollback, `/metrics`, real Docker sandbox, `WS /stream` |
| **Frontend** | 🟡 scaffolded | graph, chat, drop-off, diff/review, provenance, metrics build on README §8B API; governance panels still on fixtures |
| **Demo polish** | ⬜ pending | planted stale/duplicate/conflict seed fixtures; rehearse the 9-step demo |

---

## 10. Demo Script (the believable slice — README §11)

1. User pastes/drops a doc → intake.
2. Retrieval finds related / duplicate docs.
3. Graph highlights relationships (green / yellow / red, locked nodes).
4. Conflict detected (two build/test instructions disagree).
5. Curator proposes a merged canonical version.
6. Evidence + confidence shown (commits/config as sources).
7. Diff panel → human approve/reject.
8. Provenance logged (who / what / why / sources / rollback).
9. Metrics dashboard updates (stale fixed, conflicts resolved, duplicates reduced).

---

## 11. Risks & Mitigations (README §17)

| Risk | Mitigation |
| --- | --- |
| AI hallucinates updates | Mandatory evidence + confidence + human approval; `confidence < 0.5` ⇒ forced "needs human review" |
| Azure quota limits | ≤2 LLM calls/proposal; deterministic services do the heavy lifting; provider abstraction allows local/fake fallback |
| Graph rendering heavy | 2D React Flow, chunked/lazy rendering, scope to 1–2 repos |
| Verification hard to fully build | Sandbox **mock** for MVP; show planned real architecture |
| Conflict detection noisy | Seed with obvious **planted** conflicts; threshold-based seeding |
| Scope too large | Slice-first; Should/Nice-to-have gated behind the MVP |
| Parallel work collides | Contracts-first + mock-everything + disjoint file ownership (§8) |

---

## 12. Success Metrics (README §16)

- Stale documents detected / fixed.
- Duplicate documents identified / removed.
- Conflicts detected / resolved.
- Proposed fixes accepted by users.
- Broken links found/resolved.
- % of documents with verification stamps.
- % of AI edits carrying evidence + confidence.
- Reduction in repeated onboarding questions; time saved finding build/test instructions.

---

## 13. Source Corpus (README §9)

Ingest documentation from real, doc-rich Microsoft repos that naturally contain
stale/duplicate/conflicting docs — ideal for demonstrating detection. **All four
are configured** in `backend/repos.config.json` (each with a `shortName`,
`sparsePaths`, and `docGlobs`):

| Repo (`shortName`) | Sparse paths | Why |
| --- | --- | --- |
| `microsoft/garnet` (`garnet`) | `website/docs`, `docs` | Focused operational/getting-started docs |
| `microsoft/playwright` (`playwright`) | `docs` | Rich e2e testing docs, frequent setup/test drift |
| `microsoft/onnxruntime` (`onnxruntime`) | `docs` | Dense build/platform docs prone to version staleness |
| `microsoft/vscode` (`vscode`) | `build`, `extensions`, `src` | Large contributor/build/architecture docs |

Retrieval uses **sparse, shallow git clones** (no GitHub API, no tokens, no rate
limits); commit SHA + date are captured as freshness/provenance signals (README §9.4).
`doc_id` is `<shortName>/<path>`; the `repo` query param filters by that prefix.

---

## 14. How These Docs Fit Together

- **`implementation-status.md`** — the **as-built snapshot**: what the backend
  actually does today, the real API, and what's still pending. Start here to know reality.
- **`general-plan.md`** (this file) — the what and why: architecture, stack,
  contracts, execution model, phases, demo, risks.
- **`team-plan.md`** — the who and how-together: roles, ownership map, milestones,
  and the **general shared todos**.
- **`docs/team/person-1-frontend.md` … `person-4-governance.md`** — the per-person
  detailed plans and todos.
