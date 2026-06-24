"""Shared fixtures for the agent-layer tests.

These tests run fully offline: ``CHAT_PROVIDER=fake`` swaps the LLM for the
deterministic ``FakeChatLLM`` (no Azure), and ``patch_retrieval`` replaces the
pgvector search with canned rows (no Postgres / no embedding model download).
"""

from __future__ import annotations

import pytest

AZURE_KEYS = (
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_CHAT_DEPLOYMENT",
)


@pytest.fixture(autouse=True)
def _fake_chat_env(monkeypatch):
    """Default every test to the offline fake chat provider with Azure unset."""
    monkeypatch.setenv("CHAT_PROVIDER", "fake")
    for key in AZURE_KEYS:
        monkeypatch.delenv(key, raising=False)


def make_row(
    doc_id: str,
    score: float,
    *,
    text: str = "Run `npm ci` then `npm run watch` to build.",
    commit_sha: str = "f00dcafe1234",
    chunk_id: str | None = None,
    line_start: int = 8,
    line_end: int = 12,
    heading_path: list[str] | None = None,
) -> dict:
    """Build a retrieval row matching the shape of ``vectorstore.search``."""
    return {
        "chunk_id": chunk_id or f"{doc_id}#Build#0",
        "doc_id": doc_id,
        "repo": doc_id.split("/")[0],
        "heading_path": heading_path if heading_path is not None else ["Building"],
        "text": text,
        "line_start": line_start,
        "line_end": line_end,
        "commit_sha": commit_sha,
        "score": score,
    }


@pytest.fixture
def rows_strong() -> list[dict]:
    return [
        make_row("vscode/build.md", 0.88),
        make_row(
            "vscode/contributing.md",
            0.81,
            text="Use `yarn` then `yarn watch` to build.",
            commit_sha="beadfeed5678",
            line_start=40,
            line_end=44,
        ),
    ]


@pytest.fixture
def patch_retrieval(monkeypatch):
    """Return a callable that points the graph's retrieval at canned rows."""

    def _apply(rows: list[dict]):
        from app.agents import graph

        class _Provider:
            def embed_one(self, _query: str) -> list[float]:
                return [0.0, 0.0, 0.0, 0.0]

        monkeypatch.setattr(graph, "get_embedding_provider", lambda: _Provider())
        monkeypatch.setattr(graph, "vector_search", lambda *a, **k: list(rows))
        # Force a clean rebuild so cached graphs can't leak across tests.
        graph._chat_graph = None
        graph._propose_graph = None

    return _apply
