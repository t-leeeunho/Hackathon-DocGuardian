"""Tests for the chat provider abstraction and the deterministic fake LLM."""

from __future__ import annotations

import pytest

from app.agents import graph, llm
from app.agents.schemas import ChatAnswer, CuratorDraft, GuardianReview
from conftest import make_row


def _chat_prompt() -> str:
    rows = [make_row("vscode/build.md", 0.88)]
    return (
        f"{graph.CURATOR_CHAT_SYSTEM}\n\nQUESTION:\nhow do I build?\n\n"
        f"SOURCES:\n{graph._format_sources(rows)}"
    )


def _curator_prompt(instruction: str) -> str:
    rows = [
        make_row("vscode/build.md", 0.88),
        make_row("vscode/contributing.md", 0.81, text="Use yarn.", commit_sha="bbb"),
    ]
    return (
        f"{graph.CURATOR_DRAFT_SYSTEM}\n\nINSTRUCTION:\n{instruction}\n\n"
        f"SOURCES:\n{graph._format_sources(rows)}"
    )


# --- provider selection ------------------------------------------------------
def test_chat_provider_defaults_to_azure(monkeypatch):
    monkeypatch.delenv("CHAT_PROVIDER", raising=False)
    assert llm.chat_provider() == "azure"


def test_get_chat_llm_returns_fake_when_selected(monkeypatch):
    monkeypatch.setenv("CHAT_PROVIDER", "fake")
    assert isinstance(llm.get_chat_llm(), llm.FakeChatLLM)


def test_azure_unconfigured_raises(monkeypatch):
    monkeypatch.setenv("CHAT_PROVIDER", "azure")
    for key in ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_CHAT_DEPLOYMENT"):
        monkeypatch.delenv(key, raising=False)
    llm._azure_chat_llm.cache_clear()
    with pytest.raises(llm.AzureNotConfiguredError):
        llm.get_chat_llm()


def test_unknown_provider_raises(monkeypatch):
    monkeypatch.setenv("CHAT_PROVIDER", "bogus")
    with pytest.raises(llm.AzureNotConfiguredError):
        llm.get_chat_llm()


def test_azure_is_configured_reflects_env(monkeypatch):
    for key in ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_CHAT_DEPLOYMENT"):
        monkeypatch.setenv(key, "x")
    assert llm.azure_is_configured() is True
    monkeypatch.delenv("AZURE_OPENAI_API_KEY")
    assert llm.azure_is_configured() is False


def test_chat_provider_normalizes_case_and_whitespace(monkeypatch):
    monkeypatch.setenv("CHAT_PROVIDER", "  FAKE ")
    assert llm.chat_provider() == "fake"
    assert isinstance(llm.get_chat_llm(), llm.FakeChatLLM)


# --- fake determinism + schema validity --------------------------------------
def test_fake_chat_answer_is_deterministic_and_valid():
    runnable = llm.FakeChatLLM().with_structured_output(ChatAnswer)
    prompt = _chat_prompt()
    a1 = runnable.invoke(prompt)
    a2 = runnable.invoke(prompt)
    assert isinstance(a1, ChatAnswer)
    assert a1.model_dump() == a2.model_dump()
    assert a1.needs_human_review is False
    assert 0.0 <= a1.confidence <= 1.0


def test_fake_curator_infers_merge_and_target():
    draft = llm.FakeChatLLM().with_structured_output(CuratorDraft).invoke(
        _curator_prompt("Unify the build instructions into one canonical doc")
    )
    assert isinstance(draft, CuratorDraft)
    assert draft.action == "merge"
    assert draft.target_doc_id == "vscode/build.md"


@pytest.mark.parametrize(
    "instruction,expected",
    [
        ("Create a new onboarding doc", "create"),
        ("Deprecate the old build doc", "deprecate"),
        ("Link these related docs", "link"),
        ("Update the watch command", "update"),
    ],
)
def test_fake_curator_action_inference(instruction, expected):
    draft = (
        llm.FakeChatLLM().with_structured_output(CuratorDraft).invoke(_curator_prompt(instruction))
    )
    assert draft.action == expected


def test_fake_guardian_defaults_to_needs_review():
    review = llm.FakeChatLLM().with_structured_output(GuardianReview).invoke(
        "You are the Guardian agent.\nPROPOSED CHANGE (JSON):\n{...}"
    )
    assert isinstance(review, GuardianReview)
    assert review.recommendation == "needs-review"


def test_fake_rejects_unknown_schema():
    from pydantic import BaseModel

    class Other(BaseModel):
        x: int = 0

    with pytest.raises(TypeError):
        llm.FakeChatLLM().with_structured_output(Other).invoke("whatever")
