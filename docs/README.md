# DocGuardian AI — Planning Documentation

This folder contains the **implementation plan** for DocGuardian AI, kept in sync
with the code. The **backend is implemented** (pipeline, agents, governance,
conflict detection, verification sandbox, async ingest + `WS /stream`) and the
**frontend is scaffolded and buildable**; the main remaining work is wiring the
frontend governance panels to the live endpoints. The product spec lives in the
root [`README.md`](../README.md); these documents turn it into an actionable build
plan. For the precise as-built snapshot, see
**[`implementation-status.md`](implementation-status.md)**; for the API contract the
frontend consumes, see **[`api.md`](api.md)**.

## What is DocGuardian AI?

An AI-powered documentation governance platform that ingests real engineering
docs, detects stale / duplicate / conflicting content, proposes **evidence-backed**
fixes via two LLM agents (Curator + Guardian), and presents everything in an
interactive knowledge graph with human-in-the-loop approval, provenance, and
rollback. See [`README.md`](../README.md) for the full spec.

## Reading order

1. **[`implementation-status.md`](implementation-status.md)** — the **as-built snapshot**:
   what the backend actually does today, the real API (README §8B), the actual
   contracts, and what's still pending. *Read this first to know reality.*
2. **[`api.md`](api.md)** — the **backend API reference**: every endpoint, request/
   response shape, the WebSocket events, and the end-to-end flows. *Start here for
   frontend work.*
2. **[`general-plan.md`](general-plan.md)** — the **general plan**: problem &
   solution, MVP scope, the 5-layer architecture, runtime agent design, locked tech
   stack, the data contracts, the parallel execution model, phase status, the demo
   script, risks, and success metrics.
3. **[`team-plan.md`](team-plan.md)** — the **team plan**: the 4 roles, the
   **file/directory ownership map** (updated to the actual backend layout), the
   execution model, the milestones, and the **status-aware general TODOs**.
4. **Per-person detailed plans** (in [`team/`](team/)) — each engineer's scope,
   interfaces, and **detailed per-person TODOs**:
   - **[`team/person-1-frontend.md`](team/person-1-frontend.md)** — Frontend & Demo
     Experience (graph, chat, diff/review, drop-off, metrics, provenance, "show your work").
   - **[`team/person-2-retrieval.md`](team/person-2-retrieval.md)** — Retrieval &
     Document Intelligence (ingestion, processing, embeddings, search, duplicate/conflict).
   - **[`team/person-3-ai-orchestration.md`](team/person-3-ai-orchestration.md)** —
     Agent Orchestration & AI Reasoning (orchestrator, Curator & Guardian, providers,
     evidence/confidence, chat RAG).
   - **[`team/person-4-governance.md`](team/person-4-governance.md)** — Governance,
     Verification & Metrics (ACL, approval, provenance, rollback, store, metrics,
     sandbox, API plumbing).

## Document map

| Document | Answers | Audience |
| --- | --- | --- |
| `general-plan.md` | *What are we building and why? How does it fit together?* | Everyone |
| `team-plan.md` | *Who owns what? How do we work in parallel? What are the shared todos?* | Everyone |
| `team/person-1-frontend.md` | *Person 1's detailed scope + todos* | P1 (+ reference for all) |
| `team/person-2-retrieval.md` | *Person 2's detailed scope + todos* | P2 (+ reference for all) |
| `team/person-3-ai-orchestration.md` | *Person 3's detailed scope + todos* | P3 (+ reference for all) |
| `team/person-4-governance.md` | *Person 4's detailed scope + todos* | P4 (+ reference for all) |

## The idea that keeps work parallel

**Local-first + a live API.** The locked stack runs most of the pipeline **for
real, offline**: fastembed does embeddings locally and Postgres+pgvector is one
`docker compose up`. With the backend API already live (README §8B), the four
workstreams proceed largely in parallel — the frontend builds on the real API, and
the duplicate/conflict, governance, and metrics work builds on the existing store.
See `general-plan.md` §8 and `team-plan.md` §2 for ownership details. *(Only the
`/chat` and `/propose` agents need Azure OpenAI.)*

## Current status (2026-06-24)

- ✅ Product spec (`README.md`) + these planning docs (kept in sync with the code).
- ✅ **Backend built:** ingestion → processing → embeddings → pgvector retrieval →
  LangGraph Curator/Guardian agents → FastAPI, **plus governance** (ACL, approval/
  rollback, append-only provenance, duplicate/conflict detection, derived health,
  `/metrics`), a **real Docker verification sandbox**, atomic intake with AI
  summaries, and async ingest + `WS /stream`. 29 pytest pass.
- 🟡 **Frontend scaffolded & buildable:** graph, chat, drop-off, diff/review,
  provenance, metrics; consumes the API and live-refreshes over `WS /stream`.
- ⬜ **Pending:** wiring the frontend governance panels (approve/metrics/provenance)
  to the live endpoints, `POST /ingest/refresh`, and demo seed data.

> See [`implementation-status.md`](implementation-status.md) for the full as-built
> matrix, then follow the status-aware TODOs in `team-plan.md` §5 and each person's
> plan under `team/`.

> When the team starts building, follow the milestones in `general-plan.md` §9 and
> the general TODOs in `team-plan.md` §5, then each person executes their personal
> plan under `team/`.
