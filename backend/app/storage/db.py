"""Postgres + pgvector access.

A single Postgres instance is the metadata/graph/provenance store AND the vector
index (README Section 10.4). This module owns the connection and schema.
"""

from __future__ import annotations

import psycopg
from pgvector.psycopg import register_vector

from app.config import DATABASE_URL


def get_conn() -> psycopg.Connection:
    """Open a connection with the pgvector type adapter registered."""
    conn = psycopg.connect(DATABASE_URL)
    # The extension must exist before the vector type can be registered.
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
    conn.commit()
    register_vector(conn)
    return conn


def init_schema(dim: int) -> None:
    """Create tables and indexes. The vector column width must match the model."""
    ddl = f"""
    CREATE EXTENSION IF NOT EXISTS vector;

    CREATE TABLE IF NOT EXISTS documents (
        doc_id        TEXT PRIMARY KEY,
        repo          TEXT NOT NULL,
        path          TEXT NOT NULL,
        branch        TEXT,
        byte_size     INTEGER,
        commit_sha    TEXT,
        commit_author TEXT,
        commit_date   TIMESTAMPTZ,
        content_hash  TEXT,
        fetched_at    TIMESTAMPTZ
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

    CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON chunks(doc_id);
    CREATE INDEX IF NOT EXISTS idx_chunks_repo ON chunks(repo);
    CREATE INDEX IF NOT EXISTS idx_edges_from ON edges(from_doc);
    CREATE INDEX IF NOT EXISTS idx_edges_to ON edges(to_doc);
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(ddl)
            # HNSW index for cosine similarity search over embeddings.
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_chunks_embedding "
                "ON chunks USING hnsw (embedding vector_cosine_ops)"
            )
        conn.commit()
