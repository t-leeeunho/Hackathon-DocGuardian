"""Pure-logic tests for metrics aggregation."""

from app.governance.metrics import MetricSignals, compute_metrics


def test_detected_counts_passthrough():
    m = compute_metrics(MetricSignals(conflicts_detected=6, stale_detected=12))
    assert m["conflictsDetected"] == 6
    assert m["staleDetected"] == 12


def test_resolved_counts_only_from_applied():
    m = compute_metrics(
        MetricSignals(
            conflicts_detected=6,
            stale_detected=12,
            applied_update=2,
            applied_merge=1,
            applied_deprecate=1,
            applied_link=3,
        )
    )
    assert m["staleFixed"] == 3  # update + merge
    assert m["conflictsResolved"] == 3
    assert m["duplicatesRemoved"] == 2  # merge + deprecate
    assert m["brokenLinksResolved"] == 3


def test_resolved_clamped_to_detected():
    m = compute_metrics(MetricSignals(conflicts_detected=1, applied_update=5, applied_merge=5))
    assert m["conflictsResolved"] == 1


def test_verification_fraction():
    m = compute_metrics(MetricSignals(total_docs=4, docs_verified=1))
    assert m["docsWithVerificationStamp"] == 0.25
    assert "asOf" in m


def test_zero_docs_no_divide_by_zero():
    m = compute_metrics(MetricSignals(total_docs=0, docs_verified=0))
    assert m["docsWithVerificationStamp"] == 0.0
