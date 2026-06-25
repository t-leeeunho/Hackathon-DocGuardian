"""Intake wiring tests for the Librarian rewrite/placement.

Offline: the DB, schema init, and embedding provider are monkeypatched on the
``app.ingestion.intake`` module, so no Postgres and no model download are needed.
The pure ``chunk_document``/``extract_edges`` and the deterministic Librarian
(``CHAT_PROVIDER=fake`` via conftest) run for real.
"""

from __future__ import annotations

import contextlib

import pytest

from app.ingestion import intake


class _FakeProvider:
    name = "fake"
    dim = 4

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.0, 0.0, 0.0, 0.0] for _ in texts]

    def embed_one(self, _text: str) -> list[float]:
        return [0.0, 0.0, 0.0, 0.0]


@pytest.fixture
def captured(monkeypatch):
    """Patch every side-effecting seam in intake and capture what gets written."""
    store: dict[str, list] = {"documents": [], "chunks": [], "edges": []}

    monkeypatch.setattr(intake, "get_embedding_provider", lambda: _FakeProvider())
    monkeypatch.setattr(intake, "init_schema", lambda dim: None)
    monkeypatch.setattr(intake, "list_doc_ids", lambda ns: [])
    monkeypatch.setattr(intake, "get_doc_placement", lambda doc_id: None)

    @contextlib.contextmanager
    def _fake_conn():
        yield object()

    monkeypatch.setattr(intake, "get_conn", _fake_conn)
    monkeypatch.setattr(
        intake, "upsert_documents",
        lambda rows, conn=None: (store["documents"].extend(rows), len(rows))[1],
    )
    monkeypatch.setattr(
        intake, "upsert_chunks",
        lambda rows, embs, conn=None: (store["chunks"].extend(rows), len(rows))[1],
    )
    monkeypatch.setattr(
        intake, "upsert_edges",
        lambda rows, conn=None: (store["edges"].extend(rows), len(rows))[1],
    )
    monkeypatch.setattr(intake, "detect_conflicts_for_doc", lambda doc_id, conn=None: 0)
    return store


AUTH_DOC = "# Auth\n\nSend the API key in the `Authorization` header to reach the service.\n"


def test_intake_rewrites_and_replaces(captured):
    result = intake.ingest_content("My Notes/auth tips.md", AUTH_DOC, "user")

    # Placement reflects the agent's decision, not the user's "My Notes" folder.
    assert result["doc_id"] == "user/security/auth.md"
    assert result["doc_id"] != "user/My Notes/auth tips.md"
    assert result["aiRewritten"] is True
    assert result["originalPath"] == "My Notes/auth tips.md"
    assert result["suggestedPath"] == "security/auth.md"
    assert result["category"] == "security"

    # The stored document keeps BOTH the original and the AI rewrite.
    doc = captured["documents"][0]
    assert doc["doc_id"] == "user/security/auth.md"
    assert doc["original_content"] == AUTH_DOC
    assert doc["original_path"] == "My Notes/auth tips.md"
    assert doc["ai_rewritten"] is True
    assert doc["ai_content"].startswith("---\n")  # the rewrite
    assert doc["ai_content"] != doc["original_content"]

    # Chunks were derived from the canonical (rewritten) content and embedded.
    assert captured["chunks"]
    assert all(c["doc_id"] == "user/security/auth.md" for c in captured["chunks"])


def test_intake_without_rewrite_is_verbatim(captured):
    content = "# Plain\n\nNothing fancy here at all.\n"
    result = intake.ingest_content("folder/plain.md", content, "user", rewrite=False)

    assert result["doc_id"] == "user/folder/plain.md"
    assert result["aiRewritten"] is False

    doc = captured["documents"][0]
    assert doc["ai_rewritten"] is False
    assert doc["ai_content"] == content
    assert doc["original_content"] == content
    assert doc["original_path"] == "folder/plain.md"


def test_intake_disambiguates_to_avoid_clobber(captured, monkeypatch):
    """A different drop-off already owns the natural placement -> get a unique id."""
    monkeypatch.setattr(
        intake, "get_doc_placement",
        lambda doc_id: {"docId": doc_id, "originalPath": "someoneelse/auth.md"}
        if doc_id == "user/security/auth.md" else None,
    )
    result = intake.ingest_content("My Notes/auth tips.md", AUTH_DOC, "user")
    assert result["doc_id"] != "user/security/auth.md"
    assert result["doc_id"].startswith("user/security/auth-")
    assert result["doc_id"].endswith(".md")
    # The first doc's preserved original is never touched.
    assert captured["documents"][0]["doc_id"] == result["doc_id"]


def test_intake_reuses_placement_for_same_original(captured, monkeypatch):
    """Re-dropping the SAME original path updates in place (idempotent), no suffix."""
    monkeypatch.setattr(
        intake, "get_doc_placement",
        lambda doc_id: {"docId": doc_id, "originalPath": "My Notes/auth tips.md"}
        if doc_id == "user/security/auth.md" else None,
    )
    result = intake.ingest_content("My Notes/auth tips.md", AUTH_DOC, "user")
    assert result["doc_id"] == "user/security/auth.md"
