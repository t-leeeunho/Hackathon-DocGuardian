# Contributing to DocGuardian AI

Welcome! This guide explains **how we work** so four people can build DocGuardian AI
in parallel with Copilot without stepping on each other. For the full plan, read
[`docs/`](docs/README.md); for the product spec, read [`README.md`](README.md).
For the current implemented backend, read [`docs/implementation-status.md`](docs/implementation-status.md).

> **Status:** backend ingestion → processing → embedding → retrieval → agent API is
> implemented locally. No frontend exists yet. Governance (ACL, approval,
> provenance, rollback), metrics, verification sandbox, duplicate/conflict detection,
> and live WebSocket updates are still planned.

---

## TL;DR — the three rules that make parallel work possible

1. **Contracts-first, but match the implemented layers.** Core contracts live as
   snake_case Pydantic models in `backend/app/models.py`; API response DTOs in
   `backend/app/main.py` are camelCase; agent structured outputs live in
   `backend/app/agents/schemas.py`. There is no frontend `types.ts` yet.
2. **Use the real seams.** Ingestion/search run locally with Postgres + pgvector and
   local fastembed embeddings. `/chat` and `/propose` default to Azure OpenAI chat and
   return 503 if Azure is unconfigured; an opt-in `CHAT_PROVIDER=fake` provider runs
   them offline for dev/tests/demo.
3. **Stay in your lane while respecting current structure.** Today all endpoints are
   in `backend/app/main.py`, storage is `backend/app/storage/`, and AI code is split
   between `backend/app/embeddings/` and `backend/app/agents/`. A per-domain router
   split can be an intended future convention, but it is not the current layout.

---

## Roles & ownership

| Person | Role | Detailed plan |
| --- | --- | --- |
| P1 | Frontend & Demo Experience | [`docs/team/person-1-frontend.md`](docs/team/person-1-frontend.md) |
| P2 | Retrieval & Document Intelligence | [`docs/team/person-2-retrieval.md`](docs/team/person-2-retrieval.md) |
| P3 | Agent Orchestration & AI Reasoning | [`docs/team/person-3-ai-orchestration.md`](docs/team/person-3-ai-orchestration.md) |
| P4 | Governance, Verification & Metrics | [`docs/team/person-4-governance.md`](docs/team/person-4-governance.md) |

The full file/directory ownership table is in
[`docs/team-plan.md`](docs/team-plan.md) §2, but check
[`docs/implementation-status.md`](docs/implementation-status.md) first when plan and
code disagree.

---

## Workflow

1. **Read** [`docs/implementation-status.md`](docs/implementation-status.md) for the
   as-built snapshot, then [`docs/general-plan.md`](docs/general-plan.md),
   [`docs/team-plan.md`](docs/team-plan.md), and your `docs/team/person-N` plan.
2. **Work from current reality:** backend endpoints are in `app/main.py`; CLI scripts
   under `backend/scripts/` verify ingestion, vector loading, and search.
3. **Build in parallel:** each person implements their slice against the real contracts
   and seams, coordinating any cross-layer contract change with the director.
4. **Integrate:** keep Postgres + pgvector as the locked local storage choice; add
   frontend, governance, metrics, verification, and live updates as planned work.
5. **Demo polish:** seed 1–2 repos with planted stale/duplicate/conflict fixtures,
   wire metrics/streaming when implemented, accessibility pass, rehearse.

Milestones are defined in [`docs/team-plan.md`](docs/team-plan.md) §4, and the
shared (general) TODOs in §5.

---

## Tech stack

- **Backend:** Python 3.11+, FastAPI, Pydantic v2.
- **Frontend (when built):** React + TypeScript + Vite + Tailwind + shadcn/ui + React Flow (2D) + Monaco.
- **Storage:** PostgreSQL + pgvector in one Postgres instance for metadata, graph
  edges, and vector index; local dev uses `docker compose up -d` with `pgvector/pgvector:pg16`.
- **Embeddings:** provider-abstracted; local fastembed default
  (`BAAI/bge-small-en-v1.5`, ONNX, 384-dim), Azure optional via `EMBEDDING_PROVIDER=azure`.
- **LLM agents:** LangGraph (`langgraph` + `langchain-openai`) with Azure OpenAI chat
  required for Curator/Guardian.

Conventions are enforced automatically by Copilot via
[`.github/copilot-instructions.md`](.github/copilot-instructions.md) and the
path-specific files in [`.github/instructions/`](.github/instructions/).

---

## Backend run instructions (as built)

```powershell
cd backend
docker compose up -d
pip install -r requirements.txt
python -m scripts.run_ingest --all
python -m scripts.load_vectors --all
python -m scripts.search "how do I build garnet"
uvicorn app.main:app --reload
```

Swagger is available at `/docs` once Uvicorn is running. Azure env
(`AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_CHAT_DEPLOYMENT`) is
only needed for `/chat` and `/propose`; local ingestion, vector loading, search, tree,
graph, and document endpoints do not require Azure with the default local embedding provider.

---

## Copilot agents & skills

This repo ships Copilot **agents** and **skills** to speed up and standardize the build.

**Agents** ([`.github/agents/`](.github/agents/)) — invoke with `@<name>`:
- `@director` — architecture, contracts, integration, demo coordination.
- `@frontend`, `@retrieval`, `@ai-orchestration`, `@governance` — the four build roles.

**Skills** ([`.github/skills/`](.github/skills/)):
- `ingest-repo` — sparse/shallow clone a documentation source.
- `run-checks` — run configured checks once backend/frontend gates exist.
- `contract-sync` — coordinate contract changes across affected model/API/frontend layers.
- `seed-demo-fixtures` — generate planted stale/duplicate/conflict docs for the demo.
- `new-endpoint` — scaffold a new API route + contract + TS type + fixture consistently once the target structure exists.
- `commit-and-push` — stage, write a Conventional Commit message, and push.

---

## Quality gate (before every PR)

- **Current backend:** no `pyproject.toml`, ruff, black, pytest, or tests are configured.
  Verify with the implemented CLI/API path: run ingest, load vectors, search, start
  `uvicorn app.main:app --reload`, and check Swagger at `/docs`.
- **Frontend:** eslint/tsc/vitest gates apply when the frontend is set up.
- **Recommended future tooling:** add ruff, black, pytest, and frontend lint/type/test
  scripts before treating them as mandatory PR gates.
- Cover edge cases (empty results, low confidence, inaccessible docs, unchanged
  content, deleted docs), not just the happy path.

## Commits & PRs

- **Conventional Commits** (`feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`,
  `style:`); summary ≤72 chars, imperative mood. The `commit-and-push` skill helps.
- Keep PRs scoped to your ownership area. A PR touching contracts or another person's
  files needs director sign-off.
- Never commit secrets. Never force-push shared history without explicit agreement.

## Definition of Done

A slice is done when it honors the implemented contracts and planned invariants,
passes the checks that actually exist, works against the relevant real dependency,
and handles edge cases. See [`docs/team-plan.md`](docs/team-plan.md) §7.

---

## Product invariants (never violate)

- **Evidence-or-silence:** no AI answer/edit without supporting chunk IDs + commit
  SHAs + confidence; weak evidence (implemented threshold: ~0.45) ⇒ human review.
  Never invent sources.
- **Permissions:** enforce ACLs at retrieval, answer, and write when governance is implemented.
- **Provenance:** every governed write is logged and reversible when governance is implemented.
- **Idempotency:** unchanged `contentHash`/`content_hash` ⇒ no re-processing.
- **Cost:** ≤2 LLM calls per proposal; deterministic retrieval uses no LLM.
