# Person 1 — Frontend & Demo Experience

Own the React UI demo surface: graph, chat, evidence, review, provenance, and metrics that make DocGuardian AI feel grounded, governed, and trustworthy.

> **As-built status (2026-06-23):** the frontend is not started yet, but the backend API it consumes is implemented (README §8B); see [../implementation-status.md](../implementation-status.md).

## Mission

Person 1 owns the human-in-the-loop trust surface for DocGuardian AI. The mission is to make the AI's reasoning visible through a polished React experience: graph health, evidence-backed chat, clickable citations, reviewable proposals, provenance, and metrics. The frontend should build directly against the implemented backend API in README §8B with a thin typed client, while optional fixtures can support offline/demo fallback. `WS /stream`, metrics, approval persistence, proposal persistence, and real node-health scoring are not implemented yet, so those surfaces must clearly distinguish live API-backed behavior from pending P4 backend work. This is the demo surface, so clarity, accessibility, motion restraint, and visual polish matter.

## Scope — What You Own

- `frontend/src/**` as the implementation area for the React application.
- `frontend/src/components/**` for app shell, graph, chat, drop-off, diff/review, provenance, metrics, and shared UI composition.
- `frontend/src/hooks/**` for stateful UI logic such as graph selection, highlight lifecycles, API loading states, future WebSocket event handling, and reduced-motion detection.
- `frontend/src/lib/api.ts` for a thin typed REST client over the real backend endpoints in README §8B; optional local fixtures are acceptable for offline/demo fallback, not as the primary contract source.
- `frontend/src/lib/ws.ts` may be added for future `WS /stream` support, but the endpoint is not implemented today.
- `frontend/src/lib/fixtures.ts` may provide local fixture exports that mirror README §8B / implementation-status §4 contracts and let selected UI surfaces run offline.
- `frontend/src/styles/**`, Tailwind entry styles, theme tokens, and shadcn/ui composition inside owned frontend files.
- React Flow (`@xyflow/react`) graph layout, rendering, node/edge styling, interaction behaviors, and chunked/lazy rendering strategy.
- Monaco Editor for the proposal/diff and document editing views.
- Frontend quality gates: `npm run lint`, `npx tsc --noEmit`, and `npm run test`.

## What You Must NOT Touch

- There is no `frontend/src/lib/types.ts` yet because the frontend is not started. When created, it should mirror the backend-owned camelCase API responses in README §8B / `docs/implementation-status.md` §4 (`docId`, `chunkId`, `headingPath`, `lineRange`, `commitSha`, `score`, graph `nodes`/`edges`, etc.). After the contract is agreed, do not drift from backend shapes.
- `backend/**` — backend models, routers, services, agents, stores, governance, and API implementation belong to P2/P3/P4/director ownership.
- `backend/app/models.py`, `backend/app/main.py`, `backend/app/agents/schemas.py`, and storage query DTO shaping — backend contracts and router wiring are owned outside P1.
- `repos.config.json`, `.env.example`, and root tooling configs unless the director explicitly assigns a frontend setup change during Phase 0.
- Other people's per-person backend directories and router files listed in `docs/team-plan.md` §2.2.
- Any application source code outside `frontend/src/**`.

## Inputs (Consumed From Real API, With Optional Fixtures) & Outputs (Produced)

| Contract name | Where it comes from today / blocked status | What you render or produce |
| --- | --- | --- |
| `HealthResponse` | `GET /health` is implemented | Backend status, embedding provider, and dimension for a small connectivity/status indicator. |
| `SearchResponse` | `GET /search?q=&repo=&k=` is implemented | Optional direct search results or chat/retrieval debugging; matches use camelCase fields such as `chunkId`, `docId`, `headingPath`, `lineRange`, `commitSha`, and `score`. |
| `TreeDTO` | `GET /tree?namespace=` is implemented | Left sidebar source/file tree with nested `{name,type,path,children?}` nodes. |
| `GraphDTO` | `GET /graph?repo=` is implemented; `health`, `size`, and `accessible` are placeholders today (`green`/~0.5/`true`) until P4 health scoring/ACL work | React Flow nodes and edges; node size from `size`, color from `health`, permission fog from `accessible:false` when real ACL arrives, red dashed `conflicts-with` edges when the backend emits them, lazy cluster rendering. Expect uniform green health in the current API. |
| `DocumentResponse` | `GET /documents/{docId}` is implemented | Document/provenance-adjacent detail view with `docId`, `repo`, `path`, `commitSha`, `commitDate`, and `chunks[]` for selected nodes. |
| `DocumentIntakeResponse` | `POST /documents` is implemented for text drop-off | Upload/paste intake result: created `docId`, chunk count, and edge count; binary formats are blocked by the backend with `415`. |
| `ChatAnswer` | `POST /chat` is implemented; requires Azure OpenAI config or returns `503` | Chat answer text, confidence, `needsHumanReview` badge, optional scope echo, citation chips, and derived `GraphHighlightEvent` instructions from `citations[]`. Citations may use backend/agent naming (`doc_id`/`docId`, `line_range`/`lineRange`, `commit_sha`/`commitSha`, `relevance`), so normalize at the typed adapter boundary. |
| `AgentProposal` | `POST /propose` is implemented; requires Azure OpenAI config or returns `503` | Proposal/review side panel with `action`, `draft`, `citations`, `confidence`, `risk_level`, `conflicts_with`, `recommendation`, and `guardian_reasoning`. Today it does **not** include a persisted `proposalId`, structured `diff{}`, structured `evidence[]`, or `verification{}`. |
| `MetricsDTO` | `GET /metrics` is **not implemented** | Metrics dashboard is blocked on pending P4 backend work; fixtures may be used only as clearly labeled demo placeholders. |
| `GraphHighlightEvent` | Derived client-side from `ChatAnswer.citations[]` and `AgentProposal.citations[]`; `WS /stream` is not implemented | Highlight state consumed by the graph: node glow/pulse, cited `references` edge flowing dash, intensity/relevance scaling, `ttlMs` auto-fade, reduced-motion static halo. |
| `WS /stream` channel | **Not implemented** | Live graph/health/proposal/metrics updates are blocked on P4; use deterministic local replay only as an offline/demo fallback. |
| Proposal persistence / approval | `GET /proposals/:id` and `POST /proposals/:id/approve` are **not implemented** | Approve/reject persistence, provenance updates, rollback, and post-approval metrics are blocked on pending P4 backend work. |

Example highlight event shape for planning alignment only:

```jsonc
{
  "reason": "chat-evidence",
  "nodeIds": ["playwright/docs/src/ci.md", "playwright/docs/src/intro.md"],
  "edgeIds": ["playwright/docs/src/intro.md->playwright/docs/src/ci.md:references"],
  "intensity": 0.91,
  "ttlMs": 4000
}
```

## Dependencies & Interfaces With Others

| Partner | What P1 needs | Interface / contract boundary | When it is needed |
| --- | --- | --- | --- |
| Director / Phase 0 driver | Frontend contract examples copied from README §8B / implementation-status §4 and agreed camelCase TypeScript interfaces when `types.ts` is created | `HealthResponse`, `SearchResponse`, `TreeDTO`, `GraphDTO`, `DocumentResponse`, `ChatAnswer`, `AgentProposal`, `GraphHighlightEvent`; backend shapes are authoritative | Phase 0 → **M1** |
| P2 — Retrieval & Document Intelligence | Real document graph relationships, accessible search results, and eventually meaningful node importance/health inputs | Implemented `GET /search`, `GET /tree`, `GET /graph`, `GET /documents/{docId}`; graph health/size/accessibility placeholders remain a known gap | M1/M2 real API already available; health scoring later |
| P3 — Agent Orchestration & AI Reasoning | Evidence-backed answers and proposals with confidence, citations, relevance, uncertainty, and no-answer/needs-review behavior | Implemented `POST /chat` and `POST /propose`; citation doc IDs must map to graph node IDs for highlighting | M1/M2 real API already available when Azure is configured |
| P4 — Governance, Verification & Metrics | Metrics, approval, proposal persistence, provenance, ACL/permission flags, real node-health scoring, and WebSocket stream semantics | Pending `GET /metrics`, `GET /proposals/:id`, `POST /proposals/:id/approve`, `WS /stream`, proposal persistence, health scoring | Blocked until P4 backend work lands |
| Whole team | Seeded demo corpus and planted stale/duplicate/conflict scenarios | Fixtures should be representative, deterministic, demo-script aligned, and clearly marked as fallback where real endpoints are missing | M1 for UI build, M4 for rehearsal |

Working assumptions:

- The primary development path is the real local API at `http://localhost:8000`; CORS already allows Vite on `http://localhost:5173` and `http://localhost:3000`.
- Optional fixtures/offline mode are useful for demo resilience, but they must mirror README §8B and must not reintroduce mock-first contract drift.
- If real payloads differ from the TypeScript interfaces created for the frontend, treat README §8B / implementation-status §4 and the backend response DTOs as authoritative rather than patching around mismatches with `any`.

## Detailed TODOs

### Phase 0 — Foundation participation

- [ ] **UNBLOCKED:** Confirm the locked frontend stack is scaffolded: React + TypeScript + Vite + Tailwind + shadcn/ui + React Flow (`@xyflow/react`) + Monaco Editor, with 2D graph as the MVP and 3D explicitly deferred.
- [ ] **UNBLOCKED:** Create/review frontend TypeScript interfaces for implemented README §8B contracts: `HealthResponse`, `SearchResponse`, `TreeDTO`, `GraphDTO`, `DocumentResponse`, `DocumentIntakeResponse`, `ChatAnswer`, and today's streamlined `AgentProposal`; verify frontend field names mirror real camelCase API responses.
- [ ] **UNBLOCKED:** Create `frontend/src/lib/types.ts` if needed; it does not exist yet, so base it on README §8B / implementation-status §4 instead of assuming a frozen pre-existing file.
- [ ] Create the app shell inside `frontend/src/**`: graph workspace, left/source area if needed, right review/provenance panel area, bottom or side chat, and metrics summary region.
- [ ] Set up Tailwind and shadcn/ui usage patterns for cards, buttons, badges, panels, tabs, scroll areas, dialogs, toasts, and form controls.
- [ ] **UNBLOCKED:** Build `lib/api.ts` against the implemented REST API from README §8B: `GET /health`, `GET /search`, `POST /documents`, `GET /tree`, `GET /graph`, `GET /documents/{docId}`, `POST /chat`, and `POST /propose`.
- [ ] **BLOCKED on P4 backend:** Build real `lib/ws.ts` for `WS /stream`; until then, deterministic local event replay is fallback/demo-only.
- [ ] Add `lib/fixtures.ts` with representative fallback `GraphDTO`, `ChatAnswer`, today's `AgentProposal`, and placeholder `MetricsDTO` data; clearly label metrics/approval/WS fixtures as not backed by current endpoints.
- [ ] **PARTIALLY UNBLOCKED:** Render a real `/graph` graph. Use fixtures only to demonstrate yellow/red/gray health and `conflicts-with` edges until backend health scoring, ACLs, duplicate/conflict edges, and non-green health values exist.
- [ ] Prove **M1** visually: real graph/tree/search/chat/propose where available, citation chips, proposal review panel, and clearly marked placeholder provenance/metrics surfaces for pending backend endpoints.

### Core Build

#### Graph View

- [ ] Implement React Flow graph rendering from `GraphDTO.nodes[]` and `GraphDTO.edges[]` with stable node IDs equal to document `docId`/graph `id`.
- [ ] Map node health exactly when real values arrive: green = fresh/verified, yellow = aging/needs review, red = stale/conflicting/broken, gray/locked = inaccessible or access-restricted. **Current `/graph` returns placeholder green health, so live health coloring will look uniform until P4 health scoring lands.**
- [ ] Size nodes from `size` in the implemented `/graph` payload. Treat current values as placeholders (~0.5) until P4 adds meaningful importance/health scoring.
- [ ] Render `conflicts-with` edges as red dashed lines with clear contrast and no ambiguity with ordinary `references` edges when such edges are emitted or shown in fallback fixtures.
- [ ] Render `duplicate-of`, `deprecated-by`, and `references` edges with visually distinct but calmer treatments so conflict edges remain the strongest warning signal; semantic duplicate/conflict edges are pending backend work.
- [ ] Apply permission fog for `accessible:false`: dim/blur/lock the node, hide restricted details, and prevent provenance content from leaking beyond allowed metadata. **Current `/graph` returns placeholder `accessible:true` until ACL work lands.**
- [ ] Add selection behavior: selecting a node opens the provenance panel and highlights related chat citations when present.
- [ ] Add pan/zoom controls, fit-to-view, selected-cluster zoom, and a reset-view control appropriate for live demo use.
- [ ] Implement chunked/lazy rendering: show an overview first, render details only for selected/nearby clusters, and avoid loading full document details until a node is selected.
- [ ] Handle graph edge cases: empty graph, disconnected graph, inaccessible-only results, missing health, unknown edge type, and graph refresh while a node is selected.

#### Show-Your-Work Highlight

- [ ] Convert every `ChatAnswer.citations[]` entry into a `GraphHighlightEvent` using normalized citation `docId`/`doc_id` as `nodeIds[]`, citation `relevance` as intensity, and a default `ttlMs` around 4000 ms unless the event supplies one.
- [ ] Resolve `edgeIds[]` for cited nodes by finding `references` edges between cited documents already present in the current `GraphDTO`.
- [ ] Pulse/glow cited nodes with a subtle ~1.4s sine breathing loop: opacity roughly 0.55 → 1.0 → 0.55, not a distracting blink.
- [ ] Add a one-time scale pop for newly cited nodes: 1.0 → approximately 1.08 → 1.0, then settle into the soft pulse.
- [ ] Derive glow color from each node's existing health color; never replace or obscure green/yellow/red/gray health semantics.
- [ ] Animate cited `references` edges with a flowing dash to imply traversal; do not animate `conflicts-with` edges in a way that weakens their red warning style.
- [ ] Scale highlight brightness by citation relevance so the primary source is visibly stronger than lower-relevance supporting sources.
- [ ] Auto-fade highlight state after `ttlMs`; clear timers on unmount, graph refresh, or superseding highlight events.
- [ ] Respect `prefers-reduced-motion`: use a static halo or outline fallback with no pulsing, no scale pop, and no flowing dash animation.
- [ ] Support highlight reasons: `chat-evidence`, `proposal-evidence`, and `hover-references`, with hover highlights scoped to a single node and short TTL.

#### Chat + Scope Toggle

- [ ] Build an evidence-backed chat panel for questions like running tests, locating architecture docs, summarizing onboarding, and checking document accuracy.
- [ ] Implement the scope toggle options from README §7.7: current repository only, current team docs only, accessible company docs, selected document cluster, summary-only mode, and source-required mode.
- [ ] Send selected scope through the typed API client as supported by the current backend (for example, map repo scope to `repo` where applicable); render `ChatAnswer.scope` when present.
- [ ] Render answer text with confidence and `needsHumanReview`; low confidence or no supporting citation must look cautious rather than authoritative.
- [ ] Render citation chips for every citation with document label, line range, commit SHA snippet, and relevance indicator.
- [ ] On citation hover, emit a `GraphHighlightEvent` for just that node using `reason: "hover-references"`.
- [ ] On citation click, pan/zoom the React Flow canvas to the cited node and open the provenance panel for that `docId`.
- [ ] If a citation references a document not currently visible because of chunked rendering, load/expand the relevant cluster before panning when possible.
- [ ] Handle empty answers, API errors, unauthorized scopes, no citations, and slow responses with clear loading and recovery states.
- [ ] Preserve chat history during graph refreshes so the demo can show continuity from question → cited graph evidence → review.

#### Drop-Off Area

- [ ] Build a drop-off intake surface for upload, pasted text, documentation draft, and natural-language update as described in README §7.5.
- [ ] Post intake requests through implemented `POST /documents` using the typed REST client; fixtures may return deterministic proposals/events only for offline/demo fallback.
- [ ] Capture intake intent clearly: create, update, merge, link, deprecate, or flag may be decided by the system, not by the UI alone.
- [ ] Show upload/paste/NL input validation states, including empty content, unsupported file, oversized content, and missing target/scope.
- [ ] After successful submission, surface the implemented response (`docId`, `chunks`, `edges`). Queued/scanning/retrieving/proposal-ready live progress is blocked on pending `WS /stream`/background status work.
- [ ] Link the result to the graph by highlighting the returned `docId` and any related nodes from real graph/search/propose responses; duplicate/conflict highlighting is limited until backend duplicate/conflict detection lands.
- [ ] Provide demo-friendly sample input controls so the M4 planted conflict can be triggered reliably without typing long text live.
- [ ] Avoid storing secret or restricted content in local fixtures, logs, or visible debug output.

#### Diff/Review Panel

- [ ] **UNBLOCKED with current gap:** Render today's `POST /propose` `AgentProposal` in a readable review surface using `action`, `target_doc_id`/target doc, `draft`, `citations`, `confidence`, `risk_level`, `conflicts_with`, `recommendation`, `guardian_reasoning`, and `uncertainty`.
- [ ] **BLOCKED on richer proposal contract:** Render structured `diff.before`, `diff.after`, `diff.format`, `diff.lineRange`, `sourceDocIds`, and structured `evidence[]` when backend adds them. Today the panel may show the draft and citations, but cannot render a true structured diff without deriving one client-side or using fixtures.
- [ ] Render proposal citations with doc ID, line range, commit SHA, and relevance so the evidence is auditable; structured evidence entries with chunk ID/quote are not available yet.
- [ ] Show confidence and risk level prominently; `confidence < 0.5` or non-null `uncertainty` must force an obvious needs-human-review state.
- [ ] **BLOCKED on verification sandbox:** Display verification result: sandbox run, passed/failed, command, commit SHA, and duration when present.
- [ ] Emit `GraphHighlightEvent` with `reason: "proposal-evidence"` for cited proposal docs while the proposal is selected.
- [ ] **BLOCKED on P4 backend:** Implement persisted approve/reject controls; `POST /proposals/:id/approve`, reject persistence, and proposal IDs are not implemented. Until then, controls should be disabled, local-only, or clearly labeled demo placeholders.
- [ ] Handle approval pending, approved, rejected, failed, and permission-denied states without losing the diff context.
- [ ] **BLOCKED on P4 backend:** After approval, update the provenance panel and metrics dashboard from response or `WS /stream` events.
- [ ] Keep all proposal rendering strongly typed; do not use `any` for `AgentProposal`, citations, future evidence entries, future diff, future verification, or risk fields.

#### Provenance Panel

- [ ] Open provenance when a graph node is selected or a citation chip is clicked.
- [ ] Show repo/path, source references, current commit SHA/date, and chunk details available from `GET /documents/{docId}`; owner, last verified stamp, linked code/config, and verified-vs-current SHA fields are pending governance/health work.
- [ ] **BLOCKED on P4 backend:** Show recent changes, approval history, and evidence snapshots from proposal/provenance data.
- [ ] Include rollback affordance only as a clearly disabled governed-action placeholder; rollback/provenance routes are not part of the implemented API.
- [ ] Respect ACLs: inaccessible nodes show locked/fogged metadata only and never reveal restricted titles, quotes, diffs, or provenance details. Current API uses placeholder `accessible:true`, so real ACL validation is blocked on backend work.
- [ ] Highlight source references in the graph when hovering provenance evidence rows.
- [ ] Keep provenance readable in the demo: concise labels, commit SHA truncation with full value on copy/tooltip, and clear timestamps.
- [ ] Handle missing provenance, stale verification, deleted document, and pending approval states.

#### Metrics Dashboard

- [ ] **BLOCKED on P4 backend:** Fetch `MetricsDTO` from `GET /metrics`; this endpoint is not implemented today.
- [ ] Render the README §6.11 business-value counters: stale detected/fixed, duplicates removed, broken links resolved, conflicts detected/resolved, onboarding questions reduced when available, average time-to-update, and documents verified.
- [ ] Map `docsWithVerificationStamp` as a fraction in [0,1] to a percentage display without changing the underlying contract.
- [ ] Show `asOf` freshness in fixtures/future data and visibly update it after live metric events from `WS /stream` once implemented.
- [ ] Use compact cards or charts that fit the demo screen without stealing focus from graph/chat/review.
- [ ] Add empty/loading/error/blocked states so the dashboard does not look broken while `GET /metrics` is unavailable.
- [ ] **BLOCKED on P4 backend:** When approval succeeds, reflect updated metrics from the server event; avoid inventing permanent counts client-side beyond short optimistic feedback.
- [ ] Ensure dashboard terminology matches README/general-plan/team-plan wording exactly: stale, duplicate, conflict, broken links, verification stamps, time-to-update.

### Integration (M2/M3)

- [ ] At M2, test implemented real retrieval and real Curator/Guardian outputs against fixture assumptions without changing component-level contract expectations.
- [ ] Compare real `ChatAnswer.citations[]` normalized `docId` values to current `GraphDTO.nodes[].id`; require exact match or a director-approved mapping so highlights work.
- [ ] Compare real `AgentProposal.citations[]` and `conflicts_with[]` to graph IDs; proposal citations must light up graph nodes reliably. Structured `evidence[].docId` is not available yet.
- [ ] At M3, verify the frontend calls implemented real endpoints: `GET /health`, `GET /search`, `POST /documents`, `GET /tree`, `GET /graph`, `GET /documents/{docId}`, `POST /chat`, and `POST /propose`.
- [ ] **BLOCKED on P4 backend:** Verify `GET /proposals/:id`, `POST /proposals/:id/approve`, `GET /metrics`, and `WS /stream` once those endpoints exist.
- [ ] **BLOCKED on P4 backend:** Wire real WebSocket events for graph updates, health changes, proposal readiness, approval/provenance updates, metrics updates, and highlight events if P4 emits them.
- [ ] Reconcile loading and race states: graph refresh while chat highlight is active, proposal approval while metrics update arrives, and WebSocket reconnect after backend restart.
- [ ] Validate ACL propagation with real or seeded inaccessible docs once ACL is implemented; until then, use clearly labeled fixtures for permission-fog behavior.
- [ ] Run the frontend quality gate after switching to real API behavior: `npm run lint`, `npx tsc --noEmit`, and `npm run test`.
- [ ] Log contract mismatches as integration blockers for the director; do not solve backend/contract issues by adding untyped casts or `any`.

### Demo Polish (M4)

- [ ] Optimize graph performance for the seeded 1–2 repo corpus: overview-first layout, cluster expansion, detail-on-selection, and no unnecessary re-renders during live events.
- [ ] Tune the show-your-work glow so it is visible on projector/video capture but still subtle enough not to look like a warning state.
- [ ] Complete reduced-motion behavior for all graph highlight effects, panel transitions, and animated edge treatments.
- [ ] Polish empty, loading, error, and permission states so no part of the demo appears unfinished when data is delayed or unavailable.
- [ ] Add demo-safe fixture selectors or sample prompts for the 9-step script: drop-off → related docs → graph conflict → Curator proposal → evidence/confidence → approve → provenance → metrics.
- [ ] Ensure color contrast and keyboard accessibility for scope toggle, citation chips, approve/reject controls, graph selection alternatives, and panels.
- [ ] Verify citation click behavior during rehearsal: chip hover re-highlights, chip click pans/zooms, provenance opens, and highlight auto-fades.
- [ ] Verify approval rehearsal: diff remains visible, approve posts successfully, provenance appears, metrics update, and graph health/edges refresh.
- [ ] Prepare a frontend fallback mode using deterministic fixtures if the real backend or external provider fails during the live demo; keep it aligned with README §8B and clearly distinguish pending-only surfaces.
- [ ] Run final frontend quality gates and a full M4 rehearsal against the seeded corpus before marking the frontend slice demo-ready.

## Key Design Rules & Gotchas

- **Contracts are sacred:** when `frontend/src/lib/types.ts` is created, mirror the implemented backend contracts in README §8B / implementation-status §4. Do not assume a pre-existing frozen file.
- **Never use `any` for contract types:** if the type is awkward, improve local adapter typing inside owned files or escalate the contract issue.
- **Never override health color when glowing:** highlight derives from health color and adds halo/brightness; it must not hide green/yellow/red/gray meaning.
- **Auto-fade all highlights:** `ttlMs` is part of trust and usability; stale glows make the graph misleading.
- **Respect `prefers-reduced-motion`:** static halo fallback is required for show-your-work and demo polish.
- **Permission fog is not decoration:** `accessible:false` means restricted content must stay hidden in graph details, chat citations, diff evidence, and provenance.
- **Graph IDs must align with citations:** `ChatAnswer.citations[]` and `AgentProposal.citations[]` normalized `docId` values must map to `GraphDTO.nodes[].id` or the core trust visual breaks.
- **Chunked rendering is mandatory for large graphs:** render overview first, load cluster details on selection/zoom, and avoid expensive full-detail rendering.
- **Conflict edges must remain visually urgent:** red dashed `conflicts-with` edges should not be confused with flowing `references` highlight edges.
- **Evidence or silence:** answers and proposals without citations/evidence should render as uncertain/needs review, not as confident AI output.
- **Fixtures and real paths must stay equivalent:** fallback fixtures change data source, not component behavior or payload shape.
- **Pending endpoints must be honest:** metrics, approve persistence, proposal persistence, `WS /stream`, verification, ACLs, and health scoring are not implemented today; label placeholders and do not imply live behavior.
- **Optimistic UI must reconcile:** approval and metrics can feel instant only after server routes exist; server/WS confirmation is authoritative.
- **Keep the demo legible:** prefer readable panels, concise labels, meaningful tooltips, and stable layouts over dense dashboards.
- **Do not leak secrets or restricted data:** avoid logging full document text, private quotes, credentials, or inaccessible content.

## Definition of Done

A frontend slice is done when it satisfies the team-plan §7 quality gates and the M1–M4 expectations for the current phase.

- [ ] Honors backend-owned contracts exactly: field names, types, camelCase JSON, and frontend `types.ts` definitions match README §8B / implementation-status §4.
- [ ] Works against the implemented real API now, with optional fixtures for offline/demo fallback; `WS /stream` behavior is gated until the backend endpoint exists.
- [ ] Renders the core demo surfaces: graph, show-your-work highlights, chat + scope toggle, drop-off intake, proposal review, provenance, and metrics, with pending backend-dependent surfaces clearly marked.
- [ ] Handles edge cases called out in `docs/team-plan.md` §7: empty results, low confidence, inaccessible docs, unchanged content, and deleted docs.
- [ ] Maintains permission boundaries in graph, chat, evidence, diff, and provenance views.
- [ ] Provides accessible reduced-motion fallback for highlight effects and keyboard/contrast support for key controls.
- [ ] Runs and passes `npm run lint`, `npx tsc --noEmit`, and `npm run test` for the frontend.
- [ ] Supports the M4 rehearsed 9-step demo with seeded stale/duplicate/conflict data, live API-backed behavior where implemented, fixture fallback where necessary, and honest labeling for business-value metrics until `GET /metrics` exists.