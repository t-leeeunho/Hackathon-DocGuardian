"""Graph structure analysis (pure, deterministic — part of Insights B-pillar).

**No external dependencies** — pure-Python power-iteration PageRank replaces
the naive ``inbound_refs`` importance placeholder used in ``governance/health.py``.

All functions take plain collections and return plain collections.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# PageRank
# ---------------------------------------------------------------------------


def pagerank(
    edges: list[tuple[str, str]],
    nodes: set[str],
    damping: float = 0.85,
    iters: int = 50,
) -> dict[str, float]:
    """Compute PageRank scores via power iteration, normalised to [0, 1].

    *edges* is a list of ``(from_node, to_node)`` tuples; self-loops and edges
    to/from nodes absent in *nodes* are silently ignored.

    The result is normalised so that the highest-scoring node always has
    score 1.0 (relative importance).  An empty *nodes* set returns ``{}``.

    Dangling nodes (no outgoing edges) contribute their rank mass equally to
    all nodes on each iteration (standard dangling-node treatment).
    """
    if not nodes:
        return {}

    n = len(nodes)
    rank: dict[str, float] = {node: 1.0 / n for node in nodes}

    # Build adjacency (deduplicated, within-nodes only)
    out_edges: dict[str, list[str]] = {node: [] for node in nodes}
    for src, dst in edges:
        if src in nodes and dst in nodes and src != dst:
            if dst not in out_edges[src]:
                out_edges[src].append(dst)

    for _ in range(iters):
        # Dangling mass: rank of nodes with no outgoing edges, spread to all.
        dangling_mass = sum(rank[node] for node in nodes if not out_edges[node])
        base = (1.0 - damping) / n + damping * dangling_mass / n

        new_rank: dict[str, float] = {node: base for node in nodes}

        for src, dsts in out_edges.items():
            if dsts:
                contribution = damping * rank[src] / len(dsts)
                for dst in dsts:
                    new_rank[dst] += contribution

        rank = new_rank

    # Normalise by maximum so scores sit in [0, 1].
    max_rank = max(rank.values(), default=0.0)
    if max_rank == 0.0:
        return {node: 0.0 for node in nodes}
    return {node: round(r / max_rank, 6) for node, r in rank.items()}


# ---------------------------------------------------------------------------
# Centrality lookup
# ---------------------------------------------------------------------------


def centrality_for(doc_id: str, ranks: dict[str, float]) -> float:
    """Return the normalised PageRank for *doc_id*, or 0.0 if absent."""
    return ranks.get(doc_id, 0.0)


# ---------------------------------------------------------------------------
# Coverage gaps
# ---------------------------------------------------------------------------


def coverage_gaps(doc_ids: set[str]) -> list[tuple[str, int]]:
    """Per-namespace doc counts, sorted ascending (sparse namespaces first).

    Namespace = prefix before the first ``/`` in a doc_id
    (e.g. ``"vscode"`` from ``"vscode/docs/build.md"``).

    Returns a list of ``(namespace, count)`` tuples.  Useful to flag
    namespaces with thin documentation coverage.
    """
    counts: dict[str, int] = {}
    for doc_id in doc_ids:
        ns = doc_id.split("/", 1)[0]
        counts[ns] = counts.get(ns, 0) + 1
    return sorted(counts.items(), key=lambda kv: kv[1])
