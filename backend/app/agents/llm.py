"""Chat model factory for the agent layer.

Two providers sit behind one ``get_chat_llm()`` seam so the LangGraph nodes never
care which one is active:

* ``azure`` (default) — Azure OpenAI chat. This is the ONLY place that needs Azure
  credentials; embeddings stay local (fastembed). Missing config raises
  ``AzureNotConfiguredError`` so the API returns a clean 503.
* ``fake`` — a deterministic, offline ``FakeChatLLM`` for local development, tests,
  and demo rehearsal without Azure. Select it with ``CHAT_PROVIDER=fake``.

The default stays ``azure`` to preserve the documented "503 when Azure is
unconfigured" contract for the real demo; ``fake`` is an explicit opt-in.
"""

from __future__ import annotations

import os
import re
from functools import lru_cache
from typing import Any

from app.agents.schemas import (
    ChatAnswer,
    Citation,
    CuratorDraft,
    GuardianReview,
    ProposalDiff,
)


class AzureNotConfiguredError(RuntimeError):
    pass


def azure_is_configured() -> bool:
    return all(
        os.getenv(k)
        for k in ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_CHAT_DEPLOYMENT")
    )


def chat_provider() -> str:
    """Active chat provider, read live so tests/env changes take effect.

    Defaults to ``azure``; set ``CHAT_PROVIDER=fake`` for offline development.
    """
    return os.getenv("CHAT_PROVIDER", "azure").strip().lower()


@lru_cache(maxsize=4)
def _azure_chat_llm(temperature: float):
    if not azure_is_configured():
        raise AzureNotConfiguredError(
            "Azure OpenAI is not configured. Set AZURE_OPENAI_ENDPOINT, "
            "AZURE_OPENAI_API_KEY, and AZURE_OPENAI_CHAT_DEPLOYMENT in .env "
            "(or set CHAT_PROVIDER=fake for offline development)."
        )

    from langchain_openai import AzureChatOpenAI

    return AzureChatOpenAI(
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        azure_deployment=os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT"],
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-06-01"),
        temperature=temperature,
    )


def get_chat_llm(temperature: float = 0.1):
    """Return the active chat model.

    With ``CHAT_PROVIDER=azure`` (default) returns a cached ``AzureChatOpenAI`` and
    raises ``AzureNotConfiguredError`` when the env is missing. With
    ``CHAT_PROVIDER=fake`` returns a deterministic offline ``FakeChatLLM``.
    """
    provider = chat_provider()
    if provider == "fake":
        return FakeChatLLM(temperature=temperature)
    if provider in ("", "azure"):
        return _azure_chat_llm(temperature)
    raise AzureNotConfiguredError(
        f"Unknown CHAT_PROVIDER={provider!r}; expected 'azure' or 'fake'."
    )


# --------------------------------------------------------------------------- #
# Deterministic offline fake (CHAT_PROVIDER=fake)
# --------------------------------------------------------------------------- #
def _section(prompt: str, start: str, *, until: str | None = None) -> str:
    """Return the text after marker ``start`` (optionally up to marker ``until``)."""
    idx = prompt.find(start)
    if idx == -1:
        return ""
    body = prompt[idx + len(start) :]
    if until and until in body:
        body = body[: body.find(until)]
    return body.strip()


def _sources_block(prompt: str) -> str:
    """The retrieved-sources section, anchored on the exact ``\\n\\nSOURCES:\\n`` marker.

    Using the precise (and last) marker avoids colliding with the word ``SOURCES:``
    that legitimately appears in an agent's system prompt.
    """
    marker = "\n\nSOURCES:\n"
    idx = prompt.rfind(marker)
    return prompt[idx + len(marker) :].strip() if idx != -1 else ""


def _first_source(prompt: str) -> tuple[str, str, list[int]]:
    """Parse the first ``[1] doc_id=… lines=a-b`` block produced by ``_format_sources``."""
    sources = _sources_block(prompt)
    if not sources or sources.startswith("(no sources"):
        return "", "", []
    # Blocks are joined by "\n\n"; split only at a real block boundary so that
    # blank lines inside a source's text don't truncate the snippet.
    first = re.split(r"\n\n(?=\[\d+\]\s+doc_id=)", sources)[0]
    header = re.search(r"doc_id=(\S+)\s+lines=(\d+)-(\d+)", first)
    doc_id = header.group(1) if header else ""
    line_range = [int(header.group(2)), int(header.group(3))] if header else []
    # The snippet is the indented text line(s) after this block's "heading:" line.
    snippet = ""
    lines = first.splitlines()
    for i, line in enumerate(lines):
        if line.lstrip().startswith("heading:"):
            snippet = " ".join(seg.strip() for seg in lines[i + 1 :]).strip()
            break
    return doc_id, snippet[:400], line_range


def _source_doc_ids(prompt: str) -> list[str]:
    seen: list[str] = []
    for m in re.finditer(r"doc_id=(\S+)", _sources_block(prompt)):
        if m.group(1) not in seen:
            seen.append(m.group(1))
    return seen


def _infer_action(instruction: str) -> str:
    t = instruction.lower()
    if any(w in t for w in ("merge", "unify", "consolidat", "canonical", "single source")):
        return "merge"
    if any(w in t for w in ("deprecat", "remove", "delete")):
        return "deprecate"
    if any(w in t for w in ("link", "cross-reference", "cross reference")):
        return "link"
    if any(w in t for w in ("flag", "stale", "outdated", "out of date")):
        return "flag"
    if any(w in t for w in ("create", "add ", "new ", "draft ")):
        return "create"
    return "update"


def _fake_chat_answer(prompt: str) -> ChatAnswer:
    doc_id, snippet, line_range = _first_source(prompt)
    if snippet:
        answer = f"Based on the documentation: {snippet[:240].rstrip('. ')}."
    else:
        answer = "Based on the available documentation, this is the recommended approach."
    citations = (
        [Citation(doc_id=doc_id, line_range=line_range or [0, 0], relevance=0.8)]
        if doc_id
        else []
    )
    return ChatAnswer(answer=answer, citations=citations, confidence=0.8, needs_human_review=False)


def _fake_curator_draft(prompt: str) -> CuratorDraft:
    instruction = _section(prompt, "\n\nINSTRUCTION:\n", until="\n\nSOURCES:\n") or _section(
        prompt, "\n\nQUESTION:\n", until="\n\nSOURCES:\n"
    )
    action = _infer_action(instruction)
    doc_id, snippet, _ = _first_source(prompt)
    doc_ids = _source_doc_ids(prompt)
    conflicts = doc_ids[1:2] if action in ("merge", "update", "deprecate") else []
    draft = (
        f"## Proposed {action}\n\n{instruction.strip() or 'Apply the requested change.'}\n\n"
        f"Grounded in: {snippet[:200].strip()}"
    ).strip()
    diff = ProposalDiff(
        before=snippet[:200], after=draft[:200], format="unified", line_range=None
    )
    return CuratorDraft(
        action=action,
        target_doc_id=doc_id or None,
        draft=draft,
        citations=[],
        diff=diff,
        confidence=0.72,
        risk_level="medium",
        conflicts_with=conflicts,
    )


def _fake_guardian_review(_prompt: str) -> GuardianReview:
    return GuardianReview(
        recommendation="needs-review",
        guardian_reasoning=(
            "Offline review: the draft is plausibly supported by the cited sources, but "
            "an offline reviewer cannot fully verify it — a human should confirm before applying."
        ),
        confidence=0.6,
        risk_level="medium",
        conflicts_with=[],
        uncertainty="Generated by the offline fake provider; not a real safety verdict.",
    )


class _FakeStructuredRunnable:
    """Mimics ``llm.with_structured_output(Schema)`` — returns a Schema instance."""

    def __init__(self, schema: type) -> None:
        self._schema = schema

    def invoke(self, prompt: Any) -> Any:
        text = prompt if isinstance(prompt, str) else str(prompt)
        if self._schema is ChatAnswer:
            return _fake_chat_answer(text)
        if self._schema is CuratorDraft:
            return _fake_curator_draft(text)
        if self._schema is GuardianReview:
            return _fake_guardian_review(text)
        raise TypeError(f"FakeChatLLM has no canned output for schema {self._schema!r}")


class FakeChatLLM:
    """Deterministic, offline stand-in for ``AzureChatOpenAI`` (CHAT_PROVIDER=fake).

    Only the ``with_structured_output(Schema).invoke(prompt)`` path used by the
    LangGraph nodes is implemented. Output is a pure function of the prompt, so it
    is fully reproducible for tests and demo rehearsal.
    """

    def __init__(self, temperature: float = 0.1) -> None:
        self.temperature = temperature

    def with_structured_output(self, schema: type, **_: Any) -> _FakeStructuredRunnable:
        return _FakeStructuredRunnable(schema)

    def invoke(self, prompt: Any) -> str:  # pragma: no cover - not used by the graph
        return f"[fake-chat] {prompt if isinstance(prompt, str) else str(prompt)}"
