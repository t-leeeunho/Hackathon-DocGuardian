"""Layer 1 — Data ingestion.

Starts from git clone metadata (not full repo contents) using a sparse, shallow
clone, then extracts per-file commit metadata. Mirrors README Section 8A.2 / 9.4.
"""

from __future__ import annotations

import fnmatch
import hashlib
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Iterator

from app.config import DATA_DIR, RepoConfig
from app.models import RawDocument


def _run_git(args: list[str], cwd: Path | None = None) -> str:
    """Run a git command and return stdout, raising on failure."""
    result = subprocess.run(
        ["git", *args],
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed ({result.returncode}): {result.stderr.strip()}"
        )
    return result.stdout


def clone_or_update(cfg: RepoConfig, data_dir: Path = DATA_DIR) -> Path:
    """Sparse, shallow clone of a repo's documentation folders.

    Idempotent: if the clone already exists it is refreshed instead of re-cloned.
    """
    target = data_dir / cfg.shortName
    target.parent.mkdir(parents=True, exist_ok=True)

    if not (target / ".git").exists():
        # 1. Metadata-only clone — no blobs, no history, empty working tree.
        _run_git(
            [
                "clone",
                "--depth",
                "1",
                "--filter=blob:none",
                "--sparse",
                "--branch",
                cfg.branch,
                cfg.url,
                str(target),
            ]
        )
    else:
        # Incremental refresh of an existing shallow clone.
        _run_git(["fetch", "--depth", "1", "origin", cfg.branch], cwd=target)
        _run_git(["reset", "--hard", f"origin/{cfg.branch}"], cwd=target)

    # 2. Select only the documentation folders (downloads just those blobs).
    if cfg.sparsePaths:
        _run_git(["sparse-checkout", "set", *cfg.sparsePaths], cwd=target)

    return target


def _latest_commit_meta(repo_dir: Path, rel_path: str) -> tuple[str, str, str, datetime | None]:
    """Return (sha, author, email, date) of the latest commit touching rel_path."""
    out = _run_git(
        ["log", "-1", "--format=%H%x1f%an%x1f%ae%x1f%cI", "--", rel_path],
        cwd=repo_dir,
    ).strip()
    if not out:
        return "", "", "", None
    sha, author, email, date_iso = (out.split("\x1f") + ["", "", "", ""])[:4]
    parsed: datetime | None = None
    if date_iso:
        try:
            parsed = datetime.fromisoformat(date_iso)
        except ValueError:
            parsed = None
    return sha, author, email, parsed


def _matches_globs(rel_path: str, globs: list[str]) -> bool:
    norm = rel_path.replace("\\", "/")
    return any(fnmatch.fnmatch(norm, pattern) for pattern in globs)


def iter_raw_documents(cfg: RepoConfig, data_dir: Path = DATA_DIR) -> Iterator[RawDocument]:
    """Yield one RawDocument per documentation file in the sparse checkout."""
    repo_dir = clone_or_update(cfg, data_dir)

    for path in sorted(repo_dir.rglob("*")):
        if not path.is_file() or ".git" in path.parts:
            continue
        rel_path = path.relative_to(repo_dir).as_posix()
        if not _matches_globs(rel_path, cfg.docGlobs):
            continue

        raw_bytes = path.read_bytes()
        try:
            content = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            content = raw_bytes.decode("utf-8", errors="replace")

        sha, author, email, date = _latest_commit_meta(repo_dir, rel_path)
        content_hash = "sha256:" + hashlib.sha256(raw_bytes).hexdigest()

        yield RawDocument(
            doc_id=f"{cfg.shortName}/{rel_path}",
            repo=cfg.repo,
            path=rel_path,
            branch=cfg.branch,
            content=content,
            byte_size=len(raw_bytes),
            commit_sha=sha,
            commit_author=author,
            commit_email=email,
            commit_date=date,
            content_hash=content_hash,
        )
