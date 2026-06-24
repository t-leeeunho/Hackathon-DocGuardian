"""Edge cases from code review: negative scores, intake provenance, diff synthesis."""

from __future__ import annotations

from app.agents.graph import _build_diff, run_chat, run_propose
from app.agents.schemas import CuratorDraft
from conftest import make_row


def test_negative_similarity_score_does_not_crash_chat(patch_retrieval):
    # cosine similarity is in [-1, 1]; a negative-tail row must not raise.
    rows = [
        make_row("vscode/build.md", 0.83),
        make_row("vscode/old.md", -0.07, commit_sha="abc123"),
    ]
    patch_retrieval(rows)
    ans = run_chat("how do I build?", repo="vscode")
    assert 0.0 <= ans["confidence"] <= 1.0
    assert all(0.0 <= c["relevance"] <= 1.0 for c in ans["citations"])


def test_negative_similarity_score_does_not_crash_propose(patch_retrieval):
    rows = [
        make_row("vscode/build.md", 0.83),
        make_row("vscode/old.md", -0.03, commit_sha="abc123"),
    ]
    patch_retrieval(rows)
    p = run_propose("Unify the build docs", repo="vscode")
    # evidence[] is built from ALL rows incl. the negative-score tail.
    assert p["evidence"] and all(0.0 <= e["relevance"] <= 1.0 for e in p["evidence"])


def test_weak_negative_score_chat_short_circuits(patch_retrieval):
    # exercises the clamp on BOTH confidence and citation relevance in the short-circuit.
    patch_retrieval([make_row("vscode/x.md", -0.10)])
    ans = run_chat("anything", repo="vscode")
    assert ans["needs_human_review"] is True
    assert 0.0 <= ans["confidence"] <= 1.0
    assert all(0.0 <= c["relevance"] <= 1.0 for c in ans["citations"])


def test_chat_intake_only_evidence_forces_review(patch_retrieval):
    # intake/user docs carry commit_sha="" -> no provenance -> human review.
    patch_retrieval([make_row("user/notes.md", 0.91, commit_sha="")])
    ans = run_chat("what do my notes say?", repo="user")
    assert ans["needs_human_review"] is True
    assert ans["citations"] and ans["citations"][0]["commit_sha"] == ""


def test_build_diff_synthesizes_when_model_gives_no_diff():
    rows = [make_row("vscode/build.md", 0.9, text="Run npm ci then npm run watch.")]
    draft = CuratorDraft(
        action="update",
        target_doc_id="vscode/build.md",
        draft="Run `npm ci` then `npm run watch`.",
        citations=[],
        diff=None,
        confidence=0.8,
        risk_level="low",
        conflicts_with=[],
    )
    diff = _build_diff(draft, rows, [])
    assert diff.before  # synthesized from the top retrieved row
    assert diff.after  # synthesized from the draft
