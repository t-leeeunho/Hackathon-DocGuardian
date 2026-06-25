"""Tests for the Librarian — AI-native document rewrite + placement.

Fully offline: the autouse ``_fake_chat_env`` fixture (conftest) sets
``CHAT_PROVIDER=fake`` and unsets Azure, so ``rewrite_and_place`` runs through the
deterministic fake. No Postgres / no embedding model is touched here.
"""

from __future__ import annotations

import pytest

from app.agents.librarian import (
    build_plan_from_text,
    heuristic_category,
    identity_plan,
    rewrite_and_place,
    sanitize_rel_path,
    slugify,
)
from app.agents.schemas import LibrarianPlan

AUTH_DOC = "# Auth\n\nSend the API key in the `Authorization` header to call the service.\n"
DEPLOY_DOC = "# Deploy Guide\n\nRun `docker compose up` to install and deploy the server.\n"


# --------------------------------------------------------------------------- #
# Pure helpers
# --------------------------------------------------------------------------- #
def test_slugify_is_filesystem_safe():
    assert slugify("My Cool Doc!!") == "my-cool-doc"
    assert slugify("   ") == "document"
    assert slugify("API_Reference.v2") == "api-reference-v2"


@pytest.mark.parametrize(
    "name,content,expected",
    [
        ("auth.md", "How to authenticate with API keys", "security"),
        ("deploy.md", "Install and deploy the build", "guides"),
        ("api.md", "OpenAPI endpoint reference for the REST api", "api-reference"),
        ("random.md", "Just some unrelated prose about cats", "general"),
    ],
)
def test_heuristic_category(name, content, expected):
    assert heuristic_category(name, content) == expected


def test_sanitize_rel_path_blocks_traversal_and_absolute():
    # Directory traversal segments are dropped, never escape the namespace.
    assert ".." not in sanitize_rel_path("../../etc/passwd", category="g", fallback_slug="x")
    # A Windows drive prefix is stripped.
    out = sanitize_rel_path("C:\\evil\\x.md", category="g", fallback_slug="x")
    assert ":" not in out
    assert out == "evil/x.md"


def test_sanitize_rel_path_forces_md_and_category():
    assert sanitize_rel_path("notes", category="guides", fallback_slug="fallback") == "guides/notes.md"
    assert sanitize_rel_path("", category="guides", fallback_slug="fallback") == "guides/fallback.md"
    assert sanitize_rel_path("Guides/Foo Bar.MD", category="g", fallback_slug="x") == "guides/foo-bar.md"


def test_strip_echoed_namespace_prevents_doubled_paths():
    from app.agents.librarian import _strip_namespace_prefix

    assert _strip_namespace_prefix("microsoft-github-io/software/x.md", "microsoft-github-io") == "software/x.md"
    assert _strip_namespace_prefix("user/guides/x.md", "user") == "guides/x.md"
    assert _strip_namespace_prefix("guides/x.md", "user") == "guides/x.md"
    # repeated echo is collapsed
    assert _strip_namespace_prefix("web/web/guides/x.md", "web") == "guides/x.md"


# --------------------------------------------------------------------------- #
# Deterministic plan (the fallback + the fake's output)
# --------------------------------------------------------------------------- #
def test_build_plan_rewrites_and_structures():
    plan = build_plan_from_text("My Folder/auth tips.md", AUTH_DOC, "user")
    assert isinstance(plan, LibrarianPlan)
    assert plan.category == "security"
    assert plan.suggested_path == "security/auth.md"
    # The rewrite is AI-friendly: parseable front-matter + an explicit summary callout.
    assert plan.rewritten_content.startswith("---\n")
    assert "title:" in plan.rewritten_content
    assert "AI summary:" in plan.rewritten_content
    # The original technical fact survives the rewrite.
    assert "Authorization" in plan.rewritten_content
    # The rewrite is not byte-identical to the original (it was transformed).
    assert plan.rewritten_content.strip() != AUTH_DOC.strip()


def test_build_plan_handles_empty_content():
    plan = build_plan_from_text("empty.md", "", "user")
    assert plan.suggested_path.endswith(".md")
    assert plan.rewritten_content  # never empty — has front-matter + placeholder body


# --------------------------------------------------------------------------- #
# rewrite_and_place (fake provider via conftest)
# --------------------------------------------------------------------------- #
def test_rewrite_and_place_returns_normalized_dict():
    result = rewrite_and_place("My Folder/deploy guide.md", DEPLOY_DOC, "user", ["guides/foo.md"])
    assert set(result) >= {
        "ai_content", "suggested_path", "doc_id", "title", "summary",
        "category", "rationale", "tags", "confidence", "ai_rewritten",
    }
    # The agent re-files the doc under a category, ignoring the user's "My Folder".
    assert result["suggested_path"] == "guides/deploy-guide.md"
    assert result["doc_id"] == "user/guides/deploy-guide.md"
    assert result["ai_rewritten"] is True
    assert "docker compose up" in result["ai_content"]


def test_rewrite_and_place_sanitizes_a_hostile_path(monkeypatch):
    """Even if the model proposes a traversal path, intake gets a safe one."""

    hostile = LibrarianPlan(
        title="X",
        category="guides",
        suggested_path="../../../../etc/passwd",
        summary="s",
        rewritten_content="# X\n\nbody\n",
        rationale="r",
        tags=[],
        confidence=0.9,
    )

    class _Structured:
        def invoke(self, _prompt):
            return hostile

    class _LLM:
        def with_structured_output(self, _schema):
            return _Structured()

    monkeypatch.setattr("app.agents.llm.get_chat_llm", lambda *a, **k: _LLM())
    result = rewrite_and_place("x.md", "# X\n\nbody\n", "user")
    # The hostile value actually flows through sanitize_rel_path here.
    assert ".." not in result["doc_id"]
    assert ":" not in result["suggested_path"]
    assert result["doc_id"].startswith("user/")
    assert result["doc_id"].endswith("passwd.md")


def test_rewrite_and_place_falls_back_when_llm_unavailable(monkeypatch):
    """Azure unconfigured (or any error) must not break ingestion — degrade locally."""
    monkeypatch.setenv("CHAT_PROVIDER", "azure")  # no Azure creds -> get_chat_llm raises
    result = rewrite_and_place("auth.md", AUTH_DOC, "user")
    assert result["category"] == "security"
    assert result["ai_content"].startswith("---\n")
    assert result["ai_rewritten"] is True


def test_identity_plan_is_verbatim():
    plan = identity_plan("folder/plain.md", "# Plain\n\nbody\n", "user")
    assert plan["ai_rewritten"] is False
    assert plan["ai_content"] == "# Plain\n\nbody\n"
    assert plan["suggested_path"] == "folder/plain.md"
    assert plan["doc_id"] == "user/folder/plain.md"
