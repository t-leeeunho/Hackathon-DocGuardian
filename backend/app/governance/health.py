"""Document health + importance derivation (README §6 / graph view).

Health maps directly to the graph node colors the frontend renders:

* ``red``    — the doc conflicts with another doc (a ``conflicts-with`` edge).
* ``yellow`` — likely stale: a duplicate, or commit drift since last verification.
* ``gray``   — deprecated/unknown/inaccessible.
* ``green``  — verified and current.

These are **pure** functions over already-collected signals so they can be unit
tested without a database and reused by both the graph assembler and metrics.
"""

from __future__ import annotations

from dataclasses import dataclass

Health = str  # "green" | "yellow" | "red" | "gray"


@dataclass(frozen=True)
class DocSignals:
    """Everything the health/importance rules need about one document."""

    has_conflict_edge: bool = False
    has_duplicate_edge: bool = False
    is_deprecated: bool = False
    inbound_refs: int = 0
    current_commit_sha: str | None = None
    last_verified_sha: str | None = None

    @property
    def is_stale(self) -> bool:
        """Stale when the live commit differs from what was last verified.

        A doc that was never verified is treated as stale (needs review).
        """
        if not self.last_verified_sha:
            return True
        return self.current_commit_sha != self.last_verified_sha

    @property
    def is_verified(self) -> bool:
        return bool(self.last_verified_sha) and not self.is_stale


def derive_health(sig: DocSignals) -> Health:
    """Collapse the signals into a single node color (most severe wins)."""
    if sig.has_conflict_edge:
        return "red"
    if sig.is_deprecated:
        return "gray"
    if sig.has_duplicate_edge or sig.is_stale:
        return "yellow"
    if sig.is_verified:
        return "green"
    return "yellow"


def derive_importance(sig: DocSignals) -> float:
    """A 0–1 score used for graph node size.

    Driven mostly by how many docs reference this one (centrality), with a small
    floor so isolated nodes are still visible. Saturates at 8 inbound refs.
    """
    base = 0.35
    centrality = min(sig.inbound_refs, 8) / 8.0  # 0..1
    score = base + 0.6 * centrality
    if sig.is_deprecated:
        score *= 0.5
    return round(max(0.1, min(1.0, score)), 3)
