"""Analysis signal gathering (Layer: thin store + pure data containers).

``DocAnalysisSignals``  — all per-document inputs the analyzers need.
``CorpusSignals``       — corpus-wide doc-set and edge list.

The two ``gather_*`` helpers perform DB reads (imported lazily so this module
is importable in offline unit tests without a live Postgres connection).
All scoring / analysis is done in the sibling quality/links/drift modules
which accept plain data — no DB there.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.processing.processor import _LINK_RE, _resolve_link

# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------


def _scan_links(content: str, doc_id: str) -> tuple[list[str], list[str]]:
    """Return (internal_link_targets, external_links) found in *content*.

    ``internal_link_targets`` are resolved doc_ids (via ``_resolve_link``).
    ``external_links`` are raw http/https URLs.
    De-duplicates both lists while preserving first-seen order.
    """
    internal: list[str] = []
    external: list[str] = []
    seen_int: set[str] = set()
    seen_ext: set[str] = set()

    for m in _LINK_RE.finditer(content):
        target = m.group(2)
        if target.startswith(("http://", "https://")):
            if target not in seen_ext:
                external.append(target)
                seen_ext.add(target)
        else:
            resolved = _resolve_link(doc_id, target)
            if resolved and resolved not in seen_int:
                internal.append(resolved)
                seen_int.add(resolved)

    return internal, external


# ---------------------------------------------------------------------------
# Data contracts
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DocAnalysisSignals:
    """All signals gathered for one document before analysis."""

    doc_id: str
    repo: str
    path: str
    content: str  # ordered chunks joined; fallback ai_content
    heading_paths: list[list[str]]  # one entry per chunk (may be empty list)
    commit_sha: str | None
    commit_date: datetime | None
    last_verified_sha: str | None
    has_conflict_edge: bool = False
    has_duplicate_edge: bool = False
    is_deprecated: bool = False
    inbound_refs: int = 0
    outbound_refs: int = 0
    internal_link_targets: list[str] = field(default_factory=list)
    external_links: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CorpusSignals:
    """Corpus-wide doc ids and edge list (all types)."""

    doc_ids: set[str]
    edges: list[tuple[str, str, str]]  # (from_doc, to_doc, type)


# ---------------------------------------------------------------------------
# Store helpers (DB reads — lazy imports so offline tests stay import-safe)
# ---------------------------------------------------------------------------


def gather_doc_signals(doc_id: str) -> DocAnalysisSignals:
    """Read all signals for *doc_id* from Postgres."""
    from app.storage.db import get_conn  # lazy — avoids DB import at module load
    from psycopg.rows import dict_row

    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT repo, path, commit_sha, commit_date, last_verified_sha, "
                "health, ai_content "
                "FROM documents WHERE doc_id = %s",
                (doc_id,),
            )
            doc = cur.fetchone()
            if doc is None:
                raise ValueError(f"Document not found: {doc_id!r}")

            cur.execute(
                "SELECT text, heading_path "
                "FROM chunks WHERE doc_id = %s ORDER BY ordinal",
                (doc_id,),
            )
            chunk_rows = cur.fetchall()

            cur.execute(
                "SELECT type FROM edges WHERE from_doc = %s OR to_doc = %s",
                (doc_id, doc_id),
            )
            edge_rows = cur.fetchall()

        # Simple counts without dict_row overhead
        with conn.cursor() as plain:
            plain.execute(
                "SELECT COUNT(*) FROM edges "
                "WHERE to_doc = %s AND type = 'references'",
                (doc_id,),
            )
            inbound_refs: int = plain.fetchone()[0]  # type: ignore[index]

            plain.execute(
                "SELECT COUNT(*) FROM edges "
                "WHERE from_doc = %s AND type = 'references'",
                (doc_id,),
            )
            outbound_refs: int = plain.fetchone()[0]  # type: ignore[index]

    # Canonical text: ordered chunk texts joined; fallback to ai_content
    if chunk_rows:
        content = "\n".join(r["text"] for r in chunk_rows)
    else:
        content = doc.get("ai_content") or ""

    heading_paths: list[list[str]] = [
        list(r["heading_path"]) for r in chunk_rows if r.get("heading_path")
    ]

    has_conflict_edge = any(r["type"] == "conflicts-with" for r in edge_rows)
    has_duplicate_edge = any(r["type"] == "duplicate-of" for r in edge_rows)
    is_deprecated = doc.get("health") == "gray"

    internal_link_targets, external_links = _scan_links(content, doc_id)

    return DocAnalysisSignals(
        doc_id=doc_id,
        repo=doc["repo"],
        path=doc["path"],
        content=content,
        heading_paths=heading_paths,
        commit_sha=doc.get("commit_sha"),
        commit_date=doc.get("commit_date"),
        last_verified_sha=doc.get("last_verified_sha"),
        has_conflict_edge=has_conflict_edge,
        has_duplicate_edge=has_duplicate_edge,
        is_deprecated=is_deprecated,
        inbound_refs=inbound_refs,
        outbound_refs=outbound_refs,
        internal_link_targets=internal_link_targets,
        external_links=external_links,
    )


def gather_corpus_signals(namespace: str | None = None) -> CorpusSignals:
    """Read corpus-wide doc ids and edges from Postgres.

    Pass *namespace* (e.g. ``"vscode"``) to restrict to one repo prefix.
    """
    from app.storage.db import get_conn  # lazy

    with get_conn() as conn:
        with conn.cursor() as cur:
            if namespace:
                cur.execute(
                    "SELECT doc_id FROM documents WHERE doc_id LIKE %s",
                    (f"{namespace}/%",),
                )
            else:
                cur.execute("SELECT doc_id FROM documents")
            doc_ids: set[str] = {row[0] for row in cur.fetchall()}

            if namespace:
                cur.execute(
                    "SELECT from_doc, to_doc, type FROM edges "
                    "WHERE from_doc LIKE %s",
                    (f"{namespace}/%",),
                )
            else:
                cur.execute("SELECT from_doc, to_doc, type FROM edges")
            edges: list[tuple[str, str, str]] = [
                (row[0], row[1], row[2]) for row in cur.fetchall()
            ]

    return CorpusSignals(doc_ids=doc_ids, edges=edges)
