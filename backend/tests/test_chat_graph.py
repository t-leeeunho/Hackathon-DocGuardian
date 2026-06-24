"""Chat (RAG) graph behaviour: weak-evidence gating, scope, grounded citations."""

from __future__ import annotations

from app.agents.graph import run_chat
from conftest import make_row


def test_weak_evidence_short_circuits_without_llm(patch_retrieval):
    patch_retrieval([make_row("vscode/build.md", 0.30)])
    answer = run_chat("how do I build?", repo="vscode")
    assert answer["needs_human_review"] is True
    assert "human review" in answer["answer"].lower()
    assert answer["scope"] == "vscode"


def test_empty_retrieval_short_circuits(patch_retrieval):
    patch_retrieval([])
    answer = run_chat("anything at all")
    assert answer["needs_human_review"] is True
    assert answer["citations"] == []
    assert answer["scope"] == "all"


def test_strong_evidence_returns_grounded_answer(patch_retrieval, rows_strong):
    patch_retrieval(rows_strong)
    answer = run_chat("how do I build vscode?", repo="vscode")
    assert answer["needs_human_review"] is False
    assert answer["citations"], "expected grounded citations"
    # commit SHA is forced from the retrieved rows, never the model.
    assert answer["citations"][0]["commit_sha"] == "f00dcafe1234"
    assert answer["scope"] == "vscode"
    assert 0.0 <= answer["confidence"] <= 1.0


def test_chat_drops_hallucinated_citations_and_flags_review():
    from app.agents.graph import _ground_chat_citations
    from app.agents.schemas import ChatAnswer, Citation

    rows = [make_row("real/doc.md", 0.9)]
    answer = ChatAnswer(
        answer="confident but ungrounded",
        citations=[Citation(doc_id="ghost/none.md", line_range=[1, 2], relevance=0.9)],
        confidence=0.97,
        needs_human_review=False,
    )
    out = _ground_chat_citations(answer, rows)
    # the hallucinated citation is dropped and replaced with real retrieved evidence
    assert [c.doc_id for c in out.citations] == ["real/doc.md"]
    assert out.citations[0].commit_sha == "f00dcafe1234"
    assert out.needs_human_review is True


def test_chat_low_model_confidence_forces_review():
    from app.agents.graph import _ground_chat_citations
    from app.agents.schemas import ChatAnswer, Citation

    rows = [make_row("real/doc.md", 0.9)]
    answer = ChatAnswer(
        answer="x",
        citations=[Citation(doc_id="real/doc.md", line_range=[8, 12], relevance=0.9)],
        confidence=0.3,
        needs_human_review=False,
    )
    out = _ground_chat_citations(answer, rows)
    assert out.needs_human_review is True


def test_chat_mixed_citations_keep_grounded_without_review():
    from app.agents.graph import _ground_chat_citations
    from app.agents.schemas import ChatAnswer, Citation

    rows = [make_row("real/doc.md", 0.9)]
    answer = ChatAnswer(
        answer="x",
        citations=[
            Citation(doc_id="real/doc.md", line_range=[8, 12], relevance=0.9),
            Citation(doc_id="ghost/none.md", line_range=[1, 2], relevance=0.5),
        ],
        confidence=0.9,
        needs_human_review=False,
    )
    out = _ground_chat_citations(answer, rows)
    assert [c.doc_id for c in out.citations] == ["real/doc.md"]
    assert out.needs_human_review is False
