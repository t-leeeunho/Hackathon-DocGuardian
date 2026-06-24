"""Postgres persistence for the governance slice.

Proposals, append-only provenance, metric counts, and the ACL-filtered governed
graph. The single Postgres instance (README §10.4) is the source of truth; all
writes are idempotent.
"""

from __future__ import annotations

import secrets
from typing import Any, Optional

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.governance.acl import Principal, can_access
from app.governance.health import DocSignals, derive_health, derive_importance
from app.governance.metrics import MetricSignals, compute_metrics
from app.governance.serialize import camelize
from app.storage.db import get_conn


def _new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(8)}"


# --------------------------------------------------------------------------- #
# Proposals
# --------------------------------------------------------------------------- #
def save_proposal(proposal: dict[str, Any]) -> dict[str, Any]:
    """Persist an agent proposal (snake_case payload). Returns it with an id/status.

    Idempotent on ``proposal_id``: re-saving the same proposal updates its payload
    but never resets an already-applied status.
    """
    proposal = dict(proposal)
    pid = proposal.get("proposal_id") or _new_id("prop")
    proposal["proposal_id"] = pid
    status = proposal.get("status", "proposed")

    sql = """
    INSERT INTO proposals (proposal_id, doc_id, action, status, risk_level,
                           confidence, payload, created_at, updated_at)
    VALUES (%(proposal_id)s, %(doc_id)s, %(action)s, %(status)s, %(risk_level)s,
            %(confidence)s, %(payload)s, now(), now())
    ON CONFLICT (proposal_id) DO UPDATE SET
        payload = EXCLUDED.payload,
        updated_at = now()
    WHERE proposals.status NOT IN ('applied', 'rolled-back');
    """
    params = {
        "proposal_id": pid,
        "doc_id": proposal.get("target_doc_id"),
        "action": proposal.get("action", "flag"),
        "status": status,
        "risk_level": proposal.get("risk_level"),
        "confidence": proposal.get("confidence"),
        "payload": Jsonb(proposal),
    }
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
        conn.commit()
    return proposal


def get_proposal_row(proposal_id: str) -> Optional[dict]:
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT proposal_id, doc_id, action, status, risk_level, confidence, "
                "payload, created_at, updated_at, applied_at "
                "FROM proposals WHERE proposal_id = %s",
                (proposal_id,),
            )
            return cur.fetchone()


def get_proposal_dto(proposal_id: str) -> Optional[dict]:
    """camelCase proposal + governance status for the API (README §8B)."""
    row = get_proposal_row(proposal_id)
    if row is None:
        return None
    payload = row["payload"] or {}
    dto = camelize(payload)
    dto["proposalId"] = row["proposal_id"]
    dto["status"] = row["status"]
    dto["createdAt"] = row["created_at"].isoformat() if row["created_at"] else None
    dto["appliedAt"] = row["applied_at"].isoformat() if row["applied_at"] else None
    dto["provenance"] = list_provenance(proposal_id=proposal_id)
    return dto


def set_proposal_status(proposal_id: str, status: str, applied: bool = False) -> None:
    sql = (
        "UPDATE proposals SET status = %s, updated_at = now()"
        + (", applied_at = now()" if applied else "")
        + " WHERE proposal_id = %s"
    )
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (status, proposal_id))
        conn.commit()


# --------------------------------------------------------------------------- #
# Provenance (append-only)
# --------------------------------------------------------------------------- #
def append_provenance(entry: dict[str, Any]) -> dict[str, Any]:
    """Insert one immutable audit row. Returns the camelCase entry."""
    entry = dict(entry)
    entry_id = entry.get("entry_id") or _new_id("prov")
    entry["entry_id"] = entry_id
    sql = """
    INSERT INTO provenance (entry_id, doc_id, proposal_id, action, approved_by,
                            previous_version_ref, new_version_ref,
                            evidence_snapshot, confidence, reason)
    VALUES (%(entry_id)s, %(doc_id)s, %(proposal_id)s, %(action)s, %(approved_by)s,
            %(previous_version_ref)s, %(new_version_ref)s, %(evidence_snapshot)s,
            %(confidence)s, %(reason)s);
    """
    params = {
        "entry_id": entry_id,
        "doc_id": entry.get("doc_id"),
        "proposal_id": entry.get("proposal_id"),
        "action": entry.get("action", "update"),
        "approved_by": entry.get("approved_by", "unknown"),
        "previous_version_ref": entry.get("previous_version_ref"),
        "new_version_ref": entry.get("new_version_ref"),
        "evidence_snapshot": Jsonb(entry.get("evidence_snapshot", [])),
        "confidence": entry.get("confidence"),
        "reason": entry.get("reason"),
    }
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
        conn.commit()
    return list_provenance(entry_id=entry_id)[0]


def list_provenance(
    doc_id: str | None = None,
    proposal_id: str | None = None,
    entry_id: str | None = None,
) -> list[dict]:
    clauses, params = [], []
    if doc_id:
        clauses.append("doc_id = %s")
        params.append(doc_id)
    if proposal_id:
        clauses.append("proposal_id = %s")
        params.append(proposal_id)
    if entry_id:
        clauses.append("entry_id = %s")
        params.append(entry_id)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT entry_id, doc_id, proposal_id, action, approved_by, approved_at, "
                "previous_version_ref, new_version_ref, evidence_snapshot, confidence, reason "
                f"FROM provenance{where} ORDER BY approved_at DESC",
                params,
            )
            rows = cur.fetchall()
    return [
        {
            "entryId": r["entry_id"],
            "docId": r["doc_id"],
            "proposalId": r["proposal_id"],
            "action": r["action"],
            "approvedBy": r["approved_by"],
            "approvedAt": r["approved_at"].isoformat() if r["approved_at"] else None,
            "previousVersionRef": r["previous_version_ref"],
            "newVersionRef": r["new_version_ref"],
            "evidenceSnapshot": r["evidence_snapshot"] or [],
            "confidence": r["confidence"],
            "reason": r["reason"],
        }
        for r in rows
    ]


def stamp_verified(doc_id: str, commit_sha: str | None) -> None:
    """Record that a doc was verified at ``commit_sha`` (drives health=green)."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE documents SET last_verified_sha = %s, last_verified_at = now(), "
                "updated_at = now() WHERE doc_id = %s",
                (commit_sha, doc_id),
            )
        conn.commit()


# --------------------------------------------------------------------------- #
# Governed graph (ACL-filtered, real health/importance)
# --------------------------------------------------------------------------- #
def _collect_edge_signals(edge_rows: list[dict]) -> dict[str, dict]:
    sig: dict[str, dict] = {}

    def slot(d: str) -> dict:
        return sig.setdefault(
            d, {"conflict": False, "duplicate": False, "deprecated": False, "inbound": 0}
        )

    for e in edge_rows:
        f, t, typ = e["from_doc"], e["to_doc"], e["type"]
        if typ == "sibling":
            continue  # structural/visual only — doesn't affect health or importance
        slot(t)["inbound"] += 1
        if typ == "conflicts-with":
            slot(f)["conflict"] = True
            slot(t)["conflict"] = True
        elif typ == "duplicate-of":
            slot(f)["duplicate"] = True
            slot(t)["duplicate"] = True
        elif typ == "deprecated-by":
            slot(f)["deprecated"] = True
    return sig


def get_governed_graph(
    namespace: str | None = None, principal: Principal | None = None
) -> dict:
    """ACL-filtered graph with derived health/importance (README §8B GraphDTO)."""
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            if namespace:
                cur.execute(
                    "SELECT doc_id, repo, path, acl, commit_sha, last_verified_sha "
                    "FROM documents WHERE doc_id LIKE %s",
                    (f"{namespace}/%",),
                )
            else:
                cur.execute(
                    "SELECT doc_id, repo, path, acl, commit_sha, last_verified_sha FROM documents"
                )
            docs = cur.fetchall()
            cur.execute("SELECT from_doc, to_doc, type, weight FROM edges")
            edge_rows = cur.fetchall()

    edge_sig = _collect_edge_signals(edge_rows)
    nodes = []
    visible: set[str] = set()
    for d in docs:
        accessible = principal is None or can_access(principal, d.get("acl"))
        if not accessible:
            continue  # never leak inaccessible nodes
        visible.add(d["doc_id"])
        es = edge_sig.get(d["doc_id"], {})
        signals = DocSignals(
            has_conflict_edge=es.get("conflict", False),
            has_duplicate_edge=es.get("duplicate", False),
            is_deprecated=es.get("deprecated", False),
            inbound_refs=es.get("inbound", 0),
            current_commit_sha=d.get("commit_sha"),
            last_verified_sha=d.get("last_verified_sha"),
        )
        nodes.append(
            {
                "id": d["doc_id"],
                "label": d["path"].rsplit("/", 1)[-1],
                "health": derive_health(signals),
                "size": derive_importance(signals),
                "accessible": True,
                "repo": d["repo"],
            }
        )

    edges = [
        {"from": e["from_doc"], "to": e["to_doc"], "type": e["type"], "weight": e["weight"]}
        for e in edge_rows
        if e["from_doc"] in visible and e["to_doc"] in visible
    ]
    nodes.sort(key=lambda n: n["id"])
    edges.sort(key=lambda e: (e["from"], e["to"], e["type"]))
    return {"nodes": nodes, "edges": edges}


# --------------------------------------------------------------------------- #
# Metrics signal gathering
# --------------------------------------------------------------------------- #
def get_metric_signals() -> MetricSignals:
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT COUNT(*) AS n FROM documents")
            total_docs = cur.fetchone()["n"]
            cur.execute(
                "SELECT COUNT(*) AS n FROM documents WHERE last_verified_sha IS NOT NULL"
            )
            docs_verified = cur.fetchone()["n"]
            cur.execute(
                "SELECT COUNT(*) AS n FROM documents "
                "WHERE last_verified_sha IS NULL OR last_verified_sha <> commit_sha"
            )
            stale_detected = cur.fetchone()["n"]
            cur.execute("SELECT type, COUNT(*) AS n FROM edges GROUP BY type")
            by_type = {r["type"]: r["n"] for r in cur.fetchall()}
            cur.execute(
                "SELECT payload->>'action' AS action, COUNT(*) AS n "
                "FROM proposals WHERE status = 'applied' GROUP BY payload->>'action'"
            )
            applied = {r["action"]: r["n"] for r in cur.fetchall()}
            cur.execute(
                "SELECT AVG(EXTRACT(EPOCH FROM (applied_at - created_at)) / 3600.0) AS h "
                "FROM proposals WHERE status = 'applied' AND applied_at IS NOT NULL"
            )
            avg_hours = cur.fetchone()["h"] or 0.0

    return MetricSignals(
        total_docs=total_docs,
        docs_verified=docs_verified,
        stale_detected=stale_detected,
        conflicts_detected=by_type.get("conflicts-with", 0),
        duplicates_detected=by_type.get("duplicate-of", 0),
        broken_links_detected=0,
        applied_update=applied.get("update", 0),
        applied_merge=applied.get("merge", 0),
        applied_deprecate=applied.get("deprecate", 0),
        applied_link=applied.get("link", 0),
        avg_time_to_update_hours=float(avg_hours),
    )


def get_document_meta(doc_id: str) -> Optional[dict]:
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT doc_id, repo, path, acl, commit_sha, last_verified_sha "
                "FROM documents WHERE doc_id = %s",
                (doc_id,),
            )
            return cur.fetchone()


def get_metrics_dto() -> dict:
    """Gather raw counts and reduce them to a camelCase MetricsDTO."""
    return compute_metrics(get_metric_signals())
