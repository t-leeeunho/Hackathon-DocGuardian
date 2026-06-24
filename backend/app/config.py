"""Configuration loading for the backend."""

from __future__ import annotations

import json
import os
from pathlib import Path

from pydantic import BaseModel

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent

# Load .env from both the repo root and backend/ (repo root wins if both set a
# value, since it is loaded first and we don't override). This makes the app
# pick up secrets regardless of where the .env lives.
try:
    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / ".env")
    load_dotenv(BACKEND_DIR / ".env")
    load_dotenv()  # fallback: current working directory
except Exception:  # pragma: no cover - dotenv is optional for the CLI
    pass


REPOS_CONFIG_PATH = BACKEND_DIR / "repos.config.json"
DATA_DIR = Path(os.getenv("DATA_DIR", str(BACKEND_DIR / "data")))
PROCESSED_DIR = DATA_DIR / "_processed"

# --- Database ---
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://docguardian:docguardian@localhost:5432/docguardian",
)

# --- Embeddings ---
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "local").lower()
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
_dim = os.getenv("EMBEDDING_DIM", "").strip()
EMBEDDING_DIM = int(_dim) if _dim else None  # None => auto-detect (local)


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
