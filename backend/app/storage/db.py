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

    -- Governance fields on documents (idempotent; added after the base schema
    -- so existing deployments upgrade in place). README Section 8A DocumentRecord.
    ALTER TABLE documents ADD COLUMN IF NOT EXISTS owner             TEXT;
    ALTER TABLE documents ADD COLUMN IF NOT EXISTS title             TEXT;
    ALTER TABLE documents ADD COLUMN IF NOT EXISTS acl               TEXT[] DEFAULT '{{}}';
    ALTER TABLE documents ADD COLUMN IF NOT EXISTS health            TEXT;
    ALTER TABLE documents ADD COLUMN IF NOT EXISTS importance        REAL;
    ALTER TABLE documents ADD COLUMN IF NOT EXISTS last_verified_sha TEXT;
    ALTER TABLE documents ADD COLUMN IF NOT EXISTS last_verified_at  TIMESTAMPTZ;
    ALTER TABLE documents ADD COLUMN IF NOT EXISTS updated_at        TIMESTAMPTZ;
    ALTER TABLE documents ADD COLUMN IF NOT EXISTS summary           TEXT;

    -- Librarian (AI-native rewrite + placement). The stored chunks/`ai_content`
    -- are the agent-friendly rewrite shown by default; `original_content` keeps
    -- the user's untouched drop-off so a human can always view the source.
    ALTER TABLE documents ADD COLUMN IF NOT EXISTS original_content  TEXT;
    ALTER TABLE documents ADD COLUMN IF NOT EXISTS original_path     TEXT;
    ALTER TABLE documents ADD COLUMN IF NOT EXISTS ai_content        TEXT;
    ALTER TABLE documents ADD COLUMN IF NOT EXISTS ai_rewritten      BOOLEAN DEFAULT FALSE;
    ALTER TABLE documents ADD COLUMN IF NOT EXISTS rationale         TEXT;

    -- Persisted agent proposals (README Section 8A.4 AgentProposal). The full
    -- agent payload is kept in `payload` (snake_case JSON); indexed columns
    -- drive lookups, status transitions, and metrics.
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

    -- Append-only audit log. Historical rows are never updated or deleted;
    -- a rollback writes a NEW entry that references the prior one.
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

    CREATE INDEX IF NOT EXISTS idx_proposals_status ON proposals(status);
    CREATE INDEX IF NOT EXISTS idx_proposals_doc ON proposals(doc_id);
    CREATE INDEX IF NOT EXISTS idx_provenance_doc ON provenance(doc_id);
    CREATE INDEX IF NOT EXISTS idx_provenance_proposal ON provenance(proposal_id);

    -- Time-series snapshots for the Insights / Trends analysis subsystem (direction D).
    -- Rows are appended on ingest-complete, apply/rollback events, and POST /analysis/snapshot.
    -- append-only; never updated or deleted (rollback writes a new row).
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

    CREATE INDEX IF NOT EXISTS idx_analysis_snapshots_taken ON analysis_snapshots(taken_at);
    CREATE INDEX IF NOT EXISTS idx_analysis_snapshots_repo  ON analysis_snapshots(repo);
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
