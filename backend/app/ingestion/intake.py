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
from app.agents.librarian import identity_plan, rewrite_and_place
from app.models import RawDocument
from app.processing.conflicts import detect_conflicts_for_doc
from app.processing.processor import chunk_document, extract_edges
from app.processing.summarize import generate_summary
from app.storage.db import get_conn, init_schema
from app.storage.queries import get_doc_placement, list_doc_ids
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


def _finalize_placement(namespace: str, base_path: str, original_path: str) -> str:
    """Resolve the Librarian's chosen path to a non-clobbering doc placement.

    The Librarian picks a path from a doc's title/category, so two *different*
    drop-offs can land on the same ``doc_id`` — which would upsert over the first
    and destroy its preserved original. Guard against that: if the target id is
    already owned by a drop-off with a *different* original path, append a stable
    suffix derived from this drop's original path (so re-dropping the same file
    stays idempotent, but a different file never clobbers it).
    """
    candidate_id = f"{namespace}/{base_path}"
    try:
        occupant = get_doc_placement(candidate_id)
    except Exception:  # pragma: no cover - best effort; the write tx will surface DB errors
        return base_path
    if occupant is None or occupant.get("originalPath") == original_path:
        return base_path  # free, or our own prior drop -> update in place

    suffix = hashlib.sha256(f"{namespace}::{original_path}".encode("utf-8")).hexdigest()[:6]
    folder, _, filename = base_path.rpartition("/")
    stem, dot, ext = filename.rpartition(".")
    stem = stem or filename
    ext = ext if dot else "md"
    suffixed = f"{stem}-{suffix}.{ext}"
    return f"{folder}/{suffixed}" if folder else suffixed


def ingest_content(
    name: str, content: str, namespace: str = "user", rewrite: bool = True
) -> dict:
    """Ingest one piece of user content end-to-end, **atomically**.

    When ``rewrite`` is true (the default for user drop-off), the **Librarian**
    first rewrites the raw content into an AI-agent-friendly document and decides
    where it belongs in the library. That rewrite becomes the *canonical* content
    that is chunked, embedded, indexed, and shown by default; the user's untouched
    original is stored alongside so it can be viewed on demand. The doc_id reflects
    the agent's chosen placement, not the user's folder.

    When ``rewrite`` is false the content is ingested verbatim at ``name`` (used by
    ``/ingest/refresh`` so re-processing keeps a document's id/placement stable).

    The whole insertion is all-or-nothing: the description, embeddings, document,
    structural edges, chunks, and duplicate/conflict edges are written inside a
    single database transaction. If **any** core step fails, the transaction is
    rolled back and the system is left exactly as it was before — no half-applied
    "ghost" document, no orphan chunks, no partial edges.

    The only non-core steps are the AI rewrite and description, which already
    degrade to deterministic local results instead of failing.
    """
    original_path = (name or "untitled.md").replace("\\", "/").lstrip("/")

    if rewrite:
        try:
            existing_paths = list_doc_ids(namespace)
        except Exception:  # pragma: no cover - placement context is best-effort
            existing_paths = []
        plan = rewrite_and_place(name, content, namespace, existing_paths)
        # Never re-file onto a different drop-off's doc_id (would clobber its original).
        final_path = _finalize_placement(namespace, plan["suggested_path"], original_path)
        plan["suggested_path"] = final_path
    else:
        plan = identity_plan(name, content, namespace)

    canonical = plan["ai_content"]
    raw = make_raw_document(plan["suggested_path"], canonical, namespace)

    try:
        # 1. Derive content (pure / CPU) — before touching the DB.
        chunks = chunk_document(raw)
        edges = extract_edges(raw)
        summary = plan["summary"] or generate_summary(canonical)

        # 2. Embed (the slow part) outside the transaction so we don't hold a
        #    write lock open during model inference. A failure here aborts before
        #    anything is written.
        provider = get_embedding_provider()
        init_schema(provider.dim)
        embeddings = provider.embed([c.text for c in chunks]) if chunks else []

        # 3. Single atomic transaction: doc + edges + chunks + conflict edges.
        #    psycopg commits on clean exit and rolls back on ANY exception.
        with get_conn() as conn:
            doc_row = {
                **_doc_row(raw),
                "summary": summary,
                "title": plan["title"],
                "original_content": content,
                "original_path": original_path,
                "ai_content": canonical,
                "ai_rewritten": plan["ai_rewritten"],
                "rationale": plan["rationale"],
            }
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
        "title": plan["title"],
        "category": plan["category"],
        "rationale": plan["rationale"],
        "originalPath": original_path,
        "suggestedPath": plan["suggested_path"],
        "aiRewritten": plan["ai_rewritten"],
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
