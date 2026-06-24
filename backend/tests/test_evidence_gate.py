"""Deterministic evidence gate (_finalize_proposal) — evidence-or-review."""

from __future__ import annotations

from app.agents.graph import LOW_CONFIDENCE_THRESHOLD, _finalize_proposal


def _proposal(**overrides) -> dict:
    base = {
        "recommendation": "approve",
        "confidence": 0.9,
        "citations": [
            {"doc_id": "a/b.md", "line_range": [1, 4], "commit_sha": "deadbeef", "relevance": 0.9}
        ],
        "uncertainty": None,
    }
    base.update(overrides)
    return base


def test_strong_proposal_passes_unchanged():
    out = _finalize_proposal(_proposal())
    assert out["recommendation"] == "approve"
    assert out["uncertainty"] is None


def test_no_citations_forces_review():
    out = _finalize_proposal(_proposal(citations=[]))
    assert out["recommendation"] == "needs-review"
    assert "no supporting citations" in out["uncertainty"]


def test_missing_commit_sha_forces_review():
    out = _finalize_proposal(
        _proposal(
            citations=[{"doc_id": "a/b.md", "line_range": [1, 4], "commit_sha": "", "relevance": 0.5}]
        )
    )
    assert out["recommendation"] == "needs-review"
    assert "commit provenance" in out["uncertainty"]


def test_low_confidence_forces_review():
    out = _finalize_proposal(_proposal(confidence=LOW_CONFIDENCE_THRESHOLD - 0.1))
    assert out["recommendation"] == "needs-review"
    assert "confidence" in out["uncertainty"]


def test_existing_uncertainty_is_preserved():
    out = _finalize_proposal(_proposal(citations=[], uncertainty="prior note."))
    assert out["uncertainty"].startswith("prior note.")
    assert "Forced human review" in out["uncertainty"]
