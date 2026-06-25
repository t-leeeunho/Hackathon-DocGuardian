"""Tests for the opt-in LLM enhancement layer (``app.analysis.llm``).

Fully offline: the autouse ``_fake_chat_env`` fixture (conftest) sets
``CHAT_PROVIDER=fake`` and unsets Azure, so nothing here touches the network. The
analyzer must *always* return a schema-valid ``LlmQualityNotes`` camelCase dict and
must **never raise** — including when the provider is missing, throws, or returns
garbage. It must also honour the cost guard: at most one model call per invocation.
"""

from __future__ import annotations

import pytest

from app.agents.llm import AzureNotConfiguredError
from app.analysis.llm import _LlmNotes, analyze_with_llm

_EMPTY = {"clarityScore": None, "issues": [], "suggestedSections": []}
_KEYS = {"clarityScore", "issues", "suggestedSections"}

GOOD_DOC = """\
# Overview

This guide explains how to install and use the tool in your project.

## Installation

Run `pip install mytool` to get started with the package.

## Usage

```python
import mytool
mytool.run()
```
"""
GOOD_HEADINGS = [["Overview"], ["Installation"], ["Usage"]]


# --------------------------------------------------------------------------- #
# Test doubles
# --------------------------------------------------------------------------- #
class _SpyLLM:
    """Stand-in chat model that records calls and returns a canned structured output.

    ``result`` may be a ``_LlmNotes`` (happy path), ``None`` (empty output), or an
    ``Exception`` instance/class to raise from ``.invoke``.
    """

    def __init__(self, result):
        self.result = result
        self.structured_calls = 0
        self.invoke_calls = 0
        self.last_prompt: str | None = None

    def with_structured_output(self, schema, **_):
        self.structured_calls += 1
        assert schema is _LlmNotes  # we always ask for our LOCAL schema
        return self

    def invoke(self, prompt):
        self.invoke_calls += 1
        self.last_prompt = prompt
        if isinstance(self.result, Exception):
            raise self.result
        if isinstance(self.result, type) and issubclass(self.result, Exception):
            raise self.result("boom")
        return self.result


def _patch_llm(monkeypatch, llm) -> None:
    monkeypatch.setattr("app.agents.llm.get_chat_llm", lambda *a, **k: llm)


# --------------------------------------------------------------------------- #
# Happy path / shape
# --------------------------------------------------------------------------- #
def test_normal_doc_returns_camelcase_keys_with_correct_types():
    """Against the real fake provider (no Azure) the result is always valid.

    The fake doesn't recognise our LOCAL ``_LlmNotes`` schema, so this exercises the
    safe-degrade path — which still yields the three camelCase keys with valid types.
    """
    out = analyze_with_llm("vscode/build.md", GOOD_DOC, heading_paths=GOOD_HEADINGS)

    assert isinstance(out, dict)
    assert set(out) == _KEYS
    assert out["clarityScore"] is None or isinstance(out["clarityScore"], float)
    assert isinstance(out["issues"], list)
    assert all(isinstance(i, str) for i in out["issues"])
    assert isinstance(out["suggestedSections"], list)
    assert all(isinstance(s, str) for s in out["suggestedSections"])


def test_populated_notes_convert_to_camelcase(monkeypatch):
    """A model that returns real notes is normalised into the camelCase contract."""
    spy = _SpyLLM(
        _LlmNotes(
            clarity_score=0.82,
            issues=["Intro is vague", "   ", "No example for the watch command"],
            suggested_sections=["Troubleshooting", ""],
        )
    )
    _patch_llm(monkeypatch, spy)

    out = analyze_with_llm("vscode/build.md", GOOD_DOC, heading_paths=GOOD_HEADINGS)

    assert out["clarityScore"] == 0.82
    # Blank/whitespace entries are filtered out during normalization.
    assert out["issues"] == ["Intro is vague", "No example for the watch command"]
    assert out["suggestedSections"] == ["Troubleshooting"]


def test_clarity_score_is_clamped_into_unit_range(monkeypatch):
    _patch_llm(monkeypatch, _SpyLLM(_LlmNotes(clarity_score=4.5)))
    assert analyze_with_llm("d", "real content here")["clarityScore"] == 1.0

    _patch_llm(monkeypatch, _SpyLLM(_LlmNotes(clarity_score=-2.0)))
    assert analyze_with_llm("d", "real content here")["clarityScore"] == 0.0


# --------------------------------------------------------------------------- #
# Degradation paths — never raise, always safe-empty
# --------------------------------------------------------------------------- #
def test_azure_not_configured_degrades_to_empty(monkeypatch):
    def _raise(*_a, **_k):
        raise AzureNotConfiguredError("Azure not configured")

    monkeypatch.setattr("app.agents.llm.get_chat_llm", _raise)

    out = analyze_with_llm("vscode/build.md", GOOD_DOC, heading_paths=GOOD_HEADINGS)
    assert out == _EMPTY


def test_model_that_throws_degrades_to_empty(monkeypatch):
    _patch_llm(monkeypatch, _SpyLLM(RuntimeError("model exploded")))
    out = analyze_with_llm("vscode/build.md", "Some real content to review.")
    assert out == _EMPTY


def test_model_that_returns_none_degrades_to_empty(monkeypatch):
    _patch_llm(monkeypatch, _SpyLLM(None))
    out = analyze_with_llm("vscode/build.md", "Some real content to review.")
    assert out == _EMPTY


def test_model_returning_wrong_type_degrades_to_empty(monkeypatch):
    # A provider that hands back the wrong object must not leak through.
    _patch_llm(monkeypatch, _SpyLLM({"clarityScore": 0.9}))
    out = analyze_with_llm("vscode/build.md", "Some real content to review.")
    assert out == _EMPTY


# --------------------------------------------------------------------------- #
# Empty content short-circuit (must NOT call the model)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("empty", ["", "   ", "\n\t  \n"])
def test_empty_content_returns_empty_without_calling_model(monkeypatch, empty):
    called = {"n": 0}

    def _must_not_be_called(*_a, **_k):
        called["n"] += 1
        raise AssertionError("the model must not be invoked for empty content")

    monkeypatch.setattr("app.agents.llm.get_chat_llm", _must_not_be_called)

    out = analyze_with_llm("vscode/build.md", empty, heading_paths=GOOD_HEADINGS)
    assert out == _EMPTY
    assert called["n"] == 0


# --------------------------------------------------------------------------- #
# Cost guard — at most ONE LLM invocation per call
# --------------------------------------------------------------------------- #
def test_at_most_one_model_invocation(monkeypatch):
    spy = _SpyLLM(_LlmNotes(clarity_score=0.7, issues=["x"], suggested_sections=[]))
    _patch_llm(monkeypatch, spy)

    analyze_with_llm("vscode/build.md", GOOD_DOC, heading_paths=GOOD_HEADINGS)

    assert spy.invoke_calls == 1  # exactly one chat call (no retries / loops)
    assert spy.structured_calls == 1


def test_no_invocation_when_content_empty_spy(monkeypatch):
    spy = _SpyLLM(_LlmNotes())
    _patch_llm(monkeypatch, spy)

    analyze_with_llm("vscode/build.md", "")

    assert spy.invoke_calls == 0


# --------------------------------------------------------------------------- #
# Grounding — the prompt is built from supplied content/outline/quality only
# --------------------------------------------------------------------------- #
def test_prompt_is_grounded_in_supplied_signals(monkeypatch):
    from app.analysis.quality import analyze_quality
    from app.analysis.signals import DocAnalysisSignals

    spy = _SpyLLM(_LlmNotes(clarity_score=0.5))
    _patch_llm(monkeypatch, spy)

    dq = analyze_quality(
        DocAnalysisSignals(
            doc_id="vscode/build.md",
            repo="vscode",
            path="build.md",
            content="TODO short stub about installing the tool.",
            heading_paths=[["Overview"]],
            commit_sha=None,
            commit_date=None,
            last_verified_sha=None,
        )
    )

    out = analyze_with_llm(
        "vscode/build.md",
        "Install the tool, then run the watcher to build incrementally.",
        heading_paths=[["Overview"], ["Installation"]],
        deterministic_quality=dq,
    )

    prompt = spy.last_prompt
    assert "vscode/build.md" in prompt  # identity
    assert "watcher to build" in prompt  # supplied content is included
    assert "Installation" in prompt  # outline is included
    assert "placeholderCount" in prompt  # deterministic grounding is fed in
    assert out["clarityScore"] == 0.5


def test_deterministic_quality_is_optional(monkeypatch):
    spy = _SpyLLM(_LlmNotes(clarity_score=0.6))
    _patch_llm(monkeypatch, spy)

    out = analyze_with_llm("d", "Some content without quality grounding.")
    assert out["clarityScore"] == 0.6
    assert "(none provided)" in spy.last_prompt
