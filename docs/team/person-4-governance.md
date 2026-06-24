# Person 4 — Governance, Verification & Metrics

Own the enterprise-trust backend slice: permissions/ACL, approval workflow, provenance and rollback, metadata/graph persistence, metrics, mock verification sandbox, and the REST/WebSocket API plumbing for graph and proposals.

## Mission

Person 4 owns the part of DocGuardian AI that makes the demo feel enterprise-safe rather than merely AI-assisted. Your mission is to ensure every read, answer, and write is permission-aware; every authoritative change moves through propose → diff → approve → apply → provenance; and every visible dashboard metric can be traced back to persisted state. For M1–M4, bias toward a believable governed slice with strong contracts, append-only auditability, mock sandbox verification, and live API/WS updates that let P1 demonstrate trust, impact, and rollback.

## Scope — What You Own

You own the Layer 4 backend implementation that sits between P2/P3's retrieval/agent outputs and P1's UI surfaces.

| Area | Files / modules | Responsibility |
| --- | --- | --- |
| SQLite store | `backend/app/store/sqlite_*.py` | SQLite implementation of the frozen `Store` interface: `DocumentRecord`, graph edges, document health, importance, ACLs, approvals, and append-only provenance. |
| Governance service | `backend/app/services/governance.py` | ACL enforcement at retrieval, answer, and write; approval state machine; governed write orchestration; `ProvenanceEntry` creation; rollback. |
| Verification service | `backend/app/services/verification.py` | MVP mock verification sandbox: accept `SandboxRequest`, return `SandboxResult`; keep a clean seam for real container execution later. |
| DTO assembly | Store/service methods within your owned modules | Assemble `GraphDTO` and `MetricsDTO` exactly as frozen in README §8A.6. |
| Async jobs | Simple job queue in your backend-owned area | Keep approval application, verification, metrics recomputation, and WebSocket fan-out off latency-sensitive request paths where practical. |
| API router | `backend/app/api/graph.py` | `GET /graph`: return ACL-filtered graph nodes and edges with health/importance-derived view fields. |
| API router | `backend/app/api/proposals.py` | `GET /proposals/:id`, `POST /proposals/:id/approve`: proposal lookup, approval, governed apply, provenance, rollback hooks. |
| API router | `backend/app/api/metrics.py` | `GET /metrics`: return aggregate `MetricsDTO` counters. |
| API router | `backend/app/api/stream.py` | `WS /stream`: live proposal, graph, health, and metrics updates for the frontend. |

Concrete persisted data you own:

- `DocumentRecord` rows with `health` (`green` / `yellow` / `red` / `gray`), `importance` (`0..1`), `acl[]`, `lastVerifiedSha`, `lastVerifiedAt`, `currentCommitSha`, and `chunkIds`.
- Graph edges, including `references`, `duplicate-of`, `conflicts-with`, and `deprecated-by`.
- Approval records and decision history.
- Append-only `ProvenanceEntry` audit log for every governed change.
- Metrics rollups needed for `MetricsDTO`.
- Mock verification results matching `SandboxResult`.

## What You Must NOT Touch

Do not create or edit application code outside your ownership boundary.

| Frozen / other-owned area | Rule |
| --- | --- |
| `backend/app/models/**` | **FROZEN via director.** These define Pydantic contracts; request director changes if a contract is incomplete. |
| `frontend/src/lib/types.ts` | **FROZEN via director.** TypeScript mirror must remain director-owned. |
| `backend/app/main.py` | Router wiring is director-owned after Phase 0. Ask for wiring changes; do not edit directly. |
| P1 frontend directories | Serve `GraphDTO`, `MetricsDTO`, proposals, and WS events; do not implement UI behavior. |
| P2 ingestion/processing/retrieval/vector files | Persist P2 outputs through interfaces; do not change their implementation. |
| P3 orchestrator/agents/provider files and routers | Consume `AgentProposal` fixtures or real proposals; do not modify agent logic. |
| Shared config/contracts/tooling | Only touch if explicitly assigned in Phase 0 by the director. |

If you need another person's behavior before integration, use fixtures/fakes. Do not block on the other stream and do not patch their files to unblock yourself.

## Inputs (Consumed, Mocked) & Outputs (Produced)

| Contract / payload | Direction for P4 | M1 status | M2/M3 status | What P4 must guarantee |
| --- | --- | --- | --- | --- |
| `AgentProposal` | Consumed from P3 / proposal fixtures | Mocked fixture proposals returned by `GET /proposals/:id` | Real proposals from P3, persisted and approval-ready | Preserve diff, evidence, confidence, risk, verification, source IDs, and proposal ID exactly. |
| `DocumentRecord` | Produced/persisted by P4 | Fixture/in-memory records | SQLite canonical row | ACL, health, importance, commit refs, verification stamp, and chunk mapping are durable and idempotent. |
| `GraphEdge` | Consumed from P2/P3, persisted by P4 | Fixture edges | Real P2/P3 edges | Keep edge type and weight; include `conflicts-with` for red dashed graph visualization. |
| `ProvenanceEntry` | Produced by P4 | Fixture log entries | Append-only SQLite audit row | Mandatory on every governed write and rollback; captures who/what/why/sources/versions. |
| `SandboxRequest` | Consumed by P4 verification service | Mock request shape only | Passed to mock sandbox until stretch real sandbox | Validate repo, commit SHA, command, and timeout without executing untrusted code in MVP. |
| `SandboxResult` | Produced by P4 verification service | Deterministic mock result | Mock result attached to proposal/approval flow | Return `passed`, `exitCode`, `durationMs`, `stdoutTail`, `stderrTail`; never pretend real execution occurred. |
| `GraphDTO` | Produced by P4 for P1 | Mock API body | SQLite-backed graph assembly | Nodes sized by importance, colored by health, ACL-filtered, with accessible flags. |
| `MetricsDTO` | Produced by P4 for P1 | Mock counters | Store-backed aggregate counters | Counters update after approval/rollback/seed fixtures and expose `asOf`. |
| WebSocket events | Produced by P4 for P1 | Simple heartbeat / fixture events | Live proposal, graph, health, metrics events | Events are small, typed, and re-fetch-friendly; no inaccessible content in payloads. |

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
// SandboxResult returned by MVP mock verification
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
| P1 — Frontend & Demo Experience | UI requirements for graph, metrics, diff/review, provenance, and WebSocket event cadence | `GET /graph`, `GET /proposals/:id`, `POST /proposals/:id/approve`, `GET /metrics`, `WS /stream` | M1: fixture responses; M3: real API responses; M4: live WS dashboard/provenance demo. |
| P2 — Retrieval & Document Intelligence | `DocumentRecord` candidates, `DocChunk` references, `GraphEdge` relations, health/importance signals if supplied | Durable metadata/graph persistence, graph edges available to UI and governance | M1: fixture edges/records; M2: consume real retrieval outputs; M3: persist real edges/records in SQLite. |
| P3 — Agent Orchestration & AI Reasoning | `AgentProposal` with diff, evidence, confidence, risk, and verification context | Proposal persistence, approval result, sandbox result seam, provenance context | M1: sample proposal fixtures; M2: consume real Curator/Guardian proposals; M3: governed approval path. |
| Director / shared foundation | Frozen models, router wiring, `Store` interface, `InMemoryStore`, fixtures, toolchain | Feedback on contract gaps only; no unilateral edits to frozen files | M1: help author contracts/fixtures; after M1: request director changes for contract drift. |

Phase-by-phase integration stance:

- **M1 — contracts + mocks:** implement mock router bodies and `InMemoryStore` behavior against frozen contracts; return valid `GraphDTO`, `MetricsDTO`, and proposal fixtures before real P2/P3 outputs exist.
- **M2 — real retrieval/agents emerging:** continue to accept fixtures while adding ingestion points for P2 graph/record outputs and P3 `AgentProposal`; keep toggles or adapters so mocks remain usable.
- **M3 — real API serves UI:** replace in-memory/mock bodies with SQLite-backed service calls; enforce ACLs; write provenance on approved changes; stream updates to P1.
- **M4 — demo-ready polish:** seed planted stale/duplicate/conflict fixtures; ensure metrics visibly move; show staged approval and rollback without needing real container execution.

## Detailed TODOs

### Phase 0 — Foundation participation

- [ ] Help author the frozen `Store` interface so it supports document upsert, document lookup, edge upsert, ACL-filtered graph query, proposal lookup, approval write, provenance append, rollback lookup, and metrics aggregation.
- [ ] Help author the frozen `VectorIndex` interface only where it affects ACL-filtered retrieval handoff; keep retrieval implementation owned by P2.
- [ ] Implement or co-implement `InMemoryStore` behavior needed by P1/P2/P3/P4 fixtures, including deterministic IDs and idempotent upserts.
- [ ] Help the director validate `DocumentRecord`, `ProvenanceEntry`, `GraphDTO`, `MetricsDTO`, `SandboxRequest`, `SandboxResult`, and `AgentProposal` fixtures against README §8A shapes.
- [ ] Stand up mock bodies in `backend/app/api/graph.py`, `backend/app/api/proposals.py`, `backend/app/api/metrics.py`, and `backend/app/api/stream.py` without touching `backend/app/main.py` after director wiring.
- [ ] Ensure `GET /graph` mock returns health colors (`green` / `yellow` / `red` / `gray`), importance-derived `size`, at least one `conflicts-with` edge, and an inaccessible-node example if contract permits.
- [ ] Ensure `GET /metrics` mock returns non-zero counters that support the M1 frontend dashboard.
- [ ] Ensure `GET /proposals/:id` mock returns a proposal with diff, evidence, confidence, risk, and a mock `SandboxResult` so P1 can render the review panel.
- [ ] Ensure `POST /proposals/:id/approve` mock returns a realistic accepted response and emits or queues graph/metrics/provenance update events for WS consumers.
- [ ] Document any missing fields as director questions instead of editing frozen models yourself.

### Core Build

#### SQLite Store

- [ ] Design SQLite tables for documents, graph edges, approvals, proposal snapshots, provenance entries, version refs, metrics counters, and optional job queue rows while preserving contract field names at API boundaries.
- [ ] Persist `DocumentRecord` with unique `docId`, repo/path/title/owner, ACL list, health, importance, verification fields, `currentCommitSha`, chunk IDs, `createdAt`, and `updatedAt`.
- [ ] Store ACLs in a queryable form (for example normalized table or JSON plus helper methods) so graph/proposal/answer filters cannot accidentally leak restricted docs.
- [ ] Persist graph edges with stable IDs derived from `from`, `to`, `type`, and optional source evidence to make repeated ingestion idempotent.
- [ ] Support edge types `references`, `duplicate-of`, `conflicts-with`, and `deprecated-by`; treat unknown edge types as validation errors or director-contract issues.
- [ ] Add idempotent upsert semantics: unchanged `contentHash` or repeated edge proposal must not create duplicate records or move metrics twice.
- [ ] Implement approval persistence with proposal ID, approver, status, timestamps, staged-approval state, and risk/sensitive-space markers.
- [ ] Implement append-only provenance persistence: no update/delete path for historical entries; rollback creates a new entry rather than rewriting old audit history.
- [ ] Provide store queries for `GraphDTO`, `MetricsDTO`, `GET /proposals/:id`, approval lookup, rollback lookup, and evidence snapshots.
- [ ] Keep SQLite implementation behind the `Store` interface so `InMemoryStore` can remain a test/dev substitute.

#### GraphDTO Assembly

- [ ] Build `GraphDTO.nodes[]` from ACL-filtered `DocumentRecord` rows.
- [ ] Map `DocumentRecord.importance` directly to graph `size` unless the frozen contract specifies a scaling transform.
- [ ] Map `DocumentRecord.health` directly to graph health colors: `green`, `yellow`, `red`, `gray`.
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
- [ ] Apply approved changes through the `Store` abstraction, not by direct file edits in MVP unless the director explicitly adds an authoritative-write adapter.
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

#### Verification Sandbox (mock)

- [ ] Implement `backend/app/services/verification.py` as a mock `SandboxRequest` → `SandboxResult` service for MVP.
- [ ] Validate request shape: `repo`, `commitSha`, `command`, and `timeoutMs` must be present and within safe demo limits.
- [ ] Return deterministic mock results based on fixture IDs, command names, or seeded scenarios so demos are repeatable.
- [ ] Include realistic `durationMs`, `stdoutTail`, and `stderrTail` values without executing arbitrary commands.
- [ ] Attach or persist mock `SandboxResult` where proposals/approval logic expects verification context.
- [ ] Represent failed verification fixtures for conflict/stale demos; do not make every proposal green.
- [ ] Log clearly that execution is mocked so the team does not overclaim real container isolation.
- [ ] Sketch the stretch real architecture in comments/docs: isolated container, repo checkout at `commitSha`, command timeout, stdout/stderr tail truncation, no secrets, resource limits.

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

- [ ] Provide a simple async job queue abstraction for verification mock jobs, approval apply tasks, metrics recomputation, and WS fan-out.
- [ ] Keep job payloads contract-oriented: proposal ID, doc ID, event type, and principal context rather than arbitrary code callbacks.
- [ ] Persist or at least track job status for demo reliability: queued, running, succeeded, failed.
- [ ] Make jobs idempotent and retry-safe; approval jobs must check current proposal status before applying.
- [ ] Surface job failures to proposal status and WebSocket events so P1 can show a useful message.
- [ ] Keep the queue simple for MVP: in-process async is acceptable unless the director chooses a worker process.
- [ ] Do not make request handlers wait for long-running verification/apply work if a queued response plus WS update is sufficient for UX.

#### API routers + WebSocket

- [ ] `GET /graph`: authenticate/stub principal, query ACL-filtered graph, return `GraphDTO`, handle empty/scope-filtered graph.
- [ ] `GET /proposals/:id`: return `AgentProposal` plus approval/provenance context if contract allows; deny inaccessible proposal evidence.
- [ ] `POST /proposals/:id/approve`: validate approver, ACL, proposal status, risk/staged approval, then apply and write provenance.
- [ ] `GET /metrics`: return current `MetricsDTO` with fresh `asOf`; avoid expensive full scans if cached rollups are available.
- [ ] `WS /stream`: accept subscriptions for proposal, graph, health, and metrics updates; send compact event envelopes and let P1 re-fetch full DTOs as needed.
- [ ] Send an initial WS connected/heartbeat event so P1 can show live status during M1.
- [ ] Guard WS events with the same ACL logic as REST; never broadcast hidden proposal/document content to all clients.
- [ ] Define error shapes for denied approval, missing proposal, already-applied proposal, staged-approval required, and sandbox mock failure.
- [ ] Add pytest coverage for all routers you own with mock principals and fixture proposals.

### Integration (M2/M3)

- [ ] Swap `InMemoryStore` to SQLite behind the same `Store` interface without changing P1/P2/P3 call sites.
- [ ] Migrate or seed M1 fixtures into SQLite so the demo still works before real ingestion completes.
- [ ] Consume real `AgentProposal` payloads from P3 while retaining sample fixtures for offline development.
- [ ] Persist real graph edges and document records from P2, including duplicate/conflict/stale signals.
- [ ] Reconcile P2 health/importance signals with P4's persisted `DocumentRecord` fields; use deterministic defaults where P2 omits values.
- [ ] Confirm P3 proposal evidence only references docs/chunks visible to the request principal before exposing it to P1.
- [ ] Wire approval apply results back into P3/P2-facing state only through contracts/events, not direct source edits.
- [ ] Emit live WebSocket updates to P1 after proposal creation, approval, graph changes, health changes, and metrics changes.
- [ ] Run M3 end-to-end: drop-off → proposal → approve → provenance → metrics, matching README §8A.7.
- [ ] Validate that mock sandbox remains the active MVP path and that any real-sandbox placeholders are not accidentally invoked.

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
- [ ] Prepare concise presenter notes explaining that verification sandbox execution is mocked for MVP and real container execution is a stretch goal.

## Key Design Rules & Gotchas

| Rule / gotcha | Practical guidance |
| --- | --- |
| ACL at every stage | Enforce before retrieval, before answer/proposal display, before approval/write, and before WebSocket broadcast. If a user cannot see a doc, no title, path, snippet, evidence, or edge should reveal it unless a director-approved fog contract says otherwise. |
| Provenance on every write | No authoritative state change is complete until a `ProvenanceEntry` exists. Approval without provenance is a failed write. |
| Idempotent writes | Ingestion retries, repeated approvals, repeated WS delivery, and job retries must not duplicate graph edges, provenance entries, or metrics increments. |
| Append-only audit | Never mutate or delete historical provenance rows. Corrections and rollbacks are new audit events that refer back to previous entries/version refs. |
| Sandbox is mocked | MVP verification validates and returns deterministic `SandboxResult`; it does not run commands. Planned real architecture: isolated container, clean checkout by `commitSha`, command timeout, stdout/stderr tail truncation, resource limits, no secrets, and safe cleanup. |
| Health derivation | Use `green` for verified/current, `yellow` for likely stale or needs review, `red` for conflict/broken/high-risk, and `gray` for unknown/unverified/deprecated unless the director freezes a stricter mapping. |
| Importance derivation | Store `importance` as `0..1`; seed from P2 signals when available, otherwise use deterministic defaults based on references, ownership, recency, and demo fixture importance. |
| Sensitive spaces | Treat restricted ACLs, high-risk proposal types, or owner-marked docs as requiring staged approval. Do not silently downgrade staged approval to one-click apply. |
| Metrics credibility | Counters should move only on meaningful state transitions, especially approved/apply events. Proposal creation can increment detected counters but should not increment fixed/resolved counters. |
| Contract names | Match README §8A and general-plan §7 exactly, including camelCase JSON names. If the frozen model disagrees with docs, escalate to the director instead of inventing a local variant. |
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
| Frozen contracts honored | Router responses validate against `DocumentRecord`, `ProvenanceEntry`, `SandboxResult`, `GraphDTO`, `MetricsDTO`, and `AgentProposal` shapes; camelCase JSON names match README §8A. |
| Backend quality gate passes | Run `ruff check`, `black --check`, and `pytest -q` for touched backend modules before claiming done. |
| Works with mocks and real dependencies | M1 fixture API works; M3 SQLite-backed routes work with real P2/P3 outputs while retaining fixture fallback. |
| ACL edge cases handled | Tests cover inaccessible graph nodes/edges, proposal evidence filtering, denied approvals, denied rollback, and WS no-leak behavior. |
| Provenance mandatory | Every approve/apply/rollback path writes exactly one append-only `ProvenanceEntry` per governed state change. |
| Idempotent and retry-safe | Repeated ingestion/approval/job execution does not duplicate edges, apply changes twice, or double-count metrics. |
| Verification correctly scoped | `SandboxRequest` is accepted and `SandboxResult` returned by the mock service; no real command execution is implied or performed for MVP. |
| Metrics demo credible | `MetricsDTO` counters and `asOf` update after planted stale/duplicate/conflict approval flows. |
| WebSocket integration useful | `WS /stream` emits proposal, graph, health, and metrics updates that P1 can use for live dashboard/provenance moments. |
| M4 demo-ready | The 9-step demo can show review/approval, ACL-safe graph, provenance, rollback, staged approval, and metrics movement without manual database edits. |
