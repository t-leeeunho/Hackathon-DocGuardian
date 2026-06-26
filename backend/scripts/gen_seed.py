"""Generate the demo seed (``backend/docker/init/01-seed.sql``).

The seed is loaded by the pgvector container's ``docker-entrypoint-initdb.d`` on a
fresh ``docker compose up`` and plants the **hero demo corpus**: the Garnet
".NET 8 vs .NET 6" build conflict (matching ``frontend/src/lib/fixtures.ts`` and
the Presenter Mode storyline), plus an ONNX Runtime duplicate/deprecated pair.

Why a generator instead of a hand-written ``.sql``? The ``chunks.embedding``
column holds real 384-dim fastembed vectors that cannot be authored by hand. This
script chunks + embeds the corpus through the *real* app pipeline
(``processing.processor`` + ``embeddings.provider``) so retrieval / ``/chat`` work
on the live backend exactly as they do after a normal ingest. Re-run it whenever
the demo corpus changes:

    backend/.venv/Scripts/python.exe -m scripts.gen_seed

Health colours are *derived* live by ``governance.store.get_governed_graph`` from
the edges + commit/verification signals seeded here (conflict -> red, duplicate ->
yellow, deprecated-by -> gray, verified -> green), so the live ``/graph`` tells the
same story as the offline fixtures.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

from app.embeddings.provider import LocalEmbeddingProvider
from app.models import RawDocument
from app.processing.conflicts import _edge_id
from app.processing.processor import chunk_document, extract_edges

OUT_PATH = Path(__file__).resolve().parents[1] / "docker" / "init" / "01-seed.sql"


def _utc(y: int, m: int, d: int) -> datetime:
    return datetime(y, m, d, 12, 0, 0, tzinfo=timezone.utc)


def _sha256(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- #
# The demo corpus. ``content`` drives chunking, embeddings, and the structural
# ``references`` edges (from markdown links). Conflict/duplicate/deprecated edges
# are added explicitly below so the detections are deterministic on stage.
# --------------------------------------------------------------------------- #
README = """# Garnet

Garnet is a remote cache-store from Microsoft Research that offers strong
performance, scalability, and low latency.

## Documentation

- [Build guide](docs/build.md) — how to build Garnet from source.
- Configuration and API references live under `docs/`.

## Quick start

Clone the repository and follow the [build guide](docs/build.md) to compile a
Release build.
"""

BUILD = """# Building Garnet from source

This is the canonical guide for building Garnet from source.

## Prerequisites

- The **.NET 8 SDK** (Garnet targets .NET 8).
- A C# toolchain and Git installed.
- See the [README](../README.md) for an overview.

## Build

Restore and compile a Release build from the repository root:

```bash
dotnet restore
dotnet build -c Release
```

## Run the tests

```bash
dotnet test -c Release
```
"""

BUILD_LEGACY = """# Building Garnet (legacy)

> Older build notes. May be out of date.

## Prerequisites

- Requires the **.NET 6 SDK**.

## Build

```bash
dotnet build
```

This page predates the .NET 8 migration and is kept only for reference.
"""

INSTALL = """# Installing ONNX Runtime

Install the ONNX Runtime Python package with pip.

## Install

```bash
pip install onnxruntime
```

For GPU support install `onnxruntime-gpu` instead.
"""

INSTALL_OLD = """# Installing ONNX Runtime (old)

Install the ONNX Runtime Python package with pip.

## Install

```bash
pip install onnxruntime
```

This page is superseded by the current install guide.
"""

INTRO = """# Playwright

Playwright enables reliable end-to-end testing for modern web apps.

## Next steps

Generate tests automatically with [codegen](codegen.md).
"""

CODEGEN = """# Test generator (codegen)

Use `playwright codegen` to record actions and generate test scripts.

```bash
npx playwright codegen https://example.com
```
"""

SETUP = """# VS Code setup

Install Visual Studio Code and the recommended extensions for your stack.

## Steps

1. Download VS Code.
2. Install the language extensions you need.
"""


# doc_id, repo, path, commit_sha, author, commit_date, last_verified_sha,
# last_verified_at, summary, content
CORPUS = [
    (
        "garnet/README.md", "garnet", "README.md",
        "6104587aa0b1c2d3e4f5061728394a5b6c7d8e9f", "garnet-maintainers",
        _utc(2026, 6, 20), "6104587aa0b1c2d3e4f5061728394a5b6c7d8e9f", _utc(2026, 6, 20),
        "Garnet overview and entry point to the build guide.", README,
    ),
    (
        "garnet/docs/build.md", "garnet", "docs/build.md",
        "4e44e3e9a1b2c3d4e5f60718293a4b5c6d7e8f90", "garnet-maintainers",
        _utc(2026, 6, 21), "4e44e3e9a1b2c3d4e5f60718293a4b5c6d7e8f90", _utc(2026, 6, 21),
        "Canonical guide: build Garnet from source with the .NET 8 SDK.", BUILD,
    ),
    (
        "garnet/docs/build-legacy.md", "garnet", "docs/build-legacy.md",
        "9acb2a3bb1c2d3e4f50617283940a5b6c7d8e9f0", "garnet-maintainers",
        _utc(2023, 1, 14), None, None,
        "Stale legacy build page that still targets the .NET 6 SDK.", BUILD_LEGACY,
    ),
    (
        "onnxruntime/docs/install.md", "onnxruntime", "docs/install.md",
        "a1c0ffee0011223344556677889900aabbccddee", "onnx-maintainers",
        _utc(2026, 6, 19), "a1c0ffee0011223344556677889900aabbccddee", _utc(2026, 6, 19),
        "Current ONNX Runtime install guide.", INSTALL,
    ),
    (
        "onnxruntime/docs/install-old.md", "onnxruntime", "docs/install-old.md",
        "b2deadbeef0011223344556677889900aabbccdd", "onnx-maintainers",
        _utc(2024, 3, 2), None, None,
        "Deprecated near-duplicate of the ONNX Runtime install guide.", INSTALL_OLD,
    ),
    (
        "playwright/docs/intro.md", "playwright", "docs/intro.md",
        "c3a1b2c3d4e5f60718293a4b5c6d7e8f90123456", "playwright-team",
        _utc(2026, 6, 18), "c3a1b2c3d4e5f60718293a4b5c6d7e8f90123456", _utc(2026, 6, 18),
        "Introduction to Playwright end-to-end testing.", INTRO,
    ),
    (
        "playwright/docs/codegen.md", "playwright", "docs/codegen.md",
        "d4b2c3d4e5f60718293a4b5c6d7e8f9012345678", "playwright-team",
        _utc(2026, 6, 18), "d4b2c3d4e5f60718293a4b5c6d7e8f9012345678", _utc(2026, 6, 18),
        "Generate Playwright tests with codegen.", CODEGEN,
    ),
    (
        "vscode/docs/setup.md", "vscode", "docs/setup.md",
        "e5c3d4e5f60718293a4b5c6d7e8f901234567890", "vscode-team",
        _utc(2026, 6, 17), "e5c3d4e5f60718293a4b5c6d7e8f901234567890", _utc(2026, 6, 17),
        "Set up VS Code and recommended extensions.", SETUP,
    ),
]


# Explicit semantic edges (what the live conflict-detector would persist). Order
# of (from, to) follows the detector's sorted-pair convention so ids are stable.
MANUAL_EDGES = [
    {
        "edge_id": _edge_id("garnet/docs/build-legacy.md", "garnet/docs/build.md", "conflicts-with"),
        "from_doc": "garnet/docs/build-legacy.md", "to_doc": "garnet/docs/build.md",
        "type": "conflicts-with", "weight": 0.91,
        "reason": "Build guides disagree on the required .NET SDK (.NET 8 vs .NET 6).",
        "anchor_text": "", "line": None, "created_by": "conflict-detector", "commit_sha": "",
    },
    {
        "edge_id": _edge_id(
            "onnxruntime/docs/install-old.md", "onnxruntime/docs/install.md", "duplicate-of"
        ),
        "from_doc": "onnxruntime/docs/install-old.md", "to_doc": "onnxruntime/docs/install.md",
        "type": "duplicate-of", "weight": 0.96,
        "reason": "Near-identical install instructions.",
        "anchor_text": "", "line": None, "created_by": "conflict-detector", "commit_sha": "",
    },
    {
        "edge_id": "dep_onnxruntime_install_old",
        "from_doc": "onnxruntime/docs/install-old.md", "to_doc": "onnxruntime/docs/install.md",
        "type": "deprecated-by", "weight": 0.7,
        "reason": "Superseded by the current install guide.",
        "anchor_text": "", "line": None, "created_by": "seed", "commit_sha": "",
    },
]


# --------------------------------------------------------------------------- #
# SQL literal helpers
# --------------------------------------------------------------------------- #
def s(val: str | None) -> str:
    if val is None:
        return "NULL"
    return "'" + val.replace("'", "''") + "'"


def ts(dt: datetime | None) -> str:
    if dt is None:
        return "NULL"
    return "'" + dt.isoformat(sep=" ") + "'"


def num(val) -> str:
    return "NULL" if val is None else str(val)


def boolean(val: bool) -> str:
    return "true" if val else "false"


def arr(items: list[str]) -> str:
    """A text[] literal as a single-quoted string (assignment-cast on insert)."""
    if not items:
        return "'{}'"
    inner = ",".join('"' + e.replace("\\", "\\\\").replace('"', '\\"') + '"' for e in items)
    return s("{" + inner + "}")


def vec(values: list[float]) -> str:
    return "'[" + ",".join(repr(float(x)) for x in values) + "]'"


# --------------------------------------------------------------------------- #
# Build chunks + edges through the real pipeline, then embed.
# --------------------------------------------------------------------------- #
def main() -> None:
    provider = LocalEmbeddingProvider()
    dim = provider.dim

    doc_rows: list[dict] = []
    chunk_objs: list = []
    edges: dict[str, dict] = {}

    for (doc_id, repo, path, sha, author, cdate, lvsha, lvat, summary, content) in CORPUS:
        raw = RawDocument(
            doc_id=doc_id, repo=repo, path=path, branch="main", content=content,
            byte_size=len(content.encode("utf-8")), commit_sha=sha, commit_author=author,
            commit_date=cdate, content_hash=_sha256(content),
        )
        title = next((ln.lstrip("# ").strip() for ln in content.splitlines() if ln.startswith("# ")), None)
        doc_rows.append(
            {
                "doc_id": doc_id, "repo": repo, "path": path, "branch": "main",
                "byte_size": raw.byte_size, "commit_sha": sha, "commit_author": author,
                "commit_date": cdate, "content_hash": raw.content_hash,
                "fetched_at": _utc(2026, 6, 24), "owner": None, "title": title,
                "last_verified_sha": lvsha, "last_verified_at": lvat, "summary": summary,
            }
        )
        chunk_objs.extend(chunk_document(raw))
        for e in extract_edges(raw):
            edges[e.edge_id] = {
                "edge_id": e.edge_id, "from_doc": e.from_doc, "to_doc": e.to_doc,
                "type": e.type.value, "weight": e.weight, "reason": e.reason,
                "anchor_text": e.anchor_text, "line": e.line, "created_by": e.created_by,
                "commit_sha": e.commit_sha,
            }

    for e in MANUAL_EDGES:
        edges[e["edge_id"]] = e

    vectors = provider.embed([c.text for c in chunk_objs])

    out = _render(doc_rows, chunk_objs, vectors, list(edges.values()), dim)
    OUT_PATH.write_text(out, encoding="utf-8")
    print(f"Wrote {OUT_PATH}")
    print(f"  documents={len(doc_rows)} chunks={len(chunk_objs)} edges={len(edges)} dim={dim}")


def _render(doc_rows, chunk_objs, vectors, edge_rows, dim: int) -> str:
    lines: list[str] = []
    lines.append("--")
    lines.append("-- DocGuardian demo seed — Garnet .NET 8 vs .NET 6 build conflict.")
    lines.append("-- GENERATED by backend/scripts/gen_seed.py — do not hand-edit; re-run the")
    lines.append("-- generator instead (the embeddings are real 384-dim fastembed vectors).")
    lines.append("--")
    lines.append("")
    lines.append("CREATE EXTENSION IF NOT EXISTS vector;")
    lines.append("SET search_path TO public;")
    lines.append("")
    lines.append(_DDL.format(dim=dim))
    lines.append("")

    # documents
    cols = (
        "doc_id, repo, path, branch, byte_size, commit_sha, commit_author, commit_date, "
        "content_hash, fetched_at, owner, title, acl, last_verified_sha, last_verified_at, summary"
    )
    lines.append(f"INSERT INTO documents ({cols}) VALUES")
    vals = []
    for d in doc_rows:
        vals.append(
            "  (" + ", ".join([
                s(d["doc_id"]), s(d["repo"]), s(d["path"]), s(d["branch"]), num(d["byte_size"]),
                s(d["commit_sha"]), s(d["commit_author"]), ts(d["commit_date"]),
                s(d["content_hash"]), ts(d["fetched_at"]), s(d["owner"]), s(d["title"]),
                "'{}'", s(d["last_verified_sha"]), ts(d["last_verified_at"]), s(d["summary"]),
            ]) + ")"
        )
    lines.append(",\n".join(vals) + ";")
    lines.append("")

    # chunks
    ccols = (
        "chunk_id, doc_id, repo, heading_path, ordinal, text, token_count, line_start, "
        "line_end, contains_commands, commit_sha, commit_date, content_hash, embedding"
    )
    lines.append(f"INSERT INTO chunks ({ccols}) VALUES")
    cvals = []
    for c, v in zip(chunk_objs, vectors):
        cvals.append(
            "  (" + ", ".join([
                s(c.chunk_id), s(c.doc_id), s(c.repo), arr(list(c.heading_path)), num(c.ordinal),
                s(c.text), num(c.token_count), num(c.line_range[0]), num(c.line_range[1]),
                boolean(c.contains_commands), s(c.commit_sha), ts(c.commit_date),
                s(c.content_hash), vec(v),
            ]) + ")"
        )
    lines.append(",\n".join(cvals) + ";")
    lines.append("")

    # edges
    ecols = "edge_id, from_doc, to_doc, type, weight, reason, anchor_text, line, created_by, commit_sha"
    lines.append(f"INSERT INTO edges ({ecols}) VALUES")
    evals = []
    for e in sorted(edge_rows, key=lambda x: (x["from_doc"], x["to_doc"], x["type"])):
        evals.append(
            "  (" + ", ".join([
                s(e["edge_id"]), s(e["from_doc"]), s(e["to_doc"]), s(e["type"]), num(e["weight"]),
                s(e["reason"]), s(e["anchor_text"]), num(e["line"]), s(e["created_by"]),
                s(e["commit_sha"]),
            ]) + ")"
        )
    lines.append(",\n".join(evals) + ";")
    lines.append("")
    return "\n".join(lines)


# Schema mirrors app/storage/db.py::init_schema (kept self-sufficient so the seed
# stands alone before the app's first init_schema runs). {dim} is the vector width.
_DDL = """CREATE TABLE IF NOT EXISTS documents (
    doc_id        TEXT PRIMARY KEY,
    repo          TEXT NOT NULL,
    path          TEXT NOT NULL,
    branch        TEXT,
    byte_size     INTEGER,
    commit_sha    TEXT,
    commit_author TEXT,
    commit_date   TIMESTAMPTZ,
    content_hash  TEXT,
    fetched_at    TIMESTAMPTZ,
    owner             TEXT,
    title             TEXT,
    acl               TEXT[] DEFAULT '{{}}',
    health            TEXT,
    importance        REAL,
    last_verified_sha TEXT,
    last_verified_at  TIMESTAMPTZ,
    updated_at        TIMESTAMPTZ,
    summary           TEXT,
    original_content  TEXT,
    original_path     TEXT,
    ai_content        TEXT,
    ai_rewritten      BOOLEAN DEFAULT FALSE,
    rationale         TEXT
);

CREATE TABLE IF NOT EXISTS chunks (
    chunk_id          TEXT PRIMARY KEY,
    doc_id            TEXT NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
    repo              TEXT NOT NULL,
    heading_path      TEXT[],
    ordinal           INTEGER,
    text              TEXT NOT NULL,
    token_count       INTEGER,
    line_start        INTEGER,
    line_end          INTEGER,
    contains_commands BOOLEAN,
    commit_sha        TEXT,
    commit_date       TIMESTAMPTZ,
    content_hash      TEXT,
    embedding         VECTOR({dim})
);

CREATE TABLE IF NOT EXISTS edges (
    edge_id     TEXT PRIMARY KEY,
    from_doc    TEXT NOT NULL,
    to_doc      TEXT NOT NULL,
    type        TEXT NOT NULL,
    weight      REAL,
    reason      TEXT,
    anchor_text TEXT,
    line        INTEGER,
    created_by  TEXT,
    commit_sha  TEXT
);

CREATE TABLE IF NOT EXISTS proposals (
    proposal_id  TEXT PRIMARY KEY,
    doc_id       TEXT,
    action       TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'proposed',
    risk_level   TEXT,
    confidence   REAL,
    payload      JSONB NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    applied_at   TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS provenance (
    entry_id             TEXT PRIMARY KEY,
    doc_id               TEXT,
    proposal_id          TEXT,
    action               TEXT NOT NULL,
    approved_by          TEXT NOT NULL,
    approved_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    previous_version_ref TEXT,
    new_version_ref      TEXT,
    evidence_snapshot    JSONB DEFAULT '[]',
    confidence           REAL,
    reason               TEXT
);

CREATE TABLE IF NOT EXISTS analysis_snapshots (
    snapshot_id         TEXT PRIMARY KEY,
    taken_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    repo                TEXT,
    total_docs          INTEGER,
    quality_avg         REAL,
    broken_links        INTEGER,
    stale_detected      INTEGER,
    conflicts_detected  INTEGER,
    duplicates_detected INTEGER,
    orphan_count        INTEGER,
    at_risk_count       INTEGER,
    payload             JSONB
);

CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON chunks(doc_id);
CREATE INDEX IF NOT EXISTS idx_chunks_repo ON chunks(repo);
CREATE INDEX IF NOT EXISTS idx_edges_from ON edges(from_doc);
CREATE INDEX IF NOT EXISTS idx_edges_to ON edges(to_doc);
CREATE INDEX IF NOT EXISTS idx_proposals_status ON proposals(status);
CREATE INDEX IF NOT EXISTS idx_proposals_doc ON proposals(doc_id);
CREATE INDEX IF NOT EXISTS idx_provenance_doc ON provenance(doc_id);
CREATE INDEX IF NOT EXISTS idx_provenance_proposal ON provenance(proposal_id);
CREATE INDEX IF NOT EXISTS idx_analysis_snapshots_taken ON analysis_snapshots(taken_at);
CREATE INDEX IF NOT EXISTS idx_analysis_snapshots_repo ON analysis_snapshots(repo);
CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON chunks USING hnsw (embedding vector_cosine_ops);"""


if __name__ == "__main__":
    main()
