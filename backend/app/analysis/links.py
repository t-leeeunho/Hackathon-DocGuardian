"""Link analysis (pure, deterministic — part of Insights B-pillar).

All public functions are **pure**: they take pre-gathered signals and return
plain data.  No DB access.

Broken-internal-link detection closes the gap left by ``extract_edges``
(which silently drops unresolved links); here we recheck every internal
link target against the live corpus doc-id set.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.analysis.signals import CorpusSignals, DocAnalysisSignals

# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class DocLinks:
    """Link-health summary for one document."""

    broken_internal: list[str] = field(default_factory=list)
    broken_link_count: int = 0
    external_count: int = 0
    orphan: bool = False  # no other doc references this one
    dead_end: bool = False  # this doc references no other doc


# ---------------------------------------------------------------------------
# Pure functions
# ---------------------------------------------------------------------------


def broken_internal_links(
    sig: DocAnalysisSignals,
    corpus: CorpusSignals,
) -> list[str]:
    """Return internal link targets from *sig* that are absent from *corpus*.

    These are the links that ``extract_edges`` would silently drop — records
    the broken-link gap closed by the Insights subsystem.
    """
    return [t for t in sig.internal_link_targets if t not in corpus.doc_ids]


def analyze_links(
    sig: DocAnalysisSignals,
    corpus: CorpusSignals,
) -> DocLinks:
    """Compute full link health for one document.

    * ``orphan``   — no inbound ``references`` edges (nothing links here).
    * ``dead_end`` — no outbound ``references`` edges (links nowhere).
    """
    broken = broken_internal_links(sig, corpus)
    return DocLinks(
        broken_internal=broken,
        broken_link_count=len(broken),
        external_count=len(sig.external_links),
        orphan=sig.inbound_refs == 0,
        dead_end=sig.outbound_refs == 0,
    )


def count_broken_links(
    all_sigs: list[DocAnalysisSignals],
    corpus: CorpusSignals,
) -> int:
    """Sum of all broken internal links across *all_sigs* (corpus-wide count)."""
    return sum(len(broken_internal_links(s, corpus)) for s in all_sigs)
