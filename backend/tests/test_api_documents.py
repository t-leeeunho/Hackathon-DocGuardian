"""API-level tests for the document + original endpoints.

The storage layer is monkeypatched on ``app.main`` so these exercise the real
routes, the ``{doc_id:path}`` converters, and the camelCase response DTOs without a
Postgres dependency.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def _client() -> TestClient:
    from app.main import app

    return TestClient(app, raise_server_exceptions=False)


_DOC = {
    "docId": "user/security/auth.md",
    "repo": "user",
    "path": "security/auth.md",
    "commitSha": "",
    "commitDate": None,
    "title": "Auth",
    "aiRewritten": True,
    "originalPath": "My Notes/auth tips.md",
    "rationale": "Filed under `security/` and rewritten for agent retrieval.",
    "chunks": [{"chunkId": "c0", "headingPath": [], "lineRange": [1, 3], "text": "body"}],
}

_SOURCE = {
    "docId": "user/security/auth.md",
    "path": "security/auth.md",
    "title": "Auth",
    "summary": "Send the API key in the Authorization header.",
    "aiRewritten": True,
    "rationale": "Filed under `security/`.",
    "originalPath": "My Notes/auth tips.md",
    "originalContent": "# Auth\n\nSend the API key.",
    "aiContent": "---\ntitle: Auth\n---\n\n# Auth\n",
}


def test_document_endpoint_exposes_rewrite_metadata(monkeypatch):
    from app import main

    monkeypatch.setattr(
        main, "get_document", lambda doc_id: _DOC if doc_id == _DOC["docId"] else None
    )
    resp = _client().get("/documents/user/security/auth.md")
    assert resp.status_code == 200
    body = resp.json()
    assert body["aiRewritten"] is True
    assert body["title"] == "Auth"
    assert body["originalPath"] == "My Notes/auth tips.md"


def test_document_endpoint_404(monkeypatch):
    from app import main

    monkeypatch.setattr(main, "get_document", lambda doc_id: None)
    assert _client().get("/documents/missing.md").status_code == 404


def test_original_endpoint_returns_original_and_rewrite(monkeypatch):
    from app import main

    monkeypatch.setattr(
        main, "get_document_source", lambda doc_id: _SOURCE if doc_id == _DOC["docId"] else None
    )
    resp = _client().get("/original/user/security/auth.md")
    assert resp.status_code == 200
    body = resp.json()
    assert body["aiRewritten"] is True
    assert body["originalContent"].startswith("# Auth")
    assert body["aiContent"].startswith("---")
    assert body["originalPath"] == "My Notes/auth tips.md"


def test_original_endpoint_404(monkeypatch):
    from app import main

    monkeypatch.setattr(main, "get_document_source", lambda doc_id: None)
    assert _client().get("/original/missing.md").status_code == 404
