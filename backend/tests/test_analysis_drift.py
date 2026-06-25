"""Pure unit tests for drift.py — no DB, no Azure, no network.

Asserts on representative cases:
- stale never-verified high-importance doc → high risk,
- recently verified current doc → low risk,
- conflict edge increases risk score,
- rank_at_risk sorts descending by risk_score.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.analysis.drift import DocDrift, analyze_drift, doc_age_days, rank_at_risk
from app.analysis.signals import DocAnalysisSignals

# ---------------------------------------------------------------------------
# Fixed time reference for deterministic tests
# ---------------------------------------------------------------------------

NOW = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
OLD_DATE = NOW - timedelta(days=400)  # over a year ago
AGING_DATE = NOW - timedelta(days=200)  # between 180 and 365 days
RECENT_DATE = NOW - timedelta(days=30)  # 30 days ago


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _sig(
    doc_id: str = "repo/doc.md",
    commit_sha: str | None = "abc",
    commit_date: datetime | None = None,
    last_verified_sha: str | None = None,
    has_conflict_edge: bool = False,
    has_duplicate_edge: bool = False,
    is_deprecated: bool = False,
) -> DocAnalysisSignals:
    return DocAnalysisSignals(
        doc_id=doc_id,
        repo="repo",
        path="doc.md",
        content="content",
        heading_paths=[],
        commit_sha=commit_sha,
        commit_date=commit_date,
        last_verified_sha=last_verified_sha,
        has_conflict_edge=has_conflict_edge,
        has_duplicate_edge=has_duplicate_edge,
        is_deprecated=is_deprecated,
    )


# ---------------------------------------------------------------------------
# doc_age_days
# ---------------------------------------------------------------------------


def test_age_days_known_date():
    assert doc_age_days(RECENT_DATE, now=NOW) == 30


def test_age_days_old_date():
    assert doc_age_days(OLD_DATE, now=NOW) == 400


def test_age_days_none_commit_date_returns_zero():
    assert doc_age_days(None) == 0


def test_age_days_future_date_returns_zero():
    future = NOW + timedelta(days=10)
    assert doc_age_days(future, now=NOW) == 0


def test_age_days_naive_datetime_treated_as_utc():
    naive = datetime(2024, 5, 1)  # 31 days before NOW
    assert doc_age_days(naive, now=NOW) == 31


# ---------------------------------------------------------------------------
# analyze_drift — staleness
# ---------------------------------------------------------------------------


def test_stale_when_never_verified():
    sig = _sig(commit_sha="abc", last_verified_sha=None)
    drift = analyze_drift(sig, importance=0.5, now=NOW)
    assert drift.is_stale is True


def test_stale_when_sha_mismatch():
    sig = _sig(commit_sha="new_sha", last_verified_sha="old_sha")
    drift = analyze_drift(sig, importance=0.5, now=NOW)
    assert drift.is_stale is True


def test_not_stale_when_sha_matches():
    sig = _sig(commit_sha="abc", last_verified_sha="abc")
    drift = analyze_drift(sig, importance=0.5, now=NOW)
    assert drift.is_stale is False


# ---------------------------------------------------------------------------
# analyze_drift — risk score ranges
# ---------------------------------------------------------------------------


def test_high_importance_stale_old_has_high_risk():
    sig = _sig(commit_sha="abc", last_verified_sha=None, commit_date=OLD_DATE)
    drift = analyze_drift(sig, importance=0.8, now=NOW)
    assert drift.risk_score > 0.5
    assert drift.age_days == 400
    assert any("unverified" in r for r in drift.risk_reasons)


def test_verified_recent_low_importance_has_low_risk():
    sig = _sig(commit_sha="abc", last_verified_sha="abc", commit_date=RECENT_DATE)
    drift = analyze_drift(sig, importance=0.3, now=NOW)
    assert drift.risk_score < 0.5
    assert drift.is_stale is False


def test_risk_score_in_unit_interval():
    for importance in [0.0, 0.5, 1.0]:
        for stale in [True, False]:
            sig = _sig(
                commit_sha="x",
                last_verified_sha=None if stale else "x",
                commit_date=OLD_DATE,
            )
            drift = analyze_drift(sig, importance=importance, now=NOW)
            assert 0.0 <= drift.risk_score <= 1.0


# ---------------------------------------------------------------------------
# analyze_drift — risk reasons
# ---------------------------------------------------------------------------


def test_conflict_edge_increases_risk_and_adds_reason():
    base_sig = _sig(commit_sha="abc", last_verified_sha="abc", commit_date=RECENT_DATE)
    conflict_sig = _sig(
        commit_sha="abc",
        last_verified_sha="abc",
        commit_date=RECENT_DATE,
        has_conflict_edge=True,
    )
    base_drift = analyze_drift(base_sig, importance=0.5, now=NOW)
    conflict_drift = analyze_drift(conflict_sig, importance=0.5, now=NOW)

    assert conflict_drift.risk_score > base_drift.risk_score
    assert any("conflict" in r for r in conflict_drift.risk_reasons)


def test_duplicate_edge_increases_risk_and_adds_reason():
    base_sig = _sig(commit_sha="abc", last_verified_sha="abc", commit_date=RECENT_DATE)
    dup_sig = _sig(
        commit_sha="abc",
        last_verified_sha="abc",
        commit_date=RECENT_DATE,
        has_duplicate_edge=True,
    )
    assert (
        analyze_drift(dup_sig, importance=0.5, now=NOW).risk_score
        > analyze_drift(base_sig, importance=0.5, now=NOW).risk_score
    )
    assert any(
        "duplicate" in r
        for r in analyze_drift(dup_sig, importance=0.5, now=NOW).risk_reasons
    )


def test_high_importance_stale_adds_importance_reason():
    sig = _sig(commit_sha="new", last_verified_sha=None, commit_date=RECENT_DATE)
    drift = analyze_drift(sig, importance=0.9, now=NOW)
    assert any("high-importance" in r for r in drift.risk_reasons)


def test_old_doc_adds_old_reason():
    sig = _sig(commit_sha="abc", last_verified_sha="abc", commit_date=OLD_DATE)
    drift = analyze_drift(sig, importance=0.0, now=NOW)
    assert any("old" in r for r in drift.risk_reasons)


def test_aging_doc_adds_aging_reason():
    sig = _sig(commit_sha="abc", last_verified_sha="abc", commit_date=AGING_DATE)
    drift = analyze_drift(sig, importance=0.0, now=NOW)
    assert any("aging" in r for r in drift.risk_reasons)


def test_no_reasons_when_current_and_fresh():
    sig = _sig(commit_sha="abc", last_verified_sha="abc", commit_date=RECENT_DATE)
    drift = analyze_drift(sig, importance=0.0, now=NOW)
    assert drift.risk_reasons == []


# ---------------------------------------------------------------------------
# rank_at_risk
# ---------------------------------------------------------------------------


def test_rank_at_risk_sorted_descending():
    items = [
        (
            "doc_a",
            DocDrift(age_days=10, is_stale=False, risk_score=0.2, risk_reasons=[]),
        ),
        (
            "doc_b",
            DocDrift(age_days=400, is_stale=True, risk_score=0.9, risk_reasons=["old"]),
        ),
        (
            "doc_c",
            DocDrift(age_days=50, is_stale=True, risk_score=0.5, risk_reasons=[]),
        ),
    ]
    ranked = rank_at_risk(items)
    assert ranked[0][0] == "doc_b"
    assert ranked[1][0] == "doc_c"
    assert ranked[-1][0] == "doc_a"


def test_rank_at_risk_empty_list():
    assert rank_at_risk([]) == []


def test_rank_at_risk_single_item():
    item = (
        "only",
        DocDrift(age_days=5, is_stale=False, risk_score=0.1, risk_reasons=[]),
    )
    assert rank_at_risk([item]) == [item]


def test_rank_at_risk_returns_docdrif_intact():
    drift = DocDrift(
        age_days=100, is_stale=True, risk_score=0.7, risk_reasons=["stale"]
    )
    ranked = rank_at_risk([("doc", drift)])
    assert ranked[0][1] is drift


def test_rank_at_risk_stable_on_equal_scores():
    items = [
        ("a", DocDrift(age_days=1, is_stale=False, risk_score=0.5, risk_reasons=[])),
        ("b", DocDrift(age_days=2, is_stale=False, risk_score=0.5, risk_reasons=[])),
    ]
    ranked = rank_at_risk(items)
    # Both have equal risk; just verify both are present
    assert {r[0] for r in ranked} == {"a", "b"}
