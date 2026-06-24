# DocGuardian AI — Implementation Status (As-Built)

> **Snapshot date:** 2026-06-24. This document records what is **actually built**
> today, versus what the planning docs describe. When a planning doc disagrees
> with this file, **this file reflects reality** (it is derived directly from the
> committed code). The locked product target is README §10.

---

## 1. Summary

The **backend ingestion → processing → embedding → retrieval → agent** pipeline is
implemented and runs locally, and the backend now also includes the **governance
slice**: ACL enforcement, the approval → apply → provenance → rollback flow,
duplicate/conflict detection, derived node health/importance, a `MetricsDTO`
aggregation, a **real containerized verification sandbox** (Docker), and an
**async ingest path** (`202 + jobId`) with a live `WS /stream` event feed. Document
intake is **atomic** (all-or-nothing) and generates a one-line AI/extractive
description shown in the sidebar tree. The **React frontend is scaffolded and
buildable** (typecheck + tests + production build all green); it consumes the API,
live-refreshes over the WebSocket, and falls back to demo fixtures when offline.

Remaining work: wiring the frontend governance panels (approve/reject, metrics,
provenance) to the live endpoints, `POST /ingest/refresh`, demo seed data, and
backend lint/format tooling. The sandbox runs real containers when Docker is
present and otherwise reports `available:false` (never a fake pass).

---

## 2. Locked Stack (README §10) — and what's wired up

| Area | Locked choice | Built today? |
| --- | --- | --- |
| Backend | Python + FastAPI, Pydantic v2 | ✅ Yes |
| Storage | **Single PostgreSQL** (metadata + graph + audit/provenance) | ✅ `documents` (+governance cols), `chunks`, `edges`, **`proposals`**, append-only **`provenance`** |
| Vector index | **pgvector** in the same Postgres | ✅ `chunks.embedding VECTOR(dim)` + HNSW cosine index |
| Embeddings | Provider-abstracted; **local fastembed default**, Azure optional | ✅ `LocalEmbeddingProvider` (BAAI/bge-small-en-v1.5, 384-dim) / `AzureEmbeddingProvider` |
| LLM agents | **Azure OpenAI** chat (one deployment), two agents | ✅ Curator + Guardian via **LangGraph**; Azure **required** for agents (503 otherwise) |
| Frontend | React + TS + Vite + Tailwind + **React Flow (2D)** + **Monaco** | 🟡 Scaffolded (builds; live WS refresh; demo-mode fixtures) |
| Verification sandbox | Containerized, real (README §10.6) | ✅ Real Docker (`--network none`, mem/cpu/pids caps, timeout); `available:false` if no Docker |
| Governance/auth | Mocked auth + real ACL/approval/provenance on Postgres (README §10.7) | ✅ Mocked `Principal` + real ACL, approval, append-only provenance, rollback |

> Note: the local-first **fastembed default** means the whole ingestion + retrieval
> path runs with **no Azure** at all. Azure is the default for the `/chat` and
> `/propose` agent endpoints, but a deterministic `CHAT_PROVIDER=fake` provider now
> lets those endpoints run with **no Azure** too (local dev, tests, demo rehearsal).

---

## 3. Actual Backend Layout

```text
backend/
├── .env.example                # Azure (optional) + DATABASE_URL + EMBEDDING_* 
├── docker-compose.yml          # Postgres + pgvector (pgvector/pgvector:pg16)
├── repos.config.json           # 4 repos: garnet, playwright, onnxruntime, vscode
├── requirements.txt            # runtime deps (no dev/test tooling configured)
├── app/
│   ├── config.py               # env loading + repos.config loader
│   ├── models.py               # CORE contracts (snake_case): RawDocument, DocChunk, GraphEdge, EdgeType
│   ├── main.py                 # FastAPI app — ALL endpoints + camelCase API DTOs
│   ├── tree.py                 # build_tree() for the left-sidebar file tree
│   ├── agents/
│   │   ├── graph.py            # LangGraph chat + propose graphs; no-evidence short-circuit + evidence gate; reasoning trace
│   │   ├── llm.py              # Chat factory: CHAT_PROVIDER azure|fake (get_chat_llm) + FakeChatLLM + AzureNotConfiguredError
│   │   └── schemas.py          # Citation/Evidence/ProposalDiff/Verification, ChatAnswer (+reasoning), CuratorDraft, GuardianReview, AgentProposal
│   ├── governance/            # GOVERNANCE SLICE
│   │   ├── acl.py             # Principal + can_access/can_write (pure, fail-closed)
│   │   ├── health.py          # derive_health / derive_importance (pure)
│   │   ├── metrics.py         # compute_metrics -> MetricsDTO (pure)
│   │   ├── store.py           # proposals CRUD, append-only provenance, governed graph
│   │   ├── service.py         # approve / staged-approval / rollback flow
│   │   └── serialize.py       # snake->camel for the API boundary
│   ├── services/             # SIDE-EFFECTING SERVICES
│   │   ├── verification.py    # real Docker sandbox (SandboxRequest/Result)
│   │   ├── events.py          # in-process pub/sub bus for WS /stream
│   │   └── jobs.py            # in-memory async ingest job registry
│   ├── embeddings/
│   │   └── provider.py         # EmbeddingProvider ABC + Local (fastembed) + Azure
│   ├── ingestion/
│   │   ├── git_ingest.py       # sparse/shallow clone + commit metadata -> RawDocument
│   │   └── intake.py           # user drop-off -> atomic ingest (txn) + AI summary
│   ├── processing/
│   │   ├── processor.py        # heading-aware chunk_document() + extract_edges()
│   │   ├── conflicts.py        # duplicate/conflict edge detection (≥0.92 / ≥0.85)
│   │   └── summarize.py        # one-line doc description (AI + extractive fallback)
│   └── storage/
│       ├── db.py               # Postgres+pgvector + init_schema() (+governance tables)
│       ├── queries.py          # list_doc_ids, get_document, get_graph, get_doc_summaries
│       └── vectorstore.py      # upserts (optional shared conn) + cosine search
└── scripts/
    ├── run_ingest.py           # ingest -> process -> JSONL under data/_processed/
    ├── load_vectors.py         # embed JSONL chunks + load into pgvector
    ├── detect_conflicts.py     # batch duplicate/conflict edge detection
    ├── add_file.py             # CLI drop-off intake
    └── search.py               # CLI semantic search
```

**Differences from the original plan's assumed layout:**
- `app/models.py` is a **single file**, not a `models/` package.
- `app/main.py` holds **all endpoints**, not per-domain router files (`api/*.py`).
- Storage lives in `app/storage/`; governance logic lives in `app/governance/`
  and side-effecting services in `app/services/` (verification, events, jobs).
- AI provider split: `app/agents/` (chat via LangGraph + Azure) and
  `app/embeddings/` (vectors). There is no `app/ai/providers/` package.
- There is a `scripts/` CLI used to verify the pipeline without the API.
- Dependencies are in `requirements.txt`; `pytest` is configured (no ruff/black yet).

### 3.1 Actual Frontend Layout (as built)

```text
frontend/
├── src/
│   ├── App.tsx / main.tsx           # entry — renders <AppShell/>
│   ├── vite-env.d.ts                # VITE_API_URL env typing
│   ├── lib/                         # data layer (camelCase API contract)
│   │   ├── types.ts                 # mirrors README §8B (GraphDTO, ChatAnswer, …)
│   │   ├── api.ts                   # fetch client; snake→camel for /chat,/propose
│   │   └── fixtures.ts              # demo/offline data (planted stale/dup/conflict)
│   ├── hooks/                       # useChat, useGraph, useHighlight, useReducedMotion
│   ├── components/
│   │   ├── AppShell.tsx             # 3-pane layout + header/metrics strip
│   │   ├── graph/                   # DocGraph (React Flow), DocNode, SparkleBackground
│   │   ├── chat/                    # ChatPanel, CitationChip, ScopeToggle
│   │   ├── sidebar/                 # FileTree
│   │   ├── intake/                  # DropOffArea (drop-off intake)
│   │   └── panels/                  # ProposalPanel (Monaco diff), Provenance, Metrics
│   └── test/                        # App.test.tsx (vitest) + setup.ts
```

- The `src/lib/` folder was previously swallowed by the root `.gitignore` `lib/`
  rule (Python build convention); a `!frontend/src/lib/` negation now keeps it
  tracked.
- No shadcn/ui yet — components are hand-styled (Radix primitives + lucide icons).
- `npm run lint` is `tsc --noEmit` (no ESLint configured).

---

## 4. API Surface (as built — README §8B)

Base URL (local): `http://localhost:8000`. CORS allows the Vite dev server
(`http://localhost:5173`, `:3000`).

| Method | Path | Purpose | Notes |
| --- | --- | --- | --- |
| `GET` | `/health` | Liveness + embedding provider/dim | `{status, embeddingProvider, dim}` |
| `GET` | `/search?q=&repo=&k=` | Semantic search (LangChain retriever target) | pgvector cosine; `matches[]` camelCase |
| `POST` | `/documents` | Drop-off intake (upload/paste) | atomic; text only; `415` binary; `?background=true` → `202`+job |
| `GET` | `/jobs/{jobId}` | Async ingest job status | `{jobId,docId,status,result,error}` |
| `GET` | `/tree?namespace=` | File-system tree (left sidebar) | nested `{name,type,path,summary?,children?}` |
| `GET` | `/graph?repo=` | Document graph (nodes + edges) | **real** derived health/importance; ACL-filtered |
| `GET` | `/documents/{docId}` | Single document + its chunks | camelCase |
| `GET` | `/provenance/{docId}` | Append-only audit history | camelCase `ProvenanceEntry[]` |
| `POST` | `/chat` | Curator agent — evidence-backed answer | LangGraph; **503** if Azure not configured |
| `POST` | `/propose` | Curator + Guardian — proposed change | LangGraph; persisted to `proposals`; **503** if no Azure |
| `GET` | `/proposals/{id}` | Proposal + approval/provenance context | camelCase |
| `POST` | `/proposals/{id}/approve` | Approve + apply (writes provenance) | `202` if staged-approval required |
| `POST` | `/proposals/{id}/rollback` | Roll back an applied proposal | append-only new provenance entry |
| `GET` | `/metrics` | Governance dashboard counters | `MetricsDTO` (camelCase) |
| `POST` | `/verify` | Run a command in the Docker sandbox | real container; `available:false` if no Docker |
| `WS` | `/stream` | Live event feed (ingest/graph/metrics/proposal) | small typed envelopes + heartbeat |

**Not yet implemented** (planned in README §6/§8A.5): `POST /ingest/refresh`.

The API responses are **camelCase** (`docId`, `chunkId`, `headingPath`,
`lineRange`, `commitSha`). The agent endpoints (`/chat`, `/propose`, `/proposals/:id`)
emit snake_case internally and are deep-converted to camelCase at the boundary
(`governance/serialize.py`; the frontend client also normalizes).

---

## 5. Data Contracts (as built)

There are **three layers** of models — not one frozen camelCase package:

1. **Core internal contracts** — `app/models.py`, **snake_case** Pydantic v2
   (`RawDocument`, `DocChunk`, `GraphEdge` with `from`/`to` aliases, `EdgeType`).
   These cover Layers 1–2 (ingestion + processing). No camelCase alias generator.
2. **API response DTOs** — `app/main.py`, **camelCase** Pydantic models
   (`Match`, `SearchResponse`, `GraphNode`, `GraphResponse`, `DocumentResponse`, …)
   plus camelCase dicts from `app/storage/queries.py`. This is where the camelCase
   contract the frontend will consume actually lives.
3. **Agent structured outputs** — `app/agents/schemas.py`. Two layers: lean LLM
   I/O schemas the model fills — `ChatAnswer` (`answer`, `scope`, `citations`,
   `reasoning`, `confidence`, `needs_human_review`), `CuratorDraft` (drafting
   surface), and `GuardianReview` (judgment surface) — plus the richer response
   contract `AgentProposal` aligned with README §8A.4 (`proposal_id`, `action`,
   `target_doc_id`, `source_doc_ids`, `diff{}`, `draft`, `citations`, `evidence[]`,
   `confidence`, `risk_level`, `conflicts_with`, `verification{}`, Guardian fields
   `recommendation`/`guardian_reasoning`/`uncertainty`, `proposed_by`, `created_at`).
   New `Evidence`, `ProposalDiff`, and `Verification` sub-models support it.
4. **Governance contracts** — `app/governance/`: `Principal` (ACL), `DocSignals`
   (health/importance inputs), `MetricsDTO` (camelCase counters), persisted
   `proposals`/`provenance` rows, and `SandboxRequest`/`SandboxResult` in
   `app/services/verification.py`.

> `AgentProposal` now carries the README §8A.4 fields (`proposal_id`,
> `source_doc_ids`, `diff{}`, `evidence[]`, `verification{}`), but they are assembled
> **deterministically by the graph** from retrieved rows — the model only fills the
> lean `CuratorDraft`/`GuardianReview`, never provenance. `verification` stays `null`
> until the P4 sandbox runs against a proposal; `evidence[]` is system-populated from
> grounded retrieval rows, never the model.

---

## 6. Agent Design (as built — LangGraph)

Two compiled LangGraph graphs share one deterministic retrieval node + the two
chat agents (Azure by default, the offline fake via `CHAT_PROVIDER=fake`, or
`CHAT_PROVIDER=auto` = Azure-if-configured-else-fake):

- `/chat`: `retrieve → curator` → `ChatAnswer` (**1 LLM call**).
- `/propose`: `retrieve → {curator(draft) → guardian(review) | no_evidence}` →
  `AgentProposal` (**≤2 LLM calls**). A conditional route runs the **no-evidence
  short-circuit** (`no_evidence_proposal_node`, no LLM) when retrieval is empty or
  below `WEAK_EVIDENCE_THRESHOLD = 0.45`.
- The LLM only fills lean schemas (`CuratorDraft`, `GuardianReview`, `ChatAnswer`);
  the graph assembles the rich `AgentProposal` and grounds all provenance.
- `retrieve_node` is **deterministic** (in-process pgvector search, no LLM).
- Evidence guardrails: weak chat evidence short-circuits to an explicit "needs human
  review" answer with **no LLM cost**; `commit_sha` on every citation/evidence item
  is **overwritten** with the authoritative value from retrieved rows; and a final
  deterministic gate (`_finalize_proposal`, `LOW_CONFIDENCE_THRESHOLD = 0.5`) forces
  `needs-review` on any proposal lacking grounded citations or below the confidence
  floor — regardless of what the Guardian returned.
- Guardian contributes only its judgment (`recommendation`, `guardian_reasoning`,
  `confidence`, `risk_level`, `conflicts_with`, `uncertainty`); the Curator's draft
  and grounded citations are preserved. The merged proposal confidence is
  `min(curator, guardian)` so a thin draft can't bypass the review gate.
- Chat has a symmetric gate (`_ground_chat_citations`): it drops citations to
  non-retrieved docs and forces `needs_human_review` when no citation carries a
  commit SHA or confidence is below the floor.
- **Fail-closed**: `_safe_invoke` wraps every model call, so a throwing or
  `None`-returning LLM degrades to a deterministic needs-review answer/proposal
  (HTTP 500 avoided); a Guardian failure preserves the Curator's draft.
- Raw cosine scores (which are in `[-1, 1]`) are clamped to `[0, 1]` before they
  become `relevance`/`confidence`, so a negative-similarity tail row can't raise.

---

## 7. Pipeline Details (as built)

- **Ingestion** (`ingestion/git_ingest.py`): `git clone --depth 1
  --filter=blob:none --sparse --branch <b>` → `git sparse-checkout set <sparsePaths>`
  → per-file `git log -1` for `(sha, author, email, date)` → one `RawDocument`
  (with `content_hash = sha256`). Idempotent refresh via `fetch --depth 1` +
  `reset --hard`.
- **Processing** (`processing/processor.py`): strips YAML front-matter; splits into
  **heading-aware, fence-aware** sections; oversized sections (>1000 approx tokens)
  are split by blank-line paragraphs; target ~800 tokens; `token_count` is a
  **word-count approximation**; `char_range` is currently a placeholder
  `(0, len(block))`; **no inter-chunk overlap yet**. `extract_edges` emits only
  structural `references` edges from same-repo markdown links.
- **Embeddings** (`embeddings/provider.py`): fastembed local default
  (auto-detects dim), Azure optional via `EMBEDDING_PROVIDER=azure`.
- **Storage** (`storage/`): Postgres `documents`/`chunks`/`edges` plus `proposals`
  and append-only `provenance`; `chunks.embedding` is a pgvector column with an
  HNSW cosine index; upserts use `ON CONFLICT` for idempotency and accept an
  optional shared connection so a whole ingest can be one transaction; search is
  `1 - (embedding <=> q)` with optional `doc_id` prefix filter by `shortName`.
- **Drop-off intake** (`ingestion/intake.py`): **atomic** — summary + embed +
  doc/edges/chunks + incremental conflict detection commit together or roll back
  entirely (no "ghost" docs). Generates a one-line description (AI via the chat
  model when configured, else extractive first paragraph). Available synchronously
  (`201`) or async (`?background=true` → `202` + a job tracked in `services/jobs.py`,
  with `ingest`/`graph` events on `WS /stream`).
- **Conflict detection** (`processing/conflicts.py`): cross-document chunk cosine
  ≥ 0.92 → `duplicate-of`, ≥ 0.85 → `conflicts-with`; best edge per unordered pair
  with stable ids. Runs as a batch (`scripts/detect_conflicts.py`) or incrementally
  for one doc on intake.
- **Governance** (`governance/`): ACL `Principal` (empty ACL = public, fail-closed),
  derived node `health`/`importance`, approval with staged-approval for high-risk/
  low-confidence proposals, append-only provenance, rollback, and `MetricsDTO`.
- **Verification** (`services/verification.py`): real `docker run --network none`
  with memory/cpu/pids caps + timeout + output tail; reports `available:false`
  when Docker is absent (never a fake pass).

---

## 8. Implemented vs Pending Matrix

| Capability | Status |
| --- | --- |
| Sparse/shallow git ingestion + commit metadata | ✅ Implemented |
| Heading-aware chunking + `references` edges | ✅ Implemented (no overlap; placeholder char ranges) |
| Local + Azure embeddings (provider-abstracted) | ✅ Implemented |
| Postgres + pgvector store + cosine search | ✅ Implemented |
| Drop-off intake (`/documents`) | ✅ Implemented (text only) |
| Tree, graph, single-document endpoints | ✅ Implemented (graph health/size/accessible are placeholders) |
| LangGraph Curator (`/chat`) + Curator→Guardian (`/propose`) | ✅ Implemented (Azure default; `CHAT_PROVIDER=fake` offline) |
| Richer `AgentProposal` (`proposalId`/`sourceDocIds`/`diff`/`evidence`/`verification`) | ✅ Implemented (`verification` null until sandbox runs) |
| Offline fake chat provider (`CHAT_PROVIDER=fake`) + no-evidence short-circuit + evidence gate | ✅ Implemented |
| CLI tooling (`run_ingest`, `load_vectors`, `detect_conflicts`, `add_file`, `search`) | ✅ Implemented |
| **Duplicate/conflict detection** (score ≥ 0.92 / ≥ 0.85 edges) | ✅ Implemented (batch + incremental on intake) |
| **Node health / freshness scoring** | ✅ Implemented (`derive_health`/`derive_importance`) |
| **Governance: ACL, approval flow, provenance, rollback** | ✅ Implemented (mocked `Principal`; append-only audit) |
| **Metrics dashboard + `/metrics`** | ✅ Backend implemented (`MetricsDTO`); UI panel still on fixtures |
| **Verification sandbox** | ✅ Real Docker; `available:false` without Docker |
| **WebSocket `/stream` + async ingest (`202`+job)** | ✅ Implemented; **`/ingest/refresh`** still pending |
| **Atomic intake + AI/extractive doc summary** | ✅ Implemented (single txn; sidebar tooltip) |
| **Frontend shell + graph/chat/intake/provenance/diff UI** | 🟡 Scaffolded (builds; live WS refresh; demo-mode fixtures) |
| **Frontend data layer (`src/lib/types.ts`, `api.ts`, `fixtures.ts`)** | ✅ Implemented (camelCase API mirror + snake→camel client) |
| **Frontend gates: `npm run lint` (tsc), `npm run test`, `npm run build`** | ✅ Green (8 vitest tests pass) |
| **Frontend governance panels wired to live endpoints** | ❌ Pending (metrics/approve render from fixtures) |
| **Backend tests (pytest)** | ✅ 29 pure-logic tests; ruff/black still not configured |

---

## 9. How to Run (as built)

```powershell
cd backend
docker compose up -d                 # start Postgres + pgvector
pip install -r requirements.txt      # Python 3.11+; first run downloads the fastembed model

# Local pipeline (no Azure needed):
python -m scripts.run_ingest --all                 # clone -> chunk -> JSONL
python -m scripts.load_vectors --all               # embed + load into pgvector
python -m scripts.detect_conflicts --all           # duplicate/conflict edges
python -m scripts.search "how do I build garnet"   # sanity-check retrieval
python -m pytest tests -q                          # 29 pure-logic tests

# API:
uvicorn app.main:app --reload --port 8000          # Swagger at /docs

# Agents (/chat, /propose) + AI doc summaries use Azure OpenAI by default — set in .env:
#   AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_CHAT_DEPLOYMENT
# ...or run the agents offline with the deterministic fake (no Azure):
#   $env:CHAT_PROVIDER="fake"   # /chat and /propose then work without Azure
# The verification sandbox (POST /verify) needs Docker running locally.

# Agent-layer tests (offline; no Azure, no Postgres):
pip install -r requirements-dev.txt
python -m pytest
```

```powershell
cd frontend
npm install                          # first run downloads deps
npm run dev                          # Vite dev server at http://localhost:5173

# Quality gates:
npm run lint                         # tsc --noEmit (typecheck)
npm run test                         # vitest (fixture/contract tests)
npm run build                        # production build

# Optional: point at a non-default API with VITE_API_URL (defaults to
# http://localhost:8000). With the backend down, the UI runs in demo mode
# using src/lib/fixtures.ts.
```

---

## 10. Guidance for the Planning Docs

When reading the other docs, apply these corrections:
- **Storage** is Postgres + pgvector (one instance), **not** SQLite + Chroma/FAISS.
- **Embeddings** default to **local fastembed**; Azure is optional for embeddings.
  Agent **chat** defaults to Azure (503 if unset) but also has an offline
  deterministic `CHAT_PROVIDER=fake` provider for dev/tests/demo.
- **Agents** are built with **LangGraph**, not a hand-rolled orchestrator loop; the
  `/propose` path has a no-evidence short-circuit and a final deterministic evidence gate.
- The **API surface** is §4 above (README §8B): it now includes the governance
  routes (`/proposals/:id`, approve/rollback, `/metrics`, provenance), `/verify`,
  async ingest + `/jobs/:id`, and `WS /stream`. Only `/ingest/refresh` is pending.
- **Contracts** are snake_case core models + camelCase API DTOs + agent schemas +
  governance contracts. The frontend `frontend/src/lib/types.ts` mirrors the
  camelCase API; the client and `governance/serialize.py` deep-convert snake→camel.
  There is still no single frozen camelCase `models/` package on the backend.
- The **frontend is scaffolded and buildable** and live-refreshes over `WS /stream`;
  the **governance/metrics/conflict/sandbox backends now exist**. The remaining
  frontend work is wiring the approve/metrics/provenance panels from fixtures to
  the live endpoints.
