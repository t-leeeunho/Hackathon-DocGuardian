---
applyTo: "backend/**"
---

# Backend Instructions (Python + FastAPI)

Applies to all files under `backend/`. Read alongside `.github/copilot-instructions.md`.

## Language & style

- Target **Python 3.11+**. Use modern syntax (`X | None`, `list[str]`, `match` where it helps).
- **Type-hint everything** — function signatures, return types, dataclass/Pydantic fields.
- Format with **black** (line length 88); lint with **ruff** (`E`, `F`, `I`, `UP`, `B`).
- Keep functions small and pure where possible; push side effects to the edges.
- Only add comments that clarify non-obvious intent.

## FastAPI structure

- **One router file per domain**, and each person owns only their own router file
  (`api/ingest.py`, `api/search.py`, `api/documents.py`, `api/chat.py`, `api/graph.py`,
  `api/proposals.py`, `api/metrics.py`, `api/stream.py`). `app/main.py` wires routers
  **once** in Phase 0 and is director-owned afterward — don't edit it.
- Endpoints accept/return the **Pydantic contract models** from `app/models/**`
  (never ad-hoc dicts). Don't redefine a contract locally.
- Prefer `async def` handlers; keep heavy/blocking work in the background job queue,
  not on the request path.
- Use dependency injection for services (retrieval, store, providers, governance).

## Pydantic v2 contracts

- Contract models live in `app/models/**` and are **frozen** — do not add or change
  fields there outside a director-led `contract-sync` change.
- Models serialize to **camelCase** and accept snake_case or camelCase input:
  ```python
  from pydantic import BaseModel, ConfigDict
  from pydantic.alias_generators import to_camel

  class DocChunk(BaseModel):
      model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
      chunk_id: str
      doc_id: str
      heading_path: list[str]
  ```

## Services, providers & the orchestrator

- Put deterministic work (search, dedup, git metadata, ACL, sandbox) in **services**
  behind interfaces — these cost **no** LLM quota.
- LLM/embedding access goes **only** through `LLMProvider` / `EmbeddingProvider`
  (default Azure OpenAI, with fakes). Read config from env via `app/config.py`.
- The **orchestrator uses no LLM** — it routes and calls services, invoking the
  Curator/Guardian agents only when reasoning/drafting is required.
- Persist through the `Store` / `VectorIndex` interfaces; develop against
  `InMemoryStore` / fakes, swap to SQLite/real at integration.

## Invariants in code

- Carry `commitSha` through every record (provenance). Skip re-processing when
  `contentHash` is unchanged (idempotency).
- Enforce ACLs at retrieval, answer, and write; never return inaccessible content.
- Every proposal/answer carries evidence + confidence; `< 0.5` ⇒ needs-human-review.

## Testing & secrets

- Write `pytest` tests for the modules you touch; include edge cases (empty results,
  unchanged content, deleted docs, low confidence, ACL-denied).
- Never hard-code secrets or API keys — use environment variables / `app/config.py`.
- Run the quality gate (`ruff check`, `black --check`, `pytest -q`) before finishing.
