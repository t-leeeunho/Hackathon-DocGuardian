# DocGuardian AI

## AI-Powered Documentation Governance, Validation, and Knowledge Navigation Platform

## 1. Overview

Engineering teams rely heavily on documentation for onboarding, development workflows, architecture understanding, testing, and operational knowledge. However, documentation often becomes stale, duplicated, inconsistent, or disconnected from the actual source of truth such as code, pull requests, configuration files, tickets, and team discussions.

**DocGuardian AI** is an AI-powered documentation agent system that continuously validates, organizes, updates, and explains engineering documentation. Instead of relying on humans to manually maintain scattered docs, DocGuardian AI acts as a documentation guardian that detects stale content, identifies duplication, proposes updates, verifies changes against source-of-truth signals, and provides an interactive knowledge interface for engineers.

The goal is to make documentation trustworthy, discoverable, permission-aware, and easier to maintain.

---

## 2. Problem Statement

Engineering documentation frequently suffers from the following issues:

- Documentation becomes outdated after code, configuration, or process changes.

- Multiple documents describe the same process in slightly different ways.

- New engineers spend significant time searching through scattered docs.

- Onboarding requires reading many pages before understanding architecture or workflows.

- Teams lack confidence in whether documentation reflects the current system.

- Documentation updates are often manual, inconsistent, and difficult to review.

- Sensitive information requires permission-aware access and controlled updates.

These problems reduce engineering productivity, slow onboarding, increase operational risk, and create confusion during development and testing.

---

## 3. Proposed Solution

DocGuardian AI provides an intelligent documentation management layer that connects documents with source-of-truth signals such as repositories, commits, PRs, configuration changes, tickets, and team knowledge sources.

The system uses an orchestrator agent that routes user requests and system events to specialized sub-agents. These agents can detect stale documentation, resolve conflicts, propose edits, verify claims, enforce permissions, and maintain provenance logs.

The user interface presents documentation as an interactive graph, similar to a knowledge map, where users can visually inspect relationships, conflicts, freshness, ownership, and access levels.

---

## 4. Target Users

- Software engineers onboarding to a new project

- Engineers updating or creating documentation

- Team leads reviewing documentation quality

- Developers looking for the correct way to run tests or tools

- New team members trying to understand architecture

- Documentation owners responsible for consistency and correctness

- Project teams managing cross-repo or cross-service knowledge

---

## 5. User Scenarios and Use Cases

### 5.1 Add New Documentation

A user wants to add new documentation into DocGuardian AI. The system analyzes the content, identifies related existing documents, recommends the correct destination, and checks whether the new content duplicates or conflicts with existing knowledge.

### 5.2 Update Existing Documentation

A user wants to update old or pre-existing documentation. DocGuardian AI compares the proposed update against source-of-truth signals, identifies impacted documents, and suggests a controlled update through a diff and approval flow.

### 5.3 Ask Follow-Up Questions

A user wants to ask follow-up questions about a document. The system answers using only accessible documents and provides supporting evidence, source references, and confidence scores.

### 5.4 Interactive Project Onboarding

A user onboarding to a new project wants to understand architecture details in a more interactive way. DocGuardian AI provides guided explanations, document relationships, architecture summaries, and optional visual navigation through a document graph.

### 5.5 Unified Test and Software Workflow Guidance

A user wants one clean and unified way to run software tools, builds, or tests instead of reading multiple duplicated documents with subtly different instructions. DocGuardian AI identifies conflicting instructions, determines the likely canonical source, and proposes a single recommended workflow.

### 5.6 AI-Managed Documentation

Instead of humans manually managing all documents, an AI agent continuously monitors documentation quality, detects outdated content, and proposes improvements.

### 5.7 Specialized Sub-Agents

The system may include specialized sub-agents for tasks such as verification, placement, authoring, governance, conflict detection, and source resolution.

### 5.8 Permission-Aware Knowledge Access

Users have different permission levels for viewing documents and accessing information. DocGuardian AI enforces access control at both read and write levels.

### 5.9 Duplicate Information Reduction

The system identifies duplicated or overlapping documentation and recommends merge, link, deprecate, or canonicalization actions.

---

## 6. Functional Requirements

### 6.1 Continuous Documentation Validation

The agent continuously checks documentation against source-of-truth signals such as:

- Repository commits

- Pull requests

- Configuration changes

- Ticket closures

- Build or test instructions

- Team-owned documentation sources

When a document no longer matches reality, the system flags it as potentially stale.

### 6.2 Verification Stamp

Each document should include a verification stamp, such as:

> Last verified against commit `<commit-sha>` on `<date>`

This gives users confidence that the document was checked against a specific source at a specific time.

### 6.3 Evidence-Based AI Answers and Edits

Every AI-generated answer or proposed edit must include:

- The source that supports the answer

- Why the change is being suggested

- A confidence score

- Any uncertainty or missing evidence

### 6.4 Explicit Uncertainty Handling

When evidence is weak or unavailable, the system should explicitly state:

> I'm not sure. This needs human review.

This is important because DocGuardian AI should behave like an engineering tool, not a demo chatbot that guesses.

### 6.5 Sandbox-Based Verification

For the agent to mark an update as high confidence, a dedicated verification agent should test the relevant code, command, document instruction, or workflow inside an isolated sandbox when possible.

### 6.6 Conflict Detection

When two documents disagree, the system should:

- Detect the contradiction

- Identify the likely canonical source

- Explain why the conflict exists

- Propose a merge, update, link, deprecation, or review action

The agent should not silently choose one document without explanation.

### 6.7 Write-Time Conflict Warning

When a user writes or uploads new content, the system should surface warnings such as:

> This appears to contradict `<document-name>`.

This prevents new documentation from introducing more inconsistency.

### 6.8 Review and Approval Flow

Before writing to authoritative documentation, the system should use a controlled flow:

1. Propose change

2. Show diff view

3. Show evidence and confidence

4. Request approve or reject decision

5. Apply approved change

6. Record provenance

### 6.9 Learning from Human Feedback

The agent should learn from human accept/reject actions, including:

- Preferred documentation destination

- Preferred wording style

- Repeated risky update types

- Common correction patterns

- Team-specific documentation conventions

This supports the narrative that human correction improves the system over time.

### 6.10 Provenance and Rollback

Every document change should have a provenance log showing:

- What changed

- Who approved it

- What agent proposed it

- Why the change was made

- Which sources supported it

- Previous version

- One-click rollback option

This is critical for enterprise trust and governance.

### 6.11 Metrics Dashboard

The system should include a metrics surface showing impact, such as:

- Stale documents detected

- Stale documents fixed

- Duplicate documents removed

- Broken links resolved

- Conflicts detected

- Conflicts resolved

- Onboarding questions reduced

- Average time-to-update documentation

- Documents verified against source-of-truth signals

These metrics directly support business value, customer focus, and engineering productivity.

### 6.12 Permission and ACL Enforcement

DocGuardian AI must enforce permissions at both:

- **Read level:** what documents and information the user can see

- **Write level:** what documents the user or agent can modify

For sensitive spaces, the system should require staged approvals before changes are applied.

---

## 7. User Interface Design

The UI should be inspired by tools like Obsidian, but optimized for enterprise documentation governance and AI-assisted knowledge navigation.

### 7.1 Document Graph View

The main view is a 3D or graph-based map of documents based on their relationships, references, ownership, and source connections.

### 7.2 Referenced Document Highlighting

Documents referenced by the selected file should visually blink or highlight in the graph.

### 7.3 Chunked Rendering Strategy

To avoid heavy rendering costs, the graph can be rendered in chunks:

- Show a pre-rendered overview first

- Do not fully render document details until a file is selected

- Zoom into a selected document cluster when needed

### 7.4 File Storage Navigation

The left side of the page should show connected file storage sources, such as documentation repositories, wiki spaces, or folder structures.

### 7.5 Drop-Off Area

The UI should provide a drop-off area where users can:

- Upload a file

- Paste text

- Add a documentation draft

- Submit a natural language update

The system then decides whether to create, update, merge, link, deprecate, or flag content.

### 7.6 Chat Interface

A chat area allows users to ask questions such as:

- "Find the correct document for running tests."

- "Which document explains this architecture?"

- "Can you summarize the onboarding path?"

- "Is this document still accurate?"

The chat can either return relevant documents or answer directly using evidence-backed sources.

### 7.7 Scope Toggle

Users can choose the scope of answers, such as:

- Current repository only

- Current team docs only

- Accessible company docs

- Selected document cluster

- Summary-only mode

- Source-required mode

This helps prevent the agent from using irrelevant or unauthorized information.

### 7.8 Glossary

The UI should include a glossary for common terms, software names, hardware references, acronyms, and internal project concepts that new users may not understand.

### 7.9 Color-Coded Node Health

Document nodes should be color-coded based on health:

- Green: Fresh and verified

- Yellow: Aging or needs review soon

- Red: Stale, conflicting, or broken

- Gray/locked: User does not have access

This makes the graph an instant documentation health dashboard.

### 7.10 Node Size Based on Importance

Frequently accessed or highly referenced documents should appear larger in the graph. This helps users quickly identify important knowledge hubs.

### 7.11 Diff and Review Side Panel

When the agent proposes a change, the UI should show:

- Before and after diff

- Source evidence

- Confidence score

- Risk level

- Approve/reject controls

### 7.12 Provenance Panel

When a user selects a node, the UI should show:

- Document owner

- Source references

- Last verified stamp

- Linked code or config

- Recent changes

- Approval history

- Rollback option

### 7.13 Conflict Edges

The graph should display conflict edges between contradictory documents. These can be shown as red dashed lines to make inconsistencies easy to identify.

### 7.14 Permission-Aware Fog

Documents the user cannot access should appear dimmed, blurred, or locked. This visually reinforces permission boundaries without exposing restricted content.

---

## 8. Agent Architecture

DocGuardian AI uses a **cost-conscious agent design** suited to the Azure student plan. Instead of many independent LLM agents (each consuming separate quota), it uses a thin orchestrator plus **two LLM-backed agents**, and pushes all deterministic work (search, deduplication, git metadata, ACL checks, sandbox execution) into plain **services/tools** that cost no model quota.

### 8.1 Orchestrator (Thin Router — No LLM)

The orchestrator is a **code-level router**, not an LLM agent. It receives user requests, document events, and source-of-truth signals, calls the deterministic services it needs (search, git metadata, ACL), and invokes an LLM agent only when reasoning or drafting is actually required. Keeping orchestration rule-based avoids spending Azure OpenAI quota on routing.

### 8.2 LLM Agents (Only Two)

| Agent | Merges | Responsibility |
| --- | --- | --- |
| **Curator Agent** | Intake + Resolver + Placement + Authoring | Understands the input, reasons over retrieved related docs, decides the action (create / update / merge / link / deprecate / flag), and drafts the proposed change with evidence and a confidence score |
| **Guardian Agent** | Verification + Governance | Judges whether a proposed change is safe: reviews sandbox/verification results, checks for conflicts, and produces the approve/needs-review recommendation with ACL and provenance context |

This is the **"a couple of agents with one tool layer"** model: two reasoning agents share a single MCP/tool layer.

### 8.3 Deterministic Services (No LLM Cost)

These do the heavy lifting without any model calls, which is what keeps the system affordable on a student plan:

| Service / Tool | Responsibility (formerly an "agent") |
| --- | --- |
| Retrieval service | Similarity search, duplicate detection, related-doc lookup (vector index) |
| Ingestion service | Sparse git clone, commit-metadata extraction, incremental refresh |
| Verification sandbox | Runs build/test/doc commands in an isolated container, returns pass/fail |
| Governance/ACL service | Enforces read/write permissions, writes provenance, handles rollback |

The Curator and Guardian agents call these as **tools**, so the only true LLM invocations per request are: (1) one Curator call to reason + draft, and (2) one Guardian call to judge — roughly **two LLM calls per proposal**, which is well within student-plan limits. For the simplest chat questions, only a single Curator call (RAG answer) is made.

---

## 8A. System Architecture (End-to-End)

This section describes the complete DocGuardian AI pipeline, tracing a single document from the moment it leaves a GitHub repository as clone metadata, through the backend services and AI embedding layer, and finally to the interactive frontend graph. It is intended to be detailed enough that any team member can implement their slice without ambiguity about inputs, outputs, and contracts between layers.

### 8A.1 High-Level Layered View

DocGuardian AI is organized into five horizontal layers. Data flows **upward** (ingestion → UI) and control/approvals flow **downward** (UI → governed writes). Each arrow in the diagram below carries a specific, versioned payload; the exact JSON shape of every payload is defined in the subsection for that layer.

```text
+=============================================================================+
|                          5 · FRONTEND LAYER                                 |
|   [Graph View]   [Chat]   [Diff/Review Panel]   [Metrics + Provenance]      |
+=============================================================================+
        ^                ^                 ^                    ^
        |  GraphDTO      |  ChatAnswer     |  AgentProposal     |  MetricsDTO
        |  (8A.6)        |  (8A.4)         |  (8A.4)            |  (8A.5)
        v                v                 v                    v
+=============================================================================+
|                       4 · BACKEND / API LAYER                               |
|   [REST + WebSocket API]        [Background Job Queue]                      |
|   [Metadata + Graph Store]      [Verification Sandbox]                      |
+=============================================================================+
     ^  AgentProposal        ^  DocChunk[]            ^  SandboxResult
     |  (8A.4)               |  (8A.3)                |  (8A.5)
     v                       v                        v
+=============================================================================+
|                      3 · AI / EMBEDDING LAYER                               |
|   [Embedding Generator] -> [Vector Index] -> [Orchestrator -> Curator]      |
|                                                   -> [Guardian Agent]       |
+=============================================================================+
        ^  DocChunk (8A.3)                  ^  GraphEdge[] (8A.3)
        |                                   |
        v                                   v
+=============================================================================+
|                       2 · PROCESSING LAYER                                  |
|   [Normalizer] -> [Heading-Aware Chunker] -> [Link/Reference Extractor]     |
+=============================================================================+
        ^  RawDocument / DocumentAdded / DocumentDeleted  (8A.2)
        |
        v
+=============================================================================+
|                       1 · INGESTION LAYER                                   |
|   [Sparse/Shallow git clone]  ->  [Commit Metadata Extractor]              |
|   [Incremental Refresh Watcher]                                            |
|   Sources: microsoft/{playwright, vscode, onnxruntime, garnet}            |
+=============================================================================+
```

**Reading the diagram:** a document is born at Layer 1 as a `RawDocument`, becomes a set of `DocChunk` + `GraphEdge` records at Layer 2, gains a vector embedding and (when acted on) an `AgentProposal` at Layer 3, is persisted and served by Layer 4, and is finally rendered for human review at Layer 5. The label on each arrow names the **data format** crossing that boundary and the subsection where its schema is defined.

### 8A.2 Layer 1 — Data Ingestion (Starting From GitHub Clone Metadata)

Ingestion is the entry point of the entire system. It deliberately starts from **git clone metadata rather than full repository contents** so the corpus stays small, cheap, and verifiable. (The clone commands themselves are detailed in Section 9.4; this section describes the architecture and the exact data that flows out of it.)

**Inputs.** A configuration-driven repository list. This is the only thing an operator edits to onboard a new source:

```json
// repos.config.json — the single source of truth for ingestion
[
  {
    "repo": "microsoft/playwright",
    "url": "https://github.com/microsoft/playwright",
    "branch": "main",
    "docGlobs": ["docs/**/*.md"],
    "refreshIntervalMinutes": 60
  },
  {
    "repo": "microsoft/vscode",
    "url": "https://github.com/microsoft/vscode",
    "branch": "main",
    "docGlobs": ["**/*.md"],
    "refreshIntervalMinutes": 120
  }
]
```

**Stages (with the data produced at each step):**

1. **Metadata-only clone.** Each repo is cloned with `--depth 1 --filter=blob:none --sparse`, producing a working tree with commit metadata but no file blobs. This is the cheapest possible "handshake" with GitHub and avoids API tokens and rate limits. At this point the only data that exists locally is the *commit graph and tree listing* — no document bytes yet.
2. **Sparse folder selection.** `git sparse-checkout set <docGlobs>` triggers download of only the documentation blobs the system actually needs. The output is a filtered list of file paths plus their now-present blob contents.
3. **Commit metadata extraction.** For every selected file, `git log -1 --format="%H|%an|%ae|%cI" -- <path>` yields the latest commit SHA, author name, author email, and ISO commit date. This tuple is the atomic unit of source-of-truth and feeds the verification stamp (Section 6.2) and node-health coloring (Section 7.9).
4. **Raw document handoff.** Each file is emitted to the Processing Layer as exactly one `RawDocument` record.

**Output data format — `RawDocument`** (the single record type leaving Layer 1):

```jsonc
{
  "docId": "playwright/docs/src/intro.md",   // stable key: "<repo-short>/<path>"
  "repo": "microsoft/playwright",            // full GitHub slug
  "path": "docs/src/intro.md",               // path relative to repo root
  "branch": "main",
  "content": "# Getting Started\n\nnpm init playwright@latest ...", // raw UTF-8 markdown
  "byteSize": 4821,                           // raw size in bytes
  "encoding": "utf-8",
  "commitSha": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0", // 40-char hex
  "commitAuthor": "Jane Doe",
  "commitEmail": "jane@example.com",
  "commitDate": "2026-05-18T14:22:07Z",       // ISO 8601
  "fetchedAt": "2026-06-23T10:00:00Z",        // when ingestion ran
  "contentHash": "sha256:9f86d081884c7d659..." // sha256 of content, for idempotency
}
```

**Field semantics that matter downstream:**

- `docId` is the **primary key** used by every other layer — chunks, edges, embeddings, and graph nodes all reference it.
- `commitSha` + `commitDate` are propagated, unchanged, into every chunk and every piece of evidence, so any UI node can be traced to an exact commit.
- `contentHash` enables **idempotent ingestion**: if a refresh produces the same hash, no re-processing occurs.

**Incremental refresh.** A watcher periodically runs `git fetch --depth 1 origin` + `git reset --hard origin/<branch>`. It then diffs commit SHAs per file and emits one of three event records:

```jsonc
// DocumentAdded  — a new doc path appeared
{ "type": "DocumentAdded",   "docId": "vscode/build/new.md", "raw": { /* RawDocument */ } }

// DocumentChanged — commitSha (and contentHash) changed
{ "type": "DocumentChanged", "docId": "vscode/build.md",
  "previousCommitSha": "f00d...", "raw": { /* RawDocument */ } }

// DocumentDeleted — path no longer present in the tree
{ "type": "DocumentDeleted", "docId": "vscode/old.md", "lastKnownCommitSha": "dead..." }
```

`DocumentChanged` and `DocumentAdded` are routed back through the Processing Layer; `DocumentDeleted` flags the corresponding graph node as stale/broken. This makes the continuous validation loop (Section 6.1) **event-driven** instead of a one-time import.

### 8A.3 Layer 2 — Processing (Normalize, Chunk, Link)

The Processing Layer turns one `RawDocument` into many embeddable, graph-aware units. It is pure and deterministic: the same `RawDocument` always yields the same chunks and edges, which keeps re-processing idempotent.

1. **Normalizer.** Strips YAML front-matter, resolves relative image/link paths to absolute `docId`s, and converts markdown to clean text **while preserving** headings, code fences, and command blocks verbatim (commands are exactly what the Verification Agent later executes, so they must not be reformatted). It also records the character offset of every heading so chunk line ranges are exact.
2. **Heading-aware chunker.** Splits each document along its heading hierarchy into overlapping chunks (target ~500–800 tokens, ~80-token overlap). Splitting on headings keeps each chunk semantically self-contained, and the overlap prevents losing context across a boundary. Each chunk inherits the parent's `docId`, `commitSha`, heading path, and exact line range so evidence can be cited back to specific lines.
3. **Link/reference extractor.** Parses relative markdown links, "see also" references, and shared anchor/command names to produce candidate **graph edges**. At this stage only structural edges (`references`) are emitted; semantic edges (`duplicate-of`, `conflicts-with`) are added later by the AI layer once embeddings exist.

**Output data format — `DocChunk`** (sent to the embedding layer; one document fans out into many):

```jsonc
{
  "chunkId": "playwright/docs/src/intro.md#Installation#0", // docId#headingSlug#ordinal
  "docId": "playwright/docs/src/intro.md",
  "repo": "microsoft/playwright",
  "headingPath": ["Getting Started", "Installation"],  // breadcrumb of headings
  "ordinal": 0,                                          // chunk index within the doc
  "text": "npm init playwright@latest\n\nThis installs ...", // clean, embeddable text
  "tokenCount": 612,
  "lineRange": [12, 41],         // 1-based [startLine, endLine] in the source file
  "charRange": [180, 1422],      // byte offsets, for precise highlighting
  "containsCommands": true,      // true if a fenced command block is present
  "commitSha": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0",
  "commitDate": "2026-05-18T14:22:07Z",
  "contentHash": "sha256:1b4f0e9851971998e732..." // hash of text, for idempotent re-embed
}
```

**Output data format — `GraphEdge`** (sent to the metadata/graph store):

```jsonc
{
  "edgeId": "playwright/docs/src/intro.md->playwright/docs/src/ci.md:references",
  "from": "playwright/docs/src/intro.md",  // source docId
  "to": "playwright/docs/src/ci.md",       // target docId
  "type": "references",                     // references | duplicate-of | conflicts-with | deprecated-by
  "weight": 1.0,                            // structural=1.0; semantic edges carry similarity score
  "evidence": {                             // why this edge exists
    "reason": "explicit-markdown-link",
    "anchorText": "see the CI guide",
    "lineRange": [55, 55]
  },
  "createdBy": "link-extractor",            // link-extractor | resolver-agent
  "commitSha": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0"
}
```

The `from`/`to`/`type`/`weight` quartet is exactly what the frontend graph (Layer 5) consumes to draw nodes and color/stroke edges — e.g. `conflicts-with` renders as a red dashed line (Section 7.13).

### 8A.4 Layer 3 — AI & Embeddings

This layer gives the system its semantic understanding and reasoning. It consumes `DocChunk`s, produces vectors, and — when an action is requested — emits `AgentProposal`s.

**Embedding generation.** Each `DocChunk.text` is embedded via Azure OpenAI embeddings (e.g. `text-embedding-3-large`, 3072 dimensions) into a fixed-length float vector. The vector plus its metadata is upserted into the vector index keyed by `chunkId`. Re-embedding is skipped when `contentHash` is unchanged.

**Stored vector record format** (what lives in the index):

```jsonc
{
  "chunkId": "playwright/docs/src/intro.md#Installation#0",
  "docId": "playwright/docs/src/intro.md",
  "repo": "microsoft/playwright",
  "vector": [0.0123, -0.0481, 0.0067, "...3072 floats..."],
  "model": "text-embedding-3-large",
  "dim": 3072,
  "text": "npm init playwright@latest ...",  // stored for re-ranking + citation
  "headingPath": ["Getting Started", "Installation"],
  "lineRange": [12, 41],
  "commitSha": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0",
  "acl": ["team:qa", "role:engineer"]          // permission tags enforced at query time
}
```

**Vector index.** Azure AI Search (hybrid: BM25 keyword + vector) is the primary option; pgvector is a lighter local fallback for the hackathon. A query returns scored matches:

```jsonc
// SearchResult — returned by the index for any similarity query
{
  "query": "how do I run playwright tests in CI",
  "matches": [
    {
      "chunkId": "playwright/docs/src/ci.md#GitHub-Actions#0",
      "docId": "playwright/docs/src/ci.md",
      "score": 0.8917,            // cosine similarity in [0,1]
      "text": "npx playwright test ...",
      "lineRange": [8, 30],
      "commitSha": "9a8b7c..."
    }
  ]
}
```

The index powers three jobs, each with a concrete rule:

- **Similarity search** — top-k chunks (`score` desc) drive related-document retrieval and the chat RAG step.
- **Duplicate detection** — any chunk pair from *different* `docId`s with `score >= 0.92` becomes a `duplicate-of` `GraphEdge` candidate (with `weight = score`).
- **Conflict detection seed** — high text similarity (`score >= 0.85`) but a divergence in extracted commands/values flags a `conflicts-with` candidate for agent confirmation.

**Agent orchestration (ties to Section 8).** The thin orchestrator consumes `SearchResult`s and makes at most two LLM calls: the **Curator Agent** reasons over the retrieved related docs, decides the action (create / update / merge / link / deprecate / flag), and drafts the change with the reasoning LLM; the **Guardian Agent** then reviews the sandbox/verification result and conflicts to produce the approve/needs-review judgment. Similarity search, duplicate detection, git metadata, ACL checks, and the sandbox run are deterministic services (Section 8.3) and consume no model quota.

**Evidence enforcement.** Every LLM answer or proposed edit must carry its supporting chunk IDs, commit SHAs, and a confidence score; weak evidence (e.g. `confidence < 0.5` or no supporting chunk) forces the explicit "needs human review" path (Sections 6.3–6.4).

**Output data format — `AgentProposal`** (the central artifact handed to the backend and rendered in the diff panel):

```jsonc
{
  "proposalId": "prop_01H..",
  "action": "merge",                  // create | update | merge | link | deprecate | flag
  "targetDocId": "vscode/build.md",
  "sourceDocIds": ["vscode/build.md", "vscode/contributing.md"],
  "diff": {
    "before": "Run `yarn` then `yarn watch`.",
    "after":  "Run `npm ci` then `npm run watch`.",
    "format": "unified",              // unified | side-by-side
    "lineRange": [40, 44]
  },
  "draft": "## Building\n\nRun `npm ci` ...", // full proposed document body
  "evidence": [
    {
      "chunkId": "vscode/build.md#Build#0",
      "docId": "vscode/build.md",
      "commitSha": "f00dcafe...",
      "lineRange": [5, 22],
      "quote": "npm ci installs exact versions",
      "relevance": 0.88
    }
  ],
  "confidence": 0.82,                  // [0,1]; < 0.5 => forced human review
  "riskLevel": "medium",              // low | medium | high
  "conflictsWith": ["vscode/contributing.md"],
  "verification": {
    "sandboxRun": true,
    "passed": true,
    "command": "npm ci && npm run watch",
    "commitSha": "f00dcafe...",
    "durationMs": 18342
  },
  "uncertainty": null,                // string explanation when confidence is low
  "proposedBy": "curator-agent",     // curator drafts; guardian judges
  "createdAt": "2026-06-23T10:05:11Z"
}
```

**Output data format — `ChatAnswer`** (returned to the chat UI; always evidence-backed):

```jsonc
{
  "answer": "Run `npx playwright test` from the repo root.",
  "scope": "current-repo",            // mirrors the UI scope toggle (Section 7.7)
  "citations": [
    { "docId": "playwright/docs/src/ci.md", "lineRange": [8, 12],
      "commitSha": "9a8b7c...", "relevance": 0.91 },   // drives node glow intensity (8A.6.1)
    { "docId": "playwright/docs/src/intro.md", "lineRange": [12, 18],
      "commitSha": "a1b2c3...", "relevance": 0.64 }
  ],
  "confidence": 0.91,
  "needsHumanReview": false
}
```

### 8A.5 Layer 4 — Backend & API

The backend is the coordination and persistence hub between AI and UI.

- **API service** (FastAPI or Node/Fastify) exposes REST for CRUD/search and a WebSocket channel for live graph and proposal updates.
- **Background worker / job queue** runs the heavy, async work: scanning, chunking, embedding, and verification jobs triggered by ingestion events. Keeping these off the request path keeps the UI responsive.
- **Metadata + graph store** holds documents, chunks-to-doc mappings, graph edges, node health, ownership/ACLs, approvals, and provenance. Options: Azure Cosmos DB (document + graph) with Azure SQL for audit/approval records.
- **Verification sandbox** is an isolated container that checks out the repo at a specific commit and runs the relevant build/test/doc command, returning pass/fail to back the confidence score (Section 6.5).
- **Governance enforcement** applies ACLs at retrieval, answer, and write stages, and runs the propose to diff to approve to apply to provenance flow before any authoritative write (Sections 6.8, 6.10, 6.12).

**Representative API surface:**

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/ingest/refresh` | Trigger incremental refresh for one or all repos |
| `GET` | `/graph` | Return nodes + edges + health for the graph view |
| `GET` | `/search?q=` | Hybrid semantic search over chunks |
| `POST` | `/documents` | Drop-off intake (upload/paste/NL update) |
| `GET` | `/proposals/:id` | Fetch an `AgentProposal` with evidence + diff |
| `POST` | `/proposals/:id/approve` | Apply approved change + record provenance |
| `GET` | `/metrics` | Dashboard counters (stale fixed, conflicts resolved, etc.) |
| `WS` | `/stream` | Live proposal/graph/health updates |

**Persisted data format — `DocumentRecord`** (the canonical row in the metadata/graph store):

```jsonc
{
  "docId": "vscode/build.md",
  "repo": "microsoft/vscode",
  "path": "build.md",
  "title": "Building VS Code",
  "owner": "team:platform",
  "acl": ["team:platform", "role:engineer"],
  "health": "yellow",                 // green | yellow | red | gray (Section 7.9)
  "importance": 0.74,                 // 0..1, drives node size (Section 7.10)
  "lastVerifiedSha": "f00dcafe...",   // backs the verification stamp (Section 6.2)
  "lastVerifiedAt": "2026-06-20T09:00:00Z",
  "currentCommitSha": "f1e2d3c4...",  // if != lastVerifiedSha => candidate stale
  "chunkIds": ["vscode/build.md#Build#0", "vscode/build.md#Test#1"],
  "createdAt": "2026-06-01T00:00:00Z",
  "updatedAt": "2026-06-23T10:06:00Z"
}
```

**Persisted data format — `ProvenanceEntry`** (append-only audit row, written on every governed change):

```jsonc
{
  "entryId": "prov_01H..",
  "docId": "vscode/build.md",
  "proposalId": "prop_01H..",
  "action": "merge",
  "approvedBy": "user:alice@example.com",
  "approvedAt": "2026-06-23T10:07:30Z",
  "previousVersionRef": "blob:sha256:aaa...", // enables one-click rollback (Section 6.10)
  "newVersionRef": "blob:sha256:bbb...",
  "evidenceSnapshot": [ { "chunkId": "vscode/build.md#Build#0", "commitSha": "f00dcafe..." } ],
  "confidence": 0.82,
  "reason": "Unified yarn/npm build instructions to npm"
}
```

**Verification I/O — `SandboxRequest` / `SandboxResult`** (between backend and the isolated container):

```jsonc
// SandboxRequest (backend -> sandbox)
{ "repo": "microsoft/vscode", "commitSha": "f00dcafe...",
  "command": "npm ci && npm run watch", "timeoutMs": 60000 }

// SandboxResult (sandbox -> backend)
{ "passed": true, "exitCode": 0, "durationMs": 18342,
  "stdoutTail": "...watch build finished", "stderrTail": "" }
```

### 8A.6 Layer 5 — Frontend

The frontend renders the governed knowledge and drives human-in-the-loop actions. It is a read/act client over the backend API and WebSocket stream. The frontend is a **first-class layer**, not an afterthought: it owns perceived performance (lazy/chunked rendering), the human-in-the-loop trust surfaces (diff, evidence, confidence, provenance), and the "show your work" visuals that make the AI feel grounded rather than magical.

- **Document graph view** (React Flow for 2D MVP; React Three Fiber for optional 3D) renders nodes sized by importance (Section 7.10) and colored by health (Section 7.9), with conflict edges as red dashed lines (Section 7.13) and permission fog for inaccessible nodes (Section 7.14). Chunked/lazy rendering keeps large corpora responsive (Section 7.3).
- **Drop-off area** posts uploads/pastes/NL updates to `/documents`, kicking off the intake to placement flow.
- **Evidence-backed chat** calls `/search` + the agent layer, returning answers with source citations, confidence, and a scope toggle (Sections 7.6–7.7).
- **Diff / review side panel** renders an `AgentProposal` (before/after diff, evidence, confidence, risk) and posts approve/reject (Section 7.11).
- **Provenance + metrics surfaces** read `/proposals` and `/metrics` to show ownership, last-verified stamps, approval history, rollback, and impact counters (Sections 7.12, 6.11).

#### 8A.6.1 "Show Your Work" — Highlighting the Nodes the AI Used

When a user asks the AI something, the answer is never a black box: every `ChatAnswer.citations[]` entry (Section 8A.4) maps to a real `docId` that already exists as a node in the graph. The moment an answer streams back, the frontend takes those cited `docId`s and tells the graph to **subtly blink/glow the exact nodes the AI drew its answer from** (this is the realization of Section 7.2, *Referenced Document Highlighting*). This makes the data provenance instantly visible — the user literally sees which documents the AI "touched."

**Data that drives the effect.** The chat response already carries everything needed; the frontend derives a lightweight highlight instruction from it:

```jsonc
// GraphHighlightEvent — derived on the client from ChatAnswer.citations (or pushed over WS)
{
  "reason": "chat-evidence",          // chat-evidence | proposal-evidence | hover-references
  "nodeIds": ["playwright/docs/src/ci.md", "playwright/docs/src/intro.md"],
  "edgeIds": ["playwright/docs/src/intro.md->playwright/docs/src/ci.md:references"],
  "intensity": 0.91,                  // taken from citation relevance/confidence -> glow strength
  "ttlMs": 4000                       // auto-fade after this duration
}
```

**Visual treatment (subtle and appealing, not distracting):**

- A soft **pulsing glow / halo** on each cited node — opacity eased between ~0.55 and ~1.0 on a slow ~1.4s sine loop, so it "breathes" rather than flashes.
- The glow color is **derived from the node's existing health color** (green/yellow/red) so highlighting never overrides the health signal — it just brightens and adds a halo.
- Cited nodes get a brief one-time **scale "pop"** (1.0 → ~1.08 → 1.0) on first appearance to draw the eye, then settle into the gentle pulse.
- Connecting `references` edges between cited nodes animate a **flowing dash** to imply the AI traversed those links.
- Intensity scales with citation relevance (`intensity` field): the most-relevant source pulses brightest, weaker supporting sources glow faintly.
- Everything **auto-fades after `ttlMs`**, and respects `prefers-reduced-motion` (falls back to a static halo, no pulsing) for accessibility.

**Interaction loop.** Hovering a citation chip in the chat re-triggers the highlight for just that one node; clicking a citation chip pans/zooms the graph to that node and opens its provenance panel (Section 7.12). Conversely, selecting a node highlights the chat citations that reference it. The same `GraphHighlightEvent` mechanism (with `reason: "proposal-evidence"`) lights up the nodes behind an `AgentProposal` while it sits in the diff panel, so the user sees the evidence base of a proposed change before approving it.

**Consumed data format — `GraphDTO`** (the exact payload `/graph` returns to the graph view):

```jsonc
{
  "nodes": [
    {
      "id": "vscode/build.md",
      "label": "Building VS Code",
      "health": "yellow",        // -> node color (Section 7.9)
      "size": 0.74,              // -> node radius (Section 7.10)
      "accessible": true,        // false -> render permission fog (Section 7.14)
      "repo": "microsoft/vscode"
    }
  ],
  "edges": [
    {
      "from": "vscode/build.md",
      "to": "vscode/contributing.md",
      "type": "conflicts-with",  // -> red dashed line (Section 7.13)
      "weight": 0.87
    }
  ]
}
```

**Consumed data format — `MetricsDTO`** (the exact payload `/metrics` returns to the dashboard):

```jsonc
{
  "staleDetected": 42,
  "staleFixed": 30,
  "duplicatesRemoved": 11,
  "conflictsDetected": 9,
  "conflictsResolved": 6,
  "brokenLinksResolved": 4,
  "docsWithVerificationStamp": 0.78,   // fraction in [0,1]
  "avgTimeToUpdateHours": 3.2,
  "asOf": "2026-06-23T10:08:00Z"
}
```

### 8A.7 End-to-End Sequence (Drop-Off to Approved Write)

The following trace shows the exact data format crossing each hop, from a user pasting a doc to an approved, provenance-logged write:

```text
USER (Frontend)        BACKEND API      ORCHESTRATOR+CURATOR/GUARDIAN  VECTOR INDEX  SANDBOX   STORE
      |                     |                       |                    |            |           |
      |  POST /documents    |                       |                    |            |           |
      |  { RawDocument }    |                       |                    |            |           |
      |-------------------->|                       |                    |            |           |
      |                     |  Intake event         |                    |            |           |
      |                     |---------------------->|                    |            |           |
      |                     |                       |  similarity +      |            |           |
      |                     |                       |  duplicate query   |            |           |
      |                     |                       |------------------->|            |           |
      |                     |                       |   SearchResult[]   |            |           |
      |                     |                       |<-------------------|            |           |
      |                     |                       | Curator: reason +  |            |           |
      |                     |                       | decide + draft     |            |           |
      |                     |                       |  SandboxRequest    |            |           |
      |                     |                       |--------------------------------->|          |
      |                     |                       |          SandboxResult           |          |
      |                     |                       |<---------------------------------|          |
      |                     |   AgentProposal       |                    |            |           |
      |                     |   (diff+evidence+conf)|                    |            |           |
      |                     |<----------------------|                    |            |           |
      |   WS: AgentProposal |                       |                    |            |           |
      |<--------------------|                       |                    |            |           |
      |  (review in Diff panel)                     |                    |            |           |
      | POST /proposals/:id/approve                 |                    |            |           |
      |-------------------->|                       |                    |            |           |
      |                     |  apply change + write DocumentRecord + ProvenanceEntry  |           |
      |                     |-------------------------------------------------------->|           |
      |  WS: GraphDTO +     |                       |                    |            |           |
      |      MetricsDTO     |                       |                    |            |           |
      |<--------------------|                       |                    |            |           |
```

### 8A.8 Cross-Cutting Concerns

- **Provenance everywhere.** Every chunk, edge, and proposal carries its originating `commitSha`, so any node in the graph can be traced back to an exact source line at an exact commit.
- **Idempotent ingestion.** Re-running ingestion on an unchanged commit is a no-op (SHA comparison), so refreshes are safe and cheap.
- **Permission propagation.** ACLs attach at the document level in the store and are enforced uniformly at retrieval, answer, and write — the frontend never receives content the user cannot access.
- **Configuration-driven sources.** Adding a repository is a config change (URL + folder globs), requiring no architectural changes across any layer.

---

## 9. Data Sources

DocGuardian AI can use multiple data sources depending on permissions and integration availability.

### 9.0 Hackathon Corpus (Repositories Used)

For the hackathon, DocGuardian AI ingests documentation and source-of-truth signals from four real, large, doc-rich open-source repositories. These provide naturally occurring stale, duplicate, and conflicting documentation (especially around build, test, and setup workflows), which makes them ideal for demonstrating detection and governance.

| Repository | Source | Why It Is Useful |
| --- | --- | --- |
| Playwright | `microsoft/playwright` | Rich end-to-end testing docs, multi-language guides, frequent setup/test instructions that drift over time |
| VS Code | `microsoft/vscode` | Very large codebase with extensive contributor, build, and architecture docs spread across many folders |
| ONNX Runtime | `microsoft/onnxruntime` | AI model inference runtime with dense build, platform, and usage documentation prone to version-specific staleness |
| Garnet | `microsoft/garnet` | Microsoft cache-store project with focused operational, benchmarking, and getting-started docs |

For each repository, DocGuardian AI treats the following as ingestible signals:

- Markdown documentation (`**/*.md`)

- Commit history and pull requests as freshness and provenance signals

- Configuration and build scripts referenced by the docs for verification

To keep the demo reliable, ingestion can be scoped to documentation folders rather than full repository clones.

### 9.1 Documentation Sources

- Company documentation

- Wiki pages

- Markdown files

- Repository docs

- Onboarding guides

- Architecture documents

- Runbooks

- Troubleshooting guides

### 9.2 Engineering Sources

- Git repositories

- Commits

- Pull requests

- Configuration files

- Build scripts

- Test instructions

- CI/CD pipeline output

- Issue tracking systems

- Work items or tickets

### 9.3 Collaboration Sources

- Teams messages or channels through MCP-style integration

- Meeting notes

- Engineering discussions

- Review comments

- Team announcements

These sources can help determine whether documentation still matches current engineering reality.

### 9.4 Data Retrieval and Ingestion Mechanism

DocGuardian AI retrieves documentation directly from the source repositories using **sparse, shallow git clones** rather than the GitHub API. This avoids API tokens and rate limits, scopes each clone to the relevant documentation folders, and provides commit metadata for free.

#### How Retrieval Works

For each repository, the ingestion step performs a metadata-only clone, selects only the documentation folders, and then downloads just those files:

```powershell
# 1. Clone metadata only — no file contents, no deep history
git clone --depth 1 --filter=blob:none --sparse https://github.com/microsoft/playwright data/playwright

# 2. Select only the documentation folders
cd data/playwright
git sparse-checkout set docs

# 3. Git downloads only the blobs inside the selected folders
```

| Flag | Effect | Why It Matters |
| --- | --- | --- |
| `--depth 1` | Only the latest commit, no history | Skips the large histories of repos like VS Code and ONNX Runtime |
| `--filter=blob:none` | Defers downloading file contents | Only blobs that are checked out are fetched |
| `--sparse` | Starts with an empty working tree | Nothing is downloaded until folders are selected |
| `git sparse-checkout set <dir>` | Downloads only the chosen folders | Avoids cloning gigabyte-scale repositories |

#### Commit Metadata as Source-of-Truth Signals

Even with a shallow clone, each retrieved file retains git metadata that powers freshness and provenance features:

```powershell
# Latest commit SHA and date that touched a given document
git log -1 --format="%H %cs" -- docs/intro.md
```

This commit SHA and date directly support the verification stamp in Section 6.2 (`Last verified against commit <sha> on <date>`) and the color-coded node health described in Section 7.9.

#### Incremental Refresh (Upcoming Data)

The same mechanism keeps the corpus current without re-cloning. Refreshing pulls only new or changed documents:

```powershell
cd data/vscode
git fetch --depth 1 origin
git reset --hard origin/main
```

On refresh, changed commit SHAs are detected and only modified documents are re-chunked, re-embedded, and re-verified. Deleted files are flagged as stale or broken, and newly added files are routed through the intake flow. This makes the continuous validation loop in Section 6.1 event-driven rather than a one-time import. The repository list is configuration-driven, so additional sources can be added without architectural changes.

---

## 10. Tech Stack

The stack below is **locked** for the hackathon build (decided 2026-06-23). It is optimized for the Azure student plan: a single Postgres instance for all storage, local vector search to avoid managed-service provisioning, and only two LLM-backed agents.

### 10.1 Frontend

- **React + TypeScript**
- **Vite** as the app shell (lightweight SPA; no SSR overhead)
- **Tailwind CSS** for styling
- **shadcn/ui** for reusable UI components
- **Monaco Editor** for the diff and document editing views

### 10.2 Graph and Tree Visualization

- **React Flow (2D)** is the locked choice for the relationship graph. It powers node health coloring, importance-based sizing, conflict edges, and the citation-driven node-blink highlighting (Section 8A.6.1).
- 3D (React Three Fiber) is explicitly deferred as a post-hackathon nice-to-have.

### 10.3 Backend

- **Python + FastAPI** for the REST + WebSocket API
- **Background worker** (FastAPI background tasks / a lightweight queue) for scanning, embedding, and verification jobs

### 10.4 Storage

- **A single PostgreSQL instance** holds everything: document metadata, graph edges, audit logs, approvals, and provenance.
- **pgvector** (the same Postgres) stores embeddings for similarity, duplicate, and conflict detection.
- **Git** remains the authoritative source-of-truth for versioned docs (via sparse/shallow clones, Section 9.4).
- Managed Azure storage (Cosmos, Blob, Azure SQL, Azure AI Search) is intentionally **not** used for the MVP to stay within student-plan limits.

### 10.5 AI and Retrieval

- **Azure OpenAI** with exactly two deployments: one **chat** model (Curator + Guardian reasoning) and one **embeddings** model.
- **pgvector** provides hybrid retrieval (keyword + vector) locally.
- **RAG pipeline with source-citation enforcement** — every answer/edit carries supporting chunk IDs, commit SHAs, and a confidence score.
- **Two LLM agents** (Curator + Guardian) coordinated by a thin code-level orchestrator; all other work is deterministic services (Section 8.3).

### 10.6 Verification Environment

The verification sandbox is **built for real** (not mocked):

- **Containerized execution** in an isolated environment
- **Repo checkout at a specific commit** before running commands
- **Script execution** for the relevant build/test/doc commands
- **Validation result attached to the confidence score** (Section 6.5)

### 10.7 Governance and Security

For the MVP, authentication is **simulated** while governance mechanics are real:

- **Mocked auth**: a fake user + role map stands in for Microsoft Entra ID
- **Role-based access control** and **document-level ACL enforcement** against that map
- **Approval workflow**, **audit log**, **provenance tracking**, and **rollback** are all backed by Postgres
- Real Entra ID integration is deferred to post-hackathon.

---

## 11. Demo Flow

A strong hackathon demo can show the following sequence:

### Step 1: User Uploads or Pastes Documentation

The user drops a new document into DocGuardian AI.

### Step 2: Agent Finds Related Documents

The Curator agent (using the retrieval service) identifies existing documents that overlap or conflict with the new content.

### Step 3: Graph Highlights Relationships

The UI shows related documents as nodes in the graph. Fresh documents appear green, stale documents appear red, and restricted documents appear locked or dimmed.

### Step 4: Conflict Detection

The agent detects that two documents provide different instructions for the same workflow.

### Step 5: Proposed Merge

The Curator agent proposes a merged canonical version.

### Step 6: Evidence and Confidence

The verification agent shows evidence from commits, config files, or documentation sources and assigns a confidence score.

### Step 7: Human Review

The UI shows a before/after diff and asks the user to approve or reject.

### Step 8: Provenance Log

After approval, the governance agent records who approved the change, what changed, why it changed, and which sources supported it.

### Step 9: Metrics Dashboard

The dashboard updates to show stale documents fixed, conflicts resolved, and duplicates reduced.

---

## 12. Business Value

DocGuardian AI provides value by:

- Reducing onboarding time for new engineers

- Improving trust in documentation

- Lowering time spent searching for the correct process

- Preventing outdated instructions from spreading

- Reducing duplicate and conflicting documentation

- Helping teams maintain docs continuously instead of reactively

- Supporting safer enterprise AI adoption through permissions, provenance, and approval flows

---

## 13. Why This Is Valuable for a Hackathon

This project is strong for a hackathon because it has:

- A clear customer pain point

- A visual demo-friendly interface

- Strong AI-agent narrative

- Practical enterprise trust story

- Measurable business impact

- Permission-aware design

- Human-in-the-loop workflow

- Strong connection to real engineering productivity problems

The key is not to build every feature fully. The demo should focus on a believable slice:

1. Document ingestion

2. Duplicate/conflict detection

3. Graph visualization

4. AI-proposed update

5. Evidence/confidence panel

6. Human approval flow

7. Metrics/provenance view

---

## 14. MVP Scope

For the hackathon MVP, the team should focus on a small but compelling version.

### Must Have

- Upload or paste documentation

- Search existing documents

- Detect related or duplicate docs

- Show document graph

- Identify stale/conflicting content

- Generate proposed update

- Show evidence and confidence

- Human approve/reject flow

### Should Have

- Color-coded document health

- Diff side panel

- Provenance log

- Basic metrics dashboard

- Scope toggle

### Nice to Have

- 3D document map

- Sandbox verification

- Multi-agent orchestration UI

- Permission-aware fog

- Learning from accept/reject

- Glossary generation

- Teams or ticket integration

---

## 15. Suggested Team Split for 4 People

### Person 1: Frontend and Demo Experience

Owns:

- Main UI

- Document graph

- Upload/drop-off area

- Chat panel

- Diff/review side panel

- Demo polish

### Person 2: Retrieval and Document Intelligence

Owns:

- Document ingestion

- Embeddings/search

- Duplicate detection

- Related document retrieval

- Conflict detection logic

### Person 3: Agent Orchestration and AI Reasoning

Owns:

- Orchestrator agent

- Sub-agent prompting

- Authoring agent

- Resolver/placement logic

- Evidence-backed answer generation

- Confidence score design

### Person 4: Governance, Verification, and Metrics

Owns:

- ACL/read-write permission simulation

- Approval workflow

- Provenance log

- Rollback simulation

- Metrics dashboard

- Optional sandbox verification mock

---

## 16. Success Metrics

DocGuardian AI can be evaluated using the following metrics:

- Number of stale documents detected

- Number of duplicate documents identified

- Number of conflicts detected

- Number of proposed fixes accepted by users

- Number of broken links found

- Reduction in repeated onboarding questions

- Time saved when finding test/build instructions

- Percentage of documents with verification stamps

- Percentage of AI edits with evidence and confidence

---

## 17. Risks and Mitigations

| Risk | Mitigation |
| --- | --- |
| AI may hallucinate documentation updates | Require evidence, confidence score, and human approval |
| Agent may access restricted content | Enforce ACLs at retrieval, answer, and write stages |
| Too many documents may make graph rendering heavy | Use chunked rendering and lazy loading |
| Verification may be difficult to fully implement | Use sandbox simulation for MVP and clearly show planned architecture |
| Conflict detection may be noisy | Start with obvious duplicate or contradictory workflow examples |
| Scope may be too large for hackathon | Focus demo on one repo or one documentation folder |

---

## 18. Final Pitch

DocGuardian AI turns engineering documentation from a passive knowledge base into an active, trustworthy, AI-maintained system.

It continuously checks whether documentation matches reality, detects stale or conflicting information, proposes evidence-backed fixes, and gives engineers a visual way to explore project knowledge. With human approval, provenance tracking, rollback, and permission-aware access control, DocGuardian AI is designed not just as a chatbot, but as an enterprise-ready documentation governance agent.

For engineering teams, this means faster onboarding, fewer duplicated docs, more reliable workflows, and significantly less manual documentation maintenance.
