"""TEMP parallel restore helper: load a subset of repos from the _processed cache.

Launched 3x in parallel (disjoint repo groups) to use more of the CPU than a single
load_vectors --all. Thread-capped so the processes don't oversubscribe the cores.
Deleted after the restore completes.
"""
import os
import sys

N = int(os.environ.get("EMBED_THREADS", "5"))
os.environ.setdefault("OMP_NUM_THREADS", str(N))

from fastembed import TextEmbedding  # noqa: E402

from app.config import EMBEDDING_MODEL  # noqa: E402
from scripts.load_vectors import load_repo  # noqa: E402


class CappedProvider:
    def __init__(self, threads: int):
        self._m = TextEmbedding(model_name=EMBEDDING_MODEL, threads=threads)
        self.name = f"local-capped:{EMBEDDING_MODEL}"
        self.dim = len(next(iter(self._m.embed(["probe"]))))

    def embed(self, texts):
        return [v.tolist() for v in self._m.embed(texts)]


def main() -> None:
    repos = sys.argv[1:]
    print(f"group repos: {repos} (threads={N})", flush=True)
    provider = CappedProvider(N)  # schema already exists; skip init_schema to avoid DDL races
    for r in repos:
        try:
            load_repo(r, provider)
        except Exception as e:  # noqa: BLE001
            print(f"ERR {r}: {e}", flush=True)
    print("GROUP DONE", flush=True)


if __name__ == "__main__":
    main()
