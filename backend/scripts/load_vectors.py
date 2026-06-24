"""Embed processed chunks and load documents/chunks/edges into Postgres+pgvector.

Reads the JSONL produced by run_ingest.py, embeds each chunk with the configured
provider (local fastembed by default), and upserts everything into the DB.

    python -m scripts.load_vectors --repo garnet
    python -m scripts.load_vectors --all
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.config import PROCESSED_DIR, load_repo_configs
from app.embeddings.provider import get_embedding_provider
from app.storage.db import init_schema
from app.storage.vectorstore import upsert_chunks, upsert_documents, upsert_edges

BATCH = 256


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def _doc_row(d: dict) -> dict:
    return {
        "doc_id": d["doc_id"],
        "repo": d["repo"],
        "path": d["path"],
        "branch": d.get("branch"),
        "byte_size": d.get("byte_size"),
        "commit_sha": d.get("commit_sha"),
        "commit_author": d.get("commit_author"),
        "commit_date": d.get("commit_date"),
        "content_hash": d.get("content_hash"),
        "fetched_at": d.get("fetched_at"),
    }


def _chunk_row(c: dict) -> dict:
    line_start, line_end = c.get("line_range", [None, None])
    return {
        "chunk_id": c["chunk_id"],
        "doc_id": c["doc_id"],
        "repo": c["repo"],
        "heading_path": c.get("heading_path") or [],
        "ordinal": c.get("ordinal"),
        "text": c["text"],
        "token_count": c.get("token_count"),
        "line_start": line_start,
        "line_end": line_end,
        "contains_commands": c.get("contains_commands", False),
        "commit_sha": c.get("commit_sha"),
        "commit_date": c.get("commit_date"),
        "content_hash": c.get("content_hash"),
    }


def _edge_row(e: dict) -> dict:
    return {
        "edge_id": e["edge_id"],
        "from_doc": e.get("from") or e.get("from_doc"),
        "to_doc": e.get("to") or e.get("to_doc"),
        "type": e["type"],
        "weight": e.get("weight"),
        "reason": e.get("reason"),
        "anchor_text": e.get("anchor_text"),
        "line": e.get("line"),
        "created_by": e.get("created_by"),
        "commit_sha": e.get("commit_sha"),
    }


def load_repo(short_name: str, provider) -> dict:
    repo_dir = PROCESSED_DIR / short_name
    docs = [_doc_row(d) for d in _read_jsonl(repo_dir / "documents.jsonl")]
    chunks = [_chunk_row(c) for c in _read_jsonl(repo_dir / "chunks.jsonl")]
    edges = [_edge_row(e) for e in _read_jsonl(repo_dir / "edges.jsonl")]

    print(f"\n=== {short_name}: {len(docs)} docs, {len(chunks)} chunks, {len(edges)} edges ===")
    upsert_documents(docs)
    upsert_edges(edges)

    loaded = 0
    for i in range(0, len(chunks), BATCH):
        batch = chunks[i : i + BATCH]
        embeddings = provider.embed([c["text"] for c in batch])
        loaded += upsert_chunks(batch, embeddings)
        print(f"  embedded+loaded {loaded}/{len(chunks)} chunks", end="\r")
    print()
    return {"short": short_name, "docs": len(docs), "chunks": loaded, "edges": len(edges)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Embed + load chunks into pgvector")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--repo", help="shortName of a single repo")
    group.add_argument("--all", action="store_true", help="load all configured repos")
    args = parser.parse_args()

    provider = get_embedding_provider()
    print(f"Embedding provider: {provider.name} (dim={provider.dim})")
    init_schema(provider.dim)

    names = [c.shortName for c in load_repo_configs()] if args.all else [args.repo]
    summaries = [load_repo(n, provider) for n in names]

    print("\n=== Loaded ===")
    for s in summaries:
        print(f"  {s['short']:12} {s['docs']:5} docs  {s['chunks']:6} chunks  {s['edges']:6} edges")


if __name__ == "__main__":
    main()
