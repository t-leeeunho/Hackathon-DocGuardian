"""Read queries for the API layer (documents, tree source, graph)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime

from psycopg.rows import dict_row

from app.storage.db import get_conn


def list_doc_ids(namespace: str | None = None) -> list[str]:
    sql = "SELECT doc_id FROM documents"
    params: dict = {}
    if namespace:
        sql += " WHERE doc_id LIKE %(p)s"
        params["p"] = f"{namespace}/%"
    sql += " ORDER BY doc_id"
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return [r[0] for r in cur.fetchall()]


def get_doc_summaries(namespace: str | None = None) -> dict[str, str]:
    """Map doc_id -> one-line description for the sidebar tree.

    Uses the stored ``summary`` when present, otherwise falls back to the start of
    the document's first chunk so every file still shows *something* descriptive.
    """
    sql = """
    SELECT d.doc_id,
           COALESCE(
               NULLIF(d.summary, ''),
               (SELECT LEFT(c.text, 160) FROM chunks c
                WHERE c.doc_id = d.doc_id ORDER BY c.ordinal LIMIT 1)
           ) AS summary
    FROM documents d
    """
    params: dict = {}
    if namespace:
        sql += " WHERE d.doc_id LIKE %(p)s"
        params["p"] = f"{namespace}/%"
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return {r[0]: (r[1] or "") for r in cur.fetchall()}


def get_doc_placement(doc_id: str) -> dict | None:
    """Whether a doc_id is taken and, if so, which original drop-off owns it.

    Used by intake to disambiguate Librarian placements: a different drop-off must
    never re-file onto an existing doc_id and clobber its preserved original.
    Returns ``{"docId", "originalPath"}`` or ``None`` when the id is free.
    """
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT doc_id, original_path FROM documents WHERE doc_id = %s",
                (doc_id,),
            )
            row = cur.fetchone()
    if not row:
        return None
    return {"docId": row["doc_id"], "originalPath": row.get("original_path")}


def get_document(doc_id: str) -> dict | None:
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT doc_id, repo, path, commit_sha, commit_date, "
                "title, ai_rewritten, original_path, rationale "
                "FROM documents WHERE doc_id = %s",
                (doc_id,),
            )
            doc = cur.fetchone()
            if not doc:
                return None
            cur.execute(
                "SELECT chunk_id, heading_path, line_start, line_end, text "
                "FROM chunks WHERE doc_id = %s ORDER BY ordinal",
                (doc_id,),
            )
            chunks = cur.fetchall()

    return {
        "docId": doc["doc_id"],
        "repo": doc["repo"],
        "path": doc["path"],
        "commitSha": doc["commit_sha"],
        "commitDate": doc["commit_date"].isoformat() if doc["commit_date"] else None,
        "title": doc.get("title"),
        "aiRewritten": bool(doc.get("ai_rewritten")),
        "originalPath": doc.get("original_path"),
        "rationale": doc.get("rationale"),
        "chunks": [
            {
                "chunkId": c["chunk_id"],
                "headingPath": c["heading_path"] or [],
                "lineRange": [c["line_start"], c["line_end"]],
                "text": c["text"],
            }
            for c in chunks
        ],
    }


def get_document_source(doc_id: str) -> dict | None:
    """The original drop-off + the AI rewrite for a document, for the 'view
    original' / compare panel. Returns None when the document is unknown."""
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT doc_id, path, title, summary, ai_rewritten, rationale, "
                "original_path, original_content, ai_content "
                "FROM documents WHERE doc_id = %s",
                (doc_id,),
            )
            doc = cur.fetchone()
    if not doc:
        return None
    return {
        "docId": doc["doc_id"],
        "path": doc["path"],
        "title": doc.get("title"),
        "summary": doc.get("summary"),
        "aiRewritten": bool(doc.get("ai_rewritten")),
        "rationale": doc.get("rationale"),
        "originalPath": doc.get("original_path"),
        "originalContent": doc.get("original_content") or "",
        "aiContent": doc.get("ai_content") or "",
    }


def get_graph(namespace: str | None = None) -> dict:
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            if namespace:
                cur.execute(
                    "SELECT doc_id, repo, path FROM documents WHERE doc_id LIKE %s",
                    (f"{namespace}/%",),
                )
            else:
                cur.execute("SELECT doc_id, repo, path FROM documents")
            docs = cur.fetchall()

            if namespace:
                cur.execute(
                    "SELECT from_doc, to_doc, type, weight FROM edges WHERE from_doc LIKE %s",
                    (f"{namespace}/%",),
                )
            else:
                cur.execute("SELECT from_doc, to_doc, type, weight FROM edges")
            edge_rows = cur.fetchall()

    nodes = [
        {
            "id": d["doc_id"],
            "label": d["path"].rsplit("/", 1)[-1],
            "health": "green",  # health scoring is added by the verification layer
            "size": 0.5,
            "accessible": True,
            "repo": d["repo"],
        }
        for d in docs
    ]
    edges = [
        {
            "from": e["from_doc"],
            "to": e["to_doc"],
            "type": e["type"],
            "weight": e["weight"],
        }
        for e in edge_rows
    ]
    return {"nodes": nodes, "edges": edges}


# ---------------------------------------------------------------------------
# Analysis-snapshot helpers (pure — no DB I/O; tested offline)
# ---------------------------------------------------------------------------

def _coerce_int(v: object) -> int | None:
    """Coerce *v* to ``int`` or return ``None`` when the value is absent."""
    if v is None:
        return None
    return int(v)


def _snapshot_insert_params(row: dict) -> dict:
    """Translate a camelCase input dict to snake_case INSERT params.

    Fills defaults:
    - ``snapshot_id`` ← ``row['snapshotId']`` or a fresh ``uuid4().hex``.
    - Integer count fields are coerced via ``int()``.
    - ``payload`` dict/list is serialised to a JSON string; strings are left
      as-is; ``None`` stays ``None``.
    """
    snapshot_id: str = row.get("snapshotId") or uuid.uuid4().hex

    payload = row.get("payload")
    if payload is not None and not isinstance(payload, str):
        payload = json.dumps(payload)

    return {
        "snapshot_id": snapshot_id,
        "repo": row.get("repo"),
        "total_docs": _coerce_int(row.get("totalDocs")),
        "quality_avg": float(row["qualityAvg"]) if row.get("qualityAvg") is not None else None,
        "broken_links": _coerce_int(row.get("brokenLinks")),
        "stale_detected": _coerce_int(row.get("staleDetected")),
        "conflicts_detected": _coerce_int(row.get("conflictsDetected")),
        "duplicates_detected": _coerce_int(row.get("duplicatesDetected")),
        "orphan_count": _coerce_int(row.get("orphanCount")),
        "at_risk_count": _coerce_int(row.get("atRiskCount")),
        "payload": payload,
    }


def _snapshot_row_to_dto(row: dict) -> dict:
    """Translate a DB row (snake_case) to a camelCase DTO dict.

    ``taken_at`` is ISO 8601 string whether the DB returned a ``datetime``
    object or an already-stringified value.
    ``payload`` JSON strings are parsed back to a Python dict/list.
    """
    taken_at = row.get("taken_at")
    if isinstance(taken_at, datetime):
        taken_at_iso: str | None = taken_at.isoformat()
    else:
        taken_at_iso = taken_at  # already a string or None

    payload = row.get("payload")
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except (json.JSONDecodeError, ValueError):
            pass  # leave as raw string if unparseable

    return {
        "snapshotId": row.get("snapshot_id"),
        "takenAt": taken_at_iso,
        "repo": row.get("repo"),
        "totalDocs": row.get("total_docs"),
        "qualityAvg": row.get("quality_avg"),
        "brokenLinks": row.get("broken_links"),
        "staleDetected": row.get("stale_detected"),
        "conflictsDetected": row.get("conflicts_detected"),
        "duplicatesDetected": row.get("duplicates_detected"),
        "orphanCount": row.get("orphan_count"),
        "atRiskCount": row.get("at_risk_count"),
        "payload": payload,
    }


# ---------------------------------------------------------------------------
# Analysis-snapshot DB helpers (require live Postgres)
# ---------------------------------------------------------------------------

def insert_analysis_snapshot(row: dict) -> str:
    """Persist one snapshot and return its ``snapshot_id``.

    Idempotent: a duplicate ``snapshot_id`` is silently ignored
    (``ON CONFLICT DO NOTHING``).
    """
    params = _snapshot_insert_params(row)
    sql = """
    INSERT INTO analysis_snapshots
        (snapshot_id, repo, total_docs, quality_avg, broken_links,
         stale_detected, conflicts_detected, duplicates_detected,
         orphan_count, at_risk_count, payload)
    VALUES
        (%(snapshot_id)s, %(repo)s, %(total_docs)s, %(quality_avg)s,
         %(broken_links)s, %(stale_detected)s, %(conflicts_detected)s,
         %(duplicates_detected)s, %(orphan_count)s, %(at_risk_count)s,
         %(payload)s)
    ON CONFLICT (snapshot_id) DO NOTHING
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
        conn.commit()
    return params["snapshot_id"]


def get_edge_type_counts(namespace: str | None = None) -> dict[str, int]:
    """Return ``{edge_type: count}`` across the edge table.

    Used by the analysis-snapshot endpoint to enrich captured rows with
    conflict/duplicate tallies without requiring a full metrics recompute.

    Parameters
    ----------
    namespace:
        When given, restricts to edges whose ``from_doc`` starts with
        ``"{namespace}/"``.  Omit for a corpus-wide tally.
    """
    sql = "SELECT type, COUNT(*) AS n FROM edges"
    params: dict = {}
    if namespace:
        sql += " WHERE from_doc LIKE %(p)s"
        params["p"] = f"{namespace}/%"
    sql += " GROUP BY type"
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return {row[0]: int(row[1]) for row in cur.fetchall()}


def get_analysis_snapshots(
    namespace: str | None = None,
    limit: int = 180,
) -> list[dict]:
    """Return up to *limit* snapshots ordered oldest → newest (for charting).

    When *namespace* is given it is matched against the ``repo`` column
    (exact equality — snapshots record the full repo name, not a path prefix).
    """
    sql = "SELECT * FROM analysis_snapshots"
    params: dict = {}
    if namespace:
        sql += " WHERE repo = %(repo)s"
        params["repo"] = namespace
    sql += " ORDER BY taken_at ASC LIMIT %(limit)s"
    params["limit"] = limit
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
    return [_snapshot_row_to_dto(r) for r in rows]
