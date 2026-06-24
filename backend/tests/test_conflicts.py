"""Pure-logic tests for conflict/duplicate edge detection."""

from app.processing.conflicts import (
    CONFLICT_THRESHOLD,
    DUPLICATE_THRESHOLD,
    ChunkSimilarity,
    build_edges,
    cap_edges_per_node,
    classify_pair,
)


def test_classify_pair_thresholds():
    assert classify_pair(0.97) == "duplicate-of"
    assert classify_pair(DUPLICATE_THRESHOLD) == "duplicate-of"
    assert classify_pair(0.92) == "conflicts-with"
    assert classify_pair(CONFLICT_THRESHOLD) == "conflicts-with"
    assert classify_pair(0.85) is None  # below the raised conflict threshold


def test_build_edges_keeps_best_per_pair_and_is_order_independent():
    matches = [
        ChunkSimilarity("garnet/a.md", "garnet/b.md", 0.91),
        ChunkSimilarity("garnet/b.md", "garnet/a.md", 0.96),  # higher, reversed order
    ]
    edges = build_edges(matches)
    assert len(edges) == 1
    assert edges[0]["type"] == "duplicate-of"  # best similarity wins
    assert edges[0]["from_doc"] == "garnet/a.md"  # sorted endpoints
    assert edges[0]["to_doc"] == "garnet/b.md"


def test_build_edges_stable_idempotent_id():
    a = build_edges([ChunkSimilarity("x/a.md", "x/b.md", 0.93)])
    b = build_edges([ChunkSimilarity("x/b.md", "x/a.md", 0.93)])
    assert a[0]["edge_id"] == b[0]["edge_id"]


def test_build_edges_drops_weak_and_self_pairs():
    matches = [
        ChunkSimilarity("x/a.md", "x/a.md", 0.99),  # self
        ChunkSimilarity("x/a.md", "x/c.md", 0.70),  # weak
    ]
    assert build_edges(matches) == []


def test_build_edges_excludes_reference_linked_pairs():
    matches = [ChunkSimilarity("x/a.md", "x/b.md", 0.93)]
    excl = {frozenset(("x/a.md", "x/b.md"))}
    assert build_edges(matches, exclude_pairs=excl) == []
    assert len(build_edges(matches)) == 1  # not excluded otherwise


def test_cap_edges_per_node_keeps_strongest():
    edges = build_edges([
        ChunkSimilarity("repo/h.md", "repo/a.md", 0.99),
        ChunkSimilarity("repo/h.md", "repo/b.md", 0.97),
        ChunkSimilarity("repo/h.md", "repo/c.md", 0.95),
        ChunkSimilarity("repo/h.md", "repo/d.md", 0.93),
    ])
    capped = cap_edges_per_node(edges, max_per_node=2)
    h_edges = [e for e in capped if "repo/h.md" in (e["from_doc"], e["to_doc"])]
    assert len(h_edges) == 2
    assert sorted((e["weight"] for e in h_edges), reverse=True) == [0.99, 0.97]
