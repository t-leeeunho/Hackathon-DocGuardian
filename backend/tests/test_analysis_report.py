"""Pure unit tests for analysis/report.py — no DB, no Azure, no network.

All tests construct ``DocQuality`` / ``DocLinks`` / ``DocDrift`` literals
directly (no DB, no IO wrappers).  The ``compute_*`` IO wrappers are
explicitly NOT called here.

Coverage:
- _quality_to_dto / _links_to_dto / _drift_to_dto produce exact camelCase keys
  and no snake_case keys.
- assemble_doc_analysis produces the correct DocAnalysis dict shape,
  passes llm through, and wraps sub-DTOs correctly.
- assemble_report aggregates: qualityAvg (3dp), brokenLinksDetected (sum),
  orphanCount, atRiskCount (threshold = AT_RISK_THRESHOLD).
- assemble_report ordering: worstQuality ascending, mostAtRisk descending,
  topCentral descending.
- assemble_report top_n truncation: default=5, custom, smaller corpus.
- assemble_report DocRef shapes: correct keys, reasons truncated to 3 for
  quality, full for risk, empty list for centrality.
- assemble_report empty corpus → valid zero-valued AnalysisReport.
- report_to_snapshot_row: correct shape, values, repo fallback, extra_counts.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.analysis.drift import DocDrift
from app.analysis.links import DocLinks
from app.analysis.quality import DocQuality
from app.analysis.report import (
    AT_RISK_THRESHOLD,
    _drift_to_dto,
    _links_to_dto,
    _quality_to_dto,
    assemble_doc_analysis,
    assemble_report,
    report_to_snapshot_row,
)

# ---------------------------------------------------------------------------
# Fixed timestamp for deterministic tests
# ---------------------------------------------------------------------------

_NOW = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)

# ---------------------------------------------------------------------------
# Fixture helpers — construct dataclass literals without DB
# ---------------------------------------------------------------------------


def _make_quality(
    quality_score: float = 0.8,
    readability: float = 60.0,
    grade_level: float = 8.0,
    completeness_score: float = 0.5,
    structure_score: float = 0.75,
    word_count: int = 300,
    placeholder_count: int = 0,
    issues: list[str] | None = None,
) -> DocQuality:
    return DocQuality(
        quality_score=quality_score,
        readability=readability,
        grade_level=grade_level,
        completeness_score=completeness_score,
        structure_score=structure_score,
        word_count=word_count,
        placeholder_count=placeholder_count,
        issues=issues or [],
    )


def _make_links(
    broken_internal: list[str] | None = None,
    broken_link_count: int = 0,
    external_count: int = 2,
    orphan: bool = False,
    dead_end: bool = False,
) -> DocLinks:
    return DocLinks(
        broken_internal=broken_internal or [],
        broken_link_count=broken_link_count,
        external_count=external_count,
        orphan=orphan,
        dead_end=dead_end,
    )


def _make_drift(
    age_days: int = 30,
    is_stale: bool = False,
    risk_score: float = 0.3,
    risk_reasons: list[str] | None = None,
) -> DocDrift:
    return DocDrift(
        age_days=age_days,
        is_stale=is_stale,
        risk_score=risk_score,
        risk_reasons=risk_reasons or [],
    )


def _make_row(
    doc_id: str,
    quality_score: float = 0.8,
    risk_score: float = 0.3,
    centrality: float = 0.5,
    orphan: bool = False,
    broken_link_count: int = 0,
    quality_issues: list[str] | None = None,
    risk_reasons: list[str] | None = None,
) -> dict:
    """Build an assemble_report row dict (raw dataclasses, not DTOs)."""
    return {
        "docId": doc_id,
        "quality": _make_quality(
            quality_score=quality_score,
            issues=quality_issues,
        ),
        "links": _make_links(
            orphan=orphan,
            broken_link_count=broken_link_count,
        ),
        "drift": _make_drift(
            risk_score=risk_score,
            risk_reasons=risk_reasons,
        ),
        "centrality": centrality,
    }


# ===========================================================================
# _quality_to_dto
# ===========================================================================


class TestQualityToDto:
    def test_exact_camel_keys(self):
        dto = _quality_to_dto(_make_quality())
        assert set(dto.keys()) == {
            "qualityScore",
            "readability",
            "gradeLevel",
            "completenessScore",
            "structureScore",
            "wordCount",
            "placeholderCount",
            "issues",
        }

    def test_no_snake_case_keys(self):
        dto = _quality_to_dto(_make_quality())
        assert not any("_" in k for k in dto), f"snake_case key found: {list(dto)}"

    def test_values_passed_through(self):
        q = _make_quality(
            quality_score=0.72,
            readability=55.1,
            grade_level=9.3,
            completeness_score=0.33,
            structure_score=0.5,
            word_count=512,
            placeholder_count=3,
            issues=["thin", "missing API"],
        )
        dto = _quality_to_dto(q)
        assert dto["qualityScore"] == 0.72
        assert dto["readability"] == 55.1
        assert dto["gradeLevel"] == 9.3
        assert dto["completenessScore"] == 0.33
        assert dto["structureScore"] == 0.5
        assert dto["wordCount"] == 512
        assert dto["placeholderCount"] == 3
        assert dto["issues"] == ["thin", "missing API"]

    def test_issues_list_is_copy(self):
        """Mutation of returned issues should not affect the original."""
        issues = ["a", "b"]
        q = _make_quality(issues=issues)
        dto = _quality_to_dto(q)
        dto["issues"].append("c")
        assert issues == ["a", "b"]


# ===========================================================================
# _links_to_dto
# ===========================================================================


class TestLinksToDto:
    def test_exact_camel_keys(self):
        dto = _links_to_dto(_make_links())
        assert set(dto.keys()) == {
            "brokenInternal",
            "brokenLinkCount",
            "externalCount",
            "orphan",
            "deadEnd",
        }

    def test_no_snake_case_keys(self):
        dto = _links_to_dto(_make_links())
        assert not any("_" in k for k in dto), f"snake_case key found: {list(dto)}"

    def test_values_passed_through(self):
        lnk = _make_links(
            broken_internal=["repo/missing.md"],
            broken_link_count=1,
            external_count=5,
            orphan=True,
            dead_end=True,
        )
        dto = _links_to_dto(lnk)
        assert dto["brokenInternal"] == ["repo/missing.md"]
        assert dto["brokenLinkCount"] == 1
        assert dto["externalCount"] == 5
        assert dto["orphan"] is True
        assert dto["deadEnd"] is True

    def test_broken_internal_list_is_copy(self):
        targets = ["a/b.md"]
        lnk = _make_links(broken_internal=targets)
        dto = _links_to_dto(lnk)
        dto["brokenInternal"].append("x")
        assert targets == ["a/b.md"]


# ===========================================================================
# _drift_to_dto
# ===========================================================================


class TestDriftToDto:
    def test_exact_camel_keys(self):
        dto = _drift_to_dto(_make_drift())
        assert set(dto.keys()) == {"ageDays", "isStale", "riskScore", "riskReasons"}

    def test_no_snake_case_keys(self):
        dto = _drift_to_dto(_make_drift())
        assert not any("_" in k for k in dto), f"snake_case key found: {list(dto)}"

    def test_values_passed_through(self):
        d = _make_drift(
            age_days=180,
            is_stale=True,
            risk_score=0.75,
            risk_reasons=["old", "unverified"],
        )
        dto = _drift_to_dto(d)
        assert dto["ageDays"] == 180
        assert dto["isStale"] is True
        assert dto["riskScore"] == 0.75
        assert dto["riskReasons"] == ["old", "unverified"]

    def test_risk_reasons_list_is_copy(self):
        reasons = ["stale"]
        d = _make_drift(risk_reasons=reasons)
        dto = _drift_to_dto(d)
        dto["riskReasons"].append("extra")
        assert reasons == ["stale"]


# ===========================================================================
# assemble_doc_analysis
# ===========================================================================


class TestAssembleDocAnalysis:
    def test_top_level_shape(self):
        result = assemble_doc_analysis(
            "repo/doc.md",
            _make_quality(),
            _make_links(),
            _make_drift(),
            centrality=0.4,
        )
        assert set(result.keys()) == {
            "docId",
            "quality",
            "links",
            "drift",
            "centrality",
            "llm",
        }

    def test_doc_id_set_correctly(self):
        result = assemble_doc_analysis(
            "my/path.md", _make_quality(), _make_links(), _make_drift(), 0.0
        )
        assert result["docId"] == "my/path.md"

    def test_centrality_set_correctly(self):
        result = assemble_doc_analysis(
            "x", _make_quality(), _make_links(), _make_drift(), 0.77
        )
        assert result["centrality"] == 0.77

    def test_llm_defaults_to_none(self):
        result = assemble_doc_analysis(
            "x", _make_quality(), _make_links(), _make_drift(), 0.0
        )
        assert result["llm"] is None

    def test_llm_passed_through(self):
        notes = {"clarityScore": 0.9, "issues": ["gap"]}
        result = assemble_doc_analysis(
            "x", _make_quality(), _make_links(), _make_drift(), 0.5, llm=notes
        )
        assert result["llm"] is notes

    def test_quality_sub_dto_has_camel_keys(self):
        result = assemble_doc_analysis(
            "x", _make_quality(), _make_links(), _make_drift(), 0.0
        )
        assert "qualityScore" in result["quality"]
        assert "quality_score" not in result["quality"]

    def test_links_sub_dto_has_camel_keys(self):
        result = assemble_doc_analysis(
            "x", _make_quality(), _make_links(), _make_drift(), 0.0
        )
        assert "brokenInternal" in result["links"]
        assert "broken_internal" not in result["links"]

    def test_drift_sub_dto_has_camel_keys(self):
        result = assemble_doc_analysis(
            "x", _make_quality(), _make_links(), _make_drift(), 0.0
        )
        assert "ageDays" in result["drift"]
        assert "age_days" not in result["drift"]

    def test_sub_dto_values_correct(self):
        q = _make_quality(quality_score=0.55, word_count=200)
        lnk = _make_links(orphan=True, broken_link_count=2)
        d = _make_drift(age_days=90, risk_score=0.6)
        result = assemble_doc_analysis("z", q, lnk, d, centrality=0.3)
        assert result["quality"]["qualityScore"] == 0.55
        assert result["quality"]["wordCount"] == 200
        assert result["links"]["orphan"] is True
        assert result["links"]["brokenLinkCount"] == 2
        assert result["drift"]["ageDays"] == 90
        assert result["drift"]["riskScore"] == 0.6


# ===========================================================================
# assemble_report — empty corpus
# ===========================================================================


class TestAssembleReportEmpty:
    def test_empty_all_zero(self):
        report = assemble_report([], repo_filter=None, now=_NOW)
        assert report["totalDocs"] == 0
        assert report["qualityAvg"] == 0.0
        assert report["brokenLinksDetected"] == 0
        assert report["orphanCount"] == 0
        assert report["atRiskCount"] == 0

    def test_empty_lists(self):
        report = assemble_report([], now=_NOW)
        assert report["worstQuality"] == []
        assert report["mostAtRisk"] == []
        assert report["topCentral"] == []

    def test_empty_repo_filter_none(self):
        report = assemble_report([], now=_NOW)
        assert report["repoFilter"] is None

    def test_empty_repo_filter_passed(self):
        report = assemble_report([], repo_filter="vscode", now=_NOW)
        assert report["repoFilter"] == "vscode"

    def test_empty_as_of_set(self):
        report = assemble_report([], now=_NOW)
        assert report["asOf"] == _NOW.isoformat()

    def test_empty_shape_complete(self):
        report = assemble_report([], now=_NOW)
        assert set(report.keys()) == {
            "repoFilter",
            "totalDocs",
            "qualityAvg",
            "brokenLinksDetected",
            "orphanCount",
            "atRiskCount",
            "worstQuality",
            "mostAtRisk",
            "topCentral",
            "asOf",
        }


# ===========================================================================
# assemble_report — aggregation
# ===========================================================================


class TestAssembleReportAggregation:
    def test_total_docs(self):
        rows = [_make_row(f"doc{i}") for i in range(7)]
        assert assemble_report(rows, now=_NOW)["totalDocs"] == 7

    def test_quality_avg_simple(self):
        rows = [
            _make_row("a", quality_score=0.1),
            _make_row("b", quality_score=0.2),
            _make_row("c", quality_score=0.3),
        ]
        # mean = 0.2 exact
        assert assemble_report(rows, now=_NOW)["qualityAvg"] == 0.2

    def test_quality_avg_rounded_to_3dp(self):
        # 1/3 rounds to 0.333 at 3dp
        rows = [_make_row(f"d{i}", quality_score=1 / 3) for i in range(3)]
        avg = assemble_report(rows, now=_NOW)["qualityAvg"]
        assert avg == round(1 / 3, 3)
        # Verify it is truly 3dp (not 4 or more)
        decimal_part = str(avg).split(".")[-1]
        assert len(decimal_part) <= 3

    def test_quality_avg_single_doc(self):
        rows = [_make_row("only", quality_score=0.654)]
        assert assemble_report(rows, now=_NOW)["qualityAvg"] == 0.654

    def test_broken_links_sum(self):
        rows = [
            _make_row("a", broken_link_count=3),
            _make_row("b", broken_link_count=0),
            _make_row("c", broken_link_count=7),
        ]
        assert assemble_report(rows, now=_NOW)["brokenLinksDetected"] == 10

    def test_broken_links_all_zero(self):
        rows = [_make_row(f"d{i}", broken_link_count=0) for i in range(4)]
        assert assemble_report(rows, now=_NOW)["brokenLinksDetected"] == 0

    def test_orphan_count(self):
        rows = [
            _make_row("a", orphan=True),
            _make_row("b", orphan=False),
            _make_row("c", orphan=True),
            _make_row("d", orphan=False),
        ]
        assert assemble_report(rows, now=_NOW)["orphanCount"] == 2

    def test_at_risk_count_at_threshold(self):
        # Exactly AT_RISK_THRESHOLD → should count as at risk (>=)
        rows = [
            _make_row("exact", risk_score=AT_RISK_THRESHOLD),
            _make_row("above", risk_score=AT_RISK_THRESHOLD + 0.1),
            _make_row("below", risk_score=AT_RISK_THRESHOLD - 0.01),
        ]
        assert assemble_report(rows, now=_NOW)["atRiskCount"] == 2

    def test_at_risk_count_none_at_risk(self):
        rows = [_make_row(f"d{i}", risk_score=0.1) for i in range(5)]
        assert assemble_report(rows, now=_NOW)["atRiskCount"] == 0

    def test_at_risk_count_all_at_risk(self):
        rows = [_make_row(f"d{i}", risk_score=0.9) for i in range(4)]
        assert assemble_report(rows, now=_NOW)["atRiskCount"] == 4

    def test_as_of_uses_now(self):
        report = assemble_report([], now=_NOW)
        assert report["asOf"] == _NOW.isoformat()


# ===========================================================================
# assemble_report — ordering
# ===========================================================================


class TestAssembleReportOrdering:
    def test_worst_quality_ascending_order(self):
        rows = [
            _make_row("high", quality_score=0.9),
            _make_row("low", quality_score=0.1),
            _make_row("mid", quality_score=0.5),
        ]
        worst = assemble_report(rows, now=_NOW)["worstQuality"]
        scores = [w["score"] for w in worst]
        assert scores == sorted(scores), "worstQuality should be ascending by score"

    def test_worst_quality_first_is_lowest(self):
        rows = [
            _make_row("a", quality_score=0.9),
            _make_row("b", quality_score=0.1),
            _make_row("c", quality_score=0.5),
        ]
        worst = assemble_report(rows, now=_NOW)["worstQuality"]
        assert worst[0]["docId"] == "b"

    def test_most_at_risk_descending_order(self):
        rows = [
            _make_row("safe", risk_score=0.1),
            _make_row("danger", risk_score=0.9),
            _make_row("mid", risk_score=0.5),
        ]
        at_risk = assemble_report(rows, now=_NOW)["mostAtRisk"]
        scores = [r["score"] for r in at_risk]
        assert scores == sorted(scores, reverse=True)

    def test_most_at_risk_first_is_highest(self):
        rows = [
            _make_row("a", risk_score=0.2),
            _make_row("b", risk_score=0.95),
            _make_row("c", risk_score=0.6),
        ]
        at_risk = assemble_report(rows, now=_NOW)["mostAtRisk"]
        assert at_risk[0]["docId"] == "b"

    def test_top_central_descending_order(self):
        rows = [
            _make_row("hub", centrality=1.0),
            _make_row("leaf", centrality=0.1),
            _make_row("mid", centrality=0.5),
        ]
        central = assemble_report(rows, now=_NOW)["topCentral"]
        scores = [c["score"] for c in central]
        assert scores == sorted(scores, reverse=True)

    def test_top_central_first_is_highest(self):
        rows = [
            _make_row("peripheral", centrality=0.05),
            _make_row("hub", centrality=0.98),
            _make_row("connector", centrality=0.5),
        ]
        central = assemble_report(rows, now=_NOW)["topCentral"]
        assert central[0]["docId"] == "hub"


# ===========================================================================
# assemble_report — top_n truncation
# ===========================================================================


class TestAssembleReportTopN:
    def test_default_top_n_5(self):
        rows = [_make_row(f"doc{i}", quality_score=i / 20) for i in range(10)]
        report = assemble_report(rows, now=_NOW)
        assert len(report["worstQuality"]) == 5
        assert len(report["mostAtRisk"]) == 5
        assert len(report["topCentral"]) == 5

    def test_custom_top_n_3(self):
        rows = [_make_row(f"doc{i}") for i in range(8)]
        report = assemble_report(rows, now=_NOW, top_n=3)
        assert len(report["worstQuality"]) == 3
        assert len(report["mostAtRisk"]) == 3
        assert len(report["topCentral"]) == 3

    def test_top_n_larger_than_corpus(self):
        rows = [_make_row("only")]
        report = assemble_report(rows, now=_NOW, top_n=5)
        assert len(report["worstQuality"]) == 1
        assert len(report["mostAtRisk"]) == 1
        assert len(report["topCentral"]) == 1

    def test_top_n_1(self):
        rows = [_make_row(f"d{i}") for i in range(4)]
        report = assemble_report(rows, now=_NOW, top_n=1)
        assert len(report["worstQuality"]) == 1
        assert len(report["mostAtRisk"]) == 1
        assert len(report["topCentral"]) == 1


# ===========================================================================
# assemble_report — DocRef shapes
# ===========================================================================


class TestAssembleReportDocRefShape:
    def test_worst_quality_docref_keys(self):
        rows = [_make_row("doc", quality_score=0.4)]
        ref = assemble_report(rows, now=_NOW)["worstQuality"][0]
        assert set(ref.keys()) == {"docId", "score", "reasons"}

    def test_worst_quality_score_is_quality_score(self):
        rows = [_make_row("doc", quality_score=0.37)]
        ref = assemble_report(rows, now=_NOW)["worstQuality"][0]
        assert ref["score"] == 0.37

    def test_worst_quality_reasons_truncated_to_3(self):
        rows = [_make_row("doc", quality_issues=["i1", "i2", "i3", "i4", "i5"])]
        ref = assemble_report(rows, now=_NOW)["worstQuality"][0]
        assert ref["reasons"] == ["i1", "i2", "i3"]

    def test_worst_quality_reasons_fewer_than_3_kept(self):
        rows = [_make_row("doc", quality_issues=["only"])]
        ref = assemble_report(rows, now=_NOW)["worstQuality"][0]
        assert ref["reasons"] == ["only"]

    def test_worst_quality_reasons_empty_when_no_issues(self):
        rows = [_make_row("doc", quality_issues=[])]
        ref = assemble_report(rows, now=_NOW)["worstQuality"][0]
        assert ref["reasons"] == []

    def test_most_at_risk_docref_keys(self):
        rows = [_make_row("doc", risk_score=0.8)]
        ref = assemble_report(rows, now=_NOW)["mostAtRisk"][0]
        assert set(ref.keys()) == {"docId", "score", "reasons"}

    def test_most_at_risk_score_is_risk_score(self):
        rows = [_make_row("doc", risk_score=0.73)]
        ref = assemble_report(rows, now=_NOW)["mostAtRisk"][0]
        assert ref["score"] == 0.73

    def test_most_at_risk_reasons_are_risk_reasons(self):
        rows = [_make_row("doc", risk_reasons=["old", "unverified"])]
        ref = assemble_report(rows, now=_NOW)["mostAtRisk"][0]
        assert ref["reasons"] == ["old", "unverified"]

    def test_top_central_docref_keys(self):
        rows = [_make_row("doc", centrality=0.7)]
        ref = assemble_report(rows, now=_NOW)["topCentral"][0]
        assert set(ref.keys()) == {"docId", "score", "reasons"}

    def test_top_central_score_is_centrality(self):
        rows = [_make_row("doc", centrality=0.88)]
        ref = assemble_report(rows, now=_NOW)["topCentral"][0]
        assert ref["score"] == 0.88

    def test_top_central_reasons_always_empty(self):
        rows = [_make_row("doc", centrality=0.5)]
        ref = assemble_report(rows, now=_NOW)["topCentral"][0]
        assert ref["reasons"] == []


# ===========================================================================
# report_to_snapshot_row
# ===========================================================================


class TestReportToSnapshotRow:
    def _base_report(self) -> dict:
        rows = [
            _make_row("a", broken_link_count=2, orphan=True, risk_score=0.8),
            _make_row("b", broken_link_count=1, orphan=False, risk_score=0.3),
        ]
        return assemble_report(rows, repo_filter=None, now=_NOW)

    def test_shape(self):
        report = self._base_report()
        row = report_to_snapshot_row(report, repo="myrepo")
        assert set(row.keys()) == {
            "repo",
            "totalDocs",
            "qualityAvg",
            "brokenLinks",
            "orphanCount",
            "atRiskCount",
            "staleDetected",
            "conflictsDetected",
            "duplicatesDetected",
            "payload",
        }

    def test_scalar_values(self):
        report = self._base_report()
        row = report_to_snapshot_row(report, repo="testrepo")
        assert row["totalDocs"] == report["totalDocs"]
        assert row["qualityAvg"] == report["qualityAvg"]
        assert row["brokenLinks"] == report["brokenLinksDetected"]
        assert row["orphanCount"] == report["orphanCount"]
        assert row["atRiskCount"] == report["atRiskCount"]

    def test_payload_is_the_report(self):
        report = self._base_report()
        row = report_to_snapshot_row(report)
        assert row["payload"] is report

    def test_explicit_repo_overrides(self):
        report = assemble_report([], repo_filter="fallback", now=_NOW)
        row = report_to_snapshot_row(report, repo="explicit")
        assert row["repo"] == "explicit"

    def test_repo_falls_back_to_report_filter(self):
        report = assemble_report([], repo_filter="from-report", now=_NOW)
        row = report_to_snapshot_row(report)  # no repo argument
        assert row["repo"] == "from-report"

    def test_repo_none_when_both_absent(self):
        report = assemble_report([], repo_filter=None, now=_NOW)
        row = report_to_snapshot_row(report)
        assert row["repo"] is None

    def test_extra_counts_populated(self):
        report = assemble_report([], now=_NOW)
        row = report_to_snapshot_row(
            report,
            staleDetected=12,
            conflictsDetected=4,
            duplicatesDetected=7,
        )
        assert row["staleDetected"] == 12
        assert row["conflictsDetected"] == 4
        assert row["duplicatesDetected"] == 7

    def test_extra_counts_none_when_absent(self):
        report = assemble_report([], now=_NOW)
        row = report_to_snapshot_row(report)
        assert row["staleDetected"] is None
        assert row["conflictsDetected"] is None
        assert row["duplicatesDetected"] is None

    def test_partial_extra_counts(self):
        report = assemble_report([], now=_NOW)
        row = report_to_snapshot_row(report, staleDetected=5)
        assert row["staleDetected"] == 5
        assert row["conflictsDetected"] is None
        assert row["duplicatesDetected"] is None

    def test_empty_report_row(self):
        report = assemble_report([], repo_filter=None, now=_NOW)
        row = report_to_snapshot_row(report)
        assert row["totalDocs"] == 0
        assert row["qualityAvg"] == 0.0
        assert row["brokenLinks"] == 0
