# Person 2 — Retrieval & Document Intelligence

Person 2 owns the deterministic retrieval pipeline that turns raw repository documentation into searchable, graph-aware, embedded knowledge for DocGuardian AI.

> **As-built status (2026-06-24):** core retrieval pipeline **and** duplicate/
> conflict detection (`app/processing/conflicts.py`, `duplicate-of` ≥0.92 /
> `conflicts-with` ≥0.85) are implemented, plus atomic intake and doc summaries
> (`summarize.py`). See [../implementation-status.md](../implementation-status.md).

## Mission

Person 2's mission is to build and maintain the retrieval half of deterministic Layers 1–3: ingestion, processing, embeddings, vector indexing, search, duplicate detection, and conflict seeding. As built today, sparse/shallow git repository checkouts and user drop-off intake become snake_case `RawDocument`, `DocChunk`, and structural `GraphEdge` records, then are embedded into Postgres + pgvector for cosine search. The pipeline consumes no LLM quota; embeddings use the `EmbeddingProvider` ABC with local fastembed (`BAAI/bge-small-en-v1.5`, 384-dim, ONNX, auto-detected dim) by default and Azure only when `EMBEDDING_PROVIDER=azure`.

Duplicate detection and conflict seeding are now implemented in
`app/processing/conflicts.py` (cross-document chunk cosine ≥ 0.92 → `duplicate-of`,
≥ 0.85 → `conflicts-with`), runnable as a batch (`scripts/detect_conflicts.py`) or
incrementally on intake. Structural `references` edges also exist.

## Scope — What You Own

Person 2 owns the full path from repository clone metadata to retrieval results:

| Area | Owned paths | Responsibility |
| --- | --- | --- |
| Ingestion | `backend/app/ingestion/git_ingest.py`, `backend/app/ingestion/intake.py` | Sparse/shallow clone, sparse-checkout, repository refresh, commit metadata extraction, `RawDocument` creation, and user drop-off intake. Refresh event models (`DocumentAdded` / `DocumentChanged` / `DocumentDeleted`) are not built yet. |
| Processing | `backend/app/processing/processor.py` | Markdown normalization, YAML front-matter stripping, command/code preservation, heading-aware and fence-aware chunking, line range calculation, placeholder char ranges, and structural link/reference extraction. |
| Embeddings | `backend/app/embeddings/provider.py` | `EmbeddingProvider` ABC, local fastembed default, Azure optional provider, batch embedding for vector load/search. |
| Storage + vector search | `backend/app/storage/vectorstore.py`, `backend/app/storage/db.py`, `backend/app/storage/queries.py` | Single Postgres instance with pgvector; `documents`, `chunks`, and `edges` tables; `chunks.embedding VECTOR(dim)` with HNSW cosine index; `ON CONFLICT` upserts; `1 - (embedding <=> q)` cosine search. |
| API surface | `backend/app/main.py` | Current API lives in one FastAPI file: `GET /search` and `POST /documents` are implemented here. There are no per-domain `api/ingest.py` or `api/search.py` router files yet; a future split can move thin routers out of `main.py`. |
| CLI tooling | `backend/scripts/run_ingest.py`, `backend/scripts/load_vectors.py`, `backend/scripts/search.py`, `backend/scripts/add_file.py` | Verified local ingestion → processing → JSONL, vector loading, semantic search, and user file/paste intake workflows. |
| Dedup/conflict services | `backend/app/processing/conflicts.py`, `backend/app/processing/summarize.py` | Implemented: cross-doc duplicate/conflict edge detection (≥0.92 / ≥0.85) + one-line doc summaries (AI + extractive). |

Concrete deliverables inside that scope:

- [x] Implement repository source loading from `repos.config.json` entries.
- [x] Clone configured sources into `data/<repo-short>` using sparse/shallow git commands.
- [x] Emit deterministic `RawDocument` records with `commit_sha`, `commit_date`, `fetched_at`, and `content_hash`.
- [x] Convert each `RawDocument` into stable `DocChunk` records and structural `references` `GraphEdge` records.
- [x] Embed chunks through `EmbeddingProvider` using local fastembed by default, with Azure swappable by configuration.
- [x] Upsert documents, chunks, and edges into Postgres + pgvector using `ON CONFLICT` for idempotency.
- [x] Return search matches with cosine scores in `[0,1]` and citation metadata via `GET /search`.
- [ ] Generate `duplicate-of` candidate edges for chunk pairs from different `docId`s with score `>= 0.92`.
- [ ] Generate `conflicts-with` candidate edges for score `>= 0.85` plus divergent commands/values.
- [ ] Add an incremental-refresh API endpoint (`POST /ingest/refresh`) and explicit added/changed/deleted event output.

## What You Must NOT Touch

These files/directories are frozen or owned by other people. Person 2 should request director changes instead of editing them directly.

| Do not touch | Why |
| --- | --- |
| `backend/app/models.py` contract changes without coordination | Core Pydantic contracts are a single snake_case file today (`RawDocument`, `DocChunk`, `GraphEdge`, `EdgeType`). If fields need changes, coordinate because API DTOs and frontend assumptions must stay aligned. |
| `frontend/src/lib/types.ts` | No mirrored frontend contract exists yet in this backend slice; future TypeScript types must stay aligned with API DTOs. |
| `backend/app/main.py` route ownership without coordination | Current `GET /search` and `POST /documents` live here. Person 2 can document needs for a future router split, but app-level endpoint registration is director-owned. |
| Future router/service split files | `backend/app/api/ingest.py`, `backend/app/api/search.py`, `backend/app/services/retrieval.py`, and `backend/app/services/dedup_conflict.py` do not exist yet. Create or move them only through an agreed refactor. |
| Other people's directories | Do not edit P1 frontend implementation, P3 agent/orchestrator/provider code outside agreed interfaces, or P4 governance/store/sandbox services. |

If integration requires a contract field, a `main.py` route registration, a new store method, or a frontend type adjustment, document the request and hand it to the director. Continue against the current CLI/API path until the shared interface is updated.

## Inputs (Consumed, Mocked) & Outputs (Produced)

| Contract / artifact | Direction for P2 | Real or mocked by milestone | Source / destination | Notes |
| --- | --- | --- | --- | --- |
| `repos.config.json` | Consumed | Real | `backend/repos.config.json`, read by `app.config` | Four repos are configured: `garnet`, `playwright`, `onnxruntime`, and `vscode`, each with `shortName`, `sparsePaths`, and `docGlobs`. |
| Git repository checkout | Consumed | Real from the start | `data/<repo-short>` | Uses `git clone --depth 1 --filter=blob:none --sparse --branch <branch>` and sparse checkout; no GitHub API dependency, no tokens, no deep clone. |
| `RawDocument` | Produced | Real | Ingestion → processing/storage | Core model is snake_case in `app/models.py`. One record per selected file includes stable `doc_id`, repo/path/branch, raw UTF-8 content, byte size, commit metadata, `fetched_at`, and `content_hash`. |
| `DocumentAdded` / `DocumentChanged` / `DocumentDeleted` | Produced | Not built yet | Future refresh → processing / graph | Explicit refresh event models and an incremental-refresh API are still pending. Current refresh updates the shallow checkout and re-emits raw documents through CLI processing. |
| `DocChunk` | Produced | Real | Processing → embeddings/search/storage | Stable `chunk_id`, inherited `doc_id`/`commit_sha`/`commit_date`, heading path, source `line_range`, placeholder `char_range`, `contains_commands`, word-count `token_count`, and chunk `content_hash`. |
| `GraphEdge` (`references`) | Produced | Real | Processing → `edges` table / graph queries | Link extractor emits structural `references` edges only from same-repo markdown links. |
| `GraphEdge` (`duplicate-of`) | Produced | ✅ implemented | `app/processing/conflicts.py` → graph/P3 | Chunk pairs from different `docId`s with score `>= 0.92`; edge weight equals score. |
| `GraphEdge` (`conflicts-with`) | Produced | ✅ implemented | `app/processing/conflicts.py` → graph/P3 | Similar chunks with score `>= 0.85`; edge weight equals score. |
| `EmbeddingProvider` | Consumed | Real | `app/embeddings/provider.py` | ABC with `LocalEmbeddingProvider` as default fastembed/ONNX provider; `AzureEmbeddingProvider` when `EMBEDDING_PROVIDER=azure`. |
| Vector record | Produced internally | Real | Embeddings → Postgres `chunks` table | Keyed by `chunk_id`; includes vector, text, metadata, heading path, line range, commit SHA. Vector dimension is `VECTOR(dim)` from the active provider. |
| `SearchResult` / search matches | Produced | Real | `GET /search`, `scripts/search.py`, P3 retrieval node | API exposes camelCase DTOs from `main.py`; storage/search internals are snake_case. Results are sorted by pgvector cosine distance and scored as `1 - (embedding <=> q)`. |

Minimal contract shapes to keep in mind while building fixtures and tests:

```jsonc
// DocChunk shape in API-facing camelCase terms; core app/models.py fields are snake_case
{
  "chunkId": "playwright/docs/src/intro.md#installation#0",
  "docId": "playwright/docs/src/intro.md",
  "repo": "microsoft/playwright",
  "headingPath": ["Getting Started", "Installation"],
  "ordinal": 0,
  "text": "npm init playwright@latest ...",
  "tokenCount": 612,
  "lineRange": [12, 41],
  "charRange": [0, 1242], // placeholder today, not true source offsets
  "containsCommands": true,
  "commitSha": "a1b2c3...",
  "commitDate": "2026-05-18T14:22:07Z",
  "contentHash": "sha256:..."
}
```

```jsonc
// Search response shape in API-facing camelCase terms
{
  "query": "how do I run playwright tests in CI",
  "matches": [
    {
      "chunkId": "playwright/docs/src/ci.md#github-actions#0",
      "docId": "playwright/docs/src/ci.md",
      "score": 0.8917,
      "text": "npx playwright test ...",
      "lineRange": [8, 30],
      "commitSha": "9a8b7c..."
    }
  ]
}
```

## Dependencies & Interfaces With Others

| Person / system | P2 consumes | P2 provides | Milestone expectation |
| --- | --- | --- | --- |
| Director / Phase 0 foundation | `app/models.py`, `app/main.py`, `repos.config.json`, Postgres + pgvector config. | Contract review feedback for `RawDocument`, refresh events, `DocChunk`, `GraphEdge`, and search DTOs. | Core retrieval is implemented; future work should keep snake_case core models and camelCase API DTOs aligned. |
| P3 — Agent Orchestration & AI Reasoning | `EmbeddingProvider` interface and query conventions. | Real search matches for Curator/chat RAG; future duplicate/conflict candidates with chunk IDs and evidence. | P3 can already consume pgvector search through the retrieval node/API; semantic candidate edges are still pending. |
| P4 — Governance, Verification & Metrics | Store/ACL interfaces, graph/document persistence needs, optional permission tags for query-time filtering. | `documents`, `chunks`, structural `references` edges, and future semantic candidate edges. | Current persistence is direct Postgres tables, not a separate P4-managed store. ACL/provenance/governance are pending. |
| P1 — Frontend & Demo Experience | Search and graph expectations through API contracts only. | `/search` results and graph edges indirectly through `main.py` endpoints. | P1 consumes camelCase API DTOs; the frontend is scaffolded. |
| Git CLI / repositories | Sparse/shallow clones, file contents, commit metadata. | Local `data/<repo-short>` working copies and processed JSONL. | Real from the start. Scope aggressively to docs folders to avoid huge checkouts. |
| Embedding backend | Local fastembed by default; Azure embeddings only by config. | Chunk text and metadata for embedding/upsert. | Ingestion/search do not need Azure. Azure is required only if embeddings are explicitly switched or for P3 chat/propose agents. |

Real vs mocked by milestone:

| Milestone | Real | Mocked / fake or pending |
| --- | --- | --- |
| M1 | Contract review, `repos.config.json`, CLI tooling, core models. | Refresh events, duplicate/conflict fixtures. |
| M2 | Sparse/shallow clones, `RawDocument` creation, heading-aware/fence-aware processing, chunking, structural references, local fastembed-backed pgvector search. | Duplicate/conflict candidate logic; true char offsets; chunk overlap. |
| M3 | `GET /search`, `POST /documents`, Postgres + pgvector persistence, real search consumed by agents. | Per-domain router split, ACL filtering, incremental refresh API, governance/provenance tables. |
| M4 | Four configured seed repos (`garnet`, `playwright`, `onnxruntime`, `vscode`) can run through CLI/API path. | Planted duplicate/conflict edges and refresh demo still need implementation. |

## Detailed TODOs

### Phase 0 — Foundation participation

- [x] Review README §8A.2–§8A.4 and align planning docs to the as-built snake_case core models plus camelCase API DTOs.
- [x] Help author or review `RawDocument` shape with `doc_id`, `repo`, `path`, `branch`, `content`, `byte_size`, `encoding` assumptions, commit metadata, `fetched_at`, and `content_hash`.
- [x] Help author or review `DocChunk` shape with heading paths, ordinal values, line ranges, placeholder char ranges, `contains_commands`, inherited `commit_sha`/`commit_date`, and stable chunk `content_hash` values.
- [x] Help author or review `GraphEdge` fixtures for `references` with the `from` / `to` / `type` / `weight` quartet matching frontend graph needs.
- [x] Help author or review search response DTOs so P3 can build Curator/chat RAG over real retrieval.
- [x] Validate local fastembed provider behavior and dimension detection through `EmbeddingProvider`.
- [x] Confirm Postgres + pgvector has enough operations for upsert-by-`chunk_id`, search, and metadata lookup through `vectorstore.py`.
- [x] Set up expected local data layout: `data/<repo-short>` working copies and `data/_processed/<shortName>/` JSONL outputs.
- [x] Configure initial `repos.config.json` entries for `garnet`, `playwright`, `onnxruntime`, and `vscode`.
- [ ] Agree with the director on if/when to split `GET /search` and future `POST /ingest/refresh` out of `backend/app/main.py` into router files.

### Core Build

#### Ingestion (Layer 1)

- [x] Implement source loading from `repos.config.json` with validation for `repo`, `shortName`, `url`, `branch`, `sparsePaths`, `docGlobs`, and `refreshIntervalMinutes`.
- [x] Derive safe local checkout names under `data/<repo-short>` using `shortName`.
- [x] Run the metadata-only clone procedure for new repos:

  ```powershell
  git clone --depth 1 --filter=blob:none --sparse --branch <branch> <url> data\<repo-short>
  git sparse-checkout set <sparsePaths>
  ```

- [x] Keep sparse-checkout scoped to configured paths; current repos use `sparsePaths` and `docGlobs` from `repos.config.json`.
- [x] Enumerate selected documentation files deterministically and filter by configured `docGlobs`.
- [x] Extract per-file commit metadata with `git log -1 --format=%H%x1f%an%x1f%ae%x1f%cI -- <path>` and parse `commit_sha`, `commit_author`, `commit_email`, and `commit_date`.
- [x] Compute `byte_size`, `fetched_at` via model default, and `content_hash` as `sha256` over raw UTF-8 bytes.
- [x] Build one `RawDocument` per selected file with stable `doc_id` format `<repo-short>/<path>`.
- [x] Implement checkout refresh with `git fetch --depth 1 origin <branch>` plus `git reset --hard origin/<branch>`.
- [ ] Emit explicit `DocumentAdded`, `DocumentChanged`, and `DocumentDeleted` events from refresh; route deleted documents to stale/broken node handling.

#### Processing (Layer 2)

- [x] Build pure processing functions that return identical output for identical `RawDocument` input.
- [x] Strip YAML/front-matter before sectioning.
- [x] Preserve headings and fenced code blocks; headings inside fences are ignored.
- [x] Resolve same-repo relative markdown links ending in `.md` or `.mdx` to target `doc_id` values.
- [x] Record heading text and heading hierarchy for chunks.
- [x] Implement heading-aware chunking with target size around 800 approximate tokens and split oversized sections (>~1000 words) by blank-line paragraphs.
- [ ] Implement approximately 80-token inter-chunk overlap; current implementation has no overlap.
- [x] Ensure chunks inherit `doc_id`, `repo`, `commit_sha`, `commit_date`, heading path, and source line range from the parent document.
- [x] Generate stable `chunk_id` values using `doc_id`, heading slug, and ordinal.
- [x] Detect fenced code blocks and set `contains_commands` when chunks contain triple-backtick or tilde fences.
- [x] Compute chunk `content_hash` over chunk text.
- [ ] Compute true source `char_range`; current value is the placeholder `(0, len(block))`.

#### Link extractor

- [x] Parse explicit inline markdown links.
- [x] Normalize same-repo relative markdown link targets to corpus-style `doc_id`s when possible.
- [x] Emit only structural `references` `GraphEdge` records from Layer 2; semantic `duplicate-of` and `conflicts-with` edges are not created yet.
- [x] Populate edge evidence with reason, anchor text, and source line.
- [x] Use `created_by: "link-extractor"` and propagate the source document `commit_sha`.
- [x] Make edge IDs deterministic as `<from>-><to>:references`, deduplicated per target document.
- [ ] Parse reference-style links, image targets beyond inline syntax, unresolved-link evidence, and "see also" prose references.

#### Embeddings + Vector Index (Layer 3 half)

- [x] Implement chunk embedding orchestration in `backend/app/embeddings/provider.py` against the `EmbeddingProvider` ABC.
- [x] Use local fastembed (`BAAI/bge-small-en-v1.5`, 384-dim ONNX, auto-detected dim) by default; do not require Azure for ingestion/search.
- [x] Support Azure embeddings through `EMBEDDING_PROVIDER=azure` without changing storage/search code.
- [x] Prepare vector records keyed by `chunk_id` with vector, text, `doc_id`, repo, heading path, line range, `commit_sha`, and metadata.
- [ ] Before embedding, skip unchanged chunks by comparing existing vector metadata with the same chunk `content_hash`; current loader re-embeds loaded chunks.
- [x] Upsert changed/new chunks by `chunk_id` via `ON CONFLICT`.
- [ ] Delete vectors for chunks belonging to `DocumentDeleted` docs.
- [x] Keep storage-specific code inside `backend/app/storage/vectorstore.py` and schema code inside `backend/app/storage/db.py`.
- [x] Normalize or validate vector dimensions by creating `chunks.embedding VECTOR(dim)` from the active provider's detected dimension.
- [ ] Add tests proving repeated runs produce the same upsert set; no pytest/ruff/black tooling is configured yet.

#### Hybrid Search

- [x] Implement `GET /search` behavior that accepts a query, optional repo scope, and top-k.
- [x] Query pgvector first for semantic similarity and return cosine scores normalized as `1 - (embedding <=> q)`.
- [ ] Add keyword/BM25-like fallback or local text fallback for cases where embeddings are missing, empty, or low-confidence.
- [x] Return deterministic vector results ordered by cosine distance.
- [x] Return search response with query text plus matches containing `chunkId`, `docId`, score, text, `lineRange`, and `commitSha` via camelCase DTOs.
- [x] Preserve citation fidelity to document ID, line range, and commit SHA where available.
- [ ] Handle deleted/stale docs and ACL-inaccessible docs explicitly once governance/ACL exists.

#### Duplicate Detection

- [ ] Compare chunk pairs only across different `docId`s; never mark chunks from the same document as cross-document duplicates.
- [ ] Use threshold `score >= 0.92` for `duplicate-of` candidates.
- [ ] Set `GraphEdge.weight` equal to the similarity score.
- [ ] Include evidence with both chunk IDs, both line ranges, score, and the reason `high-similarity-threshold` or contract-approved equivalent.
- [ ] Deduplicate symmetric pairs so A→B and B→A do not create duplicate graph noise unless the graph contract explicitly requires directionality.
- [ ] Prefer the more canonical or fresher document as the target only if a deterministic rule is agreed; otherwise mark candidates neutrally for P3/P4 review.
- [ ] Add tests around just-below threshold (`0.9199`), exact threshold (`0.92`), same-doc pairs, and repeated runs.

#### Conflict Seeding

- [ ] Use threshold `score >= 0.85` for potential conflicts, but require divergent extracted commands or values before emitting a `conflicts-with` candidate.
- [ ] Extract command/value signals from preserved command blocks, inline shell commands, version numbers, config keys, environment variable values, ports, and build/test invocations.
- [ ] Compare only evidence-bearing divergences; high similarity alone is not enough for a conflict seed.
- [ ] Emit candidate `GraphEdge` records with `type: "conflicts-with"`, weight equal to similarity score, and evidence naming the divergent commands/values.
- [ ] Keep this as deterministic seeding for P3/P4; do not call LLM agents from P2's conflict service.
- [ ] Add tests for obvious planted conflicts such as `npm test` vs `npm run test`, conflicting Node versions, or different build commands in similar setup docs.
- [ ] Avoid over-flagging equivalent commands where normalization can safely identify aliases only if the normalization rule is deterministic and documented.

#### API routers (`/ingest/refresh`, `/search`)

- [ ] Create or split future `backend/app/api/ingest.py` only if the team decides to move routes out of `main.py`.
- [ ] Expose `POST /ingest/refresh` for one repo, all configured repos, or an explicit config scope; this endpoint is not built yet.
- [ ] Return refresh summaries that include counts of added/changed/deleted/unchanged documents and any errors per repo without leaking local absolute paths.
- [ ] Route added/changed refresh events through processing, embedding, and vector upsert within the job model agreed by the team.
- [x] Implement `GET /search` in `backend/app/main.py` with real pgvector retrieval.
- [x] Expose `GET /search` returning query plus matches with deterministic ordering and valid score bounds.
- [x] Validate inputs enough for current API defaults (`q`, optional `repo`, `k`).
- [ ] Keep future router files thin if/when they are created; clone/chunk/embed/search logic should remain in ingestion/processing/embedding/storage modules.

### Integration (M2/M3)

- [x] Make embedding provider swappable from local fastembed to Azure through configuration only; service code does not depend on Azure-specific classes.
- [x] Run small end-to-end ingestion/load/search paths through CLI scripts (`run_ingest`, `load_vectors`, `search`) using real providers/storage.
- [x] Expose real search records to P3's orchestrator/chat flow so Curator can reason over real retrieved chunks instead of fixtures.
- [x] Provide P3 with retrieval behavior notes through implementation status: score range, top-k defaults, empty result handling, and citation fields.
- [x] Persist document records and chunks directly in Postgres tables.
- [x] Persist structural `references` edges in the `edges` table.
- [ ] Persist semantic `duplicate-of` and `conflicts-with` candidate edges; generation is not implemented yet.
- [ ] Integrate deletion refresh events with stale/broken node handling and vector deletion.
- [ ] Enforce ACL filtering at retrieval time once P4 exposes permission context; inaccessible chunks must not appear in search results or downstream citations.
- [ ] Coordinate with P4 on provenance/audit/approval tables; only document/chunk/edge provenance fields exist today.
- [ ] Run backend quality gates for touched modules when tooling exists; currently requirements have no configured ruff/black/pytest gates.

### Demo Polish (M4)

- [x] Configure four seed repositories from the approved corpus: Garnet, Playwright, ONNX Runtime, and VS Code.
- [x] Prefer scoped documentation folders through `sparsePaths` and `docGlobs` rather than whole full-history clones.
- [ ] Ensure planted duplicate fixtures produce `duplicate-of` candidates at or above `0.92` with clear evidence and stable graph edges.
- [ ] Ensure planted conflict fixtures produce `conflicts-with` seeds at or above `0.85` plus divergent command/value evidence.
- [ ] Prepare an incremental refresh demo: change/add/delete a doc in the controlled seed source or fixture path, run refresh, and show added/changed/deleted counts.
- [x] Verify re-running ingestion/loading uses stable IDs and `ON CONFLICT` upserts for idempotency.
- [ ] Add content-hash skip logic so unchanged chunks skip re-embedding, not just duplicate row creation.
- [ ] Create a fallback retrieval dataset using the same contracts in case live clone/network access fails during rehearsal.
- [x] Confirm `/search` returns stable, readable results for demo questions once vectors are loaded.
- [x] Confirm P4 graph view can receive structural `references` edge and document metadata.
- [ ] Rehearse the 9-step demo flow with P1/P3/P4 and note exact queries or refresh actions that reliably trigger the story.

## Key Design Rules & Gotchas

| Rule / gotcha | What to do | Why it matters |
| --- | --- | --- |
| Idempotency is mandatory | Same `RawDocument` must yield the same normalized text, chunks, chunk IDs, content hashes, edges, and Postgres `ON CONFLICT` upsert results. Add content-hash embedding skip logic as pending polish. | Repeated demo runs must not create duplicate records or unnecessary work. |
| Preserve commands verbatim | Do not reformat fenced code, shell snippets, or inline commands during normalization. | Verification and future conflict seeding rely on exact commands. Rewriting `npm run test` into prose destroys evidence. |
| Citations need exact ranges | Line ranges are implemented; true source char offsets are not. Keep `char_range` TODO visible until `(0, len(block))` is replaced. | P1/P3 need evidence-backed answers and highlights; P4 provenance must trace to exact lines and commits. |
| Propagate provenance | Carry `commit_sha` and `commit_date` from `RawDocument` into every chunk, vector record, edge, and search match. | Node health, verification stamps, provenance, and trust all depend on exact commit metadata. |
| Sparse-checkout scope matters | Keep `sparsePaths` and `docGlobs` tight and clone with `--depth 1 --filter=blob:none --sparse --branch <branch>`. | Large repos like `microsoft/vscode` and `microsoft/onnxruntime` can be huge; broad clones risk slow demos and wasted disk. |
| `repos.config.json` is config-driven | Treat source onboarding as a config edit with `shortName`, `sparsePaths`, and `docGlobs`. | General-plan §7 and team-plan §6 make configuration-driven sources a cross-cutting rule. |
| Thresholds are fixed but pending | Duplicate: different `docId`s and `score >= 0.92`. Conflict seed: `score >= 0.85` plus divergent commands/values. | Stable thresholds make demo behavior explainable and prevent noisy graph edges once implemented. |
| Structural vs semantic edges differ | Link extractor emits only `references`; future dedup/conflict services emit semantic candidates later. | Keeps Layer 2 deterministic and avoids mixing link parsing with similarity reasoning. |
| Do not call LLMs | P2 deterministic services should not invoke Curator or Guardian. | The architecture budgets model quota for P3 agents; P2 consumes only embedding compute through the provider. |
| Local first | Use local fastembed by default and switch to Azure only with `EMBEDDING_PROVIDER=azure`. | Ingestion and retrieval can run with no Azure credentials. |
| Contracts are layered | Core `app/models.py` models are snake_case; API DTOs in `main.py` expose camelCase. There is no frozen camelCase `models/` package or `types.ts` yet. | Contract drift silently breaks P1/P3/P4 and the mock-to-real swap. |
| Do not leak local paths | API responses should use repo-relative paths and `docId`s, not local machine absolute paths under `data\`. | Keeps responses portable and avoids exposing implementation details. |
| Deleted docs need cleanup | On future `DocumentDeleted`, remove or stale-mark vectors/chunks and notify P4's store/graph layer. | Otherwise search can cite deleted content and graph health becomes misleading. |
| Empty states are real states | Handle empty corpus, empty query, no vector index, no matches, and future inaccessible docs. | Team-plan §7 requires edge cases, not just happy paths. |

Recommended command snippets for the ingestion design spec:

```powershell
# New checkout: metadata first, docs only
 git clone --depth 1 --filter=blob:none --sparse --branch <branch> <url> data\<repo-short>
 git sparse-checkout set <sparsePaths>

# Per-file provenance
 git log -1 --format="%H|%an|%ae|%cI" -- <path>

# Refresh existing checkout
 git fetch --depth 1 origin <branch>
 git reset --hard origin/<branch>

# Local pipeline, no Azure required
 python -m scripts.run_ingest --all
 python -m scripts.load_vectors --all
 python -m scripts.search --repo playwright "how do I run tests in CI"
```

The snippets above are process documentation, not application source code. The implementation wraps them safely, captures errors per repository where implemented, and should avoid printing secrets or local absolute paths.

## Definition of Done

Person 2's slice is done when it satisfies team-plan §7 and the retrieval-specific gates below:

| Gate | Done means |
| --- | --- |
| Contract fidelity | Core `RawDocument`, `DocChunk`, and `GraphEdge` models remain snake_case in `app/models.py`; API response DTOs in `main.py` expose camelCase JSON. No nonexistent `models/` package or `types.ts` should be treated as current reality. |
| Ingestion completeness | Configured repositories can be sparse/shallow cloned, scoped by `sparsePaths`/`docGlobs`, converted to `RawDocument`, and processed through CLI. Explicit added/changed/deleted refresh events remain pending. |
| Processing determinism | Same `RawDocument` produces the same chunks, line ranges, content hashes, and structural edges every run. Commands/code blocks remain verbatim; true char ranges and overlap remain pending. |
| Search readiness | Chunks embed through local fastembed or Azure `EmbeddingProvider`, upsert into Postgres + pgvector, and return useful search matches with score, text, `chunkId`, `docId`, line range, and commit SHA. |
| Duplicate/conflict readiness | Pending: duplicate candidates must follow `score >= 0.92` across different docs; conflict seeds must follow `score >= 0.85` plus divergent command/value evidence. |
| Integration readiness | P3 can consume real search results; P4 can consume persisted document records and structural `references` edges through existing APIs/queries. Governance, ACL, provenance tables, and semantic edges are still future work. |
| Quality gate | Documentation-only changes do not require code tests. Implementation PRs should run available backend checks; no ruff/black/pytest tooling is configured today. |
| Edge cases | Empty corpus, missing repo config, clone failure, unchanged content, deleted docs, empty search results, malformed markdown links, and inaccessible docs are handled deliberately or tracked as pending where not yet built. |
| Demo gate | By M4, configured repos ingest reliably, search returns stable results, and planted duplicate/conflict plus incremental refresh demos are implemented or replayed from fallback fixtures. |

Final acceptance is not just "the code runs." It is that the retrieval pipeline can be rerun safely, produces evidence-backed records that other teammates can consume, and preserves provenance from git clone metadata all the way to search results and graph edges.

