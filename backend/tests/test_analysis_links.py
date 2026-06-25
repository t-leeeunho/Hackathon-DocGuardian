"""Pure unit tests for links.py — no DB, no Azure, no network.

Constructs ``DocAnalysisSignals`` / ``CorpusSignals`` literals directly and
asserts on representative cases: broken links, orphan docs, dead-end docs.
"""

from __future__ import annotations

from app.analysis.links import (
    DocLinks,
    analyze_links,
    broken_internal_links,
    count_broken_links,
)
from app.analysis.signals import CorpusSignals, DocAnalysisSignals

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sig(
    doc_id: str = "repo/doc.md",
    internal_targets: list[str] | None = None,
    external_links: list[str] | None = None,
    inbound_refs: int = 1,
    outbound_refs: int = 1,
) -> DocAnalysisSignals:
    return DocAnalysisSignals(
        doc_id=doc_id,
        repo="repo",
        path=doc_id.split("/", 1)[-1],
        content="Some content",
        heading_paths=[],
        commit_sha=None,
        commit_date=None,
        last_verified_sha=None,
        inbound_refs=inbound_refs,
        outbound_refs=outbound_refs,
        internal_link_targets=internal_targets or [],
        external_links=external_links or [],
    )


def _corpus(*doc_ids: str) -> CorpusSignals:
    return CorpusSignals(doc_ids=set(doc_ids), edges=[])


# ---------------------------------------------------------------------------
# broken_internal_links
# ---------------------------------------------------------------------------


def test_no_broken_links_when_all_resolve():
    sig = _sig(
        doc_id="repo/index.md",
        internal_targets=["repo/install.md", "repo/usage.md"],
    )
    corpus = _corpus("repo/index.md", "repo/install.md", "repo/usage.md")
    assert broken_internal_links(sig, corpus) == []


def test_broken_link_detected_for_missing_target():
    sig = _sig(doc_id="repo/index.md", internal_targets=["repo/missing.md"])
    corpus = _corpus("repo/index.md")
    broken = broken_internal_links(sig, corpus)
    assert "repo/missing.md" in broken


def test_broken_links_partial_resolution():
    sig = _sig(
        doc_id="repo/a.md",
        internal_targets=["repo/exists.md", "repo/gone.md"],
    )
    corpus = _corpus("repo/a.md", "repo/exists.md")
    broken = broken_internal_links(sig, corpus)
    assert "repo/exists.md" not in broken
    assert "repo/gone.md" in broken


def test_no_broken_links_empty_targets():
    sig = _sig(doc_id="repo/a.md", internal_targets=[])
    corpus = _corpus("repo/a.md")
    assert broken_internal_links(sig, corpus) == []


# ---------------------------------------------------------------------------
# analyze_links — orphan / dead-end
# ---------------------------------------------------------------------------


def test_analyze_links_orphan():
    sig = _sig(inbound_refs=0, outbound_refs=1)
    result = analyze_links(sig, _corpus("repo/doc.md"))
    assert result.orphan is True
    assert result.dead_end is False


def test_analyze_links_dead_end():
    sig = _sig(inbound_refs=1, outbound_refs=0)
    result = analyze_links(sig, _corpus("repo/doc.md"))
    assert result.dead_end is True
    assert result.orphan is False


def test_analyze_links_both_connected():
    sig = _sig(inbound_refs=2, outbound_refs=3)
    result = analyze_links(sig, _corpus("repo/doc.md"))
    assert result.orphan is False
    assert result.dead_end is False


def test_analyze_links_both_isolated():
    sig = _sig(inbound_refs=0, outbound_refs=0)
    result = analyze_links(sig, _corpus("repo/doc.md"))
    assert result.orphan is True
    assert result.dead_end is True


def test_analyze_links_external_count():
    sig = _sig(external_links=["https://example.com", "https://github.com"])
    result = analyze_links(sig, _corpus("repo/doc.md"))
    assert result.external_count == 2


def test_analyze_links_broken_count():
    sig = _sig(
        doc_id="repo/index.md",
        internal_targets=["repo/missing.md"],
    )
    result = analyze_links(sig, _corpus("repo/index.md"))
    assert result.broken_link_count == 1
    assert result.broken_internal == ["repo/missing.md"]


def test_analyze_links_returns_dataclass():
    sig = _sig()
    result = analyze_links(sig, _corpus("repo/doc.md"))
    assert isinstance(result, DocLinks)


# ---------------------------------------------------------------------------
# count_broken_links
# ---------------------------------------------------------------------------


def test_count_broken_links_sums_across_docs():
    sig_a = _sig("repo/a.md", internal_targets=["repo/missing_a.md"])
    sig_b = _sig("repo/b.md", internal_targets=["repo/missing_b.md"])
    corpus = _corpus("repo/a.md", "repo/b.md")
    assert count_broken_links([sig_a, sig_b], corpus) == 2


def test_count_broken_links_empty_list():
    assert count_broken_links([], _corpus("repo/a.md")) == 0


def test_count_broken_links_all_resolved():
    sig = _sig("repo/a.md", internal_targets=["repo/b.md"])
    corpus = _corpus("repo/a.md", "repo/b.md")
    assert count_broken_links([sig], corpus) == 0


def test_count_broken_links_multiple_per_doc():
    sig = _sig(
        "repo/a.md",
        internal_targets=["repo/x.md", "repo/y.md", "repo/z.md"],
    )
    corpus = _corpus("repo/a.md")  # none of x/y/z exist
    assert count_broken_links([sig], corpus) == 3
