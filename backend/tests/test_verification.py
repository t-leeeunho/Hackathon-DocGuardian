"""Tests for the verification sandbox helpers + the Docker-unavailable path."""

from app.governance.serialize import camelize, to_camel
from app.services import verification
from app.services.verification import (
    SandboxRequest,
    _build_docker_cmd,
    _resolve_repo_dir,
    _tail,
    run_verification,
)


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


def test_resolve_repo_dir_rejects_traversal(tmp_path, monkeypatch):
    import app.config as config

    (tmp_path / "garnet").mkdir()
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)

    assert _resolve_repo_dir("garnet") == (tmp_path / "garnet").resolve()
    assert _resolve_repo_dir("../secrets") is None
    assert _resolve_repo_dir("a/b") is None
    assert _resolve_repo_dir("..") is None
    assert _resolve_repo_dir("missing") is None
    assert _resolve_repo_dir(None) is None


def test_build_docker_cmd_isolates_by_default():
    cmd = _build_docker_cmd(SandboxRequest(command="echo hi"), None)
    assert "--network" in cmd and cmd[cmd.index("--network") + 1] == "none"
    assert cmd[-3:] == ["sh", "-c", "echo hi"]


def test_build_docker_cmd_allows_network_when_opted_in():
    cmd = _build_docker_cmd(
        SandboxRequest(command="echo hi", allow_network=True), None
    )
    assert cmd[cmd.index("--network") + 1] == "bridge"


def test_build_docker_cmd_mounts_repo_readonly(tmp_path):
    repo_dir = tmp_path / "garnet"
    repo_dir.mkdir()
    cmd = _build_docker_cmd(SandboxRequest(command="npm run build"), repo_dir)
    assert "-v" in cmd and f"{repo_dir}:/src:ro" in cmd
    assert cmd[cmd.index("-w") + 1] == "/work"
    inner = cmd[-1]
    assert "cp -a /src/. /work/" in inner and "npm run build" in inner


def test_run_verification_reports_image_pull_failure(monkeypatch):
    monkeypatch.setattr(verification, "docker_available", lambda: True)
    monkeypatch.setattr(
        verification, "_ensure_image", lambda image: "Failed to pull image 'x'."
    )
    result = run_verification(SandboxRequest(command="echo hi", image="x"))
    assert result.available is True
    assert result.sandbox_run is False
    assert result.passed is None
    assert "Failed to pull" in result.stderr_tail
