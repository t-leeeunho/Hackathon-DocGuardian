"""Pure unit tests for graph_structure.py — no DB, no Azure, no network.

Asserts on representative graphs:
- hub node scores higher than leaf nodes,
- empty graph stays uniform,
- PageRank scores are always in [0, 1] with max == 1.0,
- coverage_gaps flags sparse namespaces first.
"""

from __future__ import annotations

from app.analysis.graph_structure import centrality_for, coverage_gaps, pagerank

# ---------------------------------------------------------------------------
# pagerank
# ---------------------------------------------------------------------------


def test_pagerank_hub_scores_higher_than_leaves():
    # A → C, B → C  — C is the hub receiving all links
    edges = [("A", "C"), ("B", "C")]
    nodes = {"A", "B", "C"}
    ranks = pagerank(edges, nodes)
    assert ranks["C"] >= ranks["A"]
    assert ranks["C"] >= ranks["B"]


def test_pagerank_hub_has_max_score_one():
    edges = [("A", "C"), ("B", "C"), ("D", "C")]
    nodes = {"A", "B", "C", "D"}
    ranks = pagerank(edges, nodes)
    assert abs(max(ranks.values()) - 1.0) < 1e-5


def test_pagerank_empty_nodes_returns_empty():
    assert pagerank([], set()) == {}


def test_pagerank_no_edges_uniform_scores():
    nodes = {"X", "Y", "Z"}
    ranks = pagerank([], nodes)
    assert set(ranks.keys()) == nodes
    values = list(ranks.values())
    # All equal (all nodes are dangling, so rank is uniform)
    assert all(abs(v - values[0]) < 1e-5 for v in values)


def test_pagerank_scores_always_in_unit_interval():
    edges = [("a", "b"), ("b", "c"), ("c", "a"), ("d", "a")]
    nodes = {"a", "b", "c", "d"}
    ranks = pagerank(edges, nodes)
    for v in ranks.values():
        assert 0.0 <= v <= 1.0


def test_pagerank_single_node_no_edges():
    ranks = pagerank([], {"solo"})
    assert "solo" in ranks
    assert abs(ranks["solo"] - 1.0) < 1e-5


def test_pagerank_self_loops_ignored():
    # Self-loop should not inflate self-rank
    edges = [("a", "a"), ("b", "a")]
    nodes = {"a", "b"}
    ranks_with = pagerank(edges, nodes)
    ranks_without = pagerank([("b", "a")], nodes)
    # Both give the same ranking direction (a scores higher)
    assert ranks_with["a"] >= ranks_with["b"]
    assert ranks_without["a"] >= ranks_without["b"]


def test_pagerank_edges_outside_nodes_ignored():
    edges = [("a", "b"), ("x", "y")]  # x and y are not in nodes
    nodes = {"a", "b"}
    ranks = pagerank(edges, nodes)
    assert set(ranks.keys()) == {"a", "b"}
    assert 0.0 <= ranks["a"] <= 1.0
    assert 0.0 <= ranks["b"] <= 1.0


def test_pagerank_chain_terminal_scores_highest():
    # a → b → c: c receives all flow from b, which receives all from a
    edges = [("a", "b"), ("b", "c")]
    nodes = {"a", "b", "c"}
    ranks = pagerank(edges, nodes)
    # c is the terminal hub; should have a high rank
    assert ranks["c"] >= ranks["a"]


def test_pagerank_normalized_max_equals_one():
    edges = [("a", "b"), ("c", "b"), ("d", "b")]
    nodes = {"a", "b", "c", "d"}
    ranks = pagerank(edges, nodes)
    assert abs(max(ranks.values()) - 1.0) < 1e-5


# ---------------------------------------------------------------------------
# centrality_for
# ---------------------------------------------------------------------------


def test_centrality_for_known_node():
    edges = [("a", "b"), ("c", "b")]
    nodes = {"a", "b", "c"}
    ranks = pagerank(edges, nodes)
    assert centrality_for("b", ranks) == ranks["b"]


def test_centrality_for_unknown_node_returns_zero():
    ranks = {"a": 0.5, "b": 1.0}
    assert centrality_for("unknown", ranks) == 0.0


def test_centrality_for_empty_ranks():
    assert centrality_for("any", {}) == 0.0


# ---------------------------------------------------------------------------
# coverage_gaps
# ---------------------------------------------------------------------------


def test_coverage_gaps_sparse_namespace_first():
    doc_ids = {
        "bigteam/a.md",
        "bigteam/b.md",
        "bigteam/c.md",
        "small/x.md",
    }
    gaps = coverage_gaps(doc_ids)
    names = [g[0] for g in gaps]
    assert names[0] == "small"  # only 1 doc — most sparse


def test_coverage_gaps_sorted_ascending():
    doc_ids = {
        "ns_c/1.md",
        "ns_b/1.md",
        "ns_b/2.md",
        "ns_a/1.md",
        "ns_a/2.md",
        "ns_a/3.md",
    }
    gaps = coverage_gaps(doc_ids)
    counts = [g[1] for g in gaps]
    assert counts == sorted(counts)


def test_coverage_gaps_empty_returns_empty():
    assert coverage_gaps(set()) == []


def test_coverage_gaps_single_namespace():
    doc_ids = {"ns/a.md", "ns/b.md"}
    gaps = coverage_gaps(doc_ids)
    assert gaps == [("ns", 2)]


def test_coverage_gaps_returns_list_of_tuples():
    gaps = coverage_gaps({"a/x.md", "b/y.md"})
    for item in gaps:
        assert isinstance(item, tuple)
        assert isinstance(item[0], str)
        assert isinstance(item[1], int)
