"""Opt-in LLM enhancement layer for the Insights subsystem (semantic quality notes).

This module adds an **on-demand**, semantic doc-quality reviewer on top of the
deterministic ``analysis.quality`` pass. It mirrors the Librarian pattern: it tries
the configured chat model (Azure by default, or the offline ``fake`` provider) and
**degrades to a safe empty result on any failure** — it never raises and never
blocks a request.

Cost invariant (see plan: Product invariant "Cost"):

* **At most ONE** LLM invocation per :func:`analyze_with_llm` call — no retries, no
  loops, no chaining.
* Invoked **only on explicit request** (e.g. ``GET /analysis/{docId}?llm=true``).
  It is **never** part of the bulk corpus analysis pass, so turning Insights on for
  a whole repo costs zero LLM calls.

The structured-output schema (:class:`_LlmNotes`) is intentionally **local** to this
module so adding this enhancement does not touch the locked agent-schema contract.
The public return shape is the locked ``LlmQualityNotes`` camelCase dict::

    {"clarityScore": float | None, "issues": [str, ...], "suggestedSections": [str, ...]}

Import-safe: no network / Azure access happens at import time (the chat factory is
imported lazily inside the single guarded call).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

# Bound the prompt + output so a single call stays cheap and predictable.
_MAX_CONTENT_CHARS = 6000
_MAX_HEADINGS = 40
_MAX_ITEMS = 20


# --------------------------------------------------------------------------- #
# Local structured-output schema (NOT part of the agent-schema contract)
# --------------------------------------------------------------------------- #
class _LlmNotes(BaseModel):
    """What the model fills in — kept local so the locked agent schemas don't change.

    Snake_case here (the model-facing layer); the public dict is camelCase.
    """

    clarity_score: float | None = Field(
        default=None,
        description="overall clarity rating in [0,1]; null when the model is unsure",
    )
    issues: list[str] = Field(
        default_factory=list,
        description="concrete clarity/quality issues, each grounded in the supplied text",
    )
    suggested_sections: list[str] = Field(
        default_factory=list,
        description="expected-but-missing sections implied by the supplied content",
    )


def _empty_notes() -> dict[str, Any]:
    """The safe, schema-valid result returned on every degradation path."""
    return {"clarityScore": None, "issues": [], "suggestedSections": []}


# --------------------------------------------------------------------------- #
# Prompt construction (grounded strictly in the supplied content + outline)
# --------------------------------------------------------------------------- #
_SYSTEM = (
    "You are the DocGuardian Insights analyst. You perform a careful, GROUNDED "
    "semantic review of ONE documentation file. Your job is to (a) rate how clearly "
    "the document reads on a 0-1 scale, (b) list concrete clarity/quality issues, and "
    "(c) name sections a reader would reasonably expect but that are missing.\n\n"
    "Strict rules: judge ONLY the supplied content and outline. Do NOT invent facts, "
    "features, APIs, commands, or sections the text does not actually imply. Every "
    "issue must refer to something genuinely present (or conspicuously absent) in the "
    "supplied text. Prefer fewer, higher-confidence items over speculation. If you are "
    "unsure of overall clarity, leave clarity_score null. Return the structured notes "
    "only."
)


def _format_outline(heading_paths: list[list[str]]) -> str:
    lines: list[str] = []
    for path in heading_paths[:_MAX_HEADINGS]:
        rendered = " > ".join(str(h).strip() for h in path if str(h).strip())
        if rendered:
            lines.append(f"- {rendered}")
    return "\n".join(lines) or "(no headings)"


def _format_quality(deterministic_quality: Any | None) -> str:
    """Render optional deterministic ``DocQuality`` signals as grounding context.

    Defensive: accepts a ``DocQuality`` dataclass (or any object exposing the same
    attributes); anything missing is simply skipped, never raised on.
    """
    if deterministic_quality is None:
        return "(none provided)"

    parts: list[str] = []
    for attr, label in (
        ("word_count", "wordCount"),
        ("placeholder_count", "placeholderCount"),
        ("completeness_score", "completeness"),
        ("structure_score", "structure"),
        ("readability", "readability"),
    ):
        val = getattr(deterministic_quality, attr, None)
        if val is not None:
            parts.append(f"{label}={val}")

    issues = getattr(deterministic_quality, "issues", None)
    if issues:
        joined = "; ".join(str(i) for i in list(issues)[:_MAX_ITEMS])
        parts.append(f"deterministicIssues=[{joined}]")

    return ", ".join(parts) or "(none provided)"


def _build_prompt(
    doc_id: str,
    content: str,
    heading_paths: list[list[str]],
    deterministic_quality: Any | None,
) -> str:
    return (
        f"{_SYSTEM}\n\n"
        f"DOC_ID:\n{doc_id}\n\n"
        f"OUTLINE:\n{_format_outline(heading_paths)}\n\n"
        f"DETERMINISTIC_SIGNALS:\n{_format_quality(deterministic_quality)}\n\n"
        f"CONTENT:\n{content[:_MAX_CONTENT_CHARS]}"
    )


# --------------------------------------------------------------------------- #
# Output normalization
# --------------------------------------------------------------------------- #
def _clean_items(items: list[str] | None) -> list[str]:
    out: list[str] = []
    for raw in items or []:
        text = str(raw).strip()
        if text:
            out.append(text)
        if len(out) >= _MAX_ITEMS:
            break
    return out


def _to_camel(notes: _LlmNotes) -> dict[str, Any]:
    """Convert a model-filled ``_LlmNotes`` into the locked camelCase dict."""
    score: float | None = notes.clarity_score
    if score is not None:
        try:
            score = round(max(0.0, min(1.0, float(score))), 3)
        except (TypeError, ValueError):
            score = None
    return {
        "clarityScore": score,
        "issues": _clean_items(notes.issues),
        "suggestedSections": _clean_items(notes.suggested_sections),
    }


# --------------------------------------------------------------------------- #
# Public entry point
# --------------------------------------------------------------------------- #
def analyze_with_llm(
    doc_id: str,
    content: str,
    *,
    heading_paths: list[list[str]] | None = None,
    deterministic_quality: Any | None = None,
) -> dict[str, Any]:
    """On-demand semantic quality notes for one doc, as a ``LlmQualityNotes`` dict.

    Returns ``{"clarityScore", "issues", "suggestedSections"}`` (camelCase). Grounds
    the model strictly in *content* + *heading_paths*, optionally feeding the
    deterministic :class:`~app.analysis.quality.DocQuality` as extra context.

    Never raises and never blocks. Degrades to a safe empty result
    (``{"clarityScore": None, "issues": [], "suggestedSections": []}``) on empty
    content, an unconfigured/failed provider, or any other error. Performs **at most
    one** LLM call (cost guard).
    """
    if not (content or "").strip():
        return _empty_notes()  # no content -> never call the model

    notes = _invoke_llm(doc_id, content, heading_paths or [], deterministic_quality)
    if notes is None:
        return _empty_notes()
    return _to_camel(notes)


def _invoke_llm(
    doc_id: str,
    content: str,
    heading_paths: list[list[str]],
    deterministic_quality: Any | None,
) -> _LlmNotes | None:
    """Run a single guarded chat call; return ``None`` on any failure.

    COST GUARD: exactly one ``structured.invoke`` happens here — there is no retry
    loop and no fan-out. The chat factory is imported lazily so this module stays
    import-safe (and so tests can monkeypatch ``app.agents.llm.get_chat_llm``).
    """
    try:
        from app.agents.llm import get_chat_llm

        llm = get_chat_llm(temperature=0.0)
        structured = llm.with_structured_output(_LlmNotes)
        result = structured.invoke(
            _build_prompt(doc_id, content, heading_paths, deterministic_quality)
        )
        return result if isinstance(result, _LlmNotes) else None
    except Exception:  # noqa: BLE001 - any provider/parse error -> safe empty result
        # AzureNotConfiguredError, the fake provider rejecting a local schema, network
        # or validation errors — all degrade to deterministic, never propagate.
        return None
