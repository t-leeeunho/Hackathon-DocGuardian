# DocGuardian AI — General Implementation Plan

> **Status:** Planning (no application code yet — this repo currently holds the
> product spec in `README.md` and these planning documents in `docs/`).
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

The product itself uses a **thin orchestrator plus exactly two LLM agents**, and
pushes all deterministic work into plain services that cost no model quota.

| Component | Type | Responsibility |
| --- | --- | --- |
| **Orchestrator** | Code router (NO LLM) | Routes requests/events, calls deterministic services, invokes an LLM agent only when reasoning/drafting is needed |
| **Curator Agent** | LLM | Reasons over retrieved docs, decides the action (create/update/merge/link/deprecate/flag), drafts the change with evidence + confidence |
| **Guardian Agent** | LLM | Judges safety: reviews sandbox + conflicts → approve / needs-review, with ACL + provenance context |
| Retrieval service | Deterministic | Similarity search, duplicate/related lookup |
| Ingestion service | Deterministic | Sparse clone, commit metadata, incremental refresh |
| Verification sandbox | Deterministic | Runs build/test/doc command at a commit → pass/fail (**mock for MVP**) |
| Governance/ACL service | Deterministic | Read/write permissions, provenance, rollback |

**Budget:** ~2 LLM calls per proposal (Curator + Guardian); 1 call for a simple
chat answer (RAG). Everything else is free deterministic work.

---

## 6. Tech Stack (Locked Decisions)

| Area | Decision | Notes |
| --- | --- | --- |
| Backend | **Python 3.11+ + FastAPI** | REST + WebSocket; Pydantic v2 |
| Frontend | **React + TypeScript + Vite + Tailwind + shadcn/ui + React Flow** | 2D graph for MVP (3D deferred) |
| Storage | **Local-first: SQLite + local vector store (Chroma/FAISS)** | Behind `Store` / `VectorIndex` interfaces; Azure (Cosmos/AI Search/Blob) is a later adapter |
| LLM + Embeddings | **Provider-abstracted, default Azure OpenAI** | `LLMProvider` / `EmbeddingProvider`; swappable to OpenAI/local; fakes for offline dev |
| Verification | **Mock sandbox** | Real container execution is a stretch goal |
| Auth/ACL | **Stubbed roles/users** | Entra ID is a stretch goal |

These are **locked**. Changing them is a director-level decision because they
ripple across every layer.

---

## 7. Frozen Data Contracts (the interface between everyone)

Every arrow between layers is a typed payload. They are defined **once** as
Pydantic v2 models and **mirrored** as TypeScript interfaces, kept identical
(camelCase JSON: `docId`, `commitSha`, `headingPath`, `riskLevel`). After they are
frozen at Milestone M1, **only the director changes them** — they are the "API
between humans." Full JSON schemas live in README §8A.

| Contract | Origin layer | Consumed by |
| --- | --- | --- |
| `RawDocument` | Ingestion (1) | Processing |
| `DocumentAdded` / `DocumentChanged` / `DocumentDeleted` | Ingestion refresh | Processing / graph |
| `DocChunk` | Processing (2) | Embeddings / search |
| `GraphEdge` (`references` / `duplicate-of` / `conflicts-with` / `deprecated-by`) | Processing + AI | Graph store / frontend |
| `SearchResult` | Vector index (3) | Orchestrator / chat |
| `AgentProposal` (diff + evidence + confidence + risk + verification) | AI (3) | Backend / diff panel |
| `ChatAnswer` (answer + citations + confidence) | AI (3) | Chat UI |
| `DocumentRecord` | Backend store (4) | Graph / provenance |
| `ProvenanceEntry` | Backend store (4) | Provenance panel / rollback |
| `SandboxRequest` / `SandboxResult` | Backend ↔ sandbox | Confidence scoring |
| `GraphDTO` / `MetricsDTO` / `GraphHighlightEvent` | Backend (4) | Frontend (5) |

**Cross-cutting rules baked into the contracts:**
- **Provenance everywhere** — every record carries its originating `commitSha`.
- **Idempotent ingestion** — unchanged `contentHash` ⇒ no re-processing.
- **Permission propagation** — ACLs enforced at retrieval, answer, and write.
- **Configuration-driven sources** — onboarding a repo is a `repos.config.json` edit.

---

## 8. Execution Model — Contracts-First Parallelism

This is **how four engineers work at the same time without blocking each other.**
Three rules:

1. **Contracts-first.** A short shared **Phase 0** freezes every data contract (§7)
   as Pydantic + mirrored TS. After the freeze, contracts only change via the director.
2. **Mock everything.** Phase 0 also ships a **mock API** (every route returns
   fixture JSON) and **fake providers** (`FakeLLMProvider`, `FakeEmbeddingProvider`,
   `InMemoryStore`). Every engineer develops against mocks on day one — nobody waits
   on Azure or on another engineer's code.
3. **Disjoint file ownership.** Each engineer owns separate directories and their
   **own API router file**. The only shared files (`models/`, `types.ts`, `main.py`,
   `repos.config.json`) are frozen in Phase 0 ⇒ **no merge conflicts.**

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

| Phase | Owner | Deliverable | Exit milestone |
| --- | --- | --- | --- |
| **Phase 0 — Foundation** | All (lead: whoever owns scaffolding) | Monorepo layout, **frozen contracts** (Pydantic + TS), provider/store interfaces + fakes, **mock API + fixtures**, tooling (ruff/black/pytest, eslint/tsc/vitest), `repos.config.json`, `.env.example` | **M1:** frontend renders mock graph/chat/diff/metrics end-to-end; everyone unblocked |
| **Phase 1–4 (parallel)** | P1 / P2 / P3 / P4 | Each builds their slice against mocks (see per-person docs) | **M2:** P2 real retrieval + P3 real Curator/Guardian replace fakes |
| **Integration** | All | Wire SQLite store + real routers; flip frontend mock→real | **M3:** real API serves the UI end-to-end |
| **Demo polish** | All | Seed 1–2 repos + **planted** stale/duplicate/conflict fixtures; live metrics over WS; accessibility | **M4:** rehearsed 9-step demo |

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
stale/duplicate/conflicting docs — ideal for demonstrating detection:

| Repo | Why |
| --- | --- |
| `microsoft/playwright` | Rich e2e testing docs, frequent setup/test drift |
| `microsoft/vscode` | Large contributor/build/architecture docs (scope to a docs subset) |
| `microsoft/onnxruntime` | Dense build/platform docs prone to version staleness |
| `microsoft/garnet` | Focused operational/getting-started docs |

Retrieval uses **sparse, shallow git clones** (no GitHub API, no tokens, no rate
limits); commit SHA + date are captured as freshness/provenance signals (README §9.4).
For a reliable demo, scope to 1–2 repos and their documentation folders only.

---

## 14. How These Docs Fit Together

- **`general-plan.md`** (this file) — the what and why: architecture, stack,
  contracts, execution model, phases, demo, risks.
- **`team-plan.md`** — the who and how-together: roles, ownership map, milestones,
  and the **general shared todos**.
- **`docs/team/person-1-frontend.md` … `person-4-governance.md`** — the per-person
  detailed plans and todos.
