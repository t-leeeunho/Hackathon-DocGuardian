"""API-level tests for the agent endpoints using the offline fake provider.

Retrieval is mocked (no Postgres / no embedding download); the fake chat provider
produces the reasoning, so these exercise the real `/chat` and `/propose` routes.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def _client(patch_retrieval, rows) -> TestClient:
    patch_retrieval(rows)
    from app.main import app

    return TestClient(app, raise_server_exceptions=False)


def test_chat_endpoint_returns_grounded_answer(patch_retrieval, rows_strong):
    client = _client(patch_retrieval, rows_strong)
    resp = client.post("/chat", json={"query": "how do I build?", "repo": "vscode"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["scope"] == "vscode"
    assert body["needs_human_review"] is False
    assert body["citations"][0]["commit_sha"] == "f00dcafe1234"


def test_propose_endpoint_returns_rich_proposal(patch_retrieval, rows_strong):
    client = _client(patch_retrieval, rows_strong)
    resp = client.post(
        "/propose",
        json={"instruction": "Unify the build docs into one canonical doc", "repo": "vscode"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["proposal_id"].startswith("prop_")
    assert body["evidence"], "expected grounded evidence in the response"
    assert body["recommendation"] in ("approve", "needs-review", "reject")
    assert body["verification"] is None


def test_chat_endpoint_returns_503_when_azure_unconfigured(
    patch_retrieval, rows_strong, monkeypatch
):
    monkeypatch.setenv("CHAT_PROVIDER", "azure")
    for key in ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_CHAT_DEPLOYMENT"):
        monkeypatch.delenv(key, raising=False)
    from app.agents import llm

    llm._azure_chat_llm.cache_clear()
    client = _client(patch_retrieval, rows_strong)
    resp = client.post("/chat", json={"query": "how do I build?"})
    assert resp.status_code == 503
