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

from pydantic import BaseModel, Field

# Conservative defaults so a demo can't wedge the host.
DEFAULT_IMAGE = "python:3.11-slim"
MAX_TIMEOUT_MS = 120_000
TAIL_CHARS = 4000


class SandboxRequest(BaseModel):
    command: str = Field(..., description="shell command to run inside the container")
    repo: str | None = Field(None, description="repo shortName for context (optional)")
    commit_sha: str | None = Field(None, description="commit the check pertains to")
    image: str = Field(DEFAULT_IMAGE, description="container image to run in")
    timeout_ms: int = Field(30_000, ge=1, le=MAX_TIMEOUT_MS)


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

    timeout_s = req.timeout_ms / 1000.0
    # Note: `docker run` does NOT inherit the host environment, so no host
    # secrets leak into the container without an explicit -e/--env-file.
    docker_cmd = [
        "docker", "run", "--rm",
        "--network", "none",        # no network access
        "--memory", "512m",          # hard memory cap
        "--cpus", "1.0",             # one core
        "--pids-limit", "256",
        req.image,
        "sh", "-c", req.command,
    ]

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
