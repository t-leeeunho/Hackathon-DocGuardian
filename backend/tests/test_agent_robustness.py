"""Robustness: LLM failures fail closed to needs-review; auto provider; call budget."""

from __future__ import annotations

import pytest

from app.agents import graph, llm
from app.agents.llm import _FakeStructuredRunnable
from app.agents.schemas import GuardianReview
from conftest import make_row


class _BoomRunnable:
    def invoke(self, _prompt):
        raise RuntimeError("simulated model failure")


class _BoomLLM:
    """Every structured-output call raises."""

    def with_structured_output(self, _schema, **_):
        return _BoomRunnable()


class _NoneRunnable:
    def invoke(self, _prompt):
        return None


class _NoneLLM:
    """Returns None (a parse miss) instead of a schema instance."""

    def with_structured_output(self, _schema, **_):
        return _NoneRunnable()


class _PartialBoomLLM:
    """Raises only for one schema; delegates to the real fake otherwise."""

    def __init__(self, boom_schema):
        self.boom_schema = boom_schema

    def with_structured_output(self, schema, **_):
        return _BoomRunnable() if schema is self.boom_schema else _FakeStructuredRunnable(schema)


class _CountingLLM:
    """Counts invoke() calls; delegates to the real fake."""

    def __init__(self):
        self.calls = 0

    def with_structured_output(self, schema, **_):
        outer = self
        real = _FakeStructuredRunnable(schema)

        class _R:
            def invoke(self, prompt):
                outer.calls += 1
                return real.invoke(prompt)

        return _R()


@pytest.fixture
def patch_llm(monkeypatch):
    def _apply(fake_llm):
        monkeypatch.setattr(graph, "get_chat_llm", lambda *a, **k: fake_llm)

    return _apply


# --- LLM failure fails closed to human review --------------------------------
def test_chat_llm_failure_returns_needs_review(patch_retrieval, rows_strong, patch_llm):
    patch_retrieval(rows_strong)
    patch_llm(_BoomLLM())
    ans = graph.run_chat("how do I build?", repo="vscode")
    assert ans["needs_human_review"] is True
    assert "human review" in ans["answer"].lower()
    # the fallback still attaches real retrieved evidence with authoritative SHAs
    assert ans["citations"] and ans["citations"][0]["commit_sha"] == "f00dcafe1234"


def test_propose_curator_failure_returns_flag(patch_retrieval, rows_strong, patch_llm):
    patch_retrieval(rows_strong)
    patch_llm(_BoomLLM())
    p = graph.run_propose("Unify the build docs", repo="vscode")
    assert p["action"] == "flag"
    assert p["recommendation"] == "needs-review"
    assert p["proposed_by"] == "orchestrator"
    assert p["confidence"] == 0.0


def test_chat_llm_returning_none_fails_closed(patch_retrieval, rows_strong, patch_llm):
    patch_retrieval(rows_strong)
    patch_llm(_NoneLLM())  # parse miss -> None, not an exception
    ans = graph.run_chat("how do I build?", repo="vscode")
    assert ans["needs_human_review"] is True
    assert ans["citations"]


def test_propose_guardian_failure_preserves_curator_draft(patch_retrieval, rows_strong, patch_llm):
    patch_retrieval(rows_strong)
    patch_llm(_PartialBoomLLM(GuardianReview))
    p = graph.run_propose("Unify the build docs into one canonical doc", repo="vscode")
    # Curator's draft is preserved; only the Guardian failed -> needs-review.
    assert p["action"] == "merge"
    assert p["proposed_by"] == "curator-agent"
    assert p["draft"]
    assert p["recommendation"] == "needs-review"
    assert "unavailable" in (p["guardian_reasoning"] or "").lower()


# --- LLM-call budget (cost invariant) ----------------------------------------
def test_chat_uses_one_llm_call(patch_retrieval, rows_strong, patch_llm):
    patch_retrieval(rows_strong)
    counter = _CountingLLM()
    patch_llm(counter)
    graph.run_chat("how do I build?", repo="vscode")
    assert counter.calls == 1


def test_propose_uses_two_llm_calls(patch_retrieval, rows_strong, patch_llm):
    patch_retrieval(rows_strong)
    counter = _CountingLLM()
    patch_llm(counter)
    graph.run_propose("Unify the build docs into one canonical doc", repo="vscode")
    assert counter.calls == 2


def test_propose_no_evidence_uses_zero_llm_calls(patch_retrieval, patch_llm):
    patch_retrieval([])
    counter = _CountingLLM()
    patch_llm(counter)
    graph.run_propose("Unify the build docs")
    assert counter.calls == 0


# --- provider auto mode ------------------------------------------------------
def test_auto_provider_uses_fake_when_azure_unconfigured(monkeypatch):
    monkeypatch.setenv("CHAT_PROVIDER", "auto")
    for key in ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_CHAT_DEPLOYMENT"):
        monkeypatch.delenv(key, raising=False)
    assert isinstance(llm.get_chat_llm(), llm.FakeChatLLM)


def test_auto_provider_uses_azure_when_configured(monkeypatch):
    monkeypatch.setenv("CHAT_PROVIDER", "auto")
    for key in ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_CHAT_DEPLOYMENT"):
        monkeypatch.setenv(key, "x")
    sentinel = object()
    monkeypatch.setattr(llm, "_azure_chat_llm", lambda temperature: sentinel)
    assert llm.get_chat_llm() is sentinel
