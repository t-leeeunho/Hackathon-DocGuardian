"""Approval workflow + rollback (README §6.8, §8A.7).

The governed-write sequence for every authoritative change:

    load proposal -> check ACL + risk/confidence -> (stage if sensitive) ->
    capture previousVersionRef -> apply -> capture newVersionRef ->
    append ProvenanceEntry -> update metrics (implicit) -> emit WS events.

Approvals are **idempotent**: re-approving an already-applied proposal returns the
existing result without re-applying or double-writing provenance. High-risk or
low-confidence proposals require a **staged** first approval (recorded as
``needs-review``) before a second approval applies them.
"""

from __future__ import annotations

import hashlib
from typing import Optional

from app.governance import store
from app.governance.acl import Principal, can_write
from app.services import events

WEAK_CONFIDENCE = 0.5


class GovernanceError(Exception):
    """Base for approval/rollback failures, with an HTTP-ish status hint."""

    status = 400


class ProposalNotFound(GovernanceError):
    status = 404


class AccessDenied(GovernanceError):
    status = 403


class StagedApprovalRequired(GovernanceError):
    """Not an error per se — signals the first stage of a sensitive approval."""

    status = 202


def _version_ref(text: str) -> str:
    return "blob:sha256:" + hashlib.sha256((text or "").encode()).hexdigest()


def _requires_staging(payload: dict) -> bool:
    risk = payload.get("risk_level")
    confidence = payload.get("confidence") or 0.0
    return risk == "high" or confidence < WEAK_CONFIDENCE


def approve_proposal(
    proposal_id: str,
    approver: str,
    roles: Optional[list[str]] = None,
    reason: str = "",
    force: bool = False,
) -> dict:
    """Approve and apply a proposal. Returns an API-ready result dict."""
    row = store.get_proposal_row(proposal_id)
    if row is None:
        raise ProposalNotFound(f"proposal not found: {proposal_id}")

    payload = row["payload"] or {}
    doc_id = row["doc_id"] or payload.get("target_doc_id")

    # Idempotency: already applied -> return the existing provenance.
    if row["status"] == "applied":
        return {
            "proposalId": proposal_id,
            "status": "applied",
            "staged": False,
            "provenance": store.list_provenance(proposal_id=proposal_id),
        }

    # ACL: the approver must hold write rights on the target doc.
    principal = Principal.from_tokens(approver, roles)
    meta = store.get_document_meta(doc_id) if doc_id else None
    acl = meta.get("acl") if meta else None
    if not can_write(principal, acl):
        raise AccessDenied(f"{approver} cannot write {doc_id}")

    # Staged approval for sensitive/low-confidence changes.
    if _requires_staging(payload) and row["status"] != "needs-review" and not force:
        store.set_proposal_status(proposal_id, "needs-review")
        events.publish("proposal", proposalId=proposal_id, status="needs-review")
        raise StagedApprovalRequired(
            "High-risk/low-confidence proposal staged for review; approve again to apply."
        )

    # Capture before/after refs from the diff/draft.
    diff = payload.get("diff") or {}
    prev_ref = _version_ref(diff.get("before") or (meta.get("commit_sha") if meta else ""))
    new_text = payload.get("draft") or diff.get("after") or ""
    new_ref = _version_ref(new_text)

    # Apply: mark applied + stamp the doc as verified at its current commit.
    store.set_proposal_status(proposal_id, "applied", applied=True)
    if doc_id and meta:
        store.stamp_verified(doc_id, meta.get("commit_sha"))

    entry = store.append_provenance(
        {
            "doc_id": doc_id,
            "proposal_id": proposal_id,
            "action": payload.get("action", "update"),
            "approved_by": approver,
            "previous_version_ref": prev_ref,
            "new_version_ref": new_ref,
            "evidence_snapshot": payload.get("evidence") or payload.get("citations") or [],
            "confidence": payload.get("confidence"),
            "reason": reason or payload.get("guardian_reasoning") or "",
        }
    )

    # Materialize the AI-rewritten document so the user can READ it in the file
    # tree (under the `curated/` namespace), alongside the untouched original.
    # Best-effort: a failure here must not fail the approval/provenance write.
    if doc_id and (payload.get("draft") or "").strip():
        try:
            from app.ingestion.intake import ingest_content

            ingest_content(doc_id, payload["draft"], namespace="curated")
        except Exception:  # pragma: no cover - curated copy is non-critical
            pass

    events.publish("proposal", proposalId=proposal_id, status="applied", docId=doc_id)
    events.publish("graph", docId=doc_id)
    events.publish("metrics")
    return {
        "proposalId": proposal_id,
        "status": "applied",
        "staged": False,
        "provenance": [entry],
    }


def rollback_proposal(
    proposal_id: str,
    approver: str,
    roles: Optional[list[str]] = None,
    reason: str = "",
) -> dict:
    """Roll back an applied proposal: append a NEW provenance entry (append-only)."""
    row = store.get_proposal_row(proposal_id)
    if row is None:
        raise ProposalNotFound(f"proposal not found: {proposal_id}")
    if row["status"] != "applied":
        raise GovernanceError(f"proposal {proposal_id} is not applied; nothing to roll back")

    payload = row["payload"] or {}
    doc_id = row["doc_id"] or payload.get("target_doc_id")
    principal = Principal.from_tokens(approver, roles)
    meta = store.get_document_meta(doc_id) if doc_id else None
    acl = meta.get("acl") if meta else None
    if not can_write(principal, acl):
        raise AccessDenied(f"{approver} cannot roll back {doc_id}")

    # The newest applied entry tells us what to restore to.
    history = store.list_provenance(proposal_id=proposal_id)
    last = history[0] if history else {}
    store.set_proposal_status(proposal_id, "rolled-back")

    entry = store.append_provenance(
        {
            "doc_id": doc_id,
            "proposal_id": proposal_id,
            "action": "rolled-back",
            "approved_by": approver,
            "previous_version_ref": last.get("newVersionRef"),
            "new_version_ref": last.get("previousVersionRef"),
            "evidence_snapshot": last.get("evidenceSnapshot", []),
            "confidence": payload.get("confidence"),
            "reason": reason or "rollback",
        }
    )
    events.publish("proposal", proposalId=proposal_id, status="rolled-back", docId=doc_id)
    events.publish("graph", docId=doc_id)
    events.publish("metrics")
    return {"proposalId": proposal_id, "status": "rolled-back", "provenance": [entry]}
