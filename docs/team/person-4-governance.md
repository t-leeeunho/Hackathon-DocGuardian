# Person 4 — Governance, Verification & Metrics

> **As-built status (2026-06-24):** the governance slice is **fully implemented** —
> ACL (`app/governance/acl.py`), approval + staged-approval + rollback
> (`service.py`), append-only provenance and proposals persistence (`store.py`,
> Postgres `proposals`/`provenance` tables), derived node health/importance
> (`health.py`), `MetricsDTO` (`metrics.py`), duplicate/conflict detection
> (`app/processing/conflicts.py`), a **real Docker** verification sandbox
> (`app/services/verification.py`), `POST /ingest/refresh` for re-processing and
> stamping documents, demo seed data (`scripts/seed_demo.py`), and the API routes
> `GET /proposals/:id`, `POST /proposals/:id/approve`, `POST /proposals/:id/rollback`,
> `GET /metrics`, `GET /provenance/:id`, `POST /verify`, `POST /ingest/refresh`, and
> `WS /stream`. The graph is ACL-filtered with real health.
> **Remaining:** wiring the frontend governance panels to these endpoints.
> The checklist below is updated to reflect as-built reality.
> See [../implementation-status.md](../implementation-status.md) for the authoritative as-built state.

Own the enterprise-trust backend slice: permissions/ACL, approval workflow, provenance and rollback, metadata/graph persistence, metrics, real containerized verification sandbox, and the REST/WebSocket API plumbing for graph and proposals.

## Mission

Person 4 owns the part of DocGuardian AI that makes the demo feel enterprise-safe rather than merely AI-assisted. Your mission is to ensure every read, answer, and write is permission-aware; every authoritative change moves through propose → diff → approve → apply → provenance; and every visible dashboard metric can be traced back to persisted state. For M1–M4, bias toward a believable governed slice with strong contracts, append-only auditability, the README §10.6 real containerized verification target, and live API/WS updates that let P1 demonstrate trust, impact, and rollback.

## Scope — What You Own

You own the Layer 4 backend implementation that sits between P2/P3's retrieval/agent outputs and P1's UI surfaces.

| Area | Files / modules | Responsibility |
| --- | --- | --- |
| Postgres + pgvector store | `backend/app/storage/db.py`, `queries.py`, `vectorstore.py` | Existing Postgres implementation: `init_schema()` creates `documents`, `chunks`, `edges` plus a `chunks.embedding` HNSW cosine index; `queries.py` exposes `list_doc_ids`, `get_document`, `get_graph`; `vectorstore.py` handles upserts and cosine search. README §10.4 locks one PostgreSQL instance for metadata, graph, audit, approvals, and provenance. |
| Governance service | `backend/app/governance/` (`acl.py`, `service.py`, `store.py`, `health.py`, `metrics.py`) | **Implemented:** ACL enforcement, approval + staged-approval state machine, governed write orchestration, `ProvenanceEntry` creation, rollback. |
| Verification service | `backend/app/services/verification.py` | **Implemented:** real containerized Docker sandbox (`--network none`, resource caps, timeout); `available:false` when Docker is absent. |
| DTO assembly | `governance/store.py` (`get_governed_graph`, `get_metrics_dto`) | `GraphDTO` carries **real** derived `health`/`importance` and is ACL-filtered; `MetricsDTO` is implemented. |
| Async jobs | `backend/app/services/jobs.py` + `events.py` | In-memory job registry for async ingest + an in-process event bus feeding `WS /stream`. |
| API router | `backend/app/main.py` | `GET /graph` (governed), `GET /metrics`, `GET /provenance/:id` implemented in the single `app/main.py`. |
| API router | `backend/app/main.py` (proposals) | **Implemented:** `GET /proposals/:id`, `POST /proposals/:id/approve`, `POST /proposals/:id/rollback`. |
| API router | `backend/app/main.py` (`/verify`, `WS /stream`) | **Implemented:** `POST /verify` and the `WS /stream` live feed (proposal/graph/metrics/ingest events). |

Concrete persisted data:

- [x] Existing Postgres rows: `documents` (`doc_id`, repo/path/commit metadata/content hash), `chunks` (text, heading path, line range, embedding), and `edges` (`from_doc`, `to_doc`, `type`, `weight`, evidence-ish metadata).
- [x] Existing graph edges are persisted in Postgres; processing emits `references`, `duplicate-of`, `conflicts-with`, and `deprecated-by` edges.
- [x] `DocumentRecord`-equivalent governance fields: `acl[]`, `last_verified_sha`, `last_verified_at`, `owner`, `title`, `summary`, `updated_at` added to `documents` via `ALTER TABLE … ADD COLUMN IF NOT EXISTS` in `init_schema`.
- [x] Duplicate/conflict/deprecated edge semantics fully implemented in `app/processing/conflicts.py`.
- [x] Approval records and decision history in `proposals` table (proposal_id, doc_id, action, status, risk_level, confidence, payload, timestamps).
- [x] Append-only `ProvenanceEntry` audit log in `provenance` table — no UPDATE/DELETE path.
- [x] Metrics aggregated live from Postgres state by `governance/store.py` → `governance/metrics.py`.
- [x] Verification results via real Docker sandbox (`SandboxResult`) in `app/services/verification.py`.

## What You Must NOT Touch

Do not create or edit application code outside your ownership boundary.

| Frozen / other-owned area | Rule |
| --- | --- |
| `backend/app/models.py` and future shared contracts | Current core models are a single `app/models.py`; README §8A governance contracts are not implemented yet. Request director changes if a contract is incomplete. |
| `frontend/src/lib/types.ts` / future frontend types | TypeScript mirror is a frontend/director-owned area when created; do not implement UI types here. |
| `backend/app/main.py` | Router wiring is director-owned after Phase 0. Ask for wiring changes; do not edit directly. |
| P1 frontend directories | Serve `GraphDTO`, `MetricsDTO`, proposals, and WS events; do not implement UI behavior. |
| P2 ingestion/processing/retrieval/vector files | Persist P2 outputs through interfaces; do not change their implementation. |
| P3 orchestrator/agents/provider files and routers | Consume `AgentProposal` fixtures or real proposals; do not modify agent logic. |
| Shared config/contracts/tooling | Only touch if explicitly assigned in Phase 0 by the director. |

If you need another person's behavior before integration, use fixtures/fakes. Do not block on the other stream and do not patch their files to unblock yourself.

## Inputs (Consumed / Pending) & Outputs (Produced / Pending)

| Contract / payload | Direction for P4 | M1 status | M2/M3 status | What P4 must guarantee |
| --- | --- | --- | --- | --- |
| `AgentProposal` | Consumed from P3 / `/propose` | `POST /propose` returns today's streamlined agent schema | Pending persisted proposal contract and `GET /proposals/:id` | Preserve diff, evidence, confidence, risk, verification, source IDs, and proposal ID once README §8A.5 contract is implemented. |
| `DocumentRecord` | Future P4 contract | Not implemented; only `documents`/`chunks` rows exist | Postgres canonical rows with governance fields | ACL, health, importance, commit refs, verification stamp, and chunk mapping must become durable and idempotent. |
| `GraphEdge` | Consumed from P2/P3, persisted in Postgres | `edges` table exists; structural `references` edges load today | Real P2/P3 edges plus duplicate/conflict/deprecated semantics | Keep edge type and weight; include `conflicts-with` for red dashed graph visualization. |
| `ProvenanceEntry` | Future P4 contract | Not implemented | Append-only Postgres audit/provenance row | Mandatory on every governed write and rollback; captures who/what/why/sources/versions. |
| `SandboxRequest` | Future P4 verification service input | Not implemented | Passed to real containerized sandbox | Validate repo, commit SHA, command, timeout, and execution isolation. |
| `SandboxResult` | Future P4 verification service output | Not implemented | Real sandbox result attached to proposal/approval flow | Return `passed`, `exitCode`, `durationMs`, `stdoutTail`, `stderrTail`; do not claim a mock as real verification. |
| `GraphDTO` | Produced for P1 | `GET /graph` exists from Postgres rows | Postgres-backed graph with real governance fields | Today's nodes use placeholder `health: "green"`, `size: 0.5`, `accessible: true`; P4 must replace with health/importance/ACL logic. |
| `MetricsDTO` | Future P4 output | Not implemented | Postgres-backed aggregate counters via `GET /metrics` | Counters update after approval/rollback/seed fixtures and expose `asOf`. |
| WebSocket events | Future P4 output | Not implemented | Live proposal, graph, health, metrics events via `WS /stream` | Events are small, typed, and re-fetch-friendly; no inaccessible content in payloads. |

Illustrative contract shapes from README §8A that must remain exact in meaning:

```jsonc
// DocumentRecord persisted by P4
{
  "docId": "vscode/build.md",
  "repo": "microsoft/vscode",
  "path": "build.md",
  "title": "Building VS Code",
  "owner": "team:platform",
  "acl": ["team:platform", "role:engineer"],
  "health": "yellow",
  "importance": 0.74,
  "lastVerifiedSha": "f00dcafe...",
  "lastVerifiedAt": "2026-06-20T09:00:00Z",
  "currentCommitSha": "f1e2d3c4...",
  "chunkIds": ["vscode/build.md#Build#0"]
}
```

```jsonc
// ProvenanceEntry append-only audit row
{
  "entryId": "prov_01H..",
  "docId": "vscode/build.md",
  "proposalId": "prop_01H..",
  "action": "merge",
  "approvedBy": "user:alice@example.com",
  "approvedAt": "2026-06-23T10:07:30Z",
  "previousVersionRef": "blob:sha256:aaa...",
  "newVersionRef": "blob:sha256:bbb...",
  "evidenceSnapshot": [{ "chunkId": "vscode/build.md#Build#0", "commitSha": "f00dcafe..." }],
  "confidence": 0.82,
  "reason": "Unified yarn/npm build instructions to npm"
}
```

```jsonc
// SandboxResult target for the real containerized verification sandbox
{
  "passed": true,
  "exitCode": 0,
  "durationMs": 18342,
  "stdoutTail": "...watch build finished",
  "stderrTail": ""
}
```

## Dependencies & Interfaces With Others

| Partner | You consume from them | You serve to them | Phase expectations |
| --- | --- | --- | --- |
| P1 — Frontend & Demo Experience | UI requirements for graph, metrics, diff/review, provenance, and WebSocket event cadence | `GET /graph` and `GET /documents/{docId}` exist today; `GET /proposals/:id`, `POST /proposals/:id/approve`, `GET /metrics`, `WS /stream` are pending | M1: current graph/document responses; M3: real governance API responses; M4: live WS dashboard/provenance demo. |
| P2 — Retrieval & Document Intelligence | Existing Postgres `documents`/`chunks`/`edges`, future `DocumentRecord` candidates, `DocChunk` references, `GraphEdge` relations, health/importance signals if supplied | Durable metadata/graph persistence, graph edges available to UI and governance | M1: existing Postgres edges/records; M2: consume real retrieval outputs; M3: extend Postgres with governance fields. |
| P3 — Agent Orchestration & AI Reasoning | `AgentProposal` with diff, evidence, confidence, risk, and verification context | Proposal persistence, approval result, sandbox result seam, provenance context | M1: sample proposal fixtures; M2: consume real Curator/Guardian proposals; M3: governed approval path. |
| Director / shared foundation | Current `app/main.py` wiring, current `app/storage/` store, future shared governance contracts, fixtures, toolchain | Feedback on contract gaps only; no unilateral edits to frozen files | M1: document reality and contract gaps; after M1: request director changes for contract drift. |

Phase-by-phase integration stance:

- **M1 — contracts + current store:** build on the existing Postgres-backed `GET /graph` and `GET /documents/{docId}`; add pending contract gaps without inventing SQLite or separate in-memory truth.
- **M2 — real retrieval/agents emerging:** continue to accept fixtures while adding ingestion points for P2 graph/record outputs and P3 `AgentProposal`; keep toggles or adapters so mocks remain usable.
- **M3 — real API serves UI:** extend Postgres-backed service calls; enforce ACLs; write provenance on approved changes; stream updates to P1.
- **M4 — demo-ready polish:** seed planted stale/duplicate/conflict fixtures; ensure metrics visibly move; show staged approval and rollback; do not overclaim verification until the real containerized sandbox exists.

## Detailed TODOs

### Phase 0 — Foundation participation

- [x] Recognize the existing Postgres store schema in `app/storage/db.py`: `documents`, `chunks`, `edges`, plus `chunks.embedding` HNSW cosine index.
- [x] Recognize existing store queries in `app/storage/queries.py`: `list_doc_ids`, `get_document`, and `get_graph`.
- [x] Recognize current API reality in single `app/main.py`: `GET /graph` and `GET /documents/{docId}` are implemented.
- [x] Extend the store contract on top of Postgres: ACL-filtered graph query, proposal lookup, approval write, provenance append, rollback lookup, and metrics aggregation — all implemented in `governance/store.py`.
- [x] Keep all governance persistence in the single Postgres instance (README §10.4).
- [x] Replace `GET /graph` placeholders: real `health`, `size` (importance), and `accessible` via `get_governed_graph()`.
- [x] Implement `GET /metrics` → `MetricsDTO` via `governance/store.get_metrics_dto`.
- [x] Implement `GET /proposals/:id` with camelCase DTO + provenance history.
- [x] Implement `POST /proposals/:id/approve` with ACL, staged-approval, idempotency, and provenance write.
- [x] Implement `POST /proposals/:id/rollback` with append-only audit entry.
- [x] Implement `POST /ingest/refresh/:doc_id` — re-runs conflict scan, stamps `last_verified_sha`, emits graph/metrics WS events.
- [x] Keep routes in `app/main.py` (director decision — no need for per-domain router split for MVP).

### Core Build

#### Postgres Store

- [x] Use the existing Postgres + pgvector store in `app/storage/`.
- [x] Persist baseline document metadata, chunks, embeddings, and graph edges in Postgres with idempotent upserts.
- [x] Governance tables: `proposals` (full proposal lifecycle) and `provenance` (append-only audit log) in `init_schema`.
- [x] Governance columns on `documents`: `owner`, `title`, `acl`, `last_verified_sha`, `last_verified_at`, `updated_at`, `summary` — added with `ADD COLUMN IF NOT EXISTS` so existing deployments upgrade in place.
- [x] ACLs stored as `TEXT[]` on `documents`; filtered in `get_governed_graph` via `governance/acl.can_access`.
- [x] Graph edges use stable `edge_id` derived from from/to/type — idempotent on re-ingest.
- [x] Edge types `references`, `duplicate-of`, `conflicts-with`, `deprecated-by` all supported; detection in `processing/conflicts.py`.
- [x] Idempotent upserts throughout: `ON CONFLICT … DO UPDATE` everywhere.
- [x] Approval persistence with proposal ID, approver, status (`proposed → needs-review → applied → rolled-back`), timestamps, risk/confidence.
- [x] Append-only provenance: no UPDATE/DELETE path; rollback creates a new row referencing prior version refs.
- [x] Store queries for `MetricsDTO`, `GET /proposals/:id`, approval lookup, rollback, and evidence snapshots.

#### GraphDTO Assembly

- [x] Build graph nodes and edges from Postgres `documents` and `edges` rows.
- [x] ACL-filtered nodes: inaccessible docs are silently dropped (never leaked).
- [x] `size` derived from `derive_importance(DocSignals)` — inbound ref centrality, 0.1–1.0.
- [x] `health` derived from `derive_health(DocSignals)` — `green/yellow/red/gray` based on conflict edges, staleness, deprecation, verification stamp.
- [x] `accessible` set to `True` only for docs that passed the ACL check.
- [x] Edges filtered: only included when both endpoints are visible to the principal.
- [x] `conflicts-with` edges included with weight so P1 can render red dashed conflict lines.
- [x] Deterministic ordering: nodes sorted by `id`, edges sorted by `(from, to, type)`.
- [x] Empty graph, single-node graph, and all-inaccessible graph handled without errors.

#### ACL/Governance Enforcement

- [x] `Principal` abstraction with stubbed roles/user tokens in `governance/acl.py`; no Entra ID needed for hackathon.
- [x] `can_access` + `can_write` enforce fail-closed ACL: unknown/empty ACL is public; non-empty ACL requires grant intersection.
- [x] Anonymous principal (`user="anonymous"`) cannot write regardless of ACL.
- [x] ACL enforced at graph read (`get_governed_graph`) and write (`approve_proposal`, `rollback_proposal`).
- [x] Sensitive-space / staged-approval: high-risk or low-confidence proposals require a second approval call to apply (`needs-review` state).
- [x] WebSocket events carry only IDs and type — no restricted content in payloads; clients re-fetch via ACL-checked REST.
- [x] Tests for ACL no-leak cases in `tests/test_acl.py`.
- [ ] ACL enforcement at chat/retrieval layer (P2-owned; P4 provides the `filter_accessible` helper for P2 to call — not yet integrated).

#### Approval Flow

- [x] Full README §6.8 sequence: propose → diff → evidence/confidence → approve/reject → apply → provenance.
- [x] Status transitions: `proposed → needs-review → applied → rolled-back` (plus implicit `rejected` path via no-apply).
- [x] Explicit approver identity required; anonymous writes denied.
- [x] Risk + confidence validation: `risk_level=high` or `confidence < 0.5` → staged approval.
- [x] Idempotent: re-approving an already-applied proposal returns existing provenance without re-applying.
- [x] Before/after version refs captured as `blob:sha256:<hash>` of diff/draft content.
- [x] Approved draft materialized into the `curated/` namespace via `ingest_content` (best-effort; failure does not fail approval).
- [x] Graph, proposal, and metrics WS events emitted after apply and rollback.
- [x] Rejection decisions preserved: proposal stays in `proposed`/`needs-review` status when not approved.

#### Provenance + Rollback

- [x] `ProvenanceEntry` written for every governed apply and rollback via `governance/store.append_provenance`.
- [x] Captures: `action`, `approvedBy`, `previousVersionRef`, `newVersionRef`, `evidenceSnapshot`, `confidence`, `reason`, `approvedAt`.
- [x] Evidence snapshots stored as immutable JSONB — unaffected by later doc/chunk changes.
- [x] Rollback implemented as a governed action: creates a new provenance row with swapped before/after refs.
- [x] Rollback ACL-checked: requester must have write rights.
- [x] Audit log is append-only (`INSERT` only; no UPDATE/DELETE on provenance rows).
- [x] Demo seed fixtures in `scripts/seed_demo.py` provide pre-seeded provenance history.
- [ ] Rollback conflict detection (when current version no longer matches `newVersionRef`) — deferred; current behaviour returns an error if status ≠ `applied`.

#### Verification Sandbox (real containerized target)

- [x] `backend/app/services/verification.py` implemented with real Docker execution.
- [x] Real containerized sandbox: `--network none`, `--memory 512m`, `--cpus 1.0`, `--pids-limit 256`, hard timeout.
- [x] Request validated: `command`, `repo`, `commitSha`, `image`, `timeoutMs` (capped at 120 s).
- [x] Returns real `SandboxResult`: `passed`, `exitCode`, `durationMs`, `stdoutTail`, `stderrTail`.
- [x] `available: false` + `sandboxRun: false` when Docker is not reachable — never a fake green pass.
- [x] `POST /verify` endpoint exposes the sandbox to the frontend.
- [ ] Persist `SandboxResult` per proposal (attach to proposal payload) — deferred; currently returned per-request only.

#### Metrics Aggregation

- [x] `MetricsDTO` fields: `staleDetected`, `staleFixed`, `duplicatesRemoved`, `conflictsDetected`, `conflictsResolved`, `brokenLinksResolved`, `docsWithVerificationStamp`, `avgTimeToUpdateHours`, `asOf`.
- [x] Counter semantics deterministic: `*Detected` from current graph/edge state; `*Fixed`/`*Resolved`/`*Removed` only from applied proposals.
- [x] Stale detected from `last_verified_sha IS NULL OR last_verified_sha <> commit_sha`.
- [x] `docsWithVerificationStamp` as fraction `[0,1]`.
- [x] `avgTimeToUpdateHours` from `created_at → applied_at` on applied proposals.
- [x] Metrics recomputed live from Postgres on each `GET /metrics` call — idempotent by construction.
- [x] WS `metrics` events emitted after approval, rollback, and refresh.

#### Job Queue

- [x] In-process async job registry in `app/services/jobs.py` (status: `queued → processing → succeeded/failed`).
- [x] `POST /documents?background=true` returns `202 + jobId` and runs ingest in a background thread.
- [x] `GET /jobs/{jobId}` exposes job status to the frontend.
- [x] Job failures emit WS `ingest` events with `status: "failed"` and error message.
- [x] Approval and rollback run synchronously (fast path) — no queue needed for MVP.

#### API routers + WebSocket

- [x] `GET /graph`: governed graph with real health/importance/ACL — `get_governed_graph()`.
- [x] `GET /documents/{docId}`: document with chunks from Postgres.
- [x] `GET /proposals/{id}`: camelCase proposal DTO with approval state and provenance.
- [x] `POST /proposals/{id}/approve`: ACL + risk validation, staged-approval, apply, provenance, WS events.
- [x] `POST /proposals/{id}/rollback`: append-only rollback provenance, WS events.
- [x] `GET /metrics`: live `MetricsDTO` from Postgres.
- [x] `GET /provenance/{docId}`: append-only audit history for a document.
- [x] `POST /ingest/refresh/{docId}`: re-process, stamp verified, emit WS events.
- [x] `POST /verify`: real Docker sandbox execution.
- [x] `WS /stream`: in-process pub/sub with heartbeat; events carry only IDs + type.
- [x] Error shapes: 404 missing proposal, 403 access denied, 202 staged-approval required, 400 governance error.
- [x] Pure-logic pytest coverage: `test_acl.py`, `test_health.py`, `test_metrics.py`, `test_verification.py`, `test_conflicts.py`.

### Integration (M2/M3)

- [x] Postgres store extended behind stable interfaces without breaking existing P1/P2/P3 call sites.
- [x] Demo seed fixtures in `scripts/seed_demo.py` — idempotent, includes stale/duplicate/conflict docs + proposals + provenance.
- [x] Real `AgentProposal` payloads from P3 persisted automatically via `save_proposal` in `/propose` handler.
- [x] Graph edges and document records from P2 ingestion persisted including duplicate/conflict signals.
- [x] WS events emitted after proposal creation, approval, rollback, graph changes, and metrics changes.
- [x] End-to-end path works: drop-off → proposal → approve → provenance → metrics.
- [x] Verification sandbox is real Docker or clearly reports `available: false`.

### Demo Polish (M4)

- [x] Provenance + rollback demo ready: `scripts/seed_demo.py` seeds `prop_demo_fix_stale` as applied with provenance entry; call `POST /proposals/prop_demo_fix_stale/rollback` to demo rollback live.
- [x] Stale fixtures seeded — `staleDetected >= 3`, `staleFixed >= 1` in metrics.
- [x] Duplicate fixture seeded — `demo/deployment-v2.md` has `duplicate-of` edge to `demo/deployment.md`.
- [x] Conflict fixture seeded — `demo/security-policy.md` has `conflicts-with` edge to `demo/zero-trust-policy.md`; node renders `health: "red"`.
- [x] Staged-approval demo ready: `prop_demo_resolve_conflict` is `risk_level: "high"` — first `POST /approve` moves it to `needs-review`; second apply applies it.
- [x] WS dashboard live: all governed writes emit events; frontend re-fetches full DTOs.
- [x] Fallback fixture data in `scripts/seed_demo.py` — demo works even with no real P2/P3 ingestion.
- [ ] Frontend governance panels (approve/reject UI, metrics dashboard, provenance panel) — owned by P1; P4 endpoints are ready.

## Key Design Rules & Gotchas

| Rule / gotcha | Practical guidance |
| --- | --- |
| ACL at every stage | Enforce before retrieval, before answer/proposal display, before approval/write, and before WebSocket broadcast. If a user cannot see a doc, no title, path, snippet, evidence, or edge should reveal it unless a director-approved fog contract says otherwise. |
| Provenance on every write | No authoritative state change is complete until a `ProvenanceEntry` exists. Approval without provenance is a failed write. |
| Idempotent writes | Ingestion retries, repeated approvals, repeated WS delivery, and job retries must not duplicate graph edges, provenance entries, or metrics increments. |
| Append-only audit | Never mutate or delete historical provenance rows. Corrections and rollbacks are new audit events that refer back to previous entries/version refs. |
| Sandbox is real or clearly absent | README §10.6 targets a real containerized sandbox — **implemented** in `app/services/verification.py`. Docker `--network none` + resource caps + timeout. Reports `available:false` when Docker is unreachable; never returns a fake pass. |
| Health derivation | Use `green` for verified/current, `yellow` for likely stale or needs review, `red` for conflict/broken/high-risk, and `gray` for unknown/unverified/deprecated unless the director freezes a stricter mapping. |
| Importance derivation | Store `importance` as `0..1`; seed from P2 signals when available, otherwise use deterministic defaults based on references, ownership, recency, and demo fixture importance. |
| Sensitive spaces | Treat restricted ACLs, high-risk proposal types, or owner-marked docs as requiring staged approval. Do not silently downgrade staged approval to one-click apply. |
| Metrics credibility | Counters should move only on meaningful state transitions, especially approved/apply events. Proposal creation can increment detected counters but should not increment fixed/resolved counters. |
| Contract names | Match README §8A and general-plan §7 target names, including camelCase JSON names. Today's implemented contracts are `documents`/`chunks`/`edges` rows plus `GraphDTO`/document response assembly; if code and docs disagree, escalate instead of inventing a local variant. |
| UI re-fetch pattern | WS events should be small and safe. Prefer sending event type + IDs + version/asOf and let P1 re-fetch `GraphDTO`/`MetricsDTO` through ACL-checked REST. |
| Failure posture | Fail closed for ACL, fail visible for job/approval errors, and fail reversible for writes by preserving prior version refs. |

Approval flow checklist for every authoritative write:

1. Load proposal and target `DocumentRecord`.
2. Verify requester can read proposal evidence and write target doc.
3. Check risk, confidence, and sensitive-space staged-approval requirements.
4. Capture `previousVersionRef`.
5. Apply the change through the store/write adapter.
6. Capture `newVersionRef`.
7. Append `ProvenanceEntry` with immutable evidence snapshot.
8. Update metrics idempotently.
9. Emit proposal, graph/health, metrics, and provenance WS events.
10. Return an approval result that P1 can display without leaking restricted data.

## Definition of Done

Tie completion to the team-plan §7 quality gate and the M1–M4 milestones.

| Done criterion | Person 4 evidence |
| --- | --- |
| Contracts honored | Current router responses validate against implemented graph/document DTOs; future governance routes validate against `DocumentRecord`, `ProvenanceEntry`, `SandboxResult`, `MetricsDTO`, and `AgentProposal` target shapes. |
| Backend quality gate passes | Run whatever backend checks are configured at the time. As of 2026-06-23, ruff/black/pytest are not configured in the repo. |
| Works with current and real dependencies | Current Postgres-backed graph/document API works; M3 Postgres-backed governance routes work with real P2/P3 outputs while retaining clearly labeled fixture fallback. |
| ACL edge cases handled | Tests cover inaccessible graph nodes/edges, proposal evidence filtering, denied approvals, denied rollback, and WS no-leak behavior. |
| Provenance mandatory | Every approve/apply/rollback path writes exactly one append-only `ProvenanceEntry` per governed state change. |
| Idempotent and retry-safe | Repeated ingestion/approval/job execution does not duplicate edges, apply changes twice, or double-count metrics. |
| Verification correctly scoped | `SandboxRequest` is accepted and `SandboxResult` is returned by the real containerized service, or the API clearly reports verification as unavailable rather than mocked as real. |
| Metrics demo credible | `MetricsDTO` counters and `asOf` update after planted stale/duplicate/conflict approval flows. |
| WebSocket integration useful | `WS /stream` emits proposal, graph, health, and metrics updates that P1 can use for live dashboard/provenance moments. |
| M4 demo-ready | The 9-step demo can show review/approval, ACL-safe graph, provenance, rollback, staged approval, and metrics movement without manual database edits. |
