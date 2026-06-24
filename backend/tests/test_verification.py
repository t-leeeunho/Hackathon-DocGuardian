"""Tests for the verification sandbox helpers + the Docker-unavailable path."""

from app.governance.serialize import camelize, to_camel
from app.services import verification
from app.services.verification import SandboxRequest, _tail, run_verification


def test_tail_truncates_from_the_end():
    assert _tail("abc", 10) == "abc"
    out = _tail("x" * 100, 10)
    assert out.endswith("x" * 10)
    assert out.startswith("…")


def test_run_verification_reports_unavailable(monkeypatch):
    monkeypatch.setattr(verification, "docker_available", lambda: False)
    result = run_verification(SandboxRequest(command="echo hi", commit_sha="abc"))
    assert result.available is False
    assert result.sandbox_run is False
    assert result.passed is None
    assert result.commit_sha == "abc"


def test_camelize_is_deep():
    assert to_camel("needs_human_review") == "needsHumanReview"
    out = camelize(
        {"doc_id": "x", "line_range": [1, 2], "nested": [{"commit_sha": "a"}]}
    )
    assert out == {"docId": "x", "lineRange": [1, 2], "nested": [{"commitSha": "a"}]}
