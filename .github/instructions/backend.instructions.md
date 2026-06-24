---
applyTo: "backend/**"
---

# Backend Instructions (Python + FastAPI)

Applies to all files under `backend/`. Read alongside `.github/copilot-instructions.md`
and `docs/implementation-status.md` for the current as-built backend.

## Language & style

- Target **Python 3.11+**. Use modern syntax (`X | None`, `list[str]`, `match` where it helps).
- **Type-hint everything** — function signatures, return types, dataclass/Pydantic fields.
- Current repo has no configured `pyproject.toml`, ruff, black, pytest, or tests. Use
  clear, typed code; adding black/ruff/pytest is recommended as future tooling, not
  a current enforced gate.
- Keep functions small and pure where possible; push side effects to the edges.
- Only add comments that clarify non-obvious intent.

## FastAPI structure

- **As built today:** `app/main.py` holds all endpoints and camelCase API response DTOs.
  There are no per-domain `api/*.py` router files yet. If the backend is later split
  into routers, do it as a coordinated refactor that preserves the current API.
- Core layer contracts live in the single file `app/models.py` (not a `models/` package).
  API response DTOs live in `app/main.py`; agent structured outputs live in
  `app/agents/schemas.py`.
- Prefer `async def` handlers when introducing new request paths, but note the current
  endpoints are thin synchronous wrappers over CLI-verified ingestion/retrieval logic.
- Use dependency seams that exist today: `app/storage/`, `app/embeddings/`, `app/agents/`,
  and `scripts/`. Do not refer to non-existent `app/store/`, `app/services/`, or
  `app/ai/providers/` packages as current code.

## Pydantic v2 contracts

- `app/models.py` contains **snake_case** core contracts (`RawDocument`, `DocChunk`,
  `GraphEdge`, `EdgeType`) for ingestion/processing. There is no camelCase
  `alias_generator=to_camel` on these core models.
- API responses are **camelCase** through DTOs in `app/main.py` and dicts from
  `app/storage/queries.py` (`docId`, `chunkId`, `headingPath`, `lineRange`, `commitSha`).
- Agent structured outputs are in `app/agents/schemas.py` (`ChatAnswer`,
  `AgentProposal`, citations, Guardian fields). Coordinate changes across all affected
  layers and the future frontend types.

## Services, providers & agents

- Storage is **PostgreSQL + pgvector** in one local Postgres instance started with
  `docker compose up -d` (`pgvector/pgvector:pg16`). It stores metadata, chunks,
  graph edges, and the vector index; Azure-ready storage is future work.
- Embeddings go only through `EmbeddingProvider`: local fastembed default
  (`BAAI/bge-small-en-v1.5`, ONNX, 384-dim) or Azure with `EMBEDDING_PROVIDER=azure`.
- Agents are implemented with **LangGraph** (`langgraph` + `langchain-openai`):
  `/chat` is `retrieve → curator` (1 LLM call) and `/propose` is
  `retrieve → curator → guardian` (2 LLM calls). The retrieve node is deterministic
  pgvector search and uses no LLM.
- Azure OpenAI chat is required for `/chat` and `/propose`; the endpoints return 503
  if `AZURE_OPENAI_*` chat settings are missing. Do not assume a `FakeLLMProvider`
  or local chat fallback exists.

## Invariants in code

- Carry `commitSha`/`commit_sha` through every record (provenance). Skip re-processing
  when `contentHash`/`content_hash` is unchanged (idempotency).
- Enforce ACLs at retrieval, answer, and write when governance is implemented; never
  return inaccessible content.
- Every proposal/answer carries evidence + confidence; weak evidence (implemented
  threshold: ~0.45) ⇒ needs-human-review.

## Verification & secrets

- Verify the current backend with the implemented local pipeline:
  `cd backend`, `docker compose up -d`, `pip install -r requirements.txt`,
  `python -m scripts.run_ingest --all`, `python -m scripts.load_vectors --all`,
  `python -m scripts.search "<query>"`, then `uvicorn app.main:app --reload` and
  check Swagger at `/docs`.
- Azure env (`AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`,
  `AZURE_OPENAI_CHAT_DEPLOYMENT`) is needed only for `/chat` and `/propose`.
- Never hard-code secrets or API keys — use environment variables / `app/config.py`.
