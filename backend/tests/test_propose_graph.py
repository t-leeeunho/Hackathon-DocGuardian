"""Propose graph behaviour: rich AgentProposal, evidence gate, no-evidence path."""

from __future__ import annotations

from app.agents.graph import run_propose
from conftest import make_row


def test_proposal_has_rich_grounded_fields(patch_retrieval, rows_strong):
    patch_retrieval(rows_strong)
    p = run_propose("Unify the build instructions into one canonical doc", repo="vscode")

    assert p["proposal_id"].startswith("prop_")
    assert p["action"] == "merge"
    assert p["target_doc_id"] == "vscode/build.md"
    assert p["source_doc_ids"]
    assert p["proposed_by"] == "curator-agent"
    assert p["created_at"]
    assert p["verification"] is None

    # evidence[] is grounded straight from retrieved rows
    assert p["evidence"], "expected grounded evidence"
    first = p["evidence"][0]
    assert first["commit_sha"] == "f00dcafe1234"
    assert first["chunk_id"]
    assert first["quote"]

    # citations carry authoritative SHAs; a structured diff is present
    assert p["citations"][0]["commit_sha"] == "f00dcafe1234"
    assert p["diff"] is not None and (p["diff"]["before"] or p["diff"]["after"])

    assert p["recommendation"] in ("approve", "needs-review", "reject")


def test_no_evidence_short_circuits_before_any_llm(patch_retrieval):
    patch_retrieval([])
    p = run_propose("merge the build docs")
    assert p["action"] == "flag"
    assert p["recommendation"] == "needs-review"
    assert p["proposed_by"] == "orchestrator"
    assert p["evidence"] == []
    assert p["uncertainty"]


def test_weak_evidence_short_circuits_before_any_llm(patch_retrieval):
    patch_retrieval([make_row("x/y.md", 0.20)])
    p = run_propose("merge the build docs")
    assert p["proposed_by"] == "orchestrator"
    assert p["recommendation"] == "needs-review"


def test_guardian_preserves_curator_draft_and_citations(patch_retrieval, rows_strong):
    # Guardian contributes only judgment; the Curator's draft + grounded citations survive.
    patch_retrieval(rows_strong)
    p = run_propose("Unify the build docs into one canonical doc", repo="vscode")
    assert p["draft"].startswith("## Proposed")
    assert [c["doc_id"] for c in p["citations"]] == ["vscode/build.md", "vscode/contributing.md"]
    assert all(c["commit_sha"] for c in p["citations"])
