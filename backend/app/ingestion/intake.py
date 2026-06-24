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
from app.processing.processor import chunk_document, extract_edges
from app.storage.db import init_schema
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


def ingest_content(name: str, content: str, namespace: str = "user") -> dict:
    """Ingest one piece of user content end-to-end into the live system."""
    raw = make_raw_document(name, content, namespace)
    chunks = chunk_document(raw)
    edges = extract_edges(raw)

    provider = get_embedding_provider()
    init_schema(provider.dim)

    upsert_documents([_doc_row(raw)])
    upsert_edges([_edge_row(e) for e in edges])
    if chunks:
        embeddings = provider.embed([c.text for c in chunks])
        upsert_chunks([_chunk_row(c) for c in chunks], embeddings)

    return {
        "doc_id": raw.doc_id,
        "chunks": len(chunks),
        "edges": len(edges),
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
