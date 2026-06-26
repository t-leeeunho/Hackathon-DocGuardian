"""Offline unit tests for app.analysis.trends (direction D).

All pure-helper functions are exercised with literal inputs.
No DB / Azure connection is opened — ``compute_trends`` is intentionally
NOT called here (it requires a live Postgres connection).
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.analysis.trends import (
    _acceptance_rate,
    _applied_by_day,
    _by_repo,
    _confidence_histogram,
    _evidence_coverage,
    _series,
    assemble_trends,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

# Two snapshots for the same day — LATE has higher takenAt.
_SNAP_DAY1_EARLY = {
    "snapshotId": "s1",
    "takenAt": "2024-01-01T08:00:00",
    "repo": "acme/docs",
    "totalDocs": 20,
    "qualityAvg": 0.70,
    "brokenLinks": 3,
    "staleDetected": 5,
    "conflictsDetected": 2,
    "orphanCount": 1,
    "atRiskCount": 4,
}

_SNAP_DAY1_LATE = {
    "snapshotId": "s2",
    "takenAt": "2024-01-01T16:00:00",
    "repo": "acme/docs",
    "totalDocs": 20,
    "qualityAvg": 0.75,
    "brokenLinks": 1,
    "staleDetected": 4,
    "conflictsDetected": 2,
    "orphanCount": 1,
    "atRiskCount": 3,
}

_SNAP_DAY2 = {
    "snapshotId": "s3",
    "takenAt": "2024-01-02T12:00:00",
    "repo": "acme/docs",
    "totalDocs": 20,
    "qualityAvg": 0.80,
    "brokenLinks": 0,
    "staleDetected": 3,
    "conflictsDetected": 1,
    "orphanCount": 0,
    "atRiskCount": 2,
}

_SNAP_DAY3 = {
    "snapshotId": "s4",
    "takenAt": "2024-01-03T10:00:00",
    "repo": "acme/docs",
    "totalDocs": 20,
    "qualityAvg": 0.85,
    "brokenLinks": 0,
    "staleDetected": 2,
    "conflictsDetected": 0,
    "orphanCount": 0,
    "atRiskCount": 1,
}

# Provenance entries (always applied — carry approvedAt).
_PROV_DAY1_UPDATE = {"action": "update", "approvedAt": "2024-01-01T10:00:00"}
_PROV_DAY1_MERGE  = {"action": "merge",  "approvedAt": "2024-01-01T14:00:00"}
_PROV_DAY3_UPDATE = {"action": "update", "approvedAt": "2024-01-03T09:00:00"}
_PROV_DAY3_LINK   = {"action": "link",   "approvedAt": "2024-01-03T11:00:00"}


# ===========================================================================
# _applied_by_day
# ===========================================================================

class TestAppliedByDay:

    def test_counts_single_day_update_and_merge(self):
        result = _applied_by_day([_PROV_DAY1_UPDATE, _PROV_DAY1_MERGE])
        day = result["2024-01-01"]
        assert day["update"] == 1
        assert day["merge"] == 1
        assert day["deprecate"] == 0
        assert day["link"] == 0

    def test_stale_fixed_equals_update_plus_merge(self):
        result = _applied_by_day([_PROV_DAY1_UPDATE, _PROV_DAY1_MERGE])
        assert result["2024-01-01"]["staleFixed"] == 2

    def test_conflicts_resolved_equals_update_plus_merge(self):
        result = _applied_by_day([_PROV_DAY1_UPDATE, _PROV_DAY1_MERGE])
        assert result["2024-01-01"]["conflictsResolved"] == 2

    def test_link_action_counted_but_does_not_affect_stale_or_conflicts(self):
        result = _applied_by_day([_PROV_DAY3_LINK])
        day = result["2024-01-03"]
        assert day["link"] == 1
        assert day["staleFixed"] == 0        # link doesn't fix stale
        assert day["conflictsResolved"] == 0

    def test_multiple_days_separated(self):
        result = _applied_by_day([_PROV_DAY1_UPDATE, _PROV_DAY3_UPDATE])
        assert set(result.keys()) == {"2024-01-01", "2024-01-03"}
        assert result["2024-01-01"]["update"] == 1
        assert result["2024-01-03"]["update"] == 1

    def test_none_approved_at_is_skipped(self):
        result = _applied_by_day([{"action": "update", "approvedAt": None}])
        assert result == {}

    def test_empty_approved_at_is_skipped(self):
        result = _applied_by_day([{"action": "update", "approvedAt": ""}])
        assert result == {}

    def test_unknown_action_produces_zero_fixed(self):
        result = _applied_by_day([{"action": "flag", "approvedAt": "2024-01-01T12:00:00"}])
        day = result["2024-01-01"]
        assert day["staleFixed"] == 0
        assert day["conflictsResolved"] == 0

    def test_empty_input_returns_empty_dict(self):
        assert _applied_by_day([]) == {}

    def test_accepts_applied_proposal_dicts(self):
        """Proposal dicts with appliedAt + status='applied' are accepted."""
        proposals = [
            {"action": "update", "appliedAt": "2024-02-01T10:00:00", "status": "applied"},
            {"action": "merge",  "appliedAt": "2024-02-01T12:00:00", "status": "applied"},
            # proposed (not yet applied) → must be ignored
            {"action": "update", "appliedAt": "2024-02-01T14:00:00", "status": "proposed"},
        ]
        result = _applied_by_day(proposals)
        assert "2024-02-01" in result
        day = result["2024-02-01"]
        assert day["update"] == 1
        assert day["merge"] == 1
        assert day["staleFixed"] == 2

    def test_proposal_without_applied_status_is_ignored(self):
        result = _applied_by_day(
            [{"action": "update", "appliedAt": "2024-02-01T10:00:00", "status": "rejected"}]
        )
        assert result == {}

    def test_deprecate_action_counted(self):
        result = _applied_by_day(
            [{"action": "deprecate", "approvedAt": "2024-03-01T09:00:00"}]
        )
        assert result["2024-03-01"]["deprecate"] == 1


# ===========================================================================
# _series
# ===========================================================================

class TestSeries:

    def test_one_point_per_day_three_days(self):
        snaps = [_SNAP_DAY1_EARLY, _SNAP_DAY1_LATE, _SNAP_DAY2, _SNAP_DAY3]
        series = _series(snaps, {})
        assert len(series) == 3
        dates = [p["date"] for p in series]
        assert dates == ["2024-01-01", "2024-01-02", "2024-01-03"]

    def test_last_of_day_wins_over_early_snapshot(self):
        # LATE: qualityAvg=0.75, brokenLinks=1, staleDetected=4
        # EARLY: qualityAvg=0.70, brokenLinks=3, staleDetected=5
        series = _series([_SNAP_DAY1_EARLY, _SNAP_DAY1_LATE], {})
        assert len(series) == 1
        p = series[0]
        assert p["qualityAvg"] == pytest.approx(0.75)
        assert p["brokenLinks"] == 1
        assert p["staleDetected"] == 4

    def test_ascending_order_regardless_of_input_order(self):
        snaps = [_SNAP_DAY3, _SNAP_DAY1_EARLY, _SNAP_DAY2]   # deliberately scrambled
        series = _series(snaps, {})
        dates = [p["date"] for p in series]
        assert dates == sorted(dates)

    def test_stale_fixed_from_applied_events_on_same_day(self):
        applied = _applied_by_day([_PROV_DAY1_UPDATE, _PROV_DAY1_MERGE])
        series = _series([_SNAP_DAY1_LATE], applied)
        assert series[0]["staleFixed"] == 2
        assert series[0]["conflictsResolved"] == 2

    def test_stale_fixed_zero_on_day_without_applied_events(self):
        applied = _applied_by_day([_PROV_DAY1_UPDATE])
        series = _series([_SNAP_DAY1_LATE, _SNAP_DAY2], applied)
        day2 = next(p for p in series if p["date"] == "2024-01-02")
        assert day2["staleFixed"] == 0
        assert day2["conflictsResolved"] == 0

    def test_three_day_applied_mapping(self):
        """Full 3-day scenario with applied events on days 1 and 3 only."""
        snaps = [_SNAP_DAY1_LATE, _SNAP_DAY2, _SNAP_DAY3]
        applied = _applied_by_day(
            [_PROV_DAY1_UPDATE, _PROV_DAY1_MERGE, _PROV_DAY3_UPDATE]
        )
        series = _series(snaps, applied)
        assert len(series) == 3

        p1, p2, p3 = series
        assert p1["date"] == "2024-01-01"
        assert p1["staleFixed"] == 2         # update + merge
        assert p1["conflictsResolved"] == 2

        assert p2["date"] == "2024-01-02"
        assert p2["staleFixed"] == 0
        assert p2["conflictsResolved"] == 0

        assert p3["date"] == "2024-01-03"
        assert p3["staleFixed"] == 1         # single update
        assert p3["conflictsResolved"] == 1

    def test_applied_event_only_day_appears_in_series(self):
        """Applied events on days without snapshots still get a series point
        (forward-filled from the most recent prior snapshot)."""
        applied = _applied_by_day([{"action": "update", "approvedAt": "2024-01-05T12:00:00"}])
        series = _series([_SNAP_DAY3], applied)
        # Day3 = 2024-01-03, applied-only day = 2024-01-05 → should have 2 points.
        dates = [p["date"] for p in series]
        assert "2024-01-03" in dates
        assert "2024-01-05" in dates

        forward = next(p for p in series if p["date"] == "2024-01-05")
        # Values forwarded from SNAP_DAY3
        assert forward["staleDetected"] == _SNAP_DAY3["staleDetected"]
        assert forward["staleFixed"] == 1   # the applied update

    def test_empty_snapshots_and_empty_applied(self):
        assert _series([], {}) == []

    def test_trend_point_has_all_expected_keys(self):
        series = _series([_SNAP_DAY1_LATE], {})
        assert set(series[0].keys()) == {
            "date", "staleDetected", "staleFixed",
            "conflictsDetected", "conflictsResolved",
            "brokenLinks", "qualityAvg",
        }

    def test_none_snapshot_values_coerced_to_zero(self):
        snap = {"snapshotId": "x", "takenAt": "2024-06-01T00:00:00", "repo": "r",
                "staleDetected": None, "conflictsDetected": None,
                "brokenLinks": None, "qualityAvg": None}
        series = _series([snap], {})
        p = series[0]
        assert p["staleDetected"] == 0
        assert p["conflictsDetected"] == 0
        assert p["brokenLinks"] == 0
        assert p["qualityAvg"] == pytest.approx(0.0)


# ===========================================================================
# _by_repo
# ===========================================================================

class TestByRepo:

    def test_latest_snapshot_wins_per_repo(self):
        old = {**_SNAP_DAY1_EARLY, "repo": "repo1", "totalDocs": 10, "atRiskCount": 3}
        new = {**_SNAP_DAY2,       "repo": "repo1", "totalDocs": 12, "atRiskCount": 1}
        breakdown = _by_repo([old, new])
        assert len(breakdown) == 1
        b = breakdown[0]
        assert b["totalDocs"] == 12        # from 'new' (later takenAt)
        assert b["atRisk"] == 1

    def test_multiple_repos_each_get_own_latest(self):
        r1 = {**_SNAP_DAY1_EARLY, "repo": "repo1", "totalDocs": 10, "atRiskCount": 2}
        r2 = {**_SNAP_DAY2,       "repo": "repo2", "totalDocs": 5,  "atRiskCount": 0}
        breakdown = _by_repo([r1, r2])
        repos = {b["repo"]: b for b in breakdown}
        assert set(repos.keys()) == {"repo1", "repo2"}
        assert repos["repo1"]["totalDocs"] == 10
        assert repos["repo2"]["totalDocs"] == 5

    def test_output_sorted_by_repo_name(self):
        snaps = [
            {**_SNAP_DAY1_EARLY, "repo": "zoo/repo"},
            {**_SNAP_DAY2,       "repo": "aaa/repo"},
        ]
        names = [b["repo"] for b in _by_repo(snaps)]
        assert names == sorted(names)

    def test_expected_keys_in_breakdown(self):
        breakdown = _by_repo([_SNAP_DAY1_LATE])
        assert set(breakdown[0].keys()) == {"repo", "totalDocs", "qualityAvg", "brokenLinks", "atRisk"}

    def test_at_risk_maps_to_at_risk_count(self):
        snap = {**_SNAP_DAY2, "repo": "r", "atRiskCount": 7}
        b = _by_repo([snap])[0]
        assert b["atRisk"] == 7

    def test_empty_input_returns_empty_list(self):
        assert _by_repo([]) == []

    def test_snapshots_with_null_repo_are_skipped(self):
        snaps = [
            {**_SNAP_DAY1_EARLY, "repo": None},
            {**_SNAP_DAY2,       "repo": ""},
        ]
        assert _by_repo(snaps) == []

    def test_none_numeric_values_coerced_to_zero(self):
        snap = {"takenAt": "2024-01-01T00:00:00", "repo": "r",
                "totalDocs": None, "qualityAvg": None, "brokenLinks": None, "atRiskCount": None}
        b = _by_repo([snap])[0]
        assert b["totalDocs"] == 0
        assert b["qualityAvg"] == pytest.approx(0.0)
        assert b["brokenLinks"] == 0
        assert b["atRisk"] == 0


# ===========================================================================
# _acceptance_rate
# ===========================================================================

class TestAcceptanceRate:

    def test_all_applied(self):
        proposals = [{"status": "applied"}, {"status": "applied"}]
        assert _acceptance_rate(proposals) == pytest.approx(1.0)

    def test_all_approved(self):
        proposals = [{"status": "approved"}, {"status": "approved"}]
        assert _acceptance_rate(proposals) == pytest.approx(1.0)

    def test_mixed_statuses(self):
        proposals = [
            {"status": "applied"},
            {"status": "approved"},
            {"status": "proposed"},
            {"status": "rejected"},
        ]
        # 2 accepted / 4 total = 0.5
        assert _acceptance_rate(proposals) == pytest.approx(0.5)

    def test_none_accepted(self):
        proposals = [{"status": "proposed"}, {"status": "rejected"}]
        assert _acceptance_rate(proposals) == pytest.approx(0.0)

    def test_case_insensitive_status(self):
        proposals = [{"status": "Applied"}, {"status": "APPROVED"}]
        assert _acceptance_rate(proposals) == pytest.approx(1.0)

    def test_empty_input_returns_zero(self):
        assert _acceptance_rate([]) == 0.0

    def test_single_applied(self):
        assert _acceptance_rate([{"status": "applied"}]) == pytest.approx(1.0)


# ===========================================================================
# _confidence_histogram
# ===========================================================================

class TestConfidenceHistogram:

    # Helper: map bucket label → count
    @staticmethod
    def _hmap(proposals):
        return {h["bucket"]: h["count"] for h in _confidence_histogram(proposals)}

    def test_all_five_buckets_always_present(self):
        labels = [h["bucket"] for h in _confidence_histogram([])]
        assert labels == ["0.0\u20130.2", "0.2\u20130.4", "0.4\u20130.6",
                          "0.6\u20130.8", "0.8\u20131.0"]

    def test_boundary_0_2_goes_to_second_bucket(self):
        hmap = self._hmap([{"confidence": 0.2}])
        assert hmap["0.0\u20130.2"] == 0
        assert hmap["0.2\u20130.4"] == 1

    def test_boundary_0_4_goes_to_third_bucket(self):
        hmap = self._hmap([{"confidence": 0.4}])
        assert hmap["0.2\u20130.4"] == 0
        assert hmap["0.4\u20130.6"] == 1

    def test_boundary_0_6_goes_to_fourth_bucket(self):
        hmap = self._hmap([{"confidence": 0.6}])
        assert hmap["0.4\u20130.6"] == 0
        assert hmap["0.6\u20130.8"] == 1

    def test_boundary_0_8_goes_to_last_bucket(self):
        hmap = self._hmap([{"confidence": 0.8}])
        assert hmap["0.6\u20130.8"] == 0
        assert hmap["0.8\u20131.0"] == 1

    def test_value_1_0_falls_in_last_bucket(self):
        hmap = self._hmap([{"confidence": 1.0}])
        assert hmap["0.8\u20131.0"] == 1

    def test_value_0_0_falls_in_first_bucket(self):
        hmap = self._hmap([{"confidence": 0.0}])
        assert hmap["0.0\u20130.2"] == 1

    def test_full_distribution(self):
        proposals = [
            {"confidence": 0.1},  # 0.0–0.2
            {"confidence": 0.2},  # 0.2–0.4  (boundary → upper)
            {"confidence": 0.5},  # 0.4–0.6
            {"confidence": 0.8},  # 0.8–1.0  (boundary → upper = last)
            {"confidence": 1.0},  # 0.8–1.0
        ]
        hmap = self._hmap(proposals)
        assert hmap["0.0\u20130.2"] == 1
        assert hmap["0.2\u20130.4"] == 1
        assert hmap["0.4\u20130.6"] == 1
        assert hmap["0.6\u20130.8"] == 0
        assert hmap["0.8\u20131.0"] == 2

    def test_none_confidence_is_skipped(self):
        hmap = self._hmap([{"confidence": None}, {"confidence": 0.5}])
        assert sum(hmap.values()) == 1

    def test_non_numeric_confidence_is_skipped(self):
        hmap = self._hmap([{"confidence": "high"}, {"confidence": 0.3}])
        assert sum(hmap.values()) == 1

    def test_empty_input_all_counts_zero(self):
        hist = _confidence_histogram([])
        assert all(h["count"] == 0 for h in hist)

    def test_histogram_count_matches_input_length(self):
        proposals = [{"confidence": i / 10} for i in range(11)]  # 0.0 … 1.0
        total = sum(h["count"] for h in _confidence_histogram(proposals))
        assert total == len(proposals)


# ===========================================================================
# _evidence_coverage
# ===========================================================================

class TestEvidenceCoverage:

    def test_snake_case_commit_sha_counted(self):
        proposals = [{"evidence": [{"commit_sha": "abc123", "doc_id": "d1"}]}]
        assert _evidence_coverage(proposals) == pytest.approx(1.0)

    def test_camel_case_commit_sha_counted(self):
        proposals = [{"evidence": [{"commitSha": "def456", "doc_id": "d2"}]}]
        assert _evidence_coverage(proposals) == pytest.approx(1.0)

    def test_citations_with_commit_sha_counted(self):
        proposals = [{"citations": [{"commit_sha": "xyz789", "chunk_id": "c1"}]}]
        assert _evidence_coverage(proposals) == pytest.approx(1.0)

    def test_empty_commit_sha_not_counted(self):
        proposals = [{"evidence": [{"commit_sha": "", "doc_id": "d1"}]}]
        assert _evidence_coverage(proposals) == pytest.approx(0.0)

    def test_absent_commit_sha_not_counted(self):
        proposals = [{"evidence": [{"doc_id": "d1"}]}]
        assert _evidence_coverage(proposals) == pytest.approx(0.0)

    def test_empty_evidence_list_not_counted(self):
        proposals = [{"evidence": []}]
        assert _evidence_coverage(proposals) == pytest.approx(0.0)

    def test_no_evidence_key_not_counted(self):
        proposals = [{"confidence": 0.8}]
        assert _evidence_coverage(proposals) == pytest.approx(0.0)

    def test_mixed_coverage_fraction(self):
        proposals = [
            {"evidence": [{"commit_sha": "abc"}]},   # grounded
            {"evidence": [{"doc_id": "d1"}]},         # not grounded
            {},                                        # no evidence
        ]
        # 1 / 3 ≈ 0.3333
        assert _evidence_coverage(proposals) == pytest.approx(1 / 3, abs=1e-3)

    def test_payload_nested_evidence_is_inspected(self):
        """Store rows wrap the proposal in a 'payload' sub-dict."""
        proposals = [{"payload": {"evidence": [{"commit_sha": "abc123"}]}}]
        assert _evidence_coverage(proposals) == pytest.approx(1.0)

    def test_payload_nested_citations_are_inspected(self):
        proposals = [{"payload": {"citations": [{"commitSha": "sha1"}]}}]
        assert _evidence_coverage(proposals) == pytest.approx(1.0)

    def test_empty_input_returns_zero(self):
        assert _evidence_coverage([]) == 0.0

    def test_all_grounded(self):
        proposals = [
            {"evidence": [{"commit_sha": f"sha{i}"}]}
            for i in range(5)
        ]
        assert _evidence_coverage(proposals) == pytest.approx(1.0)


# ===========================================================================
# assemble_trends (integration of pure helpers)
# ===========================================================================

class TestAssembleTrends:

    def test_full_dto_has_all_required_keys(self):
        dto = assemble_trends([], [], [])
        assert set(dto.keys()) == {
            "series", "byRepo", "proposalAcceptanceRate",
            "confidenceHistogram", "evidenceCoverage", "asOf",
        }

    def test_empty_inputs_return_valid_empty_dto(self):
        dto = assemble_trends([], [], [])
        assert dto["series"] == []
        assert dto["byRepo"] == []
        assert dto["proposalAcceptanceRate"] == 0.0
        assert dto["evidenceCoverage"] == 0.0
        assert len(dto["confidenceHistogram"]) == 5
        assert all(h["count"] == 0 for h in dto["confidenceHistogram"])
        assert "asOf" in dto

    def test_as_of_uses_provided_now(self):
        now = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        dto = assemble_trends([], [], [], now=now)
        assert "2024-06-01" in dto["asOf"]
        assert "T12:00:00" in dto["asOf"]

    def test_as_of_defaults_to_valid_utc_iso(self):
        dto = assemble_trends([], [], [])
        # Must be parseable as ISO 8601.
        ts = dto["asOf"].replace("Z", "+00:00")
        datetime.fromisoformat(ts)  # raises if invalid

    def test_series_assembled_from_snapshots_and_provenance(self):
        snaps = [_SNAP_DAY1_LATE, _SNAP_DAY2]
        provenance = [_PROV_DAY1_UPDATE, _PROV_DAY1_MERGE]
        dto = assemble_trends(snaps, [], provenance)

        assert len(dto["series"]) == 2
        p1 = dto["series"][0]
        assert p1["date"] == "2024-01-01"
        assert p1["staleFixed"] == 2
        assert p1["conflictsResolved"] == 2

    def test_acceptance_rate_assembled_from_proposals(self):
        proposals = [
            {"status": "applied",  "confidence": 0.9},
            {"status": "proposed", "confidence": 0.3},
        ]
        dto = assemble_trends([], proposals, [])
        assert dto["proposalAcceptanceRate"] == pytest.approx(0.5)

    def test_confidence_histogram_assembled_from_proposals(self):
        proposals = [{"confidence": 0.9}, {"confidence": 0.1}]
        dto = assemble_trends([], proposals, [])
        hmap = {h["bucket"]: h["count"] for h in dto["confidenceHistogram"]}
        assert hmap["0.8\u20131.0"] == 1
        assert hmap["0.0\u20130.2"] == 1

    def test_evidence_coverage_assembled_from_proposals(self):
        proposals = [
            {"evidence": [{"commit_sha": "sha1"}]},
            {},
        ]
        dto = assemble_trends([], proposals, [])
        assert dto["evidenceCoverage"] == pytest.approx(0.5)

    def test_by_repo_assembled_from_snapshots(self):
        dto = assemble_trends([_SNAP_DAY1_LATE, _SNAP_DAY2], [], [])
        # Both snaps share repo "acme/docs"; latest = DAY2.
        assert len(dto["byRepo"]) == 1
        b = dto["byRepo"][0]
        assert b["repo"] == "acme/docs"
        assert b["totalDocs"] == _SNAP_DAY2["totalDocs"]
