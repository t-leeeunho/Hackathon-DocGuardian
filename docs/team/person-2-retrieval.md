# Person 2 — Retrieval & Document Intelligence

Person 2 owns the deterministic retrieval pipeline that turns raw repository documentation into searchable, graph-aware, embedded knowledge for DocGuardian AI.

## Mission

Person 2's mission is to build the retrieval half of deterministic Layers 1–3: ingestion, processing, embeddings, vector indexing, search, duplicate detection, and conflict seeding. This work turns sparse/shallow git repository checkouts into `RawDocument`, `DocChunk`, `GraphEdge`, and `SearchResult` records that the rest of the product can trust. The pipeline consumes no LLM quota and should use model quota only for embeddings through the `EmbeddingProvider` interface. During M1/M2, Person 2 develops against `FakeEmbeddingProvider` plus real git clones so retrieval work can start immediately without waiting for Azure.

## Scope — What You Own

Person 2 owns the full path from repository clone metadata to retrieval results:

| Area | Owned paths | Responsibility |
| --- | --- | --- |
| Ingestion | `backend/app/ingestion/**` | Sparse/shallow clone, sparse-checkout, repository refresh, commit metadata extraction, `RawDocument` creation, `DocumentAdded` / `DocumentChanged` / `DocumentDeleted` event emission. |
| Processing | `backend/app/processing/**` | Markdown normalization, front-matter stripping, command/code preservation, heading offset tracking, heading-aware chunking, line/char range calculation, structural link/reference extraction. |
| Embeddings | `backend/app/ai/embeddings.py` | Embedding orchestration through `EmbeddingProvider`, content-hash skip logic, vector upsert preparation. |
| Retrieval services | `backend/app/services/retrieval.py` | Hybrid search, keyword fallback, `SearchResult` assembly, ACL-aware filtering once P4's interface is available. |
| Dedup/conflict services | `backend/app/services/dedup_conflict.py` | Duplicate candidate generation, conflict seed generation, evidence packaging as semantic `GraphEdge` candidates. |
| Vector adapter | `backend/app/store/vector_*.py` | Local vector index adapter behind the frozen `VectorIndex` interface; in-memory/fake first, local durable adapter next, Azure AI Search/pgvector-compatible adapter later if time permits. |
| API router | `backend/app/api/ingest.py` | Person 2's ingestion endpoints, especially `POST /ingest/refresh`. |
| API router | `backend/app/api/search.py` | Person 2's retrieval endpoints, especially `GET /search`. |

Concrete deliverables inside that scope:

- Implement repository source loading from `repos.config.json` entries.
- Clone configured sources into `data/<repo-short>` using sparse/shallow git commands.
- Emit deterministic `RawDocument` records with `commitSha`, `commitDate`, `fetchedAt`, and `contentHash`.
- Convert each `RawDocument` into stable `DocChunk` records and structural `references` `GraphEdge` records.
- Embed chunks through `FakeEmbeddingProvider` first, then the real provider behind the same interface.
- Upsert vectors keyed by `chunkId` and skip unchanged `contentHash` values.
- Return `SearchResult` records with cosine scores in `[0,1]` and precise citation metadata.
- Generate `duplicate-of` and `conflicts-with` candidate edges using the thresholds in README §8A.4.

## What You Must NOT Touch

These files/directories are frozen or owned by other people. Person 2 should request director changes instead of editing them directly.

| Do not touch | Why |
| --- | --- |
| `backend/app/models/**` | Frozen Pydantic contracts after M1. If `RawDocument`, `DocChunk`, `GraphEdge`, `SearchResult`, or refresh events need changes, ask the director to update models and mirrored TypeScript together. |
| `frontend/src/lib/types.ts` | Frozen TypeScript mirror of backend contracts. Contract drift breaks serialization across layers. |
| `backend/app/main.py` | Router wiring is director-owned after Phase 0. Person 2 owns router files, not app-level registration. |
| Other people's routers | `backend/app/api/documents.py`, `backend/app/api/chat.py`, `backend/app/api/graph.py`, `backend/app/api/proposals.py`, `backend/app/api/metrics.py`, `backend/app/api/stream.py` are owned by P3/P4. |
| Other people's directories | Do not edit P1 frontend implementation, P3 agent/orchestrator/provider code outside agreed interfaces, or P4 governance/store/sandbox services. |

If an integration requires a frozen contract field, a `main.py` route registration, a new store method, or a frontend type adjustment, document the request and hand it to the director. Continue against fixtures/fakes until the shared interface is updated.

## Inputs (Consumed, Mocked) & Outputs (Produced)

| Contract / artifact | Direction for P2 | Real or mocked by milestone | Source / destination | Notes |
| --- | --- | --- | --- | --- |
| `repos.config.json` | Consumed | Real in M1; entries may be minimal seed repos | Director-owned config, read by ingestion | Single source of truth for repo slug, clone URL, branch, `docGlobs`, and refresh interval. P2 may propose entries but should not change frozen config after M1 without director approval. |
| Git repository checkout | Consumed | Real from the start | `data/<repo-short>` | Use sparse/shallow clone; no GitHub API dependency, no tokens, no deep clone. |
| `RawDocument` | Produced | Fixtures validated in Phase 0; real records by M2 | Ingestion → Processing / P4 store | One record per selected file. Must include stable `docId`, repo/path/branch, raw UTF-8 content, byte size, commit metadata, `fetchedAt`, and `contentHash`. |
| `DocumentAdded` | Produced | Fixture in M1; real refresh event by M2/M3 | Ingestion refresh → Processing / graph | Emitted when a selected doc path appears. Carries `docId` and full `raw` record. |
| `DocumentChanged` | Produced | Fixture in M1; real refresh event by M2/M3 | Ingestion refresh → Processing / graph | Emitted when `commitSha` and/or `contentHash` changed. Carries `previousCommitSha` and new `raw`. |
| `DocumentDeleted` | Produced | Fixture in M1; real refresh event by M2/M3 | Ingestion refresh → P4 graph/store | Emitted when a path disappears. Carries `lastKnownCommitSha`; P4 marks node stale/broken. |
| `DocChunk` | Produced | Fixture validated in Phase 0; real chunks by M2 | Processing → embeddings/search/P3 evidence | Stable `chunkId`, inherited `docId`/`commitSha`/`commitDate`, heading path, exact `lineRange`, exact `charRange`, `containsCommands`, token count, and chunk `contentHash`. |
| `GraphEdge` (`references`) | Produced | Fixture in M1; real structural edges by M2 | Processing → P4 graph store | Link extractor emits structural `references` edges only. Semantic `duplicate-of` and `conflicts-with` edges are generated after embeddings/similarity. |
| `GraphEdge` (`duplicate-of`) | Produced | Candidate fixtures in M1; real candidates by M2/M3 | Dedup service → P4 graph store / P3 | Chunk pairs from different `docId`s with score `>= 0.92`; edge weight equals score. |
| `GraphEdge` (`conflicts-with`) | Produced | Candidate fixtures in M1; real seeds by M2/M3 | Conflict seeding → P4 graph store / P3 | Similar chunks with score `>= 0.85` plus divergent extracted commands/values. P3 may later confirm or resolve with agents. |
| `EmbeddingProvider` | Consumed | `FakeEmbeddingProvider` in M1/M2; Azure provider in integration | P3/provider interface | Never block on Azure. Code to the provider interface, not to Azure-specific SDK behavior. |
| `VectorIndex` | Consumed/implemented | Fake/in-memory in M1; local durable in M2; real adapter optional in M3 | Store interface | P2 owns `vector_*.py` adapters behind the frozen interface. |
| Vector record | Produced internally | Real local record by M2 | Embeddings → vector index | Keyed by `chunkId`; includes vector, model, dim, text, metadata, heading path, line range, commit SHA, ACL tags when available. |
| `SearchResult` | Produced | Fixture in M1; real by M2 | Retrieval → P3 orchestrator/chat and `/search` | Query plus scored matches, sorted descending, with cosine score in `[0,1]`, text, `chunkId`, `docId`, `lineRange`, and `commitSha`. |

Minimal contract shapes to keep in mind while building fixtures and tests:

```jsonc
// DocChunk shape, not application code
{
  "chunkId": "playwright/docs/src/intro.md#Installation#0",
  "docId": "playwright/docs/src/intro.md",
  "repo": "microsoft/playwright",
  "headingPath": ["Getting Started", "Installation"],
  "ordinal": 0,
  "text": "npm init playwright@latest ...",
  "tokenCount": 612,
  "lineRange": [12, 41],
  "charRange": [180, 1422],
  "containsCommands": true,
  "commitSha": "a1b2c3...",
  "commitDate": "2026-05-18T14:22:07Z",
  "contentHash": "sha256:..."
}
```

```jsonc
// SearchResult shape, not application code
{
  "query": "how do I run playwright tests in CI",
  "matches": [
    {
      "chunkId": "playwright/docs/src/ci.md#GitHub-Actions#0",
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
| Director / Phase 0 foundation | Frozen Pydantic models, mirrored TypeScript contracts, router registration, `repos.config.json`, `FakeEmbeddingProvider`, `VectorIndex` interface, fixture examples. | Contract review feedback for `RawDocument`, refresh events, `DocChunk`, `GraphEdge`, and `SearchResult`. | M1 freezes contracts and mock API. P2 should validate fixtures against README §8A examples before building real services. |
| P3 — Agent Orchestration & AI Reasoning | `EmbeddingProvider` interface and fake/real provider implementations; any agreed reranking/query conventions. | Real `SearchResult` records for Curator/chat RAG; duplicate/conflict candidates with chunk IDs and evidence. | M1: P3 consumes sample `SearchResult` fixtures. M2: P3 can switch to P2's real retrieval endpoint/service. |
| P4 — Governance, Verification & Metrics | Store/ACL interfaces, graph/document persistence methods, optional permission tags for query-time filtering. | `RawDocument`/document records, `DocChunk` metadata, structural `references` edges, semantic candidate edges, refresh deletion events. | M1/M2: P2 can use fake/in-memory stores. M3: persist edges and document records through P4's SQLite-backed store interface. |
| P1 — Frontend & Demo Experience | Search and graph expectations through frozen API contracts only. | `/search` results and graph edges indirectly through P4's graph API. | P1 should remain mock-driven until M3. P2 should not edit frontend files. |
| Git CLI / repositories | Sparse/shallow clones, file contents, commit metadata. | Local `data/<repo-short>` working copies and ingestion events. | Real from the start. Scope aggressively to docs folders to avoid huge checkouts. |
| Embedding backend | Fake embeddings first; Azure embeddings during integration. | Chunk text and metadata for embedding/upsert. | M1/M2: deterministic fake vectors are enough for tests. M2/M3: config switch to real Azure behind the same `EmbeddingProvider`. |

Real vs mocked by milestone:

| Milestone | Real | Mocked / fake |
| --- | --- | --- |
| M1 | Contract fixtures, route shells, `repos.config.json` shape, tooling. | Embeddings, vector index, store persistence, P3/P4 consumers. |
| M2 | Sparse/shallow clones, `RawDocument` creation, processing, chunking, fake-embedding-backed search, duplicate/conflict candidate logic. | Azure embeddings may still be fake; P4 persistence may still be in-memory. |
| M3 | Real router service calls, P4 SQLite store interface, real `SearchResult` consumed by P3, persisted graph/doc records consumed by P4/P1. | Only optional cloud services remain replaceable by local adapters. |
| M4 | Seed repo ingestion, planted duplicate/conflict fixtures, incremental refresh demo. | Fallback demo data may remain available for rehearsal resilience. |

## Detailed TODOs

### Phase 0 — Foundation participation

- [ ] Review README §8A.2–§8A.4 and validate that `RawDocument`, `DocumentAdded`, `DocumentChanged`, `DocumentDeleted`, `DocChunk`, `GraphEdge`, and `SearchResult` fixtures match the exact camelCase field names.
- [ ] Help author or review Phase 0 fixture JSON for `RawDocument` with `docId`, `repo`, `path`, `branch`, `content`, `byteSize`, `encoding`, commit metadata, `fetchedAt`, and `contentHash`.
- [ ] Help author or review `DocChunk` fixtures with heading paths, ordinal values, line ranges, char ranges, `containsCommands`, inherited `commitSha`/`commitDate`, and stable chunk `contentHash` values.
- [ ] Help author or review `GraphEdge` fixtures for `references`, `duplicate-of`, and `conflicts-with`, ensuring the `from` / `to` / `type` / `weight` quartet matches frontend graph needs.
- [ ] Help author or review `SearchResult` fixtures so P3 can build Curator/chat RAG without waiting for real indexing.
- [ ] Validate `FakeEmbeddingProvider` behavior is deterministic for the same chunk text so tests are repeatable.
- [ ] Confirm `VectorIndex` interface has enough operations for upsert-by-`chunkId`, search, delete-by-doc, and skip/metadata lookup without leaking adapter-specific details.
- [ ] Set up expected local data layout: `data/<repo-short>` working copies, with `data/` gitignored by Phase 0 tooling.
- [ ] Propose initial `repos.config.json` entries for 1–2 small doc scopes, such as focused `microsoft/playwright` docs and a scoped `microsoft/garnet` documentation subset.
- [ ] Agree with the director on how Person 2 router stubs expose `POST /ingest/refresh` and `GET /search` while `backend/app/main.py` remains director-owned.

### Core Build

#### Ingestion (Layer 1)

- [ ] Implement source loading from `repos.config.json` with validation for `repo`, `url`, `branch`, `docGlobs`, and `refreshIntervalMinutes`.
- [ ] Derive safe local checkout names under `data/<repo-short>`; avoid collisions between repos with the same short name by documenting/handling a deterministic naming rule.
- [ ] Run the metadata-only clone procedure for new repos:

  ```powershell
  git clone --depth 1 --filter=blob:none --sparse <url> data/<repo>
  git sparse-checkout set <docGlobs>
  ```

- [ ] Keep sparse-checkout scoped to documentation globs only; never expand to full large repos such as VS Code or ONNX Runtime unless the director explicitly approves a demo scope change.
- [ ] Enumerate selected markdown files deterministically, excluding binary files, generated output, vendored dependency folders, and paths outside configured doc globs.
- [ ] Extract per-file commit metadata with `git log -1 --format="%H|%an|%ae|%cI" -- <path>` and parse `commitSha`, `commitAuthor`, `commitEmail`, and `commitDate`.
- [ ] Compute `byteSize`, `encoding`, `fetchedAt`, and `contentHash` as `sha256` over raw UTF-8 content.
- [ ] Build one `RawDocument` per selected file with stable `docId` format `<repo-short>/<path>` or the contract-approved equivalent from Phase 0.
- [ ] Implement refresh with `git fetch --depth 1 origin` plus `git reset --hard origin/<branch>` and compare prior vs current file SHAs/hashes.
- [ ] Emit `DocumentAdded`, `DocumentChanged`, and `DocumentDeleted` events from refresh; route added/changed documents to processing and deleted documents to P4's stale/broken node handling interface.

#### Processing (Layer 2)

- [ ] Build a pure normalizer that returns identical output for identical `RawDocument` input, regardless of runtime environment.
- [ ] Strip YAML/front-matter without shifting reported source line ranges incorrectly; maintain mapping from normalized text back to original lines.
- [ ] Preserve headings, fenced code blocks, command blocks, inline commands, and shell snippets verbatim because verification later executes command text.
- [ ] Resolve relative markdown links and images to target `docId` values where the target exists in the same ingested corpus.
- [ ] Record heading text, heading hierarchy, start/end character offsets, and source line numbers for each heading.
- [ ] Implement heading-aware chunking with target size around 500–800 tokens and approximately 80-token overlap.
- [ ] Ensure chunks inherit `docId`, `repo`, `commitSha`, `commitDate`, heading path, and exact source line range from the parent document.
- [ ] Generate stable `chunkId` values using `docId`, heading slug/path, and ordinal; the same source document must produce the same IDs across runs.
- [ ] Detect whether each chunk contains commands and set `containsCommands` accurately.
- [ ] Compute chunk `contentHash` over chunk text so embedding upsert can skip unchanged chunks independently from unchanged documents.

#### Link extractor

- [ ] Parse explicit markdown links, reference-style links, relative paths, anchors, image targets, and "see also" style references.
- [ ] Normalize link targets to corpus `docId`s when possible; retain unresolved-link evidence for later broken-link/health metrics if the contract supports it.
- [ ] Emit only structural `references` `GraphEdge` records from Layer 2; do not create semantic `duplicate-of` or `conflicts-with` edges before embeddings exist.
- [ ] Populate edge evidence with reason, anchor text, and source `lineRange`.
- [ ] Use `createdBy: "link-extractor"` and propagate the source document `commitSha`.
- [ ] Make edge IDs deterministic, for example `<from>-><to>:references`, with a disambiguator only if multiple edges between the same docs must be preserved.

#### Embeddings + Vector Index (Layer 3 half)

- [ ] Implement chunk embedding orchestration in `backend/app/ai/embeddings.py` against the `EmbeddingProvider` interface.
- [ ] Use `FakeEmbeddingProvider` by default for local/M1/M2 development; never block ingestion/search tests on Azure availability.
- [ ] Prepare vector records keyed by `chunkId` with vector, model, dimension, text, `docId`, repo, heading path, line range, `commitSha`, and ACL tags when P4 exposes them.
- [ ] Before embedding, check whether the existing vector metadata has the same chunk `contentHash`; skip unchanged chunks.
- [ ] Upsert changed/new chunks by `chunkId`; delete vectors for chunks belonging to `DocumentDeleted` docs.
- [ ] Keep adapter-specific code inside `backend/app/store/vector_*.py` and expose only the `VectorIndex` interface to services.
- [ ] Normalize or validate vector dimensions so fake and real embedding providers cannot silently corrupt index records.
- [ ] Add tests proving the same chunks produce the same fake embeddings and the same vector upsert set across repeated runs.

#### Hybrid Search

- [ ] Implement `GET /search` service behavior that accepts a query, optional repo/doc scope, top-k, and later ACL context if P4 provides it.
- [ ] Query the vector index first for semantic similarity and return cosine scores normalized to `[0,1]`.
- [ ] Add keyword/BM25-like fallback or local text fallback for cases where embeddings are missing, empty, or low-confidence.
- [ ] Merge vector and keyword results deterministically, deduplicating by `chunkId` and sorting primarily by score descending.
- [ ] Return `SearchResult` with query text plus matches containing `chunkId`, `docId`, score, text excerpt/full chunk text per contract, `lineRange`, and `commitSha`.
- [ ] Preserve citation fidelity: a user-visible result must always be traceable to an exact document, line range, and commit SHA.
- [ ] Handle empty corpus, empty query, inaccessible docs, and deleted/stale docs explicitly rather than returning misleading matches.

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

- [ ] Replace Phase 0 mock bodies in `backend/app/api/ingest.py` with calls into the ingestion refresh service once M1 contracts are frozen.
- [ ] Expose `POST /ingest/refresh` for one repo, all configured repos, or an explicit config scope depending on the Phase 0 route contract.
- [ ] Return refresh summaries that include counts of added/changed/deleted/unchanged documents and any errors per repo without leaking local absolute paths.
- [ ] Route added/changed refresh events through processing, embedding, and vector upsert within the job model agreed by the team.
- [ ] Replace Phase 0 mock bodies in `backend/app/api/search.py` with retrieval service calls.
- [ ] Expose `GET /search` returning `SearchResult` exactly, including deterministic ordering and valid score bounds.
- [ ] Validate inputs and return useful errors for missing query, invalid top-k, unknown repo scope, or corpus not ingested.
- [ ] Keep router files thin: validation and response assembly belong there; clone/chunk/embed/search logic belongs in services.

### Integration (M2/M3)

- [ ] Swap `FakeEmbeddingProvider` to the real Azure-backed embedding provider through configuration only; no service code should depend on Azure-specific classes.
- [ ] Run a small end-to-end ingestion using fake embeddings first, then real embeddings, and compare that contract shapes remain identical even if vector scores differ.
- [ ] Expose real `SearchResult` records to P3's orchestrator/chat flow so Curator can reason over real retrieved chunks instead of fixtures.
- [ ] Provide P3 with retrieval behavior notes: score range, top-k defaults, empty result handling, duplicate/conflict candidate semantics, and citation fields.
- [ ] Persist `RawDocument` / document record metadata through P4's store interface once it is available, without importing P4 implementation details directly.
- [ ] Persist structural `references` edges and semantic candidate edges to P4's graph store through the agreed interface.
- [ ] Integrate deletion refresh events with P4's stale/broken node handling and vector deletion.
- [ ] Enforce ACL filtering at retrieval time once P4 exposes permission context; inaccessible chunks must not appear in `SearchResult` or downstream citations.
- [ ] Coordinate with P4 on provenance fields so every stored document/chunk/edge retains `commitSha` and commit date.
- [ ] Run backend quality gates for touched modules: `ruff check`, `black --check`, and `pytest -q`.

### Demo Polish (M4)

- [ ] Ingest 1–2 seed repositories from the approved hackathon corpus, scoped to reliable documentation folders rather than whole repos.
- [ ] Prefer small, high-signal demo scopes such as Playwright testing/setup docs and Garnet getting-started/operations docs unless the director chooses a different seed corpus.
- [ ] Ensure planted duplicate fixtures produce `duplicate-of` candidates at or above `0.92` with clear evidence and stable graph edges.
- [ ] Ensure planted conflict fixtures produce `conflicts-with` seeds at or above `0.85` plus divergent command/value evidence.
- [ ] Prepare an incremental refresh demo: change/add/delete a doc in the controlled seed source or fixture path, run refresh, and show added/changed/deleted counts.
- [ ] Verify re-running ingestion with unchanged `contentHash` skips re-processing and re-embedding, and be ready to explain the idempotency story during the demo.
- [ ] Create a fallback retrieval dataset using the same contracts in case live clone/network access fails during rehearsal.
- [ ] Confirm `/search` returns stable, readable results for the demo questions used by P1/P3.
- [ ] Confirm P4 graph view receives enough `GraphEdge` and document metadata to color duplicate/conflict/reference relationships.
- [ ] Rehearse the 9-step demo flow with P1/P3/P4 and note exact queries or refresh actions that reliably trigger the story.

## Key Design Rules & Gotchas

| Rule / gotcha | What to do | Why it matters |
| --- | --- | --- |
| Idempotency is mandatory | Same `RawDocument` must yield the same normalized text, chunks, chunk IDs, content hashes, edges, and vector upsert decisions. | Team-plan §6 requires unchanged `contentHash` to be a no-op; repeated demo runs must not create duplicate records. |
| Preserve commands verbatim | Do not reformat fenced code, shell snippets, or inline commands during normalization. | Verification and conflict seeding rely on exact commands. Rewriting `npm run test` into prose destroys evidence. |
| Citations need exact ranges | Maintain original source line ranges and char ranges through front-matter stripping, normalization, and chunking. | P1/P3 need evidence-backed answers and highlights; P4 provenance must trace to exact lines and commits. |
| Propagate provenance | Carry `commitSha` and `commitDate` from `RawDocument` into every chunk, vector record, edge, and search match. | Node health, verification stamps, provenance, and trust all depend on exact commit metadata. |
| Sparse-checkout scope matters | Keep `docGlobs` tight and clone with `--depth 1 --filter=blob:none --sparse`. | Large repos like `microsoft/vscode` and `microsoft/onnxruntime` can be huge; broad clones risk slow demos and wasted disk. |
| `repos.config.json` is config-driven | Treat source onboarding as a config edit, not a code change. | General-plan §7 and team-plan §6 make configuration-driven sources a cross-cutting rule. |
| Thresholds are fixed | Duplicate: different `docId`s and `score >= 0.92`. Conflict seed: `score >= 0.85` plus divergent commands/values. | Stable thresholds make demo behavior explainable and prevent noisy graph edges. |
| Structural vs semantic edges differ | Link extractor emits only `references`; embeddings/dedup/conflict services emit semantic candidates later. | Keeps Layer 2 deterministic and avoids mixing link parsing with similarity reasoning. |
| Do not call LLMs | P2 deterministic services should not invoke Curator or Guardian. | The architecture budgets model quota for P3 agents; P2 consumes only embedding quota through the provider. |
| Fake first | Use `FakeEmbeddingProvider` and fake/in-memory vector index for tests and local development. | M1/M2 parallelism depends on not waiting for Azure credentials or quota. |
| Contracts are sacred | Use camelCase field names and frozen model types exactly. | Contract drift silently breaks P1/P3/P4 and the mock-to-real swap. |
| Do not leak local paths | API responses should use repo-relative paths and `docId`s, not local machine absolute paths under `data/`. | Keeps responses portable and avoids exposing implementation details. |
| Deleted docs need cleanup | On `DocumentDeleted`, remove or stale-mark vectors/chunks and notify P4's store/graph layer. | Otherwise search can cite deleted content and graph health becomes misleading. |
| Empty states are real states | Handle empty corpus, empty query, no vector index, no matches, and inaccessible docs. | Team-plan §7 requires edge cases, not just happy paths. |

Recommended command snippets for the ingestion design spec:

```powershell
# New checkout: metadata first, docs only
 git clone --depth 1 --filter=blob:none --sparse <url> data/<repo-short>
 git sparse-checkout set <docGlobs>

# Per-file provenance
 git log -1 --format="%H|%an|%ae|%cI" -- <path>

# Refresh existing checkout
 git fetch --depth 1 origin
 git reset --hard origin/<branch>
```

The snippets above are process documentation, not application source code. The implementation should wrap them safely, capture errors per repository, and avoid printing secrets or local absolute paths.

## Definition of Done

Person 2's slice is done when it satisfies team-plan §7 and the retrieval-specific gates below:

| Gate | Done means |
| --- | --- |
| Contract fidelity | `RawDocument`, refresh events, `DocChunk`, `GraphEdge`, and `SearchResult` match frozen Pydantic models and camelCase JSON exactly. No direct edits to `backend/app/models/**` or `frontend/src/lib/types.ts` after M1. |
| Ingestion completeness | Configured repositories can be sparse/shallow cloned, scoped by `docGlobs`, converted to `RawDocument`, and refreshed into added/changed/deleted/unchanged outcomes. |
| Processing determinism | Same `RawDocument` produces the same chunks, line ranges, char ranges, content hashes, and structural edges every run. Commands/code blocks remain verbatim. |
| Search readiness | Chunks embed through `FakeEmbeddingProvider`, upsert behind `VectorIndex`, and return useful `SearchResult` records with score, text, `chunkId`, `docId`, line range, and commit SHA. |
| Duplicate/conflict readiness | Duplicate candidates follow `score >= 0.92` across different docs; conflict seeds follow `score >= 0.85` plus divergent command/value evidence. |
| Integration readiness | P3 can consume real `SearchResult`; P4 can persist document records and `GraphEdge` records through interfaces; P1 can see the effects through existing graph/search APIs without Person 2 editing frontend files. |
| Quality gate | For touched backend modules, `ruff check`, `black --check`, and `pytest -q` pass. Documentation-only changes do not require code tests, but implementation PRs do. |
| Edge cases | Empty corpus, missing repo config, clone failure, unchanged content, deleted docs, empty search results, malformed markdown links, and inaccessible docs are handled deliberately. |
| Demo gate | By M4, 1–2 seed repos ingest reliably, planted duplicate/conflict fixtures trigger consistently, and incremental refresh can be demonstrated or replayed from a fallback fixture dataset. |

Final acceptance is not just "the code runs." It is that the retrieval pipeline can be rerun safely, produces evidence-backed records that other teammates can consume, and preserves provenance from git clone metadata all the way to search results and graph edges.
