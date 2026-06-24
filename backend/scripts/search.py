"""Quick semantic search over the loaded vector store.

    python -m scripts.search "how do I run tests in CI"
    python -m scripts.search --repo playwright "record a test with codegen"
"""

from __future__ import annotations

import argparse

from app.embeddings.provider import get_embedding_provider
from app.storage.vectorstore import search


def main() -> None:
    parser = argparse.ArgumentParser(description="Semantic search over pgvector")
    parser.add_argument("query", help="natural language query")
    parser.add_argument("--repo", help="restrict to a single repo shortName")
    parser.add_argument("-k", type=int, default=5, help="number of results")
    args = parser.parse_args()

    provider = get_embedding_provider()
    query_vec = provider.embed_one(args.query)
    results = search(query_vec, top_k=args.k, repo=args.repo)

    print(f'\nTop {len(results)} results for: "{args.query}"\n')
    for r in results:
        heading = " > ".join(r["heading_path"]) if r["heading_path"] else "(root)"
        snippet = " ".join(r["text"].split())[:160]
        print(f"[{r['score']:.3f}] {r['doc_id']}  (L{r['line_start']}-{r['line_end']})")
        print(f"        {heading}")
        print(f"        {snippet}...\n")


if __name__ == "__main__":
    main()
