---
name: ingest-repo
description: >-
  Fetch documentation from a GitHub repo into DocGuardian using a sparse, shallow
  git clone (no GitHub API, no tokens, no rate limits). USE WHEN the user wants to
  "ingest a repo", "add a documentation source", "pull docs for <repo>", "refresh
  the corpus", or onboard a new entry in repos.config.json. Clones only the
  configured doc folders and extracts commit metadata as source-of-truth signals.
---

# Ingest Repo (sparse/shallow clone)

Retrieve documentation directly from a source repository as cheap clone metadata,
per `README.md` §9.4. This is the deterministic Layer 1 ingestion procedure — it
costs no model quota.

## When to use

- Onboarding a new documentation source, or refreshing an existing one.
- Preparing the corpus before chunking/embedding for a demo.

## When NOT to use

- For full repository builds or non-doc files — only documentation globs.
- To fetch private repos requiring auth tokens — this skill is token-free by design.

## Procedure

Run from the repo root. Sources are defined in `repos.config.json`
(`repo`, `url`, `branch`, `docGlobs`, `refreshIntervalMinutes`).

### 1. Metadata-only clone (no blobs, no history)

```powershell
# Example: microsoft/playwright into data/playwright
git clone --depth 1 --filter=blob:none --sparse https://github.com/microsoft/playwright data/playwright
```

| Flag | Effect |
| --- | --- |
| `--depth 1` | Latest commit only, no history |
| `--filter=blob:none` | Defer downloading file contents |
| `--sparse` | Start with an empty working tree |

### 2. Select only the documentation folders

```powershell
cd data/playwright
git sparse-checkout set docs
```

Use the `docGlobs` from `repos.config.json`. Keep globs scoped (e.g. `docs/**/*.md`),
not `**/*.md` for huge repos like VS Code, to keep the demo fast and reliable.

### 3. Extract commit metadata per document (source-of-truth signal)

```powershell
# Latest commit SHA, author, email, ISO date that touched a given doc
git log -1 --format="%H|%an|%ae|%cI" -- docs/intro.md
```

This tuple powers the verification stamp (README §6.2) and node-health coloring
(§7.9). Emit one `RawDocument` per file with `commitSha`, `commitDate`, and a
`contentHash` (sha256 of content) for idempotency.

### 4. Incremental refresh (instead of re-cloning)

```powershell
cd data/vscode
git fetch --depth 1 origin
git reset --hard origin/main
```

Diff commit SHAs per file and emit `DocumentAdded` / `DocumentChanged` /
`DocumentDeleted`. Unchanged `contentHash` ⇒ skip (no re-processing).

## Safety

- Clone only into the gitignored `data/` directory; never commit cloned content.
- Respect `docGlobs` — do not download entire repositories.
- This procedure is read-only against remotes; it never pushes.
