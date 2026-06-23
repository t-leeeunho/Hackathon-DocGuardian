# Person 1 — Frontend & Demo Experience

Own the React UI demo surface: graph, chat, evidence, review, provenance, and metrics that make DocGuardian AI feel grounded, governed, and trustworthy.

## Mission

Person 1 owns the human-in-the-loop trust surface for DocGuardian AI. The mission is to make the AI's reasoning visible through a polished React experience: graph health, evidence-backed chat, clickable citations, reviewable diffs, provenance, and metrics. The frontend should feel fast and credible against mocks at M1, then flip cleanly to the real API and `WS /stream` at M3 without contract drift. This is the demo surface, so clarity, accessibility, motion restraint, and visual polish matter.

## Scope — What You Own

- `frontend/src/**` as the implementation area for the React application.
- `frontend/src/components/**` for app shell, graph, chat, drop-off, diff/review, provenance, metrics, and shared UI composition.
- `frontend/src/hooks/**` for stateful UI logic such as graph selection, highlight lifecycles, API loading states, WebSocket event handling, and reduced-motion detection.
- `frontend/src/lib/api.ts` for the typed REST client that can use local fixtures when `VITE_USE_MOCK=true` and real HTTP endpoints when `VITE_USE_MOCK=false`.
- `frontend/src/lib/ws.ts` for the typed `WS /stream` client, including mock event replay before M3 and real WebSocket handling at M3.
- `frontend/src/lib/fixtures.ts` for local fixture exports that mirror the frozen contracts and let the full UI run offline.
- `frontend/src/styles/**`, Tailwind entry styles, theme tokens, and shadcn/ui composition inside owned frontend files.
- React Flow (`@xyflow/react`) graph layout, rendering, node/edge styling, interaction behaviors, and chunked/lazy rendering strategy.
- Frontend quality gates: `npm run lint`, `npx tsc --noEmit`, and `npm run test`.

## What You Must NOT Touch

- `frontend/src/lib/types.ts` — **FROZEN contract** mirroring backend Pydantic models. Do not edit it directly after M1; request changes through the director.
- `backend/**` — backend models, routers, services, agents, stores, governance, and API implementation belong to P2/P3/P4/director ownership.
- `backend/app/models/**` — frozen Pydantic contracts owned by the director after M1.
- `backend/app/main.py` — router wiring is director-owned after Phase 0.
- `repos.config.json`, `.env.example`, and root tooling configs unless the director explicitly assigns a frontend setup change during Phase 0.
- Other people's per-person backend directories and router files listed in `docs/team-plan.md` §2.2.
- Any application source code outside `frontend/src/**`.

## Inputs (Consumed, Mocked Until M3) & Outputs (Produced)

| Contract name | Where it comes from / mocked until M3 | What you render or produce |
| --- | --- | --- |
| `GraphDTO` | `GET /graph`; until M3 from `frontend/src/lib/fixtures.ts` or mock API behind `VITE_USE_MOCK` | React Flow nodes and edges; node size from `importance`/`size`, color from `health`, permission fog from `accessible:false`, red dashed `conflicts-with` edges, lazy cluster rendering. |
| `ChatAnswer` | Chat/RAG response from the agent layer; until M3 from fixtures/mock client | Chat answer text, confidence, `needsHumanReview` badge, scope echo, citation chips, and derived `GraphHighlightEvent` instructions from `citations[]`. |
| `AgentProposal` | `GET /proposals/:id`; until M3 from fixtures/mock client; approval via `POST /proposals/:id/approve` | Diff/review side panel with before/after diff, draft summary, evidence list, confidence, risk, conflicts, verification result, approve/reject controls, and proposal evidence highlights. |
| `MetricsDTO` | `GET /metrics`; until M3 from fixtures/mock client | Metrics dashboard counters for stale detected/fixed, duplicates removed, conflicts detected/resolved, broken links resolved, verification coverage, average time to update, and `asOf` freshness. |
| `GraphHighlightEvent` | Derived client-side from `ChatAnswer.citations[]`; may also arrive over `WS /stream` | Highlight state consumed by the graph: node glow/pulse, cited `references` edge flowing dash, intensity/relevance scaling, `ttlMs` auto-fade, reduced-motion static halo. |
| `WS /stream` channel | Mock event replay until M3; real WebSocket from P4 at M3 | Live graph/health/proposal/metrics updates, highlight events, optimistic-to-confirmed approval state, and demo-friendly real-time feedback. |
| `DocumentRecord`-like graph node fields embedded in `GraphDTO` | Backend graph store through `/graph`; fixtures before M3 | Provenance panel summary fields such as owner, repo/path, health, verification stamp, commit SHAs, recent changes, and access state when available in the graph payload. |
| `ProvenanceEntry` snapshots exposed through proposal/provenance surfaces | P4 governance/store API or proposal payload; fixtures before M3 | Approval history, evidence snapshot, previous/new version refs, rollback affordance, approved-by/approved-at metadata, and governance explanation. |

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
| Director / Phase 0 driver | Frozen `frontend/src/lib/types.ts`, contract examples, mock API availability, and agreed camelCase field names | `GraphDTO`, `ChatAnswer`, `AgentProposal`, `MetricsDTO`, `GraphHighlightEvent`; no direct edits by P1 after M1 | Phase 0 → **M1** |
| P2 — Retrieval & Document Intelligence | Real document graph relationships, duplicate/conflict edges, accessible search results, meaningful node importance and health inputs | `GraphDTO` edges and document metadata generated from ingestion/processing/search; `SearchResult` only indirectly through chat/API | M1 fixtures, M2 real retrieval, M3 real API |
| P3 — Agent Orchestration & AI Reasoning | Evidence-backed answers and proposals with confidence, citations, relevance, uncertainty, and no-answer/needs-review behavior | `ChatAnswer` and `AgentProposal` exactly as frozen; citation `docId` must match graph node IDs for highlighting | M1 sample responses, M2 real Curator/Guardian, M3 API integration |
| P4 — Governance, Verification & Metrics | Graph, proposal, approval, provenance, metrics, ACL/permission flags, and WebSocket stream semantics | `GET /graph`, `POST /documents`, `GET /proposals/:id`, `POST /proposals/:id/approve`, `GET /metrics`, `WS /stream` | M1 mock routers, M3 real routers/store, M4 live updates |
| Whole team | Seeded demo corpus and planted stale/duplicate/conflict scenarios | Fixtures must be representative, deterministic, and demo-script aligned | M1 for UI build, M4 for rehearsal |

Working assumptions:

- Before M3, P1 develops against `VITE_USE_MOCK=true`, local fixtures, and optional mock WebSocket event replay.
- At M3, flipping `VITE_USE_MOCK=false` should be the main integration switch; component contracts must not change.
- If real payloads differ from `frontend/src/lib/types.ts`, treat it as a contract bug and route it to the director rather than patching around it with `any`.

## Detailed TODOs

### Phase 0 — Foundation participation

- [ ] Confirm the locked frontend stack is scaffolded: React + TypeScript + Vite + Tailwind + shadcn/ui + React Flow (`@xyflow/react`), with 2D graph as the MVP and 3D explicitly deferred.
- [ ] Participate in contract review for `GraphDTO`, `ChatAnswer`, `AgentProposal`, `MetricsDTO`, and `GraphHighlightEvent`; verify frontend field names are camelCase and match README §8A examples.
- [ ] Validate that `frontend/src/lib/types.ts` compiles without local patches; document any mismatch as a director-level contract issue instead of editing the frozen file.
- [ ] Create the app shell inside `frontend/src/**`: graph workspace, left/source area if needed, right review/provenance panel area, bottom or side chat, and metrics summary region.
- [ ] Set up Tailwind and shadcn/ui usage patterns for cards, buttons, badges, panels, tabs, scroll areas, dialogs, toasts, and form controls.
- [ ] Build `lib/api.ts` around `VITE_USE_MOCK`: when true, return fixture data; when false, call the REST API surface from README §8A.5.
- [ ] Build `lib/ws.ts` around `VITE_USE_MOCK`: when true, replay deterministic local events; when false, connect to `WS /stream` with reconnect and cleanup behavior.
- [ ] Add `lib/fixtures.ts` with representative mock `GraphDTO`, `ChatAnswer`, `AgentProposal`, and `MetricsDTO` data that renders the M1 gate end-to-end.
- [ ] Render a tiny mock graph with at least green, yellow, red, and gray/locked nodes plus a red dashed `conflicts-with` edge to prove §7.9, §7.13, and §7.14 are feasible.
- [ ] Prove **M1** visually: mock graph, chat answer with citation chips, diff/review panel, provenance summary, and metrics dashboard all render without the real backend.

### Core Build

#### Graph View

- [ ] Implement React Flow graph rendering from `GraphDTO.nodes[]` and `GraphDTO.edges[]` with stable node IDs equal to document `docId`/graph `id`.
- [ ] Map node health exactly: green = fresh/verified, yellow = aging/needs review, red = stale/conflicting/broken, gray/locked = inaccessible or access-restricted.
- [ ] Size nodes from `importance` as specified in README §7.10; if the payload uses `size` per README §8A.6.1 example, normalize it in the typed API adapter without changing the contract file.
- [ ] Render `conflicts-with` edges as red dashed lines with clear contrast and no ambiguity with ordinary `references` edges.
- [ ] Render `duplicate-of`, `deprecated-by`, and `references` edges with visually distinct but calmer treatments so conflict edges remain the strongest warning signal.
- [ ] Apply permission fog for `accessible:false`: dim/blur/lock the node, hide restricted details, and prevent provenance content from leaking beyond allowed metadata.
- [ ] Add selection behavior: selecting a node opens the provenance panel and highlights related chat citations when present.
- [ ] Add pan/zoom controls, fit-to-view, selected-cluster zoom, and a reset-view control appropriate for live demo use.
- [ ] Implement chunked/lazy rendering: show an overview first, render details only for selected/nearby clusters, and avoid loading full document details until a node is selected.
- [ ] Handle graph edge cases: empty graph, disconnected graph, inaccessible-only results, missing health, unknown edge type, and graph refresh while a node is selected.

#### Show-Your-Work Highlight

- [ ] Convert every `ChatAnswer.citations[]` entry into a `GraphHighlightEvent` using `docId` as `nodeIds[]`, citation `relevance` as intensity, and a default `ttlMs` around 4000 ms unless the event supplies one.
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
- [ ] Send selected scope through the typed API client so the response `ChatAnswer.scope` mirrors the UI choice.
- [ ] Render answer text with confidence and `needsHumanReview`; low confidence or no supporting citation must look cautious rather than authoritative.
- [ ] Render citation chips for every citation with document label, line range, commit SHA snippet, and relevance indicator.
- [ ] On citation hover, emit a `GraphHighlightEvent` for just that node using `reason: "hover-references"`.
- [ ] On citation click, pan/zoom the React Flow canvas to the cited node and open the provenance panel for that `docId`.
- [ ] If a citation references a document not currently visible because of chunked rendering, load/expand the relevant cluster before panning when possible.
- [ ] Handle empty answers, API errors, unauthorized scopes, no citations, and slow responses with clear loading and recovery states.
- [ ] Preserve chat history during graph refreshes so the demo can show continuity from question → cited graph evidence → review.

#### Drop-Off Area

- [ ] Build a drop-off intake surface for upload, pasted text, documentation draft, and natural-language update as described in README §7.5.
- [ ] Post intake requests through `POST /documents` using the typed REST client; in mock mode, return deterministic fixture proposals/events.
- [ ] Capture intake intent clearly: create, update, merge, link, deprecate, or flag may be decided by the system, not by the UI alone.
- [ ] Show upload/paste/NL input validation states, including empty content, unsupported file, oversized content, and missing target/scope.
- [ ] After successful mock or real submission, surface progress: queued/scanning/retrieving/proposal-ready when available through response or `WS /stream`.
- [ ] Link the result to the graph by highlighting related/duplicate/conflict nodes returned by the mock or real backend.
- [ ] Provide demo-friendly sample input controls so the M4 planted conflict can be triggered reliably without typing long text live.
- [ ] Avoid storing secret or restricted content in local fixtures, logs, or visible debug output.

#### Diff/Review Panel

- [ ] Render `AgentProposal.diff.before`, `diff.after`, `diff.format`, and `diff.lineRange` in a readable before/after review surface.
- [ ] Display action, target document, source documents, proposed draft summary, conflicts, uncertainty, and proposed-by metadata.
- [ ] Render proposal evidence with chunk ID, doc ID, line range, commit SHA, quote, and relevance so the evidence is auditable.
- [ ] Show confidence and risk level prominently; `confidence < 0.5` or non-null `uncertainty` must force an obvious needs-human-review state.
- [ ] Display verification result: sandbox run, passed/failed, command, commit SHA, and duration when present.
- [ ] Emit `GraphHighlightEvent` with `reason: "proposal-evidence"` for evidence docs while the proposal is selected.
- [ ] Implement approve/reject controls; approve posts to `POST /proposals/:id/approve`, while reject records UI state and awaits the agreed backend route if no reject endpoint is frozen.
- [ ] Handle approval pending, approved, rejected, failed, and permission-denied states without losing the diff context.
- [ ] After approval, update the provenance panel and metrics dashboard from response or `WS /stream` events.
- [ ] Keep all proposal rendering strongly typed; do not use `any` for `AgentProposal`, evidence entries, diff, verification, or risk fields.

#### Provenance Panel

- [ ] Open provenance when a graph node is selected or a citation chip is clicked.
- [ ] Show document owner, repo/path, source references, last verified stamp, linked code/config, current and verified commit SHAs when available.
- [ ] Show recent changes, approval history, and evidence snapshots from proposal/provenance data.
- [ ] Include rollback affordance as a governed action placeholder if the route is not part of the frozen API, clearly indicating whether it is available in MVP.
- [ ] Respect ACLs: inaccessible nodes show locked/fogged metadata only and never reveal restricted titles, quotes, diffs, or provenance details.
- [ ] Highlight source references in the graph when hovering provenance evidence rows.
- [ ] Keep provenance readable in the demo: concise labels, commit SHA truncation with full value on copy/tooltip, and clear timestamps.
- [ ] Handle missing provenance, stale verification, deleted document, and pending approval states.

#### Metrics Dashboard

- [ ] Fetch `MetricsDTO` from `GET /metrics` through the same mock/real API switch.
- [ ] Render the README §6.11 business-value counters: stale detected/fixed, duplicates removed, broken links resolved, conflicts detected/resolved, onboarding questions reduced when available, average time-to-update, and documents verified.
- [ ] Map `docsWithVerificationStamp` as a fraction in [0,1] to a percentage display without changing the underlying contract.
- [ ] Show `asOf` freshness and visibly update it after live metric events from `WS /stream`.
- [ ] Use compact cards or charts that fit the demo screen without stealing focus from graph/chat/review.
- [ ] Add empty/loading/error states so the dashboard does not look broken before the first metrics response.
- [ ] When approval succeeds, reflect updated metrics from the server event; avoid inventing permanent counts client-side beyond short optimistic feedback.
- [ ] Ensure dashboard terminology matches README/general-plan/team-plan wording exactly: stale, duplicate, conflict, broken links, verification stamps, time-to-update.

### Integration (M2/M3)

- [ ] At M2, test P2/P3 real retrieval and real Curator/Guardian outputs against the existing fixture assumptions without changing component-level contract expectations.
- [ ] Compare real `ChatAnswer.citations[].docId` values to current `GraphDTO.nodes[].id`; require exact match or a director-approved mapping so highlights work.
- [ ] Compare real `AgentProposal.evidence[].docId` and `conflictsWith[]` to graph IDs; proposal evidence must light up graph nodes reliably.
- [ ] At M3, flip `VITE_USE_MOCK=false` locally and verify the frontend calls real `GET /graph`, `POST /documents`, `GET /proposals/:id`, `POST /proposals/:id/approve`, `GET /metrics`, and `WS /stream`.
- [ ] Wire real WebSocket events for graph updates, health changes, proposal readiness, approval/provenance updates, metrics updates, and highlight events if P4 emits them.
- [ ] Reconcile loading and race states: graph refresh while chat highlight is active, proposal approval while metrics update arrives, and WebSocket reconnect after backend restart.
- [ ] Validate ACL propagation with real or seeded inaccessible docs: inaccessible content must remain fogged/locked and must not appear in chat citations or evidence details unless permitted.
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
- [ ] Prepare a frontend fallback mode using deterministic mock fixtures if the real backend or external provider fails during the live demo.
- [ ] Run final frontend quality gates and a full M4 rehearsal against the seeded corpus before marking the frontend slice demo-ready.

## Key Design Rules & Gotchas

- **Contracts are sacred:** use `GraphDTO`, `ChatAnswer`, `AgentProposal`, `MetricsDTO`, and `GraphHighlightEvent` exactly as mirrored in `frontend/src/lib/types.ts`.
- **Never use `any` for contract types:** if the type is awkward, improve local adapter typing inside owned files or escalate the contract issue.
- **Never override health color when glowing:** highlight derives from health color and adds halo/brightness; it must not hide green/yellow/red/gray meaning.
- **Auto-fade all highlights:** `ttlMs` is part of trust and usability; stale glows make the graph misleading.
- **Respect `prefers-reduced-motion`:** static halo fallback is required for show-your-work and demo polish.
- **Permission fog is not decoration:** `accessible:false` means restricted content must stay hidden in graph details, chat citations, diff evidence, and provenance.
- **Graph IDs must align with citations:** `ChatAnswer.citations[].docId` and `AgentProposal.evidence[].docId` must map to `GraphDTO.nodes[].id` or the core trust visual breaks.
- **Chunked rendering is mandatory for large graphs:** render overview first, load cluster details on selection/zoom, and avoid expensive full-detail rendering.
- **Conflict edges must remain visually urgent:** red dashed `conflicts-with` edges should not be confused with flowing `references` highlight edges.
- **Evidence or silence:** answers and proposals without citations/evidence should render as uncertain/needs review, not as confident AI output.
- **Mock and real paths must stay equivalent:** `VITE_USE_MOCK` changes data source, not component behavior or payload shape.
- **Optimistic UI must reconcile:** approval and metrics can feel instant, but server/WS confirmation is authoritative.
- **Keep the demo legible:** prefer readable panels, concise labels, meaningful tooltips, and stable layouts over dense dashboards.
- **Do not leak secrets or restricted data:** avoid logging full document text, private quotes, credentials, or inaccessible content.

## Definition of Done

A frontend slice is done when it satisfies the team-plan §7 quality gates and the M1–M4 expectations for the current phase.

- [ ] Honors frozen contracts exactly: field names, types, camelCase JSON, and frontend `types.ts` definitions match the README/general-plan contracts.
- [ ] Works against mocks before M3 and against the real API + `WS /stream` after M3 using the same component behavior.
- [ ] Renders the core demo surfaces: graph, show-your-work highlights, chat + scope toggle, drop-off intake, diff/review, provenance, and metrics.
- [ ] Handles edge cases called out in `docs/team-plan.md` §7: empty results, low confidence, inaccessible docs, unchanged content, and deleted docs.
- [ ] Maintains permission boundaries in graph, chat, evidence, diff, and provenance views.
- [ ] Provides accessible reduced-motion fallback for highlight effects and keyboard/contrast support for key controls.
- [ ] Runs and passes `npm run lint`, `npx tsc --noEmit`, and `npm run test` for the frontend.
- [ ] Supports the M4 rehearsed 9-step demo with seeded stale/duplicate/conflict data, live or mock fallback updates, and visible business-value metrics.