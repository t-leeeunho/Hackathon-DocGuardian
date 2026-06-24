# Person 4 — Governance, Verification & Metrics

> **As-built status (2026-06-23):** the Postgres store (documents/chunks/edges) exists; governance, approval, provenance, metrics, and the verification sandbox are NOT built yet. See [../implementation-status.md](../implementation-status.md).
> Today there are no ACL columns/checks, no `approvals`/`provenance` tables, no `/metrics`, no `GET /proposals/:id`, no `POST /proposals/:id/approve`, and no `WS /stream`.

Own the enterprise-trust backend slice: permissions/ACL, approval workflow, provenance and rollback, metadata/graph persistence, metrics, real containerized verification sandbox, and the REST/WebSocket API plumbing for graph and proposals.

## Mission

Person 4 owns the part of DocGuardian AI that makes the demo feel enterprise-safe rather than merely AI-assisted. Your mission is to ensure every read, answer, and write is permission-aware; every authoritative change moves through propose → diff → approve → apply → provenance; and every visible dashboard metric can be traced back to persisted state. For M1–M4, bias toward a believable governed slice with strong contracts, append-only auditability, the README §10.6 real containerized verification target, and live API/WS updates that let P1 demonstrate trust, impact, and rollback.

## Scope — What You Own

You own the Layer 4 backend implementation that sits between P2/P3's retrieval/agent outputs and P1's UI surfaces.

| Area | Files / modules | Responsibility |
| --- | --- | --- |
| Postgres + pgvector store | `backend/app/storage/db.py`, `queries.py`, `vectorstore.py` | Existing Postgres implementation: `init_schema()` creates `documents`, `chunks`, `edges` plus a `chunks.embedding` HNSW cosine index; `queries.py` exposes `list_doc_ids`, `get_document`, `get_graph`; `vectorstore.py` handles upserts and cosine search. README §10.4 locks one PostgreSQL instance for metadata, graph, audit, approvals, and provenance. |
| Governance service | Planned `backend/app/services/governance.py` | Not built yet: ACL enforcement at retrieval, answer, and write; approval state machine; governed write orchestration; `ProvenanceEntry` creation; rollback. |
| Verification service | Planned `backend/app/services/verification.py` | Not built yet: README §10.6 now targets a real containerized sandbox, not a mock. |
| DTO assembly | Current `queries.get_graph`; future store/service methods | `GraphDTO` is assembled from Postgres rows today, but node `health`, `size`, and `accessible` are placeholders. `MetricsDTO` is not implemented. |
| Async jobs | Simple job queue in your backend-owned area | Keep approval application, verification, metrics recomputation, and WebSocket fan-out off latency-sensitive request paths where practical. |
| API router | Current `backend/app/main.py`; future `backend/app/api/graph.py` | `GET /graph` exists today in the single `app/main.py`; future split should add ACL-filtered graph nodes and health/importance-derived view fields. |
| API router | Planned `backend/app/api/proposals.py` | Not built yet: `GET /proposals/:id`, `POST /proposals/:id/approve`, proposal lookup, approval, governed apply, provenance, rollback hooks. |
| API router | Planned `backend/app/api/metrics.py` | Not built yet: `GET /metrics` returning aggregate `MetricsDTO` counters. |
| API router | Planned `backend/app/api/stream.py` | Not built yet: `WS /stream` live proposal, graph, health, and metrics updates for the frontend. |

Concrete persisted data:

- [x] Existing Postgres rows: `documents` (`doc_id`, repo/path/commit metadata/content hash), `chunks` (text, heading path, line range, embedding), and `edges` (`from_doc`, `to_doc`, `type`, `weight`, evidence-ish metadata).
- [x] Existing graph edges are persisted in Postgres; processing currently emits structural `references` edges.
- [ ] Pending P4 work: `DocumentRecord`-equivalent governance fields such as `health`, `importance`, `acl[]`, `lastVerifiedSha`, `lastVerifiedAt`, `currentCommitSha`, and `chunkIds`.
- [ ] Pending P4 work: duplicate/conflict/deprecated edge semantics beyond current stored edge rows.
- [ ] Pending P4 work: approval records and decision history.
- [ ] Pending P4 work: append-only `ProvenanceEntry` audit log for every governed change.
- [ ] Pending P4 work: metrics rollups needed for `MetricsDTO`.
- [ ] Pending P4 work: verification results matching `SandboxResult` from a real containerized sandbox target.

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
- [ ] Extend the store contract on top of Postgres so it supports ACL-filtered graph query, proposal lookup, approval write, provenance append, rollback lookup, and metrics aggregation.
- [ ] Help author the frozen `VectorIndex` interface only where it affects ACL-filtered retrieval handoff; keep retrieval implementation owned by P2.
- [ ] Add any fixture/dev-store behavior only if needed; do not replace the existing Postgres source of truth with a separate in-memory or SQLite store.
- [ ] Help the director validate future `DocumentRecord`, `ProvenanceEntry`, `MetricsDTO`, `SandboxRequest`, `SandboxResult`, and `AgentProposal` fixtures against README §8A shapes; note these are not implemented today. `GraphDTO` is the only relevant shape currently assembled, via `queries.get_graph`.
- [ ] Decide whether to keep routes in `app/main.py` or split future routers into `backend/app/api/graph.py`, `proposals.py`, `metrics.py`, and `stream.py`; current code has no per-domain router files.
- [ ] Replace `GET /graph` placeholders: today every node returns `health: "green"`, `size: 0.5`, and `accessible: true`; add real health, importance, and ACL behavior.
- [ ] Implement `GET /metrics`; no endpoint exists today.
- [ ] Implement `GET /proposals/:id`; no endpoint exists today.
- [ ] Implement `POST /proposals/:id/approve`; no endpoint exists today.
- [ ] Document any missing fields as director questions instead of editing frozen models yourself.

### Core Build

#### Postgres Store

- [x] Use the existing Postgres + pgvector store in `app/storage/`: `db.py` creates `documents`, `chunks`, and `edges`; `chunks.embedding` uses pgvector with an HNSW cosine index.
- [x] Persist baseline document metadata, chunks, embeddings, and graph edges in Postgres with idempotent upserts through `vectorstore.py`.
- [ ] Design additional Postgres tables/columns for ACLs, approvals, proposal snapshots, provenance entries, version refs, metrics counters, and optional job queue rows while preserving contract field names at API boundaries.
- [ ] Persist `DocumentRecord`-equivalent governance fields with unique `docId`, repo/path/title/owner, ACL list, health, importance, verification fields, `currentCommitSha`, chunk IDs, `createdAt`, and `updatedAt`.
- [ ] Store ACLs in a queryable form (for example normalized table or JSON plus helper methods) so graph/proposal/answer filters cannot accidentally leak restricted docs.
- [ ] Persist graph edges with stable IDs derived from `from`, `to`, `type`, and optional source evidence to make repeated ingestion idempotent.
- [ ] Support edge types `references`, `duplicate-of`, `conflicts-with`, and `deprecated-by`; treat unknown edge types as validation errors or director-contract issues.
- [ ] Add idempotent upsert semantics: unchanged `contentHash` or repeated edge proposal must not create duplicate records or move metrics twice.
- [ ] Implement approval persistence with proposal ID, approver, status, timestamps, staged-approval state, and risk/sensitive-space markers.
- [ ] Implement append-only provenance persistence: no update/delete path for historical entries; rollback creates a new entry rather than rewriting old audit history.
- [x] Provide existing store queries for `GET /graph` and `GET /documents/{docId}`.
- [ ] Provide store queries for `MetricsDTO`, `GET /proposals/:id`, approval lookup, rollback lookup, and evidence snapshots.
- [ ] Keep all new governance persistence in the single Postgres instance locked by README §10.4.

#### GraphDTO Assembly

- [x] Build current graph nodes and edges from Postgres `documents` and `edges` rows in `queries.get_graph`.
- [ ] Replace placeholder graph node fields with ACL-filtered `DocumentRecord`-equivalent rows.
- [ ] Map `DocumentRecord.importance` directly to graph `size` unless the frozen contract specifies a scaling transform; current `size` is hardcoded around `0.5`.
- [ ] Map `DocumentRecord.health` directly to graph health colors: `green`, `yellow`, `red`, `gray`; current `health` is hardcoded `"green"`.
- [ ] Set `accessible` according to the request principal; never include inaccessible titles, snippets, paths, or evidence unless the contract explicitly permits a fog-only placeholder.
- [ ] Include graph edges only when the viewer can see both endpoints, or downgrade them to non-leaking aggregate/fog indicators if the director explicitly approves that contract behavior.
- [ ] Preserve `conflicts-with` edges with weight so P1 can render red dashed conflict lines.
- [ ] Add deterministic ordering for nodes and edges so UI snapshots/tests remain stable.
- [ ] Include repo metadata needed by the graph view and scope toggles.
- [ ] Handle empty graph, all-inaccessible graph, and single-node graph without errors.

#### ACL/Governance Enforcement

- [ ] Define a request-principal abstraction using the MVP stubbed roles/users; do not attempt full Entra ID for the hackathon.
- [ ] Enforce ACLs at **retrieval**: filter document IDs/chunk IDs before they reach answer generation or proposal evidence.
- [ ] Enforce ACLs at **answer**: no `ChatAnswer` citation, excerpt, or graph highlight should reference content the user cannot access.
- [ ] Enforce ACLs at **write**: approver must have write rights for the target doc and any affected sensitive space.
- [ ] Fail closed when ACL metadata is missing: unknown ACL means inaccessible unless the director declares a public default.
- [ ] Add sensitive-space handling: high-risk docs or restricted ACLs require staged approval before apply.
- [ ] Ensure proposal evidence snapshots are ACL-checked before display and before approval.
- [ ] Ensure WebSocket events carry only IDs and fields allowed for the subscribed principal.
- [ ] Add tests for no-leak cases: hidden node, hidden edge, hidden proposal evidence, denied approval, and denied rollback.

#### Approval Flow

- [ ] Model the README §6.8 sequence exactly: propose → diff → evidence/confidence → approve/reject → apply approved change → record provenance.
- [ ] Store proposal status transitions: `proposed`, `needs-review`, `approved`, `rejected`, `applied`, `rolled-back`, and any director-approved final names.
- [ ] Require an explicit approver identity for `POST /proposals/:id/approve`; do not allow anonymous authoritative writes.
- [ ] Validate proposal risk and confidence before approval; low-confidence or high-risk proposals should require staged approval or remain `needs-review`.
- [ ] Make approval idempotent: repeated approve calls for an already-applied proposal return the existing result and must not re-apply or duplicate provenance.
- [ ] Capture before/after version refs before applying any change.
- [ ] Apply approved changes through the Postgres-backed store/write adapter, not by direct file edits in MVP unless the director explicitly adds an authoritative-write adapter.
- [ ] Emit graph, health, metrics, and proposal WebSocket events after apply.
- [ ] Preserve rejection decisions for future learning-from-feedback narratives, even if actual learning is deferred.

#### Provenance + Rollback

- [ ] Write a `ProvenanceEntry` for every governed apply, rollback, merge, deprecate, create, or metadata-changing write.
- [ ] Include what changed (`action`), who approved, which agent proposed, why, supporting sources, `previousVersionRef`, `newVersionRef`, confidence, and timestamp.
- [ ] Store evidence snapshots immutably so later document/chunk changes do not erase the approval rationale.
- [ ] Implement one-click rollback as a governed action that restores or points back to `previousVersionRef` and creates a new rollback provenance entry.
- [ ] Prevent rollback if the requester lacks write permission on the target doc.
- [ ] Handle rollback conflicts when the current version no longer matches the provenance entry's `newVersionRef`; require review instead of overwriting.
- [ ] Expose enough provenance data through proposal/graph-related reads for P1's provenance panel without leaking restricted evidence.
- [ ] Keep the audit log append-only: never mutate historical `approvedBy`, `reason`, evidence, or version refs.
- [ ] Add seeded provenance fixtures so the demo can show history even before several live approvals have occurred.

#### Verification Sandbox (real containerized target)

- [ ] Implement `backend/app/services/verification.py`; no verification service exists today.
- [ ] Build README §10.6 target for real, not mocked: isolated container, repo checkout at `commitSha`, command timeout, stdout/stderr tail truncation, no secrets, resource limits, and safe cleanup.
- [ ] Validate request shape: `repo`, `commitSha`, `command`, and `timeoutMs` must be present and within safe demo limits before execution.
- [ ] Return `SandboxResult` with real `passed`, `exitCode`, `durationMs`, `stdoutTail`, and `stderrTail` from the containerized run.
- [ ] Attach or persist `SandboxResult` where proposals/approval logic expects verification context.
- [ ] Represent failed verification scenarios for conflict/stale demos; do not make every proposal green.
- [ ] If a temporary fixture is used before the sandbox is built, label it explicitly as non-verifying so the team does not overclaim real container isolation.

#### Metrics Aggregation

- [ ] Aggregate `MetricsDTO` exactly: `staleDetected`, `staleFixed`, `duplicatesRemoved`, `conflictsDetected`, `conflictsResolved`, `brokenLinksResolved`, `docsWithVerificationStamp`, `avgTimeToUpdateHours`, and `asOf`.
- [ ] Decide which persisted events increment each counter and make the mapping deterministic.
- [ ] Count stale detected from health/commit drift signals where `currentCommitSha != lastVerifiedSha` or P2 flags staleness.
- [ ] Count stale fixed and conflicts resolved only after approved governed writes, not merely after proposal creation.
- [ ] Count duplicates removed after merge/deprecate actions are approved and applied.
- [ ] Compute `docsWithVerificationStamp` as a fraction in `[0,1]` based on records with `lastVerifiedSha` and `lastVerifiedAt`.
- [ ] Compute `avgTimeToUpdateHours` from detection timestamp to applied timestamp where available; fall back to seeded demo values only for M1/M4 fixtures.
- [ ] Recompute or increment metrics idempotently so retries do not double-count.
- [ ] Emit metrics update events on WebSocket after approval, rollback, and seeded fixture changes.

#### Job Queue

- [ ] Provide a simple async job queue abstraction for verification jobs, approval apply tasks, metrics recomputation, and WS fan-out.
- [ ] Keep job payloads contract-oriented: proposal ID, doc ID, event type, and principal context rather than arbitrary code callbacks.
- [ ] Persist or at least track job status for demo reliability: queued, running, succeeded, failed.
- [ ] Make jobs idempotent and retry-safe; approval jobs must check current proposal status before applying.
- [ ] Surface job failures to proposal status and WebSocket events so P1 can show a useful message.
- [ ] Keep the queue simple for MVP: in-process async is acceptable unless the director chooses a worker process.
- [ ] Do not make request handlers wait for long-running verification/apply work if a queued response plus WS update is sufficient for UX.

#### API routers + WebSocket

- [x] `GET /graph`: implemented in `app/main.py` using `queries.get_graph` over Postgres `documents`/`edges`.
- [x] `GET /documents/{docId}`: implemented in `app/main.py` using `queries.get_document` over Postgres `documents`/`chunks`.
- [ ] Upgrade `GET /graph`: authenticate/stub principal, query ACL-filtered graph, replace placeholder health/size/accessible fields, and handle empty/scope-filtered graph.
- [ ] `GET /proposals/:id`: return `AgentProposal` plus approval/provenance context if contract allows; deny inaccessible proposal evidence.
- [ ] `POST /proposals/:id/approve`: validate approver, ACL, proposal status, risk/staged approval, then apply and write provenance.
- [ ] `GET /metrics`: return current `MetricsDTO` with fresh `asOf`; avoid expensive full scans if cached rollups are available.
- [ ] `WS /stream`: accept subscriptions for proposal, graph, health, and metrics updates; send compact event envelopes and let P1 re-fetch full DTOs as needed.
- [ ] Send an initial WS connected/heartbeat event so P1 can show live status during M1.
- [ ] Guard WS events with the same ACL logic as REST; never broadcast hidden proposal/document content to all clients.
- [ ] Define error shapes for denied approval, missing proposal, already-applied proposal, staged-approval required, and sandbox failure/unavailable status.
- [ ] Add pytest coverage for all routers you own with mocked-auth principals and fixture proposals.

### Integration (M2/M3)

- [ ] Extend the existing Postgres store behind stable interfaces without changing P1/P2/P3 call sites.
- [ ] Migrate or seed M1 fixtures into Postgres so the demo still works before real ingestion completes.
- [ ] Consume real `AgentProposal` payloads from P3 while retaining sample fixtures for offline development.
- [ ] Persist real graph edges and document records from P2, including duplicate/conflict/stale signals.
- [ ] Reconcile P2 health/importance signals with P4's persisted `DocumentRecord` fields; use deterministic defaults where P2 omits values.
- [ ] Confirm P3 proposal evidence only references docs/chunks visible to the request principal before exposing it to P1.
- [ ] Wire approval apply results back into P3/P2-facing state only through contracts/events, not direct source edits.
- [ ] Emit live WebSocket updates to P1 after proposal creation, approval, graph changes, health changes, and metrics changes.
- [ ] Run M3 end-to-end: drop-off → proposal → approve → provenance → metrics, matching README §8A.7.
- [ ] Validate that the verification sandbox is either truly containerized or clearly marked unavailable/fixture-only; README §10.6 no longer treats a mock sandbox as the target.

### Demo Polish (M4)

- [ ] Prepare a provenance + rollback demo using at least one approved change with visible before/after version refs and an append-only rollback entry.
- [ ] Ensure planted stale fixtures move `staleDetected` and `staleFixed` counters when approved.
- [ ] Ensure planted duplicate fixtures move `duplicatesRemoved` after a merge/deprecate approval.
- [ ] Ensure planted conflict fixtures show `conflicts-with` edges and move `conflictsDetected` / `conflictsResolved` after approval.
- [ ] Create a staged-approval moment for a sensitive space: first approval records review, final approval applies the change.
- [ ] Ensure WS-driven dashboard updates are visible without manual refresh during the M4 script.
- [ ] Seed at least one inaccessible node/edge/proposal evidence case to prove ACL filtering works, while avoiding distracting demo failures.
- [ ] Add fallback fixture data so the demo can proceed if real P2/P3 outputs or live jobs are unavailable.
- [ ] Rehearse error-free approve and rollback paths; pre-clear idempotency so retries do not double-count metrics.
- [ ] Prepare concise presenter notes explaining the actual verification status: README §10.6 targets real container execution, but it is not implemented until P4 builds it.

## Key Design Rules & Gotchas

| Rule / gotcha | Practical guidance |
| --- | --- |
| ACL at every stage | Enforce before retrieval, before answer/proposal display, before approval/write, and before WebSocket broadcast. If a user cannot see a doc, no title, path, snippet, evidence, or edge should reveal it unless a director-approved fog contract says otherwise. |
| Provenance on every write | No authoritative state change is complete until a `ProvenanceEntry` exists. Approval without provenance is a failed write. |
| Idempotent writes | Ingestion retries, repeated approvals, repeated WS delivery, and job retries must not duplicate graph edges, provenance entries, or metrics increments. |
| Append-only audit | Never mutate or delete historical provenance rows. Corrections and rollbacks are new audit events that refer back to previous entries/version refs. |
| Sandbox is real or clearly absent | README §10.6 targets a real containerized sandbox. Do not present deterministic fixtures as real verification; until built, verification is pending/unavailable. |
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
