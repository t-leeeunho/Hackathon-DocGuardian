# Person 3 — Agent Orchestration & AI Reasoning

> **As-built status (2026-06-24):** the LangGraph Curator/Guardian agents are
> implemented and `/propose` now persists to the `proposals` table for the
> governance approval flow; see [../implementation-status.md](../implementation-status.md).

Person 3 owns the reasoning core: a thin deterministic retrieval step plus the only two LLM-backed agents in DocGuardian AI, Curator and Guardian. As built, the thin orchestrator is realized as two compiled LangGraph graphs, not a hand-rolled loop.

## Mission

Own the AI reasoning layer without turning the whole backend into an agent system. The mission is to keep orchestration deterministic and cost-conscious while still producing high-quality, evidence-backed proposals and chat answers. Person 3 must make the Curator and Guardian useful enough for the demo, but safe enough that weak evidence always becomes explicit uncertainty and human review. The target budget is approximately two LLM calls per proposal and one LLM call for a simple chat answer.

## Scope — What You Own

Person 3 owns the AI orchestration, agent schemas, Azure chat factory, and the two agent API entry points as they are implemented today. The intended future split can still happen later, but it is **not** the current backend layout.

- `backend/app/agents/graph.py`
  - Two compiled LangGraph graphs using `langgraph`, `langchain-openai`, and `langchain-core`.
  - `/chat`: `retrieve → curator` → `ChatAnswer` (**1 LLM call**).
  - `/propose`: `retrieve → curator(draft) → guardian(review)` → `AgentProposal` (**2 LLM calls**).
  - `retrieve_node` is deterministic in-process pgvector search and makes no LLM call.
  - Only Curator and Guardian call Azure OpenAI.
- `backend/app/agents/schemas.py`
  - Structured output schemas: `Citation`, `ChatAnswer`, and `AgentProposal`.
  - These are snake_case and streamlined compared with the long-term README §8A.4 target.
- `backend/app/agents/llm.py`
  - Azure OpenAI chat factory via `get_chat_llm()` / `AzureChatOpenAI`.
  - Raises `AzureNotConfiguredError` when required Azure chat env vars are missing.
- Agent endpoint wiring currently lives in `backend/app/main.py`
  - `POST /chat` calls `run_chat`.
  - `POST /propose` calls `run_propose`.
  - Missing Azure chat config is returned as HTTP **503**.

There is currently **no** `backend/app/ai/orchestrator.py`, no split `backend/app/ai/agents/curator.py` / `guardian.py`, no `backend/app/ai/providers/` package, and no separate `backend/app/api/documents.py` or `backend/app/api/chat.py` router files. Embedding provider abstraction exists under `backend/app/embeddings/`, but chat is Azure-only today.

## What You Must NOT Touch

The contracts-first execution model only works if ownership boundaries are respected. This section reflects current reality, where some planned files do not exist yet.

- Do not invent or document non-existent `backend/app/ai/**` implementation as current behavior.
  - Current agent code lives in `backend/app/agents/**`.
  - A future split may move code, but planning language must call that pending work.
- Do not redefine core ingestion/retrieval contracts in Person 3 docs.
  - Current core models live in `backend/app/models.py`, not `backend/app/models/**`.
  - Person 3 consumes retrieved rows and emits agent structured outputs from `backend/app/agents/schemas.py`.
- Do not claim frontend TypeScript mirrors or proposal-governance contracts are complete.
  - The frontend has not started, and richer proposal persistence/apply/governance remains pending.
- Do not bypass retrieval provenance.
  - Use retrieved `doc_id`, `line_range`, `commit_sha`, and relevance as the source of truth for citations.
  - The implementation overwrites citation `commit_sha` from retrieved rows to prevent SHA hallucination.
- Do not emit application source code from this plan.
  - This document is a planning/specification artifact only.

## Inputs (Consumed, Mocked) & Outputs (Produced)

| Contract / Artifact | Direction for P3 | Real producer / consumer | Current source or sink | P3 responsibility | Notes |
| --- | --- | --- | --- | --- | --- |
| Retrieved rows / search matches | Consumed | P2 retrieval/vector index | `retrieve_node` calls in-process pgvector search | Pass matches into Curator/Guardian as grounded context | Deterministic retrieval only; no LLM cost. Rows provide `doc_id`, line range, score, text, and `commit_sha`. |
| `Citation` | Produced | P1/P4 future consumers, agent responses today | `backend/app/agents/schemas.py` | Preserve provenance in citations | Actual fields: `doc_id`, `line_range`, `commit_sha`, `relevance`. |
| `ChatAnswer` | Produced | `/chat` response and future P1 chat UI | `run_chat` via `backend/app/main.py` | Curator produces a RAG answer | Actual fields: `answer`, `citations`, `confidence`, `needs_human_review`; `scope` is added at runtime in `run_chat`. |
| `AgentProposal` | Produced | `/propose` response and future P4 persistence/governance | `run_propose` via `backend/app/main.py` | Curator drafts; Guardian judges | Actual fields: `action`, `target_doc_id`, `draft`, `citations`, `confidence`, `risk_level`, `conflicts_with`, `recommendation`, `guardian_reasoning`, `uncertainty`. |
| Azure chat config | Consumed | Environment | Required for `/chat` and `/propose` | Use `get_chat_llm()` and surface safe 503s when missing | Required vars: `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_CHAT_DEPLOYMENT`. No fake/local chat fallback yet. |
| Embeddings | Consumed indirectly | `backend/app/embeddings/provider.py` | Local fastembed default; Azure optional | Retrieval uses embeddings before agent calls | Embeddings have provider abstraction and local default; chat does not. |
| Sandbox / ACL / proposal persistence | Future consumed/produced | P4 governance/verification | Not implemented | Keep as planned integration points | Do not claim verification, approval, provenance, rollback, or apply are built. |

Actual streamlined `AgentProposal` shape today:

```jsonc
{
  "action": "merge",
  "target_doc_id": "vscode/build.md",
  "draft": "Proposed grounded change text",
  "citations": [
    {
      "doc_id": "vscode/build.md",
      "line_range": [8, 12],
      "commit_sha": "f00dcafe...",
      "relevance": 0.88
    }
  ],
  "confidence": 0.82,
  "risk_level": "medium",
  "conflicts_with": ["vscode/contributing.md"],
  "recommendation": "needs-review",
  "guardian_reasoning": "Evidence is useful but still needs review.",
  "uncertainty": "Optional uncertainty note"
}
```

Actual `ChatAnswer` shape today:

```jsonc
{
  "answer": "Run `npx playwright test` from the repository root.",
  "scope": "playwright",
  "citations": [
    { "doc_id": "playwright/docs/src/ci.md", "line_range": [8, 12], "commit_sha": "9a8b7c...", "relevance": 0.91 }
  ],
  "confidence": 0.91,
  "needs_human_review": false
}
```

Gap/TODO versus README §8A.4: `AgentProposal` does **not** yet include `proposalId`, `sourceDocIds`, a structured `diff{}`, an `evidence[]` array, or a `verification{}` block. Keep those as pending richer-contract work.

## Dependencies & Interfaces With Others

| Person | Interface | P3 consumes | P3 produces | M1 / M2 / M3 reality |
| --- | --- | --- | --- | --- |
| P1 — Frontend & Demo Experience | API responses and fixtures | Chat scope/rendering expectations for citations and proposal risk | `ChatAnswer`, `AgentProposal` through `POST /chat` and `POST /propose` in `backend/app/main.py` | endpoints exist; frontend is scaffolded. |
| P2 — Retrieval & Document Intelligence | Retrieval/vector index | pgvector search rows, chunk provenance, scores | Queries and context needs for search | Real retrieval is integrated in `retrieve_node`; duplicate/conflict services are still pending. |
| P4 — Governance, Verification & Metrics | Future sandbox, ACL, persistence, provenance, approval flow | Not yet wired | Guardian recommendation fields only today | Proposal persistence/apply, sandbox verification, ACL, provenance, and rollback are pending. |
| Director / shared foundation | Current layout and contracts | `backend/app/models.py`, `backend/app/main.py`, `backend/app/agents/schemas.py` | Contract feedback only unless code ownership changes | Existing contracts are snake_case internally with camelCase API DTOs where needed. |

### Interface principles

- Consume retrieved rows from P2 as the source of truth for grounding.
- Hand `ChatAnswer` and `AgentProposal` to current API endpoints in `backend/app/main.py`; future router split is pending.
- Preserve Curator draft and grounded citations when Guardian judges the proposal.
- Treat Azure chat as required for agents today; no `FakeLLMProvider` or local chat fallback is implemented yet.
- Keep all payloads schema-shaped even when the long-term README contract is richer than today’s implementation.

## Detailed TODOs

### Phase 0 — Foundation participation

- [x] Implement Azure OpenAI chat construction for Curator/Guardian through `get_chat_llm()`.
- [x] Implement embedding provider abstraction compatible with P2’s vector workflow; local fastembed is the default and Azure embeddings are optional.
- [x] Add structured agent schemas for `Citation`, `ChatAnswer`, and streamlined `AgentProposal`.
- [x] Confirm retrieved evidence includes doc IDs, commit SHAs, cited line ranges, and confidence/relevance values.
- [ ] Add deterministic `FakeLLMProvider` behavior for Curator proposal generation, Guardian judgment, and chat answers.
- [ ] Add chat provider abstraction/fake-local switch for offline development; chat is Azure-only today.
- [ ] Expand `AgentProposal` toward the README §8A.4 target with `proposalId`, `sourceDocIds`, structured `diff{}`, `evidence[]`, and `verification{}`.
- [ ] Coordinate with the director before changing frozen/shared contracts or moving files into a future `app/ai/**` layout.

### Core Build

#### Provider Abstraction

- [x] Keep Azure OpenAI chat settings isolated in `backend/app/agents/llm.py`.
- [x] Normalize missing Azure chat config into `AzureNotConfiguredError` so routers return safe HTTP 503s.
- [x] Keep embeddings behind `EmbeddingProvider`; callers do not need to know local/Azure embedding details.
- [ ] Implement fake-by-default chat provider selection for local/offline development.
- [ ] Add provider-level tests for fake determinism, Azure config parsing, and schema-valid fake outputs.

#### Thin Orchestrator (routing rules)

- [x] Implement the orchestration layer as deterministic LangGraph routing rather than a hand-rolled orchestrator loop.
- [x] Implement `/chat` graph: `retrieve → curator` → `ChatAnswer` with one LLM call when evidence is strong enough.
- [x] Implement `/propose` graph: `retrieve → curator(draft) → guardian(review)` → `AgentProposal` with two LLM calls.
- [x] Keep `retrieve_node` deterministic: in-process pgvector search, no LLM call.
- [x] Short-circuit weak chat evidence to an explicit human-review answer with no LLM cost.
- [x] Enforce the normal LLM budget: one Curator call for chat; Curator plus Guardian for proposals.
- [ ] Add richer proposal no-evidence handling before spending Curator/Guardian calls.
- [ ] Invoke P4 sandbox/verification after Curator drafts proposals that reference build/test/command/workflow correctness.
- [ ] Wire P4 ACL/governance context into retrieval and Guardian judgment.

Routing pseudo-outline, not implementation code:

```text
Chat question → retrieval → if top score < 0.45, no-cost human-review ChatAnswer
              → else Curator RAG answer → grounded citations → ChatAnswer

Proposal instruction → retrieval → Curator draft AgentProposal
                     → Guardian judges recommendation/risk/uncertainty
                     → preserve Curator draft + grounded citations
```

#### Curator Agent (prompt + drafting)

- [x] Write the Curator chat prompt so it can only use supplied documentation sources.
- [x] Write the Curator draft prompt requiring one action: `create`, `update`, `merge`, `link`, `deprecate`, or `flag`.
- [x] Validate Curator chat/proposal outputs through Pydantic structured output schemas.
- [x] Require citations to map back to supplied retrieved context; fill missing citations from retrieved rows.
- [x] Overwrite citation `commit_sha` values from authoritative retrieved rows to prevent SHA hallucination.
- [ ] Add structured `diff{}` and `evidence[]` output beyond the current `draft` + `citations` shape.
- [ ] Test Curator with planted stale, duplicate, conflict, and low-confidence fixtures.

#### Guardian Agent (prompt + judging)

- [x] Write the Guardian prompt so Guardian judges a Curator proposal; Guardian does not draft the original edit.
- [x] Require Guardian to produce recommendation/risk/confidence/reasoning/uncertainty fields on `AgentProposal`.
- [x] Preserve the Curator’s draft and grounded citations; Guardian contributes only judgment fields.
- [x] Keep Guardian within the two-call proposal budget.
- [ ] Provide Guardian with sandbox/verification result, conflict context, ACL context, and provenance context when P4 services exist.
- [ ] Test Guardian with passing sandbox, failing sandbox, inaccessible evidence, and conflict-heavy fixtures.

#### Evidence & Confidence Enforcement

- [x] Set `WEAK_EVIDENCE_THRESHOLD = 0.45` for chat evidence gating.
- [x] Return the explicit fallback idea when evidence is weak: `I'm not sure. The available documentation does not clearly answer this. This needs human review.`
- [x] Set `needs_human_review` on weak-evidence chat answers.
- [x] Preserve or synthesize citations from retrieved rows and force authoritative commit SHAs.
- [ ] Add final deterministic evidence gates after every proposal output, not just chat weak-evidence gating.
- [ ] Add tests proving low-confidence, no-citation, and missing-commit cases cannot pass as confident outputs.

#### Chat/RAG path

- [x] Implement `/chat` as a RAG path that retrieves relevant chunks before calling Curator.
- [x] Use exactly one Curator call for a simple chat answer when evidence passes the threshold.
- [x] Mirror the repo scope back in `ChatAnswer.scope` at runtime.
- [x] Require citations to map to real `doc_id`s and line ranges/commit SHAs from retrieved context.
- [x] Avoid proposal/Guardian work for ordinary informational chat.
- [x] Return a useful `needs_human_review` answer when retrieval returns no or weak evidence.
- [ ] Add tests for repo scope, all-accessible scope, empty retrieval, and low-confidence chat.

#### API routers (`/propose`, `/chat`)

- [x] Implement `POST /chat` in `backend/app/main.py` as a thin call to `run_chat`.
- [x] Implement `POST /propose` in `backend/app/main.py` as a thin call to `run_propose`.
- [x] Return HTTP 503 without leaking secrets when Azure chat config is missing.
- [x] Do not persist proposals directly from the agent endpoint; proposal persistence/apply is not implemented yet.
- [ ] Split endpoints into future router files only if the backend layout is intentionally refactored.
- [ ] Return richer README §8A.4 proposal fields once those contracts are implemented.
- [ ] Add router tests with fake providers and fixture retrieval after fake chat exists.

### Integration (M2/M3)

- [x] Consume real retrieval output from P2 and preserve doc IDs, line ranges, commit SHAs, and scores in citations.
- [x] Validate Azure Curator/Guardian outputs against current `ChatAnswer` and `AgentProposal` schemas.
- [x] Run an end-to-end local backend path for `/chat` and `/propose` when Azure is configured.
- [ ] Swap a future `FakeLLMProvider` to Azure OpenAI through configuration without changing agent call sites.
- [ ] Feed real Curator `AgentProposal` output to P4’s governance/persistence interface.
- [ ] Wire P4 sandbox results into Guardian input and confirm failed sandbox produces `needs-review` / uncertainty behavior.
- [ ] Wire P4 ACL context into Guardian and chat answer generation so inaccessible evidence is not emitted.
- [ ] Run document drop-off → retrieval → Curator proposal → sandbox result → Guardian judgment → P4 handoff → P1-renderable response once P4 handoff exists.
- [ ] Reconcile richer contract mismatches through the director instead of local patching shared models or TypeScript types.
- [ ] Run backend quality gates once test/lint tooling exists; current repo has no ruff/black/pytest configuration.

### Demo Polish (M4)

- [ ] Tune Curator prompt wording against planted conflict fixtures so the merge proposal is specific, concise, and convincing.
- [ ] Tune Guardian prompt wording so approval vs human-review judgments are easy for judges to understand.
- [x] Ensure weak chat evidence triggers the human-review fallback with threshold `0.45`.
- [x] Keep token usage low by trimming retrieval context to the most relevant chunks and preserving the one/two-call budgets.
- [ ] Ensure the primary demo proposal shows richer evidence quotes, chunk IDs, commit SHAs, risk level, confidence, conflicts, and eventually a structured diff in a P1-friendly format.
- [ ] Rehearse fallback mode after a `FakeLLMProvider` exists; offline chat/proposal demo is not implemented today.
- [ ] Capture the final prompt/provider settings used for the demo in comments/config owned by P3, not in frozen contracts.
- [ ] Run final backend quality gates once quality tooling is configured.

## Key Design Rules & Gotchas

| Rule | Why it matters | Practical check |
| --- | --- | --- |
| LangGraph owns orchestration today | The actual implementation is two compiled graphs, not a hand-rolled loop. | `graph.py` has separate chat and propose graphs. |
| Two-call proposal budget | Azure student quota is limited and the architecture promises cost-conscious reasoning. | Proposal path should normally be Curator once + Guardian once. |
| One-call simple chat budget | RAG chat should be fast and cheap. | Chat path should call Curator only after deterministic retrieval passes the evidence gate. |
| Retrieval stays LLM-free | Routing should be explainable, testable, and free. | `retrieve_node` uses pgvector search only. |
| Evidence or review | DocGuardian must behave like an engineering tool, not a guessing chatbot. | Weak evidence produces explicit human review rather than a confident answer. |
| Weak-evidence threshold is 0.45 as built | README says approximately 0.5, but code uses `WEAK_EVIDENCE_THRESHOLD = 0.45`. | Top retrieval score below 0.45 short-circuits chat with no LLM call. |
| Azure chat is required today | There is no fake/local chat fallback yet. | Missing Azure env vars return HTTP 503 for `/chat` and `/propose`. |
| Never invent sources | Fake confidence is worse than no answer. | Citations must be selected from supplied retrieval context only. |
| Commit SHAs are authoritative data | Models can hallucinate plausible SHAs. | Citation `commit_sha` is overwritten from retrieved rows. |
| Guardian judges; Curator drafts | The Guardian should not erase grounded proposal content. | Guardian contributes recommendation/reasoning/risk/conflict/uncertainty fields while Curator draft + citations are preserved. |
| Prompt-injection caution | Retrieved documents may contain instructions that try to manipulate the model. | Prompt states retrieved text is evidence, not instructions; system/developer policy wins. |
| ACL/governance/sandbox are pending | Planning must not imply these safeguards are already wired. | Keep P4 integration as unchecked TODOs until services exist. |
| Contract names reflect current layer | Agent schemas are snake_case; HTTP DTOs elsewhere may be camelCase. | Use `target_doc_id`, `risk_level`, `needs_human_review` for agent schemas today. |

### Common failure modes to avoid

- Describing `backend/app/ai/orchestrator.py` as implemented; it does not exist.
- Describing split `curator.py` / `guardian.py` modules or `app/ai/providers/**` as implemented; they do not exist.
- Claiming fake chat/offline LLM behavior exists; it is still pending.
- Letting routers make independent reasoning decisions that drift from the LangGraph graphs.
- Returning a beautiful answer with no citations.
- Returning citations without authoritative `commit_sha`.
- Treating a high retrieval score as proof when the quoted text does not support the claim.
- Allowing Guardian to rewrite the proposal instead of judging it.
- Claiming proposal persistence/apply, verification, ACL, provenance, rollback, or richer diff/evidence contracts are done.
- Leaking raw prompts, inaccessible document snippets, or provider configuration in errors.

## Definition of Done

Person 3’s slice is mostly built for the current backend, with richer governance/proposal work still pending.

- [x] Current schemas are honored exactly: `Citation`, `ChatAnswer`, and streamlined `AgentProposal` from `backend/app/agents/schemas.py`.
- [x] `backend/app/agents/graph.py` implements deterministic retrieval plus Curator/Guardian LangGraph nodes.
- [x] Curator produces proposal and chat outputs from supplied retrieved context, with citations and confidence.
- [x] Guardian judges Curator proposals and preserves the Curator draft plus grounded citations.
- [x] Every chat answer carries citations, runtime `scope`, confidence, and `needs_human_review`.
- [x] Weak chat evidence below `0.45` forces the explicit human-review path with no LLM call.
- [x] Citation commit SHAs are grounded by retrieved rows rather than model output.
- [x] `/chat` and `/propose` are available in `backend/app/main.py` and return 503 if Azure chat is not configured.
- [ ] Richer `AgentProposal` contract includes `proposalId`, `sourceDocIds`, structured `diff{}`, `evidence[]`, and `verification{}`.
- [ ] Deterministic fake/local chat provider exists for offline development and demo rehearsal.
- [ ] Proposal persistence, approval/apply, provenance, rollback, ACL, sandbox verification, metrics, and frontend rendering are integrated.
- [ ] Edge cases are tested: empty results, inaccessible docs, low confidence, failed sandbox, unresolved conflict, provider failure, and malformed model output.
- [ ] Backend quality gates pass once repository lint/test tooling is configured.
