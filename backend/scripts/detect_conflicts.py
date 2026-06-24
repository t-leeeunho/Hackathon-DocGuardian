"""Detect duplicate/conflict edges across embedded chunks and persist them.

Run after `load_vectors` so the graph shows `duplicate-of` and `conflicts-with`
edges (the red dashed conflict lines in the UI).

    python -m scripts.detect_conflicts --all
    python -m scripts.detect_conflicts --repo garnet
"""

from __future__ import annotations

import argparse

from app.processing.conflicts import CONFLICT_THRESHOLD, detect_conflict_edges


def main() -> None:
    parser = argparse.ArgumentParser(description="Detect duplicate/conflict edges.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="scan the whole corpus")
    group.add_argument("--repo", help="scan one repo shortName (e.g. garnet)")
    parser.add_argument(
        "--min-similarity",
        type=float,
        default=CONFLICT_THRESHOLD,
        help=f"minimum cosine similarity to consider (default {CONFLICT_THRESHOLD})",
    )
    args = parser.parse_args()

    repo = None if args.all else args.repo
    written = detect_conflict_edges(repo=repo, min_similarity=args.min_similarity)
    scope = "all repos" if args.all else f"repo {args.repo}"
    print(f"Wrote {written} duplicate/conflict edge(s) for {scope}.")


if __name__ == "__main__":
    main()
