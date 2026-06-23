"""Configuration loading for the backend."""

from __future__ import annotations

import json
import os
from pathlib import Path

from pydantic import BaseModel

try:  # optional: .env support without hard dependency at import time
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover - dotenv is optional for the CLI
    pass


BACKEND_DIR = Path(__file__).resolve().parent.parent
REPOS_CONFIG_PATH = BACKEND_DIR / "repos.config.json"
DATA_DIR = Path(os.getenv("DATA_DIR", str(BACKEND_DIR / "data")))


class RepoConfig(BaseModel):
    repo: str
    shortName: str
    url: str
    branch: str = "main"
    sparsePaths: list[str] = []
    docGlobs: list[str] = ["**/*.md"]
    refreshIntervalMinutes: int = 120


def load_repo_configs() -> list[RepoConfig]:
    raw = json.loads(REPOS_CONFIG_PATH.read_text(encoding="utf-8"))
    return [RepoConfig(**item) for item in raw]


def get_repo_config(short_name: str) -> RepoConfig:
    for cfg in load_repo_configs():
        if cfg.shortName == short_name:
            return cfg
    raise KeyError(f"No repo configured with shortName={short_name!r}")
