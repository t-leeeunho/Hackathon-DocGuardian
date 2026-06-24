"""Duplicate / conflict detection (README §6, §10.7).

Two documents whose chunks are highly similar are either **duplicates** (say the
same thing — should be merged) or **conflicts** (overlap strongly but the live
text differs — a likely contradiction to review). We approximate this cheaply
from the embeddings we already store:

* cross-document chunk cosine ``>= DUPLICATE_THRESHOLD``  -> ``duplicate-of``
* cosine in ``[CONFLICT_THRESHOLD, DUPLICATE_THRESHOLD)`` -> ``conflicts-with``

The classification and edge-building are **pure** (unit testable with no DB);
``detect_conflict_edges`` runs the actual pgvector self-join and persists edges.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Optional

# Similarity thresholds (chunk cosine). Tuned up from the original 0.85/0.92 so
# the graph shows only *real* conflicts/duplicates instead of a red hairball of
# shared boilerplate.
DUPLICATE_THRESHOLD = 0.95
CONFLICT_THRESHOLD = 0.90
# Cap how many conflict/duplicate edges any single node can anchor, so hub docs
# don't dominate the graph. Highest-similarity edges win.
MAX_EDGES_PER_NODE = 3


def classify_pair(similarity: float) -> Optional[str]:
    """Map a chunk-pair similarity to an edge type, or None if too weak."""
    if similarity >= DUPLICATE_THRESHOLD:
        return "duplicate-of"
    if similarity >= CONFLICT_THRESHOLD:
        return "conflicts-with"
    return None


@dataclass(frozen=True)
class ChunkSimilarity:
    """One cross-document chunk match (already filtered to different docs)."""

    from_doc: str
    to_doc: str
    similarity: float
    from_chunk: str = ""
    to_chunk: str = ""


def _edge_id(from_doc: str, to_doc: str, edge_type: str) -> str:
    # Order-independent id so A~B and B~A collapse to one stable edge.
    a, b = sorted((from_doc, to_doc))
    raw = f"{a}|{b}|{edge_type}"
    return "sim_" + hashlib.sha1(raw.encode()).hexdigest()[:16]


def _pair_key(a: str, b: str) -> frozenset:
    return frozenset((a, b))


def build_edges(
    matches: list[ChunkSimilarity],
    exclude_pairs: Optional[set[frozenset]] = None,
) -> list[dict]:
    """Reduce raw chunk matches to one best edge per document pair.

    Keeps the highest similarity seen for each unordered pair and classifies it.
    ``exclude_pairs`` (sets of two doc ids) are skipped — e.g. pairs that already
    have a structural ``references`` link, which are legitimate relationships
    rather than conflicts. Returns rows ready for ``vectorstore.upsert_edges``.
    """
    exclude_pairs = exclude_pairs or set()
    best: dict[tuple[str, str], ChunkSimilarity] = {}
    for m in matches:
        if m.from_doc == m.to_doc:
            continue
        if _pair_key(m.from_doc, m.to_doc) in exclude_pairs:
            continue
        key = tuple(sorted((m.from_doc, m.to_doc)))
        cur = best.get(key)
        if cur is None or m.similarity > cur.similarity:
            best[key] = m

    edges: list[dict] = []
    for (a, b), m in sorted(best.items()):
        edge_type = classify_pair(m.similarity)
        if edge_type is None:
            continue
        edges.append(
            {
                "edge_id": _edge_id(a, b, edge_type),
                "from_doc": a,
                "to_doc": b,
                "type": edge_type,
                "weight": round(float(m.similarity), 4),
                "reason": f"chunk cosine {m.similarity:.3f}",
                "anchor_text": "",
                "line": None,
                "created_by": "conflict-detector",
                "commit_sha": "",
            }
        )
    return edges


def cap_edges_per_node(edges: list[dict], max_per_node: int = MAX_EDGES_PER_NODE) -> list[dict]:
    """Keep only the strongest ``max_per_node`` edges touching each document.

    Greedy by descending weight: an edge is kept only if neither endpoint has
    already hit the cap. Prevents hub documents from anchoring a hairball.
    """
    counts: dict[str, int] = {}
    kept: list[dict] = []
    for e in sorted(edges, key=lambda x: x["weight"] or 0, reverse=True):
        f, t = e["from_doc"], e["to_doc"]
        if counts.get(f, 0) >= max_per_node or counts.get(t, 0) >= max_per_node:
            continue
        kept.append(e)
        counts[f] = counts.get(f, 0) + 1
        counts[t] = counts.get(t, 0) + 1
    return sorted(kept, key=lambda x: (x["from_doc"], x["to_doc"], x["type"]))


def detect_conflict_edges(repo: str | None = None, min_similarity: float = CONFLICT_THRESHOLD) -> int:
    """Find near-duplicate cross-doc chunks in pgvector and persist edges.

    Returns the number of edges written. Imports the DB lazily so this module
    stays import-safe for unit tests.
    """
    from app.storage.db import get_conn
    from app.storage.vectorstore import upsert_edges

    prefix = f"{repo}/%" if repo else "%"
    # Self-join chunks on cosine similarity across *different* documents. The
    # pgvector `<=>` operator is cosine distance, so similarity = 1 - distance.
    sql = """
    SELECT a.doc_id AS from_doc, b.doc_id AS to_doc,
           a.chunk_id AS from_chunk, b.chunk_id AS to_chunk,
           1 - (a.embedding <=> b.embedding) AS similarity
    FROM chunks a
    JOIN chunks b
      ON a.doc_id < b.doc_id
     AND a.repo = b.repo
     AND a.embedding <=> b.embedding < %(max_dist)s
    WHERE a.doc_id LIKE %(prefix)s AND b.doc_id LIKE %(prefix)s
    """
    from psycopg.rows import dict_row

    matches: list[ChunkSimilarity] = []
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, {"max_dist": 1 - min_similarity, "prefix": prefix})
            for r in cur.fetchall():
                matches.append(
                    ChunkSimilarity(
                        from_doc=r["from_doc"],
                        to_doc=r["to_doc"],
                        similarity=float(r["similarity"]),
                        from_chunk=r["from_chunk"],
                        to_chunk=r["to_chunk"],
                    )
                )
        refs = _reference_pairs(conn)

    edges = cap_edges_per_node(build_edges(matches, exclude_pairs=refs))
    return upsert_edges(edges)


def _reference_pairs(conn, doc_id: str | None = None) -> set[frozenset]:
    """Document pairs already linked by a structural ``references`` edge.

    These are legitimate relationships (an index linking a page, etc.), so we
    don't also flag them as conflicts/duplicates.
    """
    if doc_id is None:
        sql = "SELECT from_doc, to_doc FROM edges WHERE type = 'references'"
        params: tuple = ()
    else:
        sql = (
            "SELECT from_doc, to_doc FROM edges "
            "WHERE type = 'references' AND (from_doc = %s OR to_doc = %s)"
        )
        params = (doc_id, doc_id)
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return {frozenset((f, t)) for f, t in cur.fetchall()}


def detect_conflicts_for_doc(
    doc_id: str, min_similarity: float = CONFLICT_THRESHOLD, conn=None
) -> int:
    """Compare ONE document's chunks against the rest of the corpus and persist
    any duplicate/conflict edges. Cheap enough to run on intake (only the new
    doc's chunks drive the scan). Returns the number of edges written.

    Pass ``conn`` to run inside an existing transaction (so intake can keep the
    whole insert atomic — the new chunks are visible to their own transaction
    before commit). With no ``conn`` it opens and commits its own connection.
    """
    from app.storage.db import get_conn

    if conn is not None:
        return _detect_on_conn(doc_id, min_similarity, conn)
    with get_conn() as own:
        return _detect_on_conn(doc_id, min_similarity, own)


def _detect_on_conn(doc_id: str, min_similarity: float, conn) -> int:
    from psycopg.rows import dict_row

    from app.storage.vectorstore import upsert_edges

    sql = """
    SELECT a.doc_id AS from_doc, b.doc_id AS to_doc,
           a.chunk_id AS from_chunk, b.chunk_id AS to_chunk,
           1 - (a.embedding <=> b.embedding) AS similarity
    FROM chunks a
    JOIN chunks b
      ON b.doc_id <> a.doc_id
     AND a.repo = b.repo
     AND a.embedding <=> b.embedding < %(max_dist)s
    WHERE a.doc_id = %(doc_id)s
    """
    matches: list[ChunkSimilarity] = []
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql, {"max_dist": 1 - min_similarity, "doc_id": doc_id})
        for r in cur.fetchall():
            matches.append(
                ChunkSimilarity(
                    from_doc=r["from_doc"],
                    to_doc=r["to_doc"],
                    similarity=float(r["similarity"]),
                    from_chunk=r["from_chunk"],
                    to_chunk=r["to_chunk"],
                )
            )
    refs = _reference_pairs(conn, doc_id)
    edges = cap_edges_per_node(build_edges(matches, exclude_pairs=refs))
    return upsert_edges(edges, conn=conn)
