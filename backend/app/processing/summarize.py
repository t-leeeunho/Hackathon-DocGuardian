"""Short document descriptions for the sidebar tree.

When a document is ingested we derive a one-line description so the left tree can
show *what a file is about*, not just its filename. Two strategies:

* ``extractive_summary`` — pure, instant, free: the document's first real
  paragraph (skipping front-matter, headings, and code fences). Always available.
* ``generate_summary`` — uses the Azure/Foundry chat model for a crisper one-liner
  **when it is configured**, and transparently falls back to the extractive one
  otherwise (so ingestion never depends on the LLM and never blocks on it twice).
"""

from __future__ import annotations

import re

MAX_LEN = 160

_FRONT_MATTER = re.compile(r"^\s*---\n.*?\n---\n", re.DOTALL)
_MD_INLINE = re.compile(r"[*_`>#\[\]]")  # strip common markdown punctuation


def _clean(text: str, max_len: int = MAX_LEN) -> str:
    text = _MD_INLINE.sub("", text).strip()
    text = re.sub(r"\s+", " ", text)
    if len(text) > max_len:
        text = text[: max_len - 1].rstrip() + "…"
    return text


def extractive_summary(content: str, max_len: int = MAX_LEN) -> str:
    """First meaningful paragraph of the doc, cleaned and truncated."""
    if not content:
        return ""
    body = _FRONT_MATTER.sub("", content)
    in_fence = False
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or not line:
            continue
        if line.startswith("#"):  # heading — the filename already conveys this
            continue
        if line.startswith(("|", "-", "*", ">")) and len(line) < 4:
            continue
        return _clean(line, max_len)
    # Fallback: first non-empty line at all (e.g. a doc that is only a heading).
    for raw_line in body.splitlines():
        if raw_line.strip():
            return _clean(raw_line, max_len)
    return ""


def generate_summary(content: str, use_ai: bool = True, max_len: int = MAX_LEN) -> str:
    """Best available one-line description for a document.

    Uses the AI model only when configured; otherwise (and on any AI error)
    returns the extractive summary. Never raises.
    """
    base = extractive_summary(content, max_len)
    if not use_ai or not content.strip():
        return base
    try:
        from app.agents.llm import azure_is_configured, get_chat_llm

        if not azure_is_configured():
            return base
        llm = get_chat_llm(temperature=0.0)
        prompt = (
            "Summarize what this documentation file is about in ONE sentence "
            "(max 20 words), no preamble:\n\n" + content[:4000]
        )
        result = llm.invoke(prompt)
        text = getattr(result, "content", str(result))
        summary = _clean(text, max_len)
        return summary or base
    except Exception:  # pragma: no cover - AI is optional, fall back silently
        return base
