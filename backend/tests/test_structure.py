"""Pure-logic tests for folder/sibling structure edges."""

from app.processing.structure import build_structure_edges


def test_connects_docs_within_a_repo():
    docs = [
        "garnet/README.md",
        "garnet/docs/build.md",
        "garnet/docs/test.md",
        "garnet/docs/api/index.md",
        "garnet/docs/api/class.md",
    ]
    edges = build_structure_edges(docs)
    assert all(e["type"] == "sibling" for e in edges)
    # Every non-anchor doc should appear in at least one edge -> no orphans.
    touched = {e["from_doc"] for e in edges} | {e["to_doc"] for e in edges}
    assert set(docs) <= touched


def test_separate_repos_do_not_link():
    docs = ["a/x.md", "a/y.md", "b/p.md", "b/q.md"]
    edges = build_structure_edges(docs)
    for e in edges:
        assert e["from_doc"].split("/")[0] == e["to_doc"].split("/")[0]


def test_idempotent_stable_ids():
    docs = ["r/a.md", "r/b.md"]
    a = build_structure_edges(docs)
    b = build_structure_edges(list(reversed(docs)))
    assert {e["edge_id"] for e in a} == {e["edge_id"] for e in b}


def test_single_doc_repo_has_no_self_edge():
    edges = build_structure_edges(["solo/only.md"])
    assert edges == []
