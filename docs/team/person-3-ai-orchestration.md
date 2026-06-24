# Person 3 — Agent Orchestration & AI Reasoning

Person 3 owns the reasoning core: a thin, rule-based orchestrator plus the only two LLM-backed agents in DocGuardian AI, Curator and Guardian.

## Mission

Own the AI reasoning layer without turning the whole backend into an agent system. The mission is to keep orchestration deterministic and cost-conscious while still producing high-quality, evidence-backed proposals and chat answers. Person 3 must make the Curator and Guardian useful enough for the demo, but safe enough that weak evidence always becomes explicit uncertainty and human review. The target budget is approximately two LLM calls per proposal and one LLM call for a simple chat answer.

## Scope — What You Own

Person 3 owns only the AI orchestration, agent, provider, and two API entry-point files listed here.

- `backend/app/ai/orchestrator.py`
  - Code-level router only.
  - No model prompts, no direct model call, and no free-form LLM routing.
  - Decides which deterministic services to call and whether a Curator and/or Guardian call is justified.
- `backend/app/ai/agents/**`
  - `curator.py`
  - `guardian.py`
  - Curator prompt assets.
  - Guardian prompt assets.
  - Agent-specific schema validation helpers if they live inside this owned directory and do not redefine frozen models.
- `backend/app/ai/providers/**`
  - `LLMProvider` abstraction.
  - `EmbeddingProvider` abstraction.
  - Azure OpenAI chat implementation.
  - Azure OpenAI embeddings implementation.
  - `FakeLLMProvider` and `FakeEmbeddingProvider` for deterministic offline development.
  - Configuration switch for fake vs Azure providers.
- API router files owned by Person 3:
  - `backend/app/api/documents.py` — document intake/proposal path, including `POST /documents`.
  - `backend/app/api/chat.py` — chat/RAG answer path.

## What You Must NOT Touch

The contracts-first execution model only works if ownership boundaries are respected.

- Do not edit `backend/app/models/**`.
  - These Pydantic contracts are frozen after M1 and changed only by the director.
  - Person 3 consumes `SearchResult`, `AgentProposal`, `ChatAnswer`, `SandboxRequest`, and `SandboxResult`; Person 3 does not redefine them.
- Do not edit `frontend/src/lib/types.ts`.
  - TypeScript contract mirrors are frozen and director-owned.
- Do not edit `backend/app/main.py`.
  - Router wiring is director-owned after Phase 0.
- Do not edit other people’s directories or router files.
  - P2 owns retrieval, ingestion, processing, vector index details, and `backend/app/api/search.py` / `backend/app/api/ingest.py`.
  - P4 owns governance, verification, store, job queue, and `backend/app/api/proposals.py`, `graph.py`, `metrics.py`, `stream.py`.
  - P1 owns frontend source.
- Do not bypass service interfaces.
  - Call retrieval, duplicate/conflict detection, ACL, sandbox, persistence, provenance, and rollback through their public interfaces.
  - Do not import another person’s implementation internals just because a helper is convenient.
- Do not emit application source code from this plan.
  - This document is a planning/specification artifact only.

## Inputs (Consumed, Mocked) & Outputs (Produced)

| Contract / Artifact | Direction for P3 | Real producer / consumer | M1 mocked source or sink | P3 responsibility | Notes |
| --- | --- | --- | --- | --- | --- |
| `SearchResult` | Consumed | P2 retrieval/vector index | Sample fixtures | Pass matches into Curator as grounded context | Do not block on P2; develop against stable fixture matches with `chunkId`, `docId`, `score`, `text`, `lineRange`, `commitSha`. |
| `DocChunk` metadata | Consumed indirectly | P2 processing/vector index | Fixture-backed search matches | Preserve provenance in evidence/citations | P3 should not create processing logic; use metadata supplied by retrieval. |
| `RawDocument` / intake payload | Consumed by router | P1/UI and backend API | Mock API fixture | Route document intake through orchestrator | The document router should hand the event to the orchestrator; it should not perform agent reasoning itself. |
| `SandboxRequest` | Produced request | P4 verification service | Mock sandbox interface | Request verification when a proposed edit claims executable/build/test/workflow correctness | P3 may assemble the request from proposal context, but P4 owns execution. |
| `SandboxResult` | Consumed | P4 verification service | Deterministic mock result | Feed into Guardian judgment and confidence/risk review | Guardian reviews the result; orchestrator does not interpret it with LLM logic. |
| ACL / governance context | Consumed | P4 governance/ACL service | Hardcoded roles/users | Include read/write permission context in Guardian review | Retrieval and answer output must respect inaccessible content. |
| Conflict candidates | Consumed | P2 deterministic conflict/dedup service | Planted fixture conflicts | Pass conflicts into Curator and Guardian | Curator may confirm/explain; it must not silently pick a winner. |
| `AgentProposal` | Produced | P4 persistence/governance, P1 diff panel | Fixture sink / mock API | Curator drafts it; Guardian judges it | Must include `diff`, `evidence[]`, `confidence`, `riskLevel`, `conflictsWith`, `verification`, `uncertainty`, and Curator provenance. |
| `ChatAnswer` | Produced | P1 chat UI | Mock API response | Curator produces a RAG answer | Must include citations, UI scope, confidence, and `needsHumanReview`. |
| Provider config | Consumed | Environment | Local fake defaults | Switch fake ↔ Azure OpenAI without changing callers | Default chat model example: `gpt-4o-mini`; default embedding model example: `text-embedding-3-large`. |

Illustrative shape only; use the frozen contract from `backend/app/models/**` once it exists:

```jsonc
{
  "proposalId": "prop_demo_merge_build_docs",
  "action": "merge",
  "targetDocId": "vscode/build.md",
  "sourceDocIds": ["vscode/build.md", "vscode/contributing.md"],
  "diff": { "before": "old instruction", "after": "new instruction", "format": "unified" },
  "evidence": [
    {
      "chunkId": "vscode/build.md#Build#0",
      "docId": "vscode/build.md",
      "commitSha": "f00dcafe...",
      "quote": "npm ci installs exact versions",
      "relevance": 0.88
    }
  ],
  "confidence": 0.82,
  "riskLevel": "medium",
  "conflictsWith": ["vscode/contributing.md"],
  "proposedBy": "curator-agent"
}
```

```jsonc
{
  "answer": "Run `npx playwright test` from the repository root.",
  "scope": "current-repo",
  "citations": [
    { "docId": "playwright/docs/src/ci.md", "lineRange": [8, 12], "commitSha": "9a8b7c...", "relevance": 0.91 }
  ],
  "confidence": 0.91,
  "needsHumanReview": false
}
```

## Dependencies & Interfaces With Others

| Person | Interface | P3 consumes | P3 produces | M1 / M2 / M3 reality |
| --- | --- | --- | --- | --- |
| P1 — Frontend & Demo Experience | API responses and fixtures | Chat scope toggle, document drop-off payload shape, rendering expectations for citations/diff/risk | `ChatAnswer`, `AgentProposal` through `backend/app/api/chat.py` and `backend/app/api/documents.py` | M1: mock API fixtures. M2: real P3 responses may still be fixture-backed. M3: real routers serve P1. |
| P2 — Retrieval & Document Intelligence | Retrieval and conflict service interfaces | `SearchResult`, duplicate candidates, conflict candidates, chunk provenance | Queries and context needs for search | M1: sample `SearchResult` fixtures. M2: real retrieval replaces fixtures. M3: integrated API path uses real search. |
| P4 — Governance, Verification & Metrics | Sandbox, ACL, persistence, provenance, approval flow | `SandboxResult`, ACL/write context, proposal persistence status | `AgentProposal`, Guardian recommendation, verification request context | M1: sample `AgentProposal` fixtures and mock sandbox. M2: P3 can feed real proposals to P4 fixtures. M3: real store/governance/router path. |
| Director / shared foundation | Frozen contracts and router wiring | `backend/app/models/**`, `frontend/src/lib/types.ts`, `backend/app/main.py` route registration | Contract feedback only, not direct edits | M1 freezes contracts; after that, changes are director-mediated only. |

### Interface principles

- Consume `SearchResult` from P2 as the source of truth for grounding.
- Hand `AgentProposal` to P4 for persistence/governance and to P1 for diff rendering.
- Hand `ChatAnswer` to P1 for chat rendering and graph citation highlighting.
- Call P4’s sandbox and ACL services via interfaces before Guardian judgment.
- Treat fake providers and fixture data as first-class development dependencies, not throwaway hacks.
- Keep all payloads contract-shaped even when the backing implementation is fake.

## Detailed TODOs

### Phase 0 — Foundation participation

- [ ] Co-author the `LLMProvider` interface in `backend/app/ai/providers/**` with a minimal chat completion method that returns structured, schema-valid content.
- [ ] Co-author the `EmbeddingProvider` interface with an embedding method compatible with P2’s vector workflow and fake embeddings.
- [ ] Add Azure OpenAI provider stubs behind the provider interfaces, reading deployment/model/config from environment variables.
- [ ] Add deterministic `FakeLLMProvider` behavior for Curator proposal generation, Guardian judgment, and chat answers.
- [ ] Add deterministic `FakeEmbeddingProvider` behavior so P2/P3 local flows do not require Azure quota.
- [ ] Help author `AgentProposal` and `ChatAnswer` fixtures that validate against the frozen Pydantic contracts and TypeScript mirrors.
- [ ] Help author sample `SearchResult` fixtures with at least one high-confidence duplicate, one conflict seed, one low-confidence/no-evidence case, and one normal chat retrieval case.
- [ ] Confirm the shared fixture examples include chunk IDs, commit SHAs, quotes or cited line ranges, and confidence values.
- [ ] Coordinate with the director before M1 if the provider interface needs a contract-level field; do not edit frozen models directly.

### Core Build

#### Provider Abstraction

- [ ] Implement provider selection rules: fake by default for local/offline development; Azure when explicitly configured.
- [ ] Keep Azure OpenAI chat settings behind `LLMProvider`; callers should not know SDK-specific request/response details.
- [ ] Keep Azure OpenAI embeddings behind `EmbeddingProvider`; callers should not know deployment names, dimensions, or SDK details.
- [ ] Use environment-driven defaults: chat model/deployment example `gpt-4o-mini`; embedding model/deployment example `text-embedding-3-large`.
- [ ] Ensure fake provider outputs are deterministic, schema-valid, and useful for screenshots/demo rehearsal.
- [ ] Normalize provider errors into predictable service-level failures that routers can return safely without leaking secrets or SDK internals.
- [ ] Add provider-level tests for fake determinism, Azure config parsing, and schema-valid fake outputs.

#### Thin Orchestrator (routing rules)

- [ ] Keep the orchestrator as a deterministic code router with no prompt text and no direct LLM call logic.
- [ ] Route document intake events through retrieval first, passing returned `SearchResult` matches to Curator only when reasoning/drafting is needed.
- [ ] Route obvious no-op or insufficient-context cases to explicit review/uncertainty without spending Guardian calls unnecessarily.
- [ ] Invoke Curator for create/update/merge/link/deprecate/flag decisions when related docs, duplicate candidates, or conflict candidates exist.
- [ ] Invoke P4 sandbox/verification after Curator drafts any proposal that references build/test/command/workflow correctness.
- [ ] Invoke Guardian after Curator output plus sandbox/conflict/ACL context are available.
- [ ] Enforce the LLM budget: approximately one Curator call plus one Guardian call per proposal, and one Curator call for simple chat.
- [ ] Return contract-shaped failure states when dependencies are unavailable, instead of raising raw provider/service errors.

Routing pseudo-outline, not implementation code:

```text
Document intake → ACL precheck → retrieval/search → duplicate/conflict context
  if no evidence or low retrieval scores: return needs-human-review proposal shell
  else Curator drafts AgentProposal
       optional sandbox verification through P4 interface
       Guardian judges proposal with sandbox + ACL + conflicts
       evidence/confidence gate runs before returning

Chat question → ACL-scoped retrieval → Curator RAG answer → evidence/confidence gate → ChatAnswer
```

#### Curator Agent (prompt + drafting)

- [ ] Write the Curator prompt so it can only use supplied `SearchResult` context and user/intake content.
- [ ] Require Curator to choose exactly one action: `create`, `update`, `merge`, `link`, `deprecate`, or `flag`.
- [ ] Require Curator to draft an `AgentProposal` with `diff`, `draft`, `evidence[]`, `confidence`, `riskLevel`, and `conflictsWith`.
- [ ] Require every evidence item to include a real `chunkId`, `docId`, `commitSha`, quote or line range, and relevance score from supplied context.
- [ ] Teach Curator to explain conflicts rather than silently selecting a canonical source.
- [ ] Teach Curator to prefer small, reviewable diffs over broad rewrites when evidence is narrow.
- [ ] Teach Curator to mark missing evidence as uncertainty instead of inventing sources.
- [ ] Validate Curator output against the frozen `AgentProposal` contract before it reaches P4/P1.
- [ ] Test Curator with planted stale, duplicate, conflict, and low-confidence fixtures.

#### Guardian Agent (prompt + judging)

- [ ] Write the Guardian prompt so Guardian judges a Curator proposal; Guardian does not draft the original edit.
- [ ] Provide Guardian with the Curator proposal, sandbox/verification result, conflict context, ACL context, and provenance context.
- [ ] Require Guardian to produce an `approve` or `needs-review` recommendation according to the frozen contract fields available at M1.
- [ ] Require Guardian to downgrade or block proposals with failed sandbox verification, missing evidence, inaccessible sources, or unresolved high-risk conflicts.
- [ ] Require Guardian to preserve `proposedBy` as Curator-originated; Guardian judges safety and governance.
- [ ] Require Guardian to explain why a proposal needs review without adding unsupported new claims.
- [ ] Test Guardian with passing sandbox, failing sandbox, inaccessible evidence, and conflict-heavy fixtures.
- [ ] Ensure Guardian does not push total proposal cost beyond the two-call budget.

#### Evidence & Confidence Enforcement

- [ ] Add a final deterministic evidence gate after every Curator/Guardian output and every chat answer.
- [ ] Force explicit uncertainty when `confidence < 0.5`.
- [ ] Force explicit uncertainty when there is no supporting chunk/citation.
- [ ] Force explicit uncertainty when supporting evidence lacks a `commitSha`.
- [ ] Set `uncertainty` on proposals that fail evidence gating.
- [ ] Set `needsHumanReview` on chat answers that fail evidence gating.
- [ ] Use the exact user-facing fallback idea: `I'm not sure. This needs human review.`
- [ ] Never allow an answer/edit to leave P3 without supporting chunk IDs + commit SHAs + confidence.
- [ ] Add tests proving low-confidence, no-citation, and missing-commit cases cannot pass as confident outputs.

#### Chat/RAG path

- [ ] Implement `/chat` as an ACL-scoped RAG path that retrieves relevant chunks before calling Curator.
- [ ] Use exactly one Curator call for a simple chat answer.
- [ ] Pass the UI scope toggle through to retrieval and mirror it back in `ChatAnswer.scope`.
- [ ] Require citations to map to real `docId`s and line ranges/commit SHAs from `SearchResult` context.
- [ ] Avoid proposal/Guardian work for ordinary informational chat unless the user explicitly asks for an edit/proposal path.
- [ ] Return a useful `needsHumanReview` answer when retrieval returns no evidence.
- [ ] Ensure citation relevance scores can drive P1 graph highlighting intensity.
- [ ] Add tests for current-repo scope, all-accessible scope, empty retrieval, and low-confidence chat.

#### API routers (`/documents` proposal path, `/chat`)

- [ ] In `backend/app/api/documents.py`, keep router logic thin: parse request, call orchestrator, return `AgentProposal` or review-needed response.
- [ ] In `backend/app/api/chat.py`, keep router logic thin: parse question/scope, call orchestrator chat path, return `ChatAnswer`.
- [ ] Do not duplicate orchestration decisions in routers.
- [ ] Do not persist proposals directly from the P3 router unless the P4 interface requires a handoff call; P4 owns store/provenance.
- [ ] Return frozen contract field names exactly, including camelCase JSON.
- [ ] Keep mock-friendly behavior so P1 can render responses before full M3 integration.
- [ ] Add router tests with fake providers and fixture retrieval.
- [ ] Ensure error responses do not expose provider credentials, raw prompts, or inaccessible document text.

### Integration (M2/M3)

- [ ] Swap `FakeLLMProvider` to Azure OpenAI through configuration without changing orchestrator or agent call sites.
- [ ] Validate Azure Curator outputs against the same `AgentProposal` schema used by fakes.
- [ ] Validate Azure chat outputs against the same `ChatAnswer` schema used by fakes.
- [ ] Consume real `SearchResult` output from P2 retrieval and verify chunk IDs, doc IDs, line ranges, commit SHAs, and scores survive into evidence/citations.
- [ ] Feed real Curator `AgentProposal` output to P4’s governance/persistence interface.
- [ ] Wire P4 sandbox results into Guardian input and confirm failed sandbox produces `needs-review` / uncertainty behavior.
- [ ] Wire P4 ACL context into Guardian and chat answer generation so inaccessible evidence is not emitted.
- [ ] Run an end-to-end local path: document drop-off → retrieval → Curator proposal → sandbox result → Guardian judgment → P4 handoff → P1-renderable response.
- [ ] Reconcile any contract mismatch through the director instead of local patching frozen models or TypeScript types.
- [ ] Run backend quality gates before declaring M2/M3 integration complete: `ruff check`, `black --check`, `pytest -q`.

### Demo Polish (M4)

- [ ] Tune Curator prompt wording against planted conflict fixtures so the merge proposal is specific, concise, and convincing.
- [ ] Tune Guardian prompt wording so approval vs human-review judgments are easy for judges to understand.
- [ ] Ensure a planted low-confidence fixture reliably triggers `I'm not sure. This needs human review.`
- [ ] Ensure a planted no-supporting-chunk fixture reliably triggers human review even if the model text sounds plausible.
- [ ] Ensure the primary demo proposal shows evidence quotes, chunk IDs, commit SHAs, risk level, confidence, and conflicts in a P1-friendly format.
- [ ] Keep token usage low by trimming retrieval context to the most relevant chunks and avoiding repeated full-document prompts.
- [ ] Rehearse fallback mode with `FakeLLMProvider` so the demo can run offline or if Azure quota/rate limits fail.
- [ ] Capture the final prompt/provider settings used for the demo in comments/config owned by P3, not in frozen contracts.
- [ ] Run the final backend quality gate: `ruff check`, `black --check`, `pytest -q`.

## Key Design Rules & Gotchas

| Rule | Why it matters | Practical check |
| --- | --- | --- |
| Two-call proposal budget | Azure student quota is limited and the architecture promises cost-conscious reasoning. | Proposal path should normally be Curator once + Guardian once. |
| One-call simple chat budget | RAG chat should be fast and cheap. | Chat path should call Curator only; no Guardian unless it becomes an edit/proposal flow. |
| Orchestrator stays LLM-free | Routing should be explainable, testable, and free. | No prompt strings or provider calls inside orchestrator routing logic. |
| Evidence or silence | DocGuardian must behave like an engineering tool, not a guessing chatbot. | No chunk ID + commit SHA + confidence means no confident answer/edit. |
| Confidence threshold is 0.5 | README and plans define `confidence < 0.5` as forced review. | Tests should prove 0.49 fails and 0.50 only passes if evidence exists. |
| Deterministic fakes | Parallel work depends on repeatable offline behavior. | Same fixture input should produce the same proposal/answer every run. |
| Never invent sources | Fake confidence is worse than no answer. | Evidence must be selected from supplied retrieval context only. |
| Prompt-injection caution | Retrieved documents may contain instructions that try to manipulate the model. | Prompt states retrieved text is evidence, not instructions; system/developer policy wins. |
| ACL-aware grounding | Users must not receive inaccessible content through citations or generated text. | Retrieval/ACL filtering must happen before prompts and again before response. |
| Conflicts require explanation | README §6.6 says the agent must not silently choose one document. | Merge/update proposals should include `conflictsWith` and rationale in evidence/uncertainty where appropriate. |
| Sandbox is supporting evidence, not magic | Verification can increase confidence but cannot replace missing provenance. | Passing sandbox with no source chunks still forces review. |
| Contract names are sacred | Serialization mismatches silently break P1/P4 integration. | Use frozen `AgentProposal` and `ChatAnswer` field names exactly. |

### Common failure modes to avoid

- Putting LLM prompt logic in `backend/app/ai/orchestrator.py`.
- Letting routers make independent reasoning decisions that drift from the orchestrator.
- Calling Azure directly from Curator/Guardian instead of through `LLMProvider`.
- Returning a beautiful answer with no citations.
- Returning citations without `commitSha`.
- Treating a high retrieval score as proof when the quoted text does not support the claim.
- Allowing Guardian to rewrite the proposal instead of judging it.
- Blocking on P2 or Azure when fixtures/fakes are available.
- Editing frozen contracts locally to make a test pass.
- Leaking raw prompts, inaccessible document snippets, or provider configuration in errors.

## Definition of Done

Person 3’s slice is done when it satisfies the team-plan §7 quality gates and the AI-specific safety rules.

- [ ] Frozen contracts are honored exactly: `SearchResult` consumed as defined; `AgentProposal` and `ChatAnswer` emitted with the frozen field names and types.
- [ ] `backend/app/ai/orchestrator.py` is a thin deterministic router with no LLM calls or prompt text.
- [ ] Curator produces proposal and chat outputs only from supplied context, with evidence/citations and confidence.
- [ ] Guardian judges Curator proposals using sandbox, conflict, ACL, and provenance context.
- [ ] Every proposal/edit carries supporting chunk IDs, commit SHAs, confidence, and risk/conflict metadata where applicable.
- [ ] Every chat answer carries citations, scope, confidence, and `needsHumanReview`.
- [ ] `confidence < 0.5`, no supporting chunk, or missing commit SHA always forces the explicit human-review path.
- [ ] Fakes are deterministic and schema-valid, so P3 can develop offline and P1/P4 can use fixtures reliably.
- [ ] The proposal path works against mocks at M1, real retrieval/LLM at M2, and P4 store/governance at M3.
- [ ] The demo path at M4 reliably produces a convincing conflict/merge proposal and a demonstrable low-confidence human-review response.
- [ ] Edge cases are tested: empty results, inaccessible docs, low confidence, failed sandbox, unresolved conflict, provider failure, and malformed model output.
- [ ] Backend quality gates pass for touched modules: `ruff check`, `black --check`, and `pytest -q`.
- [ ] No Person 3 work requires edits to `backend/app/models/**`, `frontend/src/lib/types.ts`, `backend/app/main.py`, or another person’s owned router/directory.
