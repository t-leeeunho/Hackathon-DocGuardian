"""End-to-end local pipeline: ingest -> process -> write JSON.

No Azure required. Run from the backend/ directory:

    python -m scripts.run_ingest --repo garnet
    python -m scripts.run_ingest --all

Outputs are written under data/_processed/<shortName>/.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.config import DATA_DIR, RepoConfig, get_repo_config, load_repo_configs
from app.ingestion.git_ingest import iter_raw_documents
from app.processing.processor import chunk_document, extract_edges


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, default=str, ensure_ascii=False) + "\n")


def process_repo(cfg: RepoConfig) -> dict:
    out_dir = DATA_DIR / "_processed" / cfg.shortName
    docs: list[dict] = []
    chunks: list[dict] = []
    edges: list[dict] = []

    print(f"\n=== {cfg.repo} ({cfg.shortName}) ===")
    for raw in iter_raw_documents(cfg):
        docs.append(raw.model_dump(mode="json"))
        doc_chunks = chunk_document(raw)
        doc_edges = extract_edges(raw)
        chunks.extend(c.model_dump(mode="json") for c in doc_chunks)
        edges.extend(e.model_dump(by_alias=True, mode="json") for e in doc_edges)
        print(f"  {raw.doc_id}: {len(doc_chunks)} chunks, {len(doc_edges)} edges")

    _write_jsonl(out_dir / "documents.jsonl", docs)
    _write_jsonl(out_dir / "chunks.jsonl", chunks)
    _write_jsonl(out_dir / "edges.jsonl", edges)

    summary = {
        "repo": cfg.repo,
        "shortName": cfg.shortName,
        "documents": len(docs),
        "chunks": len(chunks),
        "edges": len(edges),
        "output": str(out_dir),
    }
    print(
        f"  -> {summary['documents']} docs, {summary['chunks']} chunks, "
        f"{summary['edges']} edges written to {out_dir}"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="DocGuardian local ingestion pipeline")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--repo", help="shortName of a single repo to ingest")
    group.add_argument("--all", action="store_true", help="ingest all configured repos")
    args = parser.parse_args()

    configs = load_repo_configs() if args.all else [get_repo_config(args.repo)]

    summaries = [process_repo(cfg) for cfg in configs]

    print("\n=== Summary ===")
    for s in summaries:
        print(
            f"  {s['shortName']:12} {s['documents']:5} docs  "
            f"{s['chunks']:6} chunks  {s['edges']:6} edges"
        )


if __name__ == "__main__":
    main()
