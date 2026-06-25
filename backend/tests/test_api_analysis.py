"""API-level tests for the Analysis / Insights endpoints.

Runs fully OFFLINE (no DB / Azure) by monkeypatching all I/O entry-points:
  - app.main.compute_report / compute_doc_analysis / report_to_snapshot_row
  - app.main.compute_trends
  - app.main.analyze_with_llm
  - app.main.insert_analysis_snapshot / get_edge_type_counts / get_document
  - app.governance.store.get_document_meta (for ACL checks)

Invariants checked:
  - Every endpoint returns 200 + required camelCase keys.
  - /analysis/trends is NOT shadowed by the /analysis/{doc_id:path} catch-all.
  - GET /analysis/{id}?llm=true calls analyze_with_llm exactly once; the
    response ``llm`` field is populated.
  - GET /analysis/{id} (no ?llm) does NOT call analyze_with_llm; ``llm`` is null.
  - Unknown doc_id → 404.
  - Doc with a restricted ACL → 404 (existence must not be leaked).
  - POST /analysis/snapshot inserts once and returns a ``snapshotId``.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


# ─────────────────────────────────────────────────────────────────────────────
# Shared test data (all camelCase, matching DTO schemas from main.py)
# ─────────────────────────────────────────────────────────────────────────────

_REPORT = {
    "repoFilter": None,
    "totalDocs": 3,
    "qualityAvg": 0.75,
    "brokenLinksDetected": 1,
    "orphanCount": 1,
    "atRiskCount": 0,
    "worstQuality": [],
    "mostAtRisk": [],
    "topCentral": [],
    "asOf": "2026-01-01T00:00:00+00:00",
}

_DOC = {
    "docId": "user/test.md",
    "repo": "user",
    "path": "test.md",
    "commitSha": "abc123",
    "commitDate": None,
    "title": "Test Doc",
    "aiRewritten": False,
    "originalPath": None,
    "rationale": None,
    "chunks": [
        {
            "chunkId": "user/test.md#0",
            "headingPath": ["Introduction"],
            "lineRange": [1, 10],
            "text": "Hello world. This is a test document with some content.",
        }
    ],
}

_DOC_ANALYSIS = {
    "docId": "user/test.md",
    "quality": {
        "qualityScore": 0.8,
        "readability": 60.0,
        "gradeLevel": 8.0,
        "completenessScore": 0.7,
        "structureScore": 0.9,
        "wordCount": 200,
        "placeholderCount": 0,
        "issues": [],
    },
    "links": {
        "brokenInternal": [],
        "brokenLinkCount": 0,
        "externalCount": 1,
        "orphan": False,
        "deadEnd": False,
    },
    "drift": {
        "ageDays": 10,
        "isStale": False,
        "riskScore": 0.2,
        "riskReasons": [],
    },
    "centrality": 0.5,
    "llm": None,
}

_LLM_NOTES = {
    "clarityScore": 0.85,
    "issues": ["Introduction is too brief"],
    "suggestedSections": ["Examples", "API Reference"],
}

_TRENDS = {
    "series": [],
    "byRepo": [],
    "proposalAcceptanceRate": 0.5,
    "confidenceHistogram": [
        {"bucket": "0.0\u20130.2", "count": 0},
        {"bucket": "0.2\u20130.4", "count": 1},
        {"bucket": "0.4\u20130.6", "count": 2},
        {"bucket": "0.6\u20130.8", "count": 0},
        {"bucket": "0.8\u20131.0", "count": 1},
    ],
    "evidenceCoverage": 0.8,
    "asOf": "2026-01-01T00:00:00+00:00",
}

_SNAPSHOT_ID = "snap_abc123def456"

# Doc meta with empty ACL → publicly accessible to PUBLIC_PRINCIPAL
_META_PUBLIC: dict = {
    "doc_id": "user/test.md",
    "repo": "user",
    "path": "test.md",
    "acl": [],          # empty list = public
    "commit_sha": "abc123",
    "last_verified_sha": None,
}

# Doc meta with a restricted ACL → NOT accessible to PUBLIC_PRINCIPAL (role:engineer)
_META_RESTRICTED: dict = {
    "doc_id": "user/test.md",
    "repo": "user",
    "path": "test.md",
    "acl": ["team:security-only"],  # PUBLIC_PRINCIPAL has only role:engineer → denied
    "commit_sha": "abc123",
    "last_verified_sha": None,
}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _client() -> TestClient:
    from app.main import app
    return TestClient(app, raise_server_exceptions=False)


def _make_row(report: dict, repo: object = None, **extra: object) -> dict:
    """Minimal snapshot row (mirrors report_to_snapshot_row output)."""
    return {
        "repo": repo,
        "totalDocs": report.get("totalDocs", 0),
        "qualityAvg": report.get("qualityAvg", 0.0),
        "brokenLinks": report.get("brokenLinksDetected", 0),
        "orphanCount": report.get("orphanCount", 0),
        "atRiskCount": report.get("atRiskCount", 0),
        "staleDetected": extra.get("staleDetected"),
        "conflictsDetected": extra.get("conflictsDetected"),
        "duplicatesDetected": extra.get("duplicatesDetected"),
        "payload": report,
    }


def _patch_core(monkeypatch, *, doc: dict | None = _DOC) -> None:
    """Patch all shared I/O entry-points on app.main so no DB calls happen."""
    import app.main as _main
    import app.governance.store as _gov

    # compute_report returns the fixed report dict
    monkeypatch.setattr(_main, "compute_report", lambda namespace=None: _REPORT)

    # report_to_snapshot_row builds a snapshot row (no I/O)
    monkeypatch.setattr(
        _main,
        "report_to_snapshot_row",
        lambda r, repo=None, **kw: _make_row(r, repo=repo, **kw),
    )

    # compute_doc_analysis echoes _DOC_ANALYSIS with llm_notes injected
    monkeypatch.setattr(
        _main,
        "compute_doc_analysis",
        lambda doc_id, namespace=None, llm_notes=None: {**_DOC_ANALYSIS, "llm": llm_notes},
    )

    # compute_trends returns the fixed trends dict
    monkeypatch.setattr(_main, "compute_trends", lambda namespace=None: _TRENDS)

    # analyze_with_llm returns the fixed LLM notes (but see specific tests below)
    monkeypatch.setattr(
        _main,
        "analyze_with_llm",
        lambda doc_id, content, *, heading_paths=None, deterministic_quality=None: _LLM_NOTES,
    )

    # insert_analysis_snapshot returns a fixed snapshot id
    monkeypatch.setattr(_main, "insert_analysis_snapshot", lambda row: _SNAPSHOT_ID)

    # get_edge_type_counts returns two edge-type counts
    monkeypatch.setattr(
        _main,
        "get_edge_type_counts",
        lambda namespace=None: {"conflicts-with": 2, "duplicate-of": 1},
    )

    # get_document returns the test doc for its exact docId, None otherwise
    _doc_id = (doc or {}).get("docId")
    monkeypatch.setattr(
        _main,
        "get_document",
        lambda doc_id, _id=_doc_id, _d=doc: _d if doc_id == _id else None,
    )

    # get_document_meta returns public meta by default
    monkeypatch.setattr(
        _gov,
        "get_document_meta",
        lambda doc_id: {**_META_PUBLIC, "doc_id": doc_id},
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /analysis
# ─────────────────────────────────────────────────────────────────────────────

class TestGetAnalysis:
    def test_returns_200(self, monkeypatch):
        _patch_core(monkeypatch)
        resp = _client().get("/analysis")
        assert resp.status_code == 200

    def test_camelcase_shape(self, monkeypatch):
        _patch_core(monkeypatch)
        body = _client().get("/analysis").json()
        for key in (
            "totalDocs", "qualityAvg", "brokenLinksDetected",
            "orphanCount", "atRiskCount",
            "worstQuality", "mostAtRisk", "topCentral", "asOf",
        ):
            assert key in body, f"missing required key: {key!r}"

    def test_no_snake_case_leak(self, monkeypatch):
        _patch_core(monkeypatch)
        body = _client().get("/analysis").json()
        snake_keys = [k for k in body if "_" in k]
        assert not snake_keys, f"snake_case keys leaked into response: {snake_keys}"

    def test_repo_filter_forwarded_to_compute_report(self, monkeypatch):
        import app.main as _main
        captured: list[object] = []

        def _mock_report(namespace=None):
            captured.append(namespace)
            return _REPORT

        _patch_core(monkeypatch)
        monkeypatch.setattr(_main, "compute_report", _mock_report)
        resp = _client().get("/analysis?repo=vscode")
        assert resp.status_code == 200
        assert captured == ["vscode"], "repo param must be forwarded"

    def test_no_repo_param_passes_none(self, monkeypatch):
        import app.main as _main
        captured: list[object] = []

        def _mock_report(namespace=None):
            captured.append(namespace)
            return _REPORT

        _patch_core(monkeypatch)
        monkeypatch.setattr(_main, "compute_report", _mock_report)
        resp = _client().get("/analysis")
        assert resp.status_code == 200
        assert captured == [None]


# ─────────────────────────────────────────────────────────────────────────────
# GET /analysis/trends  —  must NOT be shadowed by /analysis/{doc_id:path}
# ─────────────────────────────────────────────────────────────────────────────

class TestGetAnalysisTrends:
    def test_returns_200(self, monkeypatch):
        _patch_core(monkeypatch)
        resp = _client().get("/analysis/trends")
        assert resp.status_code == 200

    def test_not_shadowed_by_catch_all(self, monkeypatch):
        """Endpoint must resolve to TrendsDTO, never DocAnalysis.

        TrendsDTO has ``proposalAcceptanceRate``; DocAnalysis has ``quality``.
        These keys are mutually exclusive — their presence distinguishes the routes.
        """
        _patch_core(monkeypatch)
        body = _client().get("/analysis/trends").json()
        assert "proposalAcceptanceRate" in body, (
            "/analysis/trends was shadowed by /analysis/{doc_id:path} catch-all"
        )
        assert "quality" not in body, "TrendsDTO must not include DocAnalysis keys"

    def test_camelcase_shape(self, monkeypatch):
        _patch_core(monkeypatch)
        body = _client().get("/analysis/trends").json()
        for key in (
            "series", "byRepo", "proposalAcceptanceRate",
            "confidenceHistogram", "evidenceCoverage", "asOf",
        ):
            assert key in body, f"missing required key: {key!r}"

    def test_repo_filter_forwarded(self, monkeypatch):
        import app.main as _main
        captured: list[object] = []

        def _mock_trends(namespace=None):
            captured.append(namespace)
            return _TRENDS

        _patch_core(monkeypatch)
        monkeypatch.setattr(_main, "compute_trends", _mock_trends)
        resp = _client().get("/analysis/trends?repo=garnet")
        assert resp.status_code == 200
        assert captured == ["garnet"]


# ─────────────────────────────────────────────────────────────────────────────
# GET /analysis/{doc_id:path}
# ─────────────────────────────────────────────────────────────────────────────

class TestGetDocAnalysis:
    def test_known_doc_returns_200(self, monkeypatch):
        _patch_core(monkeypatch)
        resp = _client().get("/analysis/user/test.md")
        assert resp.status_code == 200

    def test_unknown_doc_returns_404(self, monkeypatch):
        import app.main as _main
        _patch_core(monkeypatch)
        monkeypatch.setattr(_main, "get_document", lambda doc_id: None)
        resp = _client().get("/analysis/user/missing.md")
        assert resp.status_code == 404

    def test_camelcase_shape(self, monkeypatch):
        _patch_core(monkeypatch)
        body = _client().get("/analysis/user/test.md").json()
        for key in ("docId", "quality", "links", "drift", "centrality"):
            assert key in body, f"missing required key: {key!r}"

    def test_quality_sub_shape(self, monkeypatch):
        _patch_core(monkeypatch)
        q = _client().get("/analysis/user/test.md").json()["quality"]
        for key in ("qualityScore", "readability", "gradeLevel",
                    "completenessScore", "structureScore",
                    "wordCount", "placeholderCount", "issues"):
            assert key in q, f"quality sub-DTO missing key: {key!r}"

    def test_links_sub_shape(self, monkeypatch):
        _patch_core(monkeypatch)
        lnk = _client().get("/analysis/user/test.md").json()["links"]
        for key in ("brokenInternal", "brokenLinkCount", "externalCount", "orphan", "deadEnd"):
            assert key in lnk, f"links sub-DTO missing key: {key!r}"

    def test_drift_sub_shape(self, monkeypatch):
        _patch_core(monkeypatch)
        drift = _client().get("/analysis/user/test.md").json()["drift"]
        for key in ("ageDays", "isStale", "riskScore", "riskReasons"):
            assert key in drift, f"drift sub-DTO missing key: {key!r}"

    # ── LLM layer ──────────────────────────────────────────────────────────

    def test_no_llm_param_does_not_call_analyze_with_llm(self, monkeypatch):
        """Without ?llm=true, analyze_with_llm must never be invoked."""
        import app.main as _main
        call_count: list[int] = [0]

        def _forbidden_llm(*a, **kw):
            call_count[0] += 1
            return _LLM_NOTES

        _patch_core(monkeypatch)
        monkeypatch.setattr(_main, "analyze_with_llm", _forbidden_llm)
        resp = _client().get("/analysis/user/test.md")
        assert resp.status_code == 200
        assert call_count[0] == 0, "analyze_with_llm must NOT be called without ?llm=true"

    def test_no_llm_param_response_llm_field_is_null(self, monkeypatch):
        """Without ?llm=true the ``llm`` field must be null."""
        _patch_core(monkeypatch)
        body = _client().get("/analysis/user/test.md").json()
        assert body.get("llm") is None, "llm field must be null when ?llm is absent"

    def test_llm_true_calls_analyze_with_llm_exactly_once(self, monkeypatch):
        """?llm=true must invoke analyze_with_llm exactly once (cost guard)."""
        import app.main as _main
        call_count: list[int] = [0]

        def _counting_llm(doc_id, content, *, heading_paths=None, deterministic_quality=None):
            call_count[0] += 1
            return _LLM_NOTES

        _patch_core(monkeypatch)
        monkeypatch.setattr(_main, "analyze_with_llm", _counting_llm)
        resp = _client().get("/analysis/user/test.md?llm=true")
        assert resp.status_code == 200
        assert call_count[0] == 1, "analyze_with_llm must be called exactly once per request"

    def test_llm_true_populates_llm_field(self, monkeypatch):
        """?llm=true must populate response['llm'] with the notes dict."""
        import app.main as _main
        _patch_core(monkeypatch)
        # Ensure compute_doc_analysis threads llm_notes into the response
        monkeypatch.setattr(
            _main,
            "compute_doc_analysis",
            lambda doc_id, namespace=None, llm_notes=None: {**_DOC_ANALYSIS, "llm": llm_notes},
        )
        resp = _client().get("/analysis/user/test.md?llm=true")
        assert resp.status_code == 200
        llm = resp.json().get("llm")
        assert llm is not None, "llm field must be populated when ?llm=true"
        assert "clarityScore" in llm
        assert "issues" in llm
        assert "suggestedSections" in llm

    def test_llm_true_issues_populated(self, monkeypatch):
        """LLM issues from mock must appear in the response."""
        import app.main as _main
        _patch_core(monkeypatch)
        monkeypatch.setattr(
            _main,
            "compute_doc_analysis",
            lambda doc_id, namespace=None, llm_notes=None: {**_DOC_ANALYSIS, "llm": llm_notes},
        )
        llm = _client().get("/analysis/user/test.md?llm=true").json()["llm"]
        assert llm["issues"] == _LLM_NOTES["issues"]

    # ── Path with slashes ───────────────────────────────────────────────────

    def test_multipart_doc_id_accepted(self, monkeypatch):
        """The {doc_id:path} converter must pass doc_ids with multiple slashes."""
        import app.main as _main
        import app.governance.store as _gov

        deep_doc = {**_DOC, "docId": "vscode/docs/build.md"}
        _patch_core(monkeypatch)
        monkeypatch.setattr(
            _main,
            "get_document",
            lambda doc_id: deep_doc if doc_id == "vscode/docs/build.md" else None,
        )
        monkeypatch.setattr(
            _gov,
            "get_document_meta",
            lambda doc_id: {**_META_PUBLIC, "doc_id": doc_id},
        )
        monkeypatch.setattr(
            _main,
            "compute_doc_analysis",
            lambda doc_id, namespace=None, llm_notes=None: {
                **_DOC_ANALYSIS,
                "docId": doc_id,
                "llm": llm_notes,
            },
        )
        resp = _client().get("/analysis/vscode/docs/build.md")
        assert resp.status_code == 200
        assert resp.json()["docId"] == "vscode/docs/build.md"

    # ── ACL ────────────────────────────────────────────────────────────────

    def test_acl_denial_returns_404(self, monkeypatch):
        """Docs with a restricted ACL that PUBLIC_PRINCIPAL cannot satisfy → 404.

        404 (not 403) is used so the existence of restricted content is never
        revealed to an unprivileged caller.
        """
        import app.main as _main
        import app.governance.store as _gov

        _patch_core(monkeypatch)
        # Doc exists in storage ...
        monkeypatch.setattr(_main, "get_document", lambda doc_id: _DOC)
        # ... but its ACL blocks PUBLIC_PRINCIPAL (which only has role:engineer)
        monkeypatch.setattr(_gov, "get_document_meta", lambda doc_id: _META_RESTRICTED)
        resp = _client().get("/analysis/user/test.md")
        assert resp.status_code == 404, (
            "Restricted doc must return 404 to avoid leaking its existence"
        )

    def test_acl_public_doc_accessible(self, monkeypatch):
        """A doc with an empty ACL must be accessible to PUBLIC_PRINCIPAL."""
        _patch_core(monkeypatch)  # default meta has empty ACL
        resp = _client().get("/analysis/user/test.md")
        assert resp.status_code == 200

    def test_acl_matching_role_accessible(self, monkeypatch):
        """A doc whose ACL includes role:engineer must be accessible to PUBLIC_PRINCIPAL."""
        import app.governance.store as _gov

        _patch_core(monkeypatch)
        # PUBLIC_PRINCIPAL has role:engineer → can access
        monkeypatch.setattr(
            _gov,
            "get_document_meta",
            lambda doc_id: {**_META_PUBLIC, "acl": ["role:engineer"]},
        )
        resp = _client().get("/analysis/user/test.md")
        assert resp.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# POST /analysis/snapshot
# ─────────────────────────────────────────────────────────────────────────────

class TestCreateAnalysisSnapshot:
    def test_returns_200(self, monkeypatch):
        _patch_core(monkeypatch)
        resp = _client().post("/analysis/snapshot")
        assert resp.status_code == 200

    def test_response_contains_snapshot_id(self, monkeypatch):
        _patch_core(monkeypatch)
        body = _client().post("/analysis/snapshot").json()
        assert "snapshotId" in body
        assert body["snapshotId"] == _SNAPSHOT_ID

    def test_response_echoes_row_fields(self, monkeypatch):
        """The response must echo the snapshot row fields (totalDocs etc.)."""
        _patch_core(monkeypatch)
        body = _client().post("/analysis/snapshot").json()
        assert "totalDocs" in body
        assert "qualityAvg" in body

    def test_insert_called_exactly_once(self, monkeypatch):
        """insert_analysis_snapshot must be called exactly once per request."""
        import app.main as _main
        insert_calls: list = []

        def _mock_insert(row):
            insert_calls.append(row)
            return _SNAPSHOT_ID

        _patch_core(monkeypatch)
        monkeypatch.setattr(_main, "insert_analysis_snapshot", _mock_insert)
        resp = _client().post("/analysis/snapshot")
        assert resp.status_code == 200
        assert len(insert_calls) == 1, "insert must be called exactly once"

    def test_repo_body_forwarded_to_compute_report(self, monkeypatch):
        """repo from the request body must be forwarded to compute_report."""
        import app.main as _main
        captured: list[object] = []

        def _mock_report(namespace=None):
            captured.append(namespace)
            return _REPORT

        _patch_core(monkeypatch)
        monkeypatch.setattr(_main, "compute_report", _mock_report)
        resp = _client().post("/analysis/snapshot", json={"repo": "vscode"})
        assert resp.status_code == 200
        assert captured == ["vscode"]

    def test_no_body_uses_none_repo(self, monkeypatch):
        """Absent body must use repo=None (full corpus)."""
        import app.main as _main
        captured: list[object] = []

        def _mock_report(namespace=None):
            captured.append(namespace)
            return _REPORT

        _patch_core(monkeypatch)
        monkeypatch.setattr(_main, "compute_report", _mock_report)
        resp = _client().post("/analysis/snapshot")
        assert resp.status_code == 200
        assert captured == [None]

    def test_edge_counts_included_in_snapshot(self, monkeypatch):
        """conflictsDetected and duplicatesDetected must flow into the snapshot row."""
        import app.main as _main
        inserted_rows: list[dict] = []

        def _mock_insert(row):
            inserted_rows.append(row)
            return _SNAPSHOT_ID

        _patch_core(monkeypatch)
        monkeypatch.setattr(_main, "insert_analysis_snapshot", _mock_insert)
        resp = _client().post("/analysis/snapshot")
        assert resp.status_code == 200
        row = inserted_rows[0]
        assert row.get("conflictsDetected") == 2
        assert row.get("duplicatesDetected") == 1

    def test_with_json_body(self, monkeypatch):
        """POST with a JSON body must work and use the provided repo."""
        _patch_core(monkeypatch)
        resp = _client().post("/analysis/snapshot", json={"repo": "playwright"})
        assert resp.status_code == 200
        assert "snapshotId" in resp.json()
