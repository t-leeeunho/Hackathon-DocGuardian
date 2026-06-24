# DocGuardian AI — Implementation Status (As-Built)

> **Snapshot date:** 2026-06-23. This document records what is **actually built**
> in the backend today, versus what the planning docs describe. When a planning
> doc disagrees with this file, **this file reflects reality** (it is derived
> directly from the committed code). The locked product target is README §10.

---

## 1. Summary

The **backend ingestion → processing → embedding → retrieval → agent** pipeline is
implemented and runs locally. The HTTP API (README §8B) is a thin FastAPI wrapper
over verified CLI logic. **No frontend exists yet.** Governance (ACL, approval,
provenance, rollback), metrics, the verification sandbox, duplicate/conflict
detection, and live WebSocket updates are **not implemented yet** — they remain
planned (README §6, §10.6–10.7).

---

## 2. Locked Stack (README §10) — and what's wired up

| Area | Locked choice | Built today? |
| --- | --- | --- |
| Backend | Python + FastAPI, Pydantic v2 | ✅ Yes |
| Storage | **Single PostgreSQL** (metadata + graph + audit/provenance) | ✅ Postgres tables: `documents`, `chunks`, `edges` (audit/approval/provenance tables **not yet**) |
| Vector index | **pgvector** in the same Postgres | ✅ `chunks.embedding VECTOR(dim)` + HNSW cosine index |
| Embeddings | Provider-abstracted; **local fastembed default**, Azure optional | ✅ `LocalEmbeddingProvider` (BAAI/bge-small-en-v1.5, 384-dim) / `AzureEmbeddingProvider` |
| LLM agents | **Azure OpenAI** chat (one deployment), two agents | ✅ Curator + Guardian via **LangGraph**; Azure **default** (503 if unset), `CHAT_PROVIDER=fake` offline stand-in |
| Frontend | React + TS + Vite + Tailwind + shadcn/ui + **React Flow (2D)** + **Monaco** | ❌ Not started |
| Verification sandbox | Containerized, real (README §10.6) | ❌ Not implemented |
| Governance/auth | Mocked auth + real ACL/approval/provenance on Postgres (README §10.7) | ❌ Not implemented |

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
│   │   ├── graph.py            # LangGraph chat + propose graphs; no-evidence short-circuit + evidence gate
│   │   ├── llm.py              # Chat factory: CHAT_PROVIDER azure|fake (get_chat_llm) + FakeChatLLM + AzureNotConfiguredError
│   │   └── schemas.py          # Citation/Evidence/ProposalDiff/Verification, ChatAnswer, CuratorDraft, GuardianReview, AgentProposal
│   ├── embeddings/
│   │   └── provider.py         # EmbeddingProvider ABC + Local (fastembed) + Azure
│   ├── ingestion/
│   │   ├── git_ingest.py       # sparse/shallow clone + commit metadata -> RawDocument
│   │   └── intake.py           # user drop-off -> same RawDocument path
│   ├── processing/
│   │   └── processor.py        # heading-aware chunk_document() + extract_edges()
│   └── storage/
│       ├── db.py               # Postgres+pgvector connection + init_schema()
│       ├── queries.py          # list_doc_ids, get_document, get_graph (camelCase out)
│       └── vectorstore.py      # upsert_documents/chunks/edges + cosine search
└── scripts/
    ├── run_ingest.py           # ingest -> process -> JSONL under data/_processed/
    ├── load_vectors.py         # embed JSONL chunks + load into pgvector
    ├── add_file.py             # CLI drop-off intake
    └── search.py               # CLI semantic search
```

**Differences from the original plan's assumed layout:**
- `app/models.py` is a **single file**, not a `models/` package.
- `app/main.py` holds **all endpoints**, not per-domain router files (`api/*.py`).
- Storage lives in `app/storage/` (not `app/store/`); there is no separate
  `services/` package — retrieval/dedup/governance services are not yet split out.
- AI provider split: `app/agents/` (chat via LangGraph + Azure) and
  `app/embeddings/` (vectors). There is no `app/ai/providers/` package.
- There is a `scripts/` CLI used to verify the pipeline without the API.
- Dependencies are in `requirements.txt` (no `pyproject.toml`, ruff/black/pytest).

---

## 4. API Surface (as built — README §8B)

Base URL (local): `http://localhost:8000`. CORS allows the Vite dev server
(`http://localhost:5173`, `:3000`).

| Method | Path | Purpose | Notes |
| --- | --- | --- | --- |
| `GET` | `/health` | Liveness + embedding provider/dim | `{status, embeddingProvider, dim}` |
| `GET` | `/search?q=&repo=&k=` | Semantic search (LangChain retriever target) | pgvector cosine; `matches[]` camelCase |
| `POST` | `/documents` | Drop-off intake (upload/paste) | text formats only; `415` for binary; lands under `user/` |
| `GET` | `/tree?namespace=` | File-system tree (left sidebar) | nested `{name,type,path,children?}` |
| `GET` | `/graph?repo=` | Document graph (nodes + edges) | health/size/accessible are **placeholders** today |
| `GET` | `/documents/{docId}` | Single document + its chunks | camelCase |
| `POST` | `/chat` | Curator agent — evidence-backed answer | LangGraph; **503** if Azure not configured |
| `POST` | `/propose` | Curator + Guardian — proposed change | LangGraph; **503** if Azure not configured |

**Not yet implemented** (planned in README §6/§8A.5): `POST /ingest/refresh`,
`GET /proposals/:id`, `POST /proposals/:id/approve`, `GET /metrics`, `WS /stream`.

The API responses are **camelCase** (`docId`, `chunkId`, `headingPath`,
`lineRange`, `commitSha`) — implemented as dedicated response DTOs in `main.py`
and camelCase dicts in `queries.py`.

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
   `confidence`, `needs_human_review`), `CuratorDraft` (drafting surface), and
   `GuardianReview` (judgment surface) — plus the richer response contract
   `AgentProposal` aligned with README §8A.4 (`proposal_id`, `action`,
   `target_doc_id`, `source_doc_ids`, `diff{}`, `draft`, `citations`, `evidence[]`,
   `confidence`, `risk_level`, `conflicts_with`, `verification{}`, Guardian fields
   `recommendation`/`guardian_reasoning`/`uncertainty`, `proposed_by`, `created_at`).
   New `Evidence`, `ProposalDiff`, and `Verification` sub-models support it.

> `AgentProposal` now carries the README §8A.4 fields (`proposal_id`,
> `source_doc_ids`, `diff{}`, `evidence[]`, `verification{}`), but they are assembled
> **deterministically by the graph** from retrieved rows — the model only fills the
> lean `CuratorDraft`/`GuardianReview`, never provenance. `verification` stays `null`
> until the P4 sandbox runs.

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
- **Storage** (`storage/`): Postgres `documents`/`chunks`/`edges`; `chunks.embedding`
  is a pgvector column with an HNSW cosine index; upserts use `ON CONFLICT` for
  idempotency; search is `1 - (embedding <=> q)` with optional `doc_id` prefix
  filter by `shortName`.

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
| Richer `AgentProposal` (`proposalId`/`sourceDocIds`/`diff`/`evidence`/`verification`) | ✅ Implemented (`verification` null until P4 sandbox) |
| Offline fake chat provider (`CHAT_PROVIDER=fake`) + no-evidence short-circuit + evidence gate | ✅ Implemented |
| CLI tooling (`run_ingest`, `load_vectors`, `add_file`, `search`) | ✅ Implemented |
| **Duplicate/conflict detection** (score ≥ 0.92 / ≥ 0.85 edges) | ❌ Pending |
| **Node health / freshness scoring** | ❌ Pending (hardcoded `green`) |
| **Governance: ACL, approval flow, provenance, rollback** | ❌ Pending |
| **Metrics dashboard + `/metrics`** | ❌ Pending |
| **Verification sandbox** | ❌ Pending |
| **WebSocket `/stream`, `/ingest/refresh`, proposal apply** | ❌ Pending |
| **Frontend (entire)** | ❌ Pending |
| **Dev tooling** | ⚠️ Partial — `pytest` configured for `backend/tests/` (agent layer); ruff/black still not configured |

---

## 9. How to Run (as built)

```powershell
cd backend
docker compose up -d                 # start Postgres + pgvector
pip install -r requirements.txt      # Python 3.11+; first run downloads the fastembed model

# Local pipeline (no Azure needed):
python -m scripts.run_ingest --all                 # clone -> chunk -> JSONL
python -m scripts.load_vectors --all               # embed + load into pgvector
python -m scripts.search "how do I build garnet"   # sanity-check retrieval

# API:
uvicorn app.main:app --reload --port 8000          # Swagger at /docs

# Agents (/chat, /propose) use Azure OpenAI by default — set in .env:
#   AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_CHAT_DEPLOYMENT
# ...or run the agents offline with the deterministic fake (no Azure):
#   $env:CHAT_PROVIDER="fake"   # /chat and /propose then work without Azure

# Agent-layer tests (offline; no Azure, no Postgres):
pip install -r requirements-dev.txt
python -m pytest
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
- The **API surface** is §4 above (README §8B), not the older §8A.5 table.
- **Contracts** are snake_case core models + camelCase API DTOs + agent schemas —
  there is no single frozen camelCase `models/` package or `types.ts` yet.
- **Governance, metrics, verification, conflict detection, and the frontend** are
  **not built yet** — they are the next work, not current behavior.
