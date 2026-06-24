# DocGuardian AI — Copilot Instructions

These instructions apply to **all** Copilot work in this repository. Follow them
unless a more specific `.github/instructions/*.instructions.md` file overrides them
for a path.

## Project context

**DocGuardian AI** is an AI-powered documentation governance platform: it ingests
real engineering docs, detects stale / duplicate / conflicting content, proposes
**evidence-backed** fixes via two LLM agents (Curator + Guardian), and presents
everything in an interactive knowledge graph with human approval, provenance, and
rollback.

- Product spec: `README.md` (architecture + data-contract JSON schemas in §8A).
- As-built backend snapshot: `docs/implementation-status.md` (authoritative when plans disagree).
- Implementation plan: `docs/general-plan.md`, `docs/team-plan.md`, `docs/team/person-1..4-*.md`.
- This is a 4-person hackathon build organized for **parallel work** (see below).

## Golden rules (non-negotiable)

1. **Contracts are coordinated, not assumed.** Today there are four implemented
   model layers: snake_case core contracts in `backend/app/models.py`, camelCase
   API response DTOs in `backend/app/main.py`, agent structured outputs in
   `backend/app/agents/schemas.py`, and the frontend camelCase mirror in
   `frontend/src/lib/types.ts`. Contract changes require director coordination and
   must keep all layers aligned with the camelCase API responses in README §8B.
2. **Stay in your lane, but match the current backend.** The implemented API is
   currently a single `backend/app/main.py` file holding all endpoints, not per-domain
   routers. A future router split is allowed only as a coordinated refactor.
3. **Use real implemented seams.** Ingestion/retrieval run locally with Postgres +
   pgvector and local fastembed embeddings. `/chat` and `/propose` default to Azure
   OpenAI chat and return 503 if Azure is unconfigured; an opt-in deterministic
   `CHAT_PROVIDER=fake` provider (`FakeChatLLM`) runs them offline for dev/tests/demo.

## Stack & versions

- **Backend:** Python **3.11+**, FastAPI, Pydantic **v2**.
- **Frontend:** React + TypeScript + Vite + Tailwind + React Flow (`@xyflow/react`) 2D graph + Monaco (scaffolded; Radix + lucide, no shadcn/ui yet).
- **Storage:** PostgreSQL + **pgvector** in one Postgres instance for metadata, graph edges, and vector index; local dev uses `docker compose up -d` with `pgvector/pgvector:pg16`. Azure-ready storage is future work.
- **Embeddings:** provider-abstracted `EmbeddingProvider`; local fastembed default (`BAAI/bge-small-en-v1.5`, ONNX, 384-dim), swappable to Azure with `EMBEDDING_PROVIDER=azure`.
- **LLM agents:** LangGraph (`langgraph` + `langchain-openai`) with Azure OpenAI chat required for Curator/Guardian.

## Naming & style

- Core backend models in `backend/app/models.py` are **snake_case** Pydantic v2.
- API responses consumed by the frontend are **camelCase** DTOs in `backend/app/main.py`
  and camelCase dictionaries from `backend/app/storage/queries.py`.
- Agent structured outputs live in `backend/app/agents/schemas.py`.
- Prefer clear, typed code. **No `any`** for a contract type in TypeScript once the
  frontend exists. Use type hints in Python. Only comment code that genuinely needs clarification.

## Product invariants (always uphold)

- **Evidence-or-silence.** No AI answer or proposed edit without supporting
  `chunkId`s + `commitSha`s + a `confidence` score. Weak evidence (implemented
  threshold: ~0.45) or no supporting chunk ⇒ the explicit "needs human review" path.
  Never invent sources.
- **Permissions.** Enforce ACLs at retrieval, answer, **and** write. Never surface
  content the user cannot access to any layer.
- **Provenance.** Every governed write records what / who / which agent / why /
  sources / previous version and supports rollback when governance is implemented.
- **Idempotency.** Re-processing an unchanged `contentHash` is a no-op.
- **Cost.** ≤2 LLM calls per proposal (`retrieve → curator → guardian`); the
  deterministic retrieve node uses **no** LLM.

## Quality gate (run before declaring work done)

- Current backend has no `pyproject.toml`, ruff, black, pytest, or tests configured.
  Verify backend changes with the implemented CLI/API path: `python -m scripts.run_ingest --all`,
  `python -m scripts.load_vectors --all`, `python -m scripts.search "<query>"`, and
  `uvicorn app.main:app --reload` with Swagger at `/docs`.
- Frontend gates (`npm run lint`, `npx tsc --noEmit`, `npm run test`) apply once the
  frontend is set up.
- Adding ruff/black/pytest is recommended for future backend work, but do not claim
  those are the current required gate.

## Commits

- Use **Conventional Commits** (`feat:`, `fix:`, `docs:`, `chore:`, `refactor:`,
  `test:`, `style:`). Keep the summary ≤72 chars, imperative mood.
- Use the `commit-and-push` skill to stage, message, and push.
- Never commit secrets. Never force-push or rewrite published history without
  explicit confirmation.

## Agents & skills available

- **Agents** (`.github/agents/`): `director` (architecture, contracts, integration),
  `frontend`, `retrieval`, `ai-orchestration`, `governance` (the four build roles).
- **Skills** (`.github/skills/`): `commit-and-push`, `ingest-repo` (sparse-clone a
  doc source), `run-checks` (lint+test both stacks once configured), `contract-sync`,
  `seed-demo-fixtures` (planted stale/dup/conflict docs), `new-endpoint` (scaffold a
  route + contract + TS type + fixture consistently once the target structure exists).

> When in doubt about current behavior, consult `docs/implementation-status.md` first;
> for planned scope or ownership, consult the relevant `docs/` plan or ask the `director`.
