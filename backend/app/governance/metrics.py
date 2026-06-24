"""MetricsDTO aggregation (README §8A — governance dashboard).

``compute_metrics`` is a **pure** reduction over already-counted raw signals, so
the mapping from persisted state to dashboard counters is deterministic and unit
testable. The store gathers the raw counts; this module only does arithmetic.

Counter semantics (idempotent — driven by persisted state, never by retries):
* ``*Detected``  — derived from current graph/edge state (e.g. conflict edges).
* ``*Fixed`` / ``*Resolved`` / ``*Removed`` — only count **applied** proposals,
  never mere proposal creation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class MetricSignals:
    total_docs: int = 0
    docs_verified: int = 0
    stale_detected: int = 0
    conflicts_detected: int = 0
    duplicates_detected: int = 0
    broken_links_detected: int = 0
    # Applied (governed-write) counts, grouped by proposal action:
    applied_update: int = 0
    applied_merge: int = 0
    applied_deprecate: int = 0
    applied_link: int = 0
    avg_time_to_update_hours: float = 0.0


def compute_metrics(sig: MetricSignals) -> dict:
    """Return a camelCase ``MetricsDTO`` dict (README §8A)."""
    stale_fixed = sig.applied_update + sig.applied_merge
    conflicts_resolved = sig.applied_update + sig.applied_merge
    duplicates_removed = sig.applied_merge + sig.applied_deprecate
    verification_fraction = (
        round(sig.docs_verified / sig.total_docs, 3) if sig.total_docs else 0.0
    )
    return {
        "staleDetected": sig.stale_detected,
        "staleFixed": min(stale_fixed, sig.stale_detected) if sig.stale_detected else stale_fixed,
        "duplicatesRemoved": duplicates_removed,
        "conflictsDetected": sig.conflicts_detected,
        "conflictsResolved": min(conflicts_resolved, sig.conflicts_detected)
        if sig.conflicts_detected
        else conflicts_resolved,
        "brokenLinksResolved": sig.applied_link,
        "docsWithVerificationStamp": verification_fraction,
        "avgTimeToUpdateHours": round(sig.avg_time_to_update_hours, 2),
        "asOf": datetime.now(timezone.utc).isoformat(),
    }
