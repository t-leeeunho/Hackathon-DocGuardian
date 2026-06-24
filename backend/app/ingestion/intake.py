"""User drop-off intake (README Sections 5.1 / 7.5).

Turns arbitrary user-provided content (an uploaded file or pasted text) into the
SAME RawDocument the git ingestion produces, then runs it through the SAME
processing + embedding + storage path. This means an added file automatically
appears in:

  - the file-system tree (left sidebar)   -> it has a doc_id path
  - the document graph                     -> its links become GraphEdges
  - semantic search / duplicate detection  -> its chunks are embedded into pgvector

User content lives under the synthetic "user/" namespace so it is visually
separate from the ingested repositories.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

from app.embeddings.provider import get_embedding_provider
from app.models import RawDocument
from app.processing.conflicts import detect_conflicts_for_doc
from app.processing.processor import chunk_document, extract_edges
from app.processing.summarize import generate_summary
from app.storage.db import get_conn, init_schema
from app.storage.vectorstore import upsert_chunks, upsert_documents, upsert_edges

# Text-based formats we can ingest directly. Binary formats (pdf, docx) would
# need a text-extraction step before reaching here.
TEXT_SUFFIXES = {".md", ".mdx", ".markdown", ".txt", ".rst", ".text", ""}


class UnsupportedFormatError(ValueError):
    pass


def make_raw_document(name: str, content: str, namespace: str = "user") -> RawDocument:
    """Build a RawDocument for user content under the given namespace."""
    rel = name.replace("\\", "/").lstrip("/")
    doc_id = f"{namespace}/{rel}"
    raw_bytes = content.encode("utf-8")
    return RawDocument(
        doc_id=doc_id,
        repo=namespace,
        path=rel,
        branch=namespace,
        content=content,
        byte_size=len(raw_bytes),
        commit_sha="",  # user uploads have no source commit
        commit_author="user-upload",
        commit_date=datetime.now(timezone.utc),
        content_hash="sha256:" + hashlib.sha256(raw_bytes).hexdigest(),
    )


class IngestError(RuntimeError):
    """A core ingestion step failed; nothing was persisted (full rollback)."""


def ingest_content(name: str, content: str, namespace: str = "user") -> dict:
    """Ingest one piece of user content end-to-end, **atomically**.

    The whole insertion is all-or-nothing: the description, embeddings, document,
    structural edges, chunks, and duplicate/conflict edges are written inside a
    single database transaction. If **any** core step fails, the transaction is
    rolled back and the system is left exactly as it was before — no half-applied
    "ghost" document, no orphan chunks, no partial edges.

    The only non-core step is the AI description, which already degrades to a
    free extractive summary instead of failing.
    """
    raw = make_raw_document(name, content, namespace)

    try:
        # 1. Derive content (pure / CPU) — before touching the DB.
        chunks = chunk_document(raw)
        edges = extract_edges(raw)
        summary = generate_summary(content)  # never raises; falls back to extractive

        # 2. Embed (the slow part) outside the transaction so we don't hold a
        #    write lock open during model inference. A failure here aborts before
        #    anything is written.
        provider = get_embedding_provider()
        init_schema(provider.dim)
        embeddings = provider.embed([c.text for c in chunks]) if chunks else []

        # 3. Single atomic transaction: doc + edges + chunks + conflict edges.
        #    psycopg commits on clean exit and rolls back on ANY exception.
        with get_conn() as conn:
            doc_row = {**_doc_row(raw), "summary": summary}
            upsert_documents([doc_row], conn=conn)
            if edges:
                upsert_edges([_edge_row(e) for e in edges], conn=conn)
            if chunks:
                upsert_chunks([_chunk_row(c) for c in chunks], embeddings, conn=conn)
                # Real-time duplicate/conflict detection in the SAME transaction:
                # the new chunks are visible to their own tx, and any failure here
                # rolls the entire ingest back.
                conflict_edges = detect_conflicts_for_doc(raw.doc_id, conn=conn)
            else:
                conflict_edges = 0
    except UnsupportedFormatError:
        raise
    except Exception as exc:  # any core failure -> nothing persisted
        raise IngestError(f"ingest failed and was rolled back: {exc}") from exc

    return {
        "doc_id": raw.doc_id,
        "chunks": len(chunks),
        "edges": len(edges) + conflict_edges,
        "conflictEdges": conflict_edges,
        "summary": summary,
    }


def ingest_file(path: str | Path, namespace: str = "user") -> dict:
    """Ingest a file from disk. Raises UnsupportedFormatError for binary formats."""
    p = Path(path)
    if p.suffix.lower() not in TEXT_SUFFIXES:
        raise UnsupportedFormatError(
            f"{p.suffix!r} is not a supported text format yet "
            f"(supported: {', '.join(sorted(s for s in TEXT_SUFFIXES if s))})"
        )
    content = p.read_text(encoding="utf-8", errors="replace")
    return ingest_content(p.name, content, namespace)


# --- row mappers (shared shape with scripts/load_vectors.py) ---

def _doc_row(raw: RawDocument) -> dict:
    d = raw.model_dump(mode="json")
    return {
        "doc_id": d["doc_id"],
        "repo": d["repo"],
        "path": d["path"],
        "branch": d.get("branch"),
        "byte_size": d.get("byte_size"),
        "commit_sha": d.get("commit_sha"),
        "commit_author": d.get("commit_author"),
        "commit_date": d.get("commit_date"),
        "content_hash": d.get("content_hash"),
        "fetched_at": d.get("fetched_at"),
    }


def _chunk_row(chunk) -> dict:
    c = chunk.model_dump(mode="json")
    line_start, line_end = c["line_range"]
    return {
        "chunk_id": c["chunk_id"],
        "doc_id": c["doc_id"],
        "repo": c["repo"],
        "heading_path": c.get("heading_path") or [],
        "ordinal": c.get("ordinal"),
        "text": c["text"],
        "token_count": c.get("token_count"),
        "line_start": line_start,
        "line_end": line_end,
        "contains_commands": c.get("contains_commands", False),
        "commit_sha": c.get("commit_sha"),
        "commit_date": c.get("commit_date"),
        "content_hash": c.get("content_hash"),
    }


def _edge_row(edge) -> dict:
    e = edge.model_dump(by_alias=True, mode="json")
    return {
        "edge_id": e["edge_id"],
        "from_doc": e["from"],
        "to_doc": e["to"],
        "type": e["type"],
        "weight": e.get("weight"),
        "reason": e.get("reason"),
        "anchor_text": e.get("anchor_text"),
        "line": e.get("line"),
        "created_by": e.get("created_by"),
        "commit_sha": e.get("commit_sha"),
    }
