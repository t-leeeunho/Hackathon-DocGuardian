# DocGuardian AI — Planning Documentation

This folder contains the **implementation plan** for DocGuardian AI. It is
planning only — there is no application code in the repository yet. The product
specification lives in the root [`README.md`](../README.md); these documents turn
that spec into an actionable, parallelizable build plan.

## What is DocGuardian AI?

An AI-powered documentation governance platform that ingests real engineering
docs, detects stale / duplicate / conflicting content, proposes **evidence-backed**
fixes via two LLM agents (Curator + Guardian), and presents everything in an
interactive knowledge graph with human-in-the-loop approval, provenance, and
rollback. See [`README.md`](../README.md) for the full spec.

## Reading order

1. **[`general-plan.md`](general-plan.md)** — the **detailed general plan**: problem &
   solution, MVP scope, the 5-layer architecture, runtime agent design, locked tech
   stack, the frozen data contracts, the **contracts-first parallel execution model**,
   phases & milestones (M1–M4), the demo script, risks, and success metrics. *Read this first.*
2. **[`team-plan.md`](team-plan.md)** — the **team plan**: the 4 roles, the
   **file/directory ownership map** (which guarantees no merge conflicts), the
   parallel execution model, the milestones, and the **general (shared) TODOs**.
3. **Per-person detailed plans** (in [`team/`](team/)) — each engineer's scope,
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

## The one idea that makes this work

**Contracts-first parallelism.** A short shared **Phase 0** freezes every data
contract and ships a **mock API** plus **fake providers**. After that (Milestone
**M1**), the four engineers build fully in parallel against mocks — nobody waits on
Azure or on each other — and because each person owns **disjoint files** (separate
directories + their own API router file), there are **no merge conflicts**. The
fakes are swapped for real implementations at integration (M2/M3) behind the same
interfaces. See `general-plan.md` §8 and `team-plan.md` §2 for the details.

## Current status

- ✅ Product spec (`README.md`) and these planning documents.
- ⬜ Phase 0 foundation (scaffold, frozen contracts, mock API, fakes) — **not started**.
- ⬜ Parallel build (P1–P4), integration, demo polish — **not started**.

> When the team starts building, follow the milestones in `general-plan.md` §9 and
> the general TODOs in `team-plan.md` §5, then each person executes their personal
> plan under `team/`.
