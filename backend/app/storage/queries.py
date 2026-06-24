"""Read queries for the API layer (documents, tree source, graph)."""

from __future__ import annotations

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


def get_document(doc_id: str) -> dict | None:
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT doc_id, repo, path, commit_sha, commit_date "
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
        "commitDate": doc["commit_date"],
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
