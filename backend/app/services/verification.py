"""Verification sandbox (README §10.6 — real containerized execution).

Runs a verification command inside an isolated Docker container with no network,
constrained CPU/memory, a hard timeout, and a clean environment (no host secrets).
The result is a ``SandboxResult`` with the real exit code and truncated output.

This is **real** container execution, not a mock. When Docker is not available on
the host, ``run_verification`` returns a result with ``sandboxRun=False`` and
``available=False`` so callers can honestly report verification as *unavailable*
rather than passing a fake green check.
"""

from __future__ import annotations

import shutil
import subprocess
import time
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field

# Conservative defaults so a demo can't wedge the host.
DEFAULT_IMAGE = "python:3.11-slim"
MAX_TIMEOUT_MS = 120_000
TAIL_CHARS = 4000
PULL_TIMEOUT_S = 180  # cold image pulls are not counted against the run budget


class SandboxRequest(BaseModel):
    command: str = Field(..., description="shell command to run inside the container")
    repo: str | None = Field(None, description="repo shortName for context (optional)")
    commit_sha: str | None = Field(None, description="commit the check pertains to")
    image: str = Field(DEFAULT_IMAGE, description="container image to run in")
    timeout_ms: int = Field(30_000, ge=1, le=MAX_TIMEOUT_MS)
    allow_network: bool = Field(
        False,
        description="allow container network access (needed for install/build "
        "steps). Off by default so untrusted doc commands stay isolated.",
    )


class SandboxResult(BaseModel):
    sandbox_run: bool = Field(..., description="true if a container actually executed")
    available: bool = Field(..., description="false when Docker is not installed/running")
    passed: bool | None = Field(None, description="exit code 0; None when not run")
    exit_code: int | None = None
    duration_ms: int = 0
    stdout_tail: str = ""
    stderr_tail: str = ""
    commit_sha: str | None = None
    command: str | None = None


def _tail(text: str, limit: int = TAIL_CHARS) -> str:
    """Keep only the last ``limit`` characters (the interesting end of a log)."""
    if text is None:
        return ""
    if len(text) <= limit:
        return text
    return "…" + text[-limit:]


@lru_cache(maxsize=1)
def docker_available() -> bool:
    """True if a usable Docker CLI + daemon is reachable."""
    if shutil.which("docker") is None:
        return False
    try:
        proc = subprocess.run(
            ["docker", "version", "--format", "{{.Server.Version}}"],
            capture_output=True,
            timeout=10,
        )
        return proc.returncode == 0
    except (subprocess.SubprocessError, OSError):
        return False


def _resolve_repo_dir(repo: str | None) -> Path | None:
    """Resolve a repo shortName to its ingested data dir, safely.

    Returns the absolute directory only when ``repo`` names an existing folder
    directly under the data dir. Rejects path traversal (``..``, absolute paths,
    nested separators) so a caller can't mount an arbitrary host path.
    """
    if not repo:
        return None
    # Reject anything that isn't a plain folder name.
    if "/" in repo or "\\" in repo or repo in {".", ".."}:
        return None
    from app.config import DATA_DIR

    base = Path(DATA_DIR).resolve()
    candidate = (base / repo).resolve()
    if candidate.parent != base or not candidate.is_dir():
        return None
    return candidate


def _ensure_image(image: str) -> str | None:
    """Pull ``image`` if it isn't present. Returns an error string on failure.

    Done before the timed run so a cold pull can't masquerade as a command
    timeout. Network failures here surface honestly to the caller.
    """
    inspect = subprocess.run(
        ["docker", "image", "inspect", image],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if inspect.returncode == 0:
        return None
    try:
        pull = subprocess.run(
            ["docker", "pull", image],
            capture_output=True,
            text=True,
            timeout=PULL_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        return f"Timed out pulling image '{image}'."
    if pull.returncode != 0:
        return _tail(pull.stderr) or f"Failed to pull image '{image}'."
    return None


def _build_docker_cmd(req: SandboxRequest, repo_dir: Path | None) -> list[str]:
    """Assemble the ``docker run`` argv for ``req``.

    When a repo dir is given it is mounted read-only at ``/src`` and copied into
    a writable ``/work`` so build commands can produce artifacts without ever
    mutating the host's ingested copy.
    """
    cmd = [
        "docker", "run", "--rm",
        "--network", "bridge" if req.allow_network else "none",
        "--memory", "512m",
        "--cpus", "1.0",
        "--pids-limit", "256",
    ]
    if repo_dir is not None:
        cmd += ["-v", f"{repo_dir}:/src:ro", "-w", "/work"]
        inner = f"mkdir -p /work && cp -a /src/. /work/ && {req.command}"
    else:
        inner = req.command
    cmd += [req.image, "sh", "-c", inner]
    return cmd


def run_verification(req: SandboxRequest) -> SandboxResult:
    """Execute ``req.command`` in an isolated container and return the result."""
    if not docker_available():
        return SandboxResult(
            sandbox_run=False,
            available=False,
            commit_sha=req.commit_sha,
            command=req.command,
            stderr_tail="Docker is not available on this host; verification unavailable.",
        )

    # Pull the image up front so a cold pull isn't charged to the run timeout.
    pull_err = _ensure_image(req.image)
    if pull_err is not None:
        return SandboxResult(
            sandbox_run=False,
            available=True,
            passed=None,
            commit_sha=req.commit_sha,
            command=req.command,
            stderr_tail=pull_err,
        )

    repo_dir = _resolve_repo_dir(req.repo)
    timeout_s = req.timeout_ms / 1000.0
    # Note: `docker run` does NOT inherit the host environment, so no host
    # secrets leak into the container without an explicit -e/--env-file.
    docker_cmd = _build_docker_cmd(req, repo_dir)

    start = time.monotonic()
    try:
        proc = subprocess.run(
            docker_cmd,
            capture_output=True,
            text=True,
            timeout=timeout_s + 5,  # grace over the in-container budget
        )
    except subprocess.TimeoutExpired:
        duration_ms = int((time.monotonic() - start) * 1000)
        return SandboxResult(
            sandbox_run=True,
            available=True,
            passed=False,
            exit_code=124,
            duration_ms=duration_ms,
            stderr_tail=f"Timed out after {req.timeout_ms}ms",
            commit_sha=req.commit_sha,
            command=req.command,
        )

    duration_ms = int((time.monotonic() - start) * 1000)
    return SandboxResult(
        sandbox_run=True,
        available=True,
        passed=proc.returncode == 0,
        exit_code=proc.returncode,
        duration_ms=duration_ms,
        stdout_tail=_tail(proc.stdout),
        stderr_tail=_tail(proc.stderr),
        commit_sha=req.commit_sha,
        command=req.command,
    )
