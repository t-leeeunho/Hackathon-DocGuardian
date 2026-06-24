"""Vector store operations over the pgvector `chunks` table."""

from __future__ import annotations

from typing import Any, Optional

import psycopg
from psycopg.rows import dict_row

from app.storage.db import get_conn


def _execmany(sql: str, params: list[dict], conn: Optional[psycopg.Connection]) -> int:
    """Run an executemany either on a caller-provided connection (no commit, so
    the caller controls the transaction) or on a fresh self-committing one."""
    if not params:
        return 0
    if conn is not None:
        with conn.cursor() as cur:
            cur.executemany(sql, params)
        return len(params)
    with get_conn() as own:
        with own.cursor() as cur:
            cur.executemany(sql, params)
        own.commit()
    return len(params)


def upsert_documents(rows: list[dict[str, Any]], conn: Optional[psycopg.Connection] = None) -> int:
    sql = """
    INSERT INTO documents (doc_id, repo, path, branch, byte_size, commit_sha,
                           commit_author, commit_date, content_hash, fetched_at, summary)
    VALUES (%(doc_id)s, %(repo)s, %(path)s, %(branch)s, %(byte_size)s, %(commit_sha)s,
            %(commit_author)s, %(commit_date)s, %(content_hash)s, %(fetched_at)s, %(summary)s)
    ON CONFLICT (doc_id) DO UPDATE SET
        commit_sha = EXCLUDED.commit_sha,
        commit_date = EXCLUDED.commit_date,
        content_hash = EXCLUDED.content_hash,
        fetched_at = EXCLUDED.fetched_at,
        summary = COALESCE(EXCLUDED.summary, documents.summary);
    """
    # `summary` is optional for callers (e.g. repo ingest) that don't compute it.
    rows = [{"summary": None, **r} for r in rows]
    return _execmany(sql, rows, conn)


def upsert_chunks(
    rows: list[dict[str, Any]],
    embeddings: list[list[float]],
    conn: Optional[psycopg.Connection] = None,
) -> int:
    """Insert chunk rows with their embeddings. `rows` and `embeddings` align by index."""
    sql = """
    INSERT INTO chunks (chunk_id, doc_id, repo, heading_path, ordinal, text,
                        token_count, line_start, line_end, contains_commands,
                        commit_sha, commit_date, content_hash, embedding)
    VALUES (%(chunk_id)s, %(doc_id)s, %(repo)s, %(heading_path)s, %(ordinal)s, %(text)s,
            %(token_count)s, %(line_start)s, %(line_end)s, %(contains_commands)s,
            %(commit_sha)s, %(commit_date)s, %(content_hash)s, %(embedding)s)
    ON CONFLICT (chunk_id) DO UPDATE SET
        text = EXCLUDED.text,
        content_hash = EXCLUDED.content_hash,
        embedding = EXCLUDED.embedding;
    """
    params = [{**row, "embedding": emb} for row, emb in zip(rows, embeddings)]
    return _execmany(sql, params, conn)


def upsert_edges(rows: list[dict[str, Any]], conn: Optional[psycopg.Connection] = None) -> int:
    sql = """
    INSERT INTO edges (edge_id, from_doc, to_doc, type, weight, reason,
                       anchor_text, line, created_by, commit_sha)
    VALUES (%(edge_id)s, %(from_doc)s, %(to_doc)s, %(type)s, %(weight)s, %(reason)s,
            %(anchor_text)s, %(line)s, %(created_by)s, %(commit_sha)s)
    ON CONFLICT (edge_id) DO NOTHING;
    """
    return _execmany(sql, rows, conn)


def search(query_embedding: list[float], top_k: int = 5, repo: str | None = None) -> list[dict]:
    """Cosine-similarity search over chunk embeddings (1 - distance => similarity).

    `repo` is the shortName (e.g. "garnet"); it filters by doc_id prefix.
    """
    where = "WHERE doc_id LIKE %(prefix)s" if repo else ""
    sql = f"""
    SELECT chunk_id, doc_id, repo, heading_path, text, line_start, line_end,
           commit_sha, 1 - (embedding <=> %(q)s::vector) AS score
    FROM chunks
    {where}
    ORDER BY embedding <=> %(q)s::vector
    LIMIT %(k)s;
    """
    q_str = "[" + ",".join(repr(float(x)) for x in query_embedding) + "]"
    params: dict[str, Any] = {"q": q_str, "k": top_k}
    if repo:
        params["prefix"] = f"{repo}/%"
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            return cur.fetchall()


def count_chunks() -> int:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM chunks")
            return cur.fetchone()[0]
