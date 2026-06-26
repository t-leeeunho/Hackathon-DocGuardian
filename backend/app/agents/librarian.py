"""The Librarian — AI-native document rewrite + placement.

DocGuardian does not just *reference* the docs a user drops off: the Librarian
**rewrites** each one into an agent-friendly form (explicit title, machine-readable
front-matter, a self-contained summary, normalized structure) and **decides where
it belongs** in the library, re-organizing the user's folders into a layout that is
easier for downstream AI agents to retrieve and reason over.

The rewrite is the canonical content that gets chunked, embedded, and shown by
default; the original is preserved separately so a human can always fall back to it.

Like ``summarize.generate_summary``, this never blocks ingestion: it tries the chat
model when one is configured (Azure by default, or the offline fake), and degrades
to a fully deterministic local rewrite/placement on any error.
"""

from __future__ import annotations

import re

from app.agents.schemas import LibrarianPlan

# --------------------------------------------------------------------------- #
# Placement heuristics
# --------------------------------------------------------------------------- #
# Ordered, first-match-wins. Each category maps to keyword fragments we look for
# in the filename + content. This is the deterministic backstop for the LLM's
# own categorization, and the offline fake reuses it verbatim.
_CATEGORY_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("security", ("auth", "authentication", "permission", "acl", "secret", "token", "security")),
    ("guides", ("guide", "how to", "how-to", "tutorial", "getting started", "getting-started",
                "install", "setup", "build", "deploy", "deployment", "migration", "quickstart")),
    ("api-reference", ("api reference", "api-reference", "endpoint", "openapi", "swagger",
                       "rest api", "graphql")),
    ("architecture", ("architecture", "design doc", "adr", "rfc", "internals")),
    ("configuration", ("config", "configuration", "settings", "environment variable", "env var",
                       ".env")),
    ("troubleshooting", ("faq", "troubleshoot", "debugging", "known issue", "error")),
    ("operations", ("runbook", "monitoring", "alerting", "oncall", "on-call", "incident")),
    ("release-notes", ("changelog", "release notes", "release-notes", "what's new", "whats new")),
]

DEFAULT_CATEGORY = "general"
_MAX_TITLE = 80
_MAX_SUMMARY = 160
_FRONT_MATTER = re.compile(r"^\s*---\n.*?\n---\n", re.DOTALL)
_H1 = re.compile(r"^\s*#\s+(.+?)\s*#*\s*$")


def slugify(text: str) -> str:
    """Lowercase, hyphenated, filesystem-safe slug (always non-empty)."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "document"


def _titleize(stem: str) -> str:
    words = re.sub(r"[-_]+", " ", stem).strip()
    return words.title() if words else "Document"


def heuristic_category(name: str, content: str) -> str:
    """Pick a library category from filename + content keywords (deterministic)."""
    haystack = f"{name}\n{content[:2000]}".lower()
    for category, needles in _CATEGORY_RULES:
        if any(n in haystack for n in needles):
            return category
    return DEFAULT_CATEGORY


def sanitize_rel_path(path: str, *, category: str, fallback_slug: str) -> str:
    """Coerce an arbitrary suggested path into a safe ``<category>/<slug>.md``.

    Defends against directory traversal and absolute paths the model might emit:
    drops ``.``/``..``/empty segments and any drive/UNC prefix, keeps a single
    leading category folder, and guarantees a ``.md`` suffix.
    """
    raw = (path or "").replace("\\", "/").strip()
    segments = [seg for seg in raw.split("/") if seg not in ("", ".", "..")]
    # Strip a Windows drive letter or stray colon-bearing segment.
    segments = [seg for seg in segments if ":" not in seg]

    if not segments:
        folder, filename = slugify(category) or DEFAULT_CATEGORY, f"{fallback_slug}.md"
    else:
        filename = segments[-1]
        folder_parts = segments[:-1]
        folder = "/".join(slugify(p) for p in folder_parts) if folder_parts else (
            slugify(category) or DEFAULT_CATEGORY
        )

    stem, _, ext = filename.rpartition(".")
    if ext.lower() in ("md", "markdown", "mdx", "txt", "rst", "text"):
        base = slugify(stem or fallback_slug)
    else:
        base = slugify(filename or fallback_slug)
    return f"{folder}/{base}.md"


def _strip_namespace_prefix(path: str, namespace: str) -> str:
    """Drop a leading namespace/host folder the model may have echoed into the path.

    Prevents doubled doc_ids like ``web-host/web-host/guides/x.md`` when the LLM
    repeats the NAMESPACE it was given inside ``suggested_path``.
    """
    rel = (path or "").replace("\\", "/").lstrip("/")
    candidates = {namespace.strip().lower(), slugify(namespace)}
    parts = rel.split("/", 1)
    while len(parts) == 2 and parts[0].lower() in candidates:
        rel = parts[1]
        parts = rel.split("/", 1)
    return rel


def _strip_leading_h1(body: str) -> str:
    """Drop a single leading H1 so the rewrite's own title isn't duplicated."""
    lines = body.lstrip("\n").splitlines()
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        if _H1.match(line):
            return "\n".join(lines[i + 1 :]).lstrip("\n")
        break
    return body.strip("\n")


def _extract_title(name: str, body: str) -> str:
    for line in body.splitlines():
        m = _H1.match(line)
        if m:
            return m.group(1).strip()[:_MAX_TITLE]
        if line.strip():
            break
    stem = name.replace("\\", "/").rsplit("/", 1)[-1].rsplit(".", 1)[0]
    return _titleize(stem)[:_MAX_TITLE]


def _extract_summary(body: str) -> str:
    in_fence = False
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or not line or line.startswith("#"):
            continue
        clean = re.sub(r"[*_`>#\[\]]", "", line)
        clean = re.sub(r"\s+", " ", clean).strip()
        if clean:
            return clean[: _MAX_SUMMARY - 1] + "…" if len(clean) > _MAX_SUMMARY else clean
    return ""


def _keyword_tags(name: str, content: str, category: str) -> list[str]:
    haystack = f"{name}\n{content[:2000]}".lower()
    tags: list[str] = [category]
    for keyword in ("install", "build", "deploy", "config", "auth", "api", "migration",
                    "security", "test", "docker", "database"):
        if keyword in haystack and keyword not in tags:
            tags.append(keyword)
        if len(tags) >= 5:
            break
    return tags


def _render_rewrite(*, title: str, category: str, summary: str, tags: list[str],
                    original_path: str, body: str) -> str:
    """Compose the AI-agent-friendly document.

    Adds parseable front-matter and a self-contained summary callout so a
    retrieval agent gets the *what* and *why* before the body, then the normalized
    original content (front-matter stripped, duplicate title removed).
    """
    tag_list = ", ".join(tags)
    summary_line = summary or "No summary available."
    return (
        "---\n"
        f"title: {title}\n"
        f"category: {category}\n"
        f"summary: {summary_line}\n"
        f"tags: [{tag_list}]\n"
        f"source_path: {original_path}\n"
        "rewritten_by: docguardian-librarian\n"
        "---\n\n"
        f"# {title}\n\n"
        f"> **AI summary:** {summary_line}\n>\n"
        f"> _Reorganized by the DocGuardian Librarian into `{category}/` for agent "
        f"retrieval. Original dropped at `{original_path}`._\n\n"
        f"{body}\n"
    ).rstrip() + "\n"


def build_plan_from_text(
    name: str, content: str, namespace: str = "user", existing_paths: list[str] | None = None
) -> LibrarianPlan:
    """Deterministic rewrite + placement (no LLM).

    Doubles as both the offline fake's output and the fallback when the chat model
    is unavailable or returns something unusable.
    """
    body_no_fm = _FRONT_MATTER.sub("", content or "")
    title = _extract_title(name, body_no_fm)
    category = heuristic_category(name, content or "")
    summary = _extract_summary(body_no_fm)
    tags = _keyword_tags(name, content or "", category)
    original_path = (name or "untitled.md").replace("\\", "/").lstrip("/")
    fallback_slug = slugify(title)

    suggested_path = sanitize_rel_path(
        f"{category}/{fallback_slug}.md", category=category, fallback_slug=fallback_slug
    )

    normalized_body = _strip_leading_h1(body_no_fm).strip() or "_(empty document)_"
    rewritten = _render_rewrite(
        title=title, category=category, summary=summary, tags=tags,
        original_path=original_path, body=normalized_body,
    )
    rationale = (
        f"Filed under `{category}/` based on its content, and rewritten with explicit "
        f"front-matter, a one-line summary, and a normalized structure so AI agents can "
        f"retrieve and reason over it without parsing ad-hoc formatting."
    )
    return LibrarianPlan(
        title=title,
        category=category,
        suggested_path=suggested_path,
        summary=summary,
        rewritten_content=rewritten,
        rationale=rationale,
        tags=tags,
        confidence=0.6,
    )


# --------------------------------------------------------------------------- #
# LLM-backed orchestration (Azure default / fake offline, deterministic fallback)
# --------------------------------------------------------------------------- #
_SYSTEM = (
    "You are the DocGuardian Librarian. You take a single raw documentation file a "
    "user dropped off and (1) REWRITE it into an AI-agent-friendly document and "
    "(2) DECIDE where it belongs in a documentation library.\n\n"
    "Rewrite rules: keep all real technical facts, commands, and code unchanged; do "
    "not invent information; make the structure explicit and self-contained (clear "
    "title, a one-line summary, short well-headed sections); prefer canonical "
    "terminology. Placement rules: choose a concise top-level category folder and a "
    "slug filename ending in .md; reuse an existing category when one fits. Return "
    "the structured plan only."
)


def _build_prompt(name: str, content: str, namespace: str, existing_paths: list[str]) -> str:
    existing = "\n".join(f"- {p}" for p in existing_paths[:40]) or "(library is empty)"
    return (
        f"{_SYSTEM}\n\n"
        f"NAMESPACE:\n{namespace}\n\n"
        f"EXISTING_PATHS:\n{existing}\n\n"
        f"ORIGINAL_NAME:\n{name}\n\n"
        f"ORIGINAL_CONTENT:\n{content[:6000]}"
    )


def rewrite_and_place(
    name: str, content: str, namespace: str = "user", existing_paths: list[str] | None = None
) -> dict:
    """Rewrite ``content`` for AI agents and choose its library placement.

    Returns a normalized dict the intake layer consumes::

        {ai_content, suggested_path, doc_id, title, summary, category,
         rationale, tags, confidence, ai_rewritten}

    Never raises: any model/parse failure degrades to the deterministic plan.
    """
    existing_paths = existing_paths or []
    plan = _invoke_llm(name, content, namespace, existing_paths)
    if plan is None:
        plan = build_plan_from_text(name, content, namespace, existing_paths)

    fallback_slug = slugify(plan.title or name or "document")
    category = (plan.category or DEFAULT_CATEGORY).strip() or DEFAULT_CATEGORY
    suggested_path = sanitize_rel_path(
        _strip_namespace_prefix(plan.suggested_path, namespace),
        category=category,
        fallback_slug=fallback_slug,
    )

    ai_content = plan.rewritten_content.strip()
    if not ai_content:
        # The model gave us a placement but no usable body — rebuild the body
        # deterministically rather than indexing an empty document.
        ai_content = build_plan_from_text(name, content, namespace, existing_paths).rewritten_content

    ai_rewritten = ai_content.strip() != (content or "").strip()
    return {
        "ai_content": ai_content,
        "suggested_path": suggested_path,
        "doc_id": f"{namespace}/{suggested_path}",
        "title": (plan.title or _titleize(slugify(name)))[:_MAX_TITLE],
        "summary": (plan.summary or "").strip()[:_MAX_SUMMARY],
        "category": category,
        "rationale": (plan.rationale or "").strip(),
        "tags": list(plan.tags or []),
        "confidence": float(plan.confidence),
        "ai_rewritten": ai_rewritten,
    }


def _invoke_llm(
    name: str, content: str, namespace: str, existing_paths: list[str]
) -> LibrarianPlan | None:
    """Call the configured chat model; return None on any failure (caller falls back)."""
    if not (content or "").strip():
        return None
    try:
        from app.agents.llm import get_chat_llm

        llm = get_chat_llm(temperature=0.1)
        structured = llm.with_structured_output(LibrarianPlan)
        result = structured.invoke(_build_prompt(name, content, namespace, existing_paths))
        return result if isinstance(result, LibrarianPlan) else None
    except Exception:  # pragma: no cover - any provider/parse error -> deterministic fallback
        return None


def identity_plan(name: str, content: str, namespace: str = "user") -> dict:
    """Pass-through 'plan' that keeps a document exactly as-is (no rewrite/move).

    Used when rewrite is disabled (e.g. ``/ingest/refresh`` re-processing an
    existing doc) so its doc_id/placement stay stable.
    """
    rel = (name or "untitled.md").replace("\\", "/").lstrip("/")
    return {
        "ai_content": content,
        "suggested_path": rel,
        "doc_id": f"{namespace}/{rel}",
        "title": _extract_title(name, content or ""),
        "summary": "",
        "category": "",
        "rationale": "",
        "tags": [],
        "confidence": 1.0,
        "ai_rewritten": False,
    }
