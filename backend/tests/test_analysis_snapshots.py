"""Offline tests for the analysis-snapshot pure helpers.

Only ``_snapshot_insert_params`` and ``_snapshot_row_to_dto`` are exercised.
No Postgres connection is opened; no external service is needed.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from app.storage.queries import _snapshot_insert_params, _snapshot_row_to_dto


# ---------------------------------------------------------------------------
# _snapshot_insert_params
# ---------------------------------------------------------------------------


class TestSnapshotInsertParams:
    def test_generates_snapshot_id_when_missing(self):
        params = _snapshot_insert_params({})
        assert params["snapshot_id"], "snapshot_id must not be empty or falsy"

    def test_generated_ids_are_unique(self):
        a = _snapshot_insert_params({})["snapshot_id"]
        b = _snapshot_insert_params({})["snapshot_id"]
        assert a != b

    def test_preserves_provided_snapshot_id(self):
        params = _snapshot_insert_params({"snapshotId": "my-snap-001"})
        assert params["snapshot_id"] == "my-snap-001"

    def test_empty_string_snapshot_id_triggers_generation(self):
        # falsy string "" → generate a new one
        params = _snapshot_insert_params({"snapshotId": ""})
        assert params["snapshot_id"] != ""
        assert len(params["snapshot_id"]) > 0

    # --- payload serialisation ---

    def test_serializes_dict_payload_to_json_string(self):
        payload_in = {"issues": ["stale"], "count": 3}
        params = _snapshot_insert_params({"payload": payload_in})
        assert isinstance(params["payload"], str)
        decoded = json.loads(params["payload"])
        assert decoded == payload_in

    def test_serializes_list_payload_to_json_string(self):
        payload_in = [1, 2, 3]
        params = _snapshot_insert_params({"payload": payload_in})
        assert isinstance(params["payload"], str)
        assert json.loads(params["payload"]) == [1, 2, 3]

    def test_payload_already_string_left_unchanged(self):
        raw = '{"already": "serialized"}'
        params = _snapshot_insert_params({"payload": raw})
        assert params["payload"] == raw

    def test_payload_none_stays_none(self):
        params = _snapshot_insert_params({})
        assert params["payload"] is None

    # --- count-field coercion ---

    def test_coerces_count_fields_from_float(self):
        inp = {
            "totalDocs": 10.9,
            "brokenLinks": 3.0,
            "staleDetected": 2.5,
            "conflictsDetected": 1.0,
            "duplicatesDetected": 4.1,
            "orphanCount": 0.0,
            "atRiskCount": 5.9,
        }
        params = _snapshot_insert_params(inp)
        # int() truncates toward zero — check type and value
        assert params["total_docs"] == 10 and isinstance(params["total_docs"], int)
        assert params["broken_links"] == 3 and isinstance(params["broken_links"], int)
        assert params["stale_detected"] == 2
        assert params["conflicts_detected"] == 1
        assert params["duplicates_detected"] == 4
        assert params["orphan_count"] == 0
        assert params["at_risk_count"] == 5

    def test_coerces_count_fields_from_string(self):
        inp = {
            "totalDocs": "7",
            "brokenLinks": "2",
            "staleDetected": "0",
            "conflictsDetected": "3",
            "duplicatesDetected": "1",
            "orphanCount": "4",
            "atRiskCount": "6",
        }
        params = _snapshot_insert_params(inp)
        assert params["total_docs"] == 7
        assert params["broken_links"] == 2
        assert params["stale_detected"] == 0
        assert params["conflicts_detected"] == 3
        assert params["duplicates_detected"] == 1
        assert params["orphan_count"] == 4
        assert params["at_risk_count"] == 6

    def test_count_fields_none_when_absent(self):
        params = _snapshot_insert_params({})
        for key in (
            "total_docs",
            "broken_links",
            "stale_detected",
            "conflicts_detected",
            "duplicates_detected",
            "orphan_count",
            "at_risk_count",
        ):
            assert params[key] is None, f"expected None for {key!r}"

    def test_repo_and_quality_avg_pass_through(self):
        params = _snapshot_insert_params({"repo": "acme/docs", "qualityAvg": 0.75})
        assert params["repo"] == "acme/docs"
        assert abs(params["quality_avg"] - 0.75) < 1e-9


# ---------------------------------------------------------------------------
# _snapshot_row_to_dto
# ---------------------------------------------------------------------------


class TestSnapshotRowToDto:
    # --- camelCase key contract ---

    _EXPECTED_KEYS = frozenset(
        {
            "snapshotId",
            "takenAt",
            "repo",
            "totalDocs",
            "qualityAvg",
            "brokenLinks",
            "staleDetected",
            "conflictsDetected",
            "duplicatesDetected",
            "orphanCount",
            "atRiskCount",
            "payload",
        }
    )

    def test_exact_camelcase_keys(self):
        row = {
            "snapshot_id": "s1",
            "taken_at": "2024-01-01T00:00:00",
            "repo": "r",
            "total_docs": 1,
            "quality_avg": 0.9,
            "broken_links": 0,
            "stale_detected": 0,
            "conflicts_detected": 0,
            "duplicates_detected": 0,
            "orphan_count": 0,
            "at_risk_count": 0,
            "payload": None,
        }
        dto = _snapshot_row_to_dto(row)
        assert set(dto.keys()) == self._EXPECTED_KEYS

    def test_values_map_correctly(self):
        row = {
            "snapshot_id": "snap42",
            "taken_at": "2025-03-01T08:00:00",
            "repo": "myorg/myrepo",
            "total_docs": 50,
            "quality_avg": 0.82,
            "broken_links": 3,
            "stale_detected": 7,
            "conflicts_detected": 2,
            "duplicates_detected": 5,
            "orphan_count": 1,
            "at_risk_count": 4,
            "payload": None,
        }
        dto = _snapshot_row_to_dto(row)
        assert dto["snapshotId"] == "snap42"
        assert dto["repo"] == "myorg/myrepo"
        assert dto["totalDocs"] == 50
        assert abs(dto["qualityAvg"] - 0.82) < 1e-9
        assert dto["brokenLinks"] == 3
        assert dto["staleDetected"] == 7
        assert dto["conflictsDetected"] == 2
        assert dto["duplicatesDetected"] == 5
        assert dto["orphanCount"] == 1
        assert dto["atRiskCount"] == 4

    # --- takenAt formatting ---

    def test_aware_datetime_iso_formatted(self):
        dt = datetime(2024, 6, 15, 12, 30, 0, tzinfo=timezone.utc)
        dto = _snapshot_row_to_dto({"taken_at": dt})
        assert isinstance(dto["takenAt"], str)
        # Must be valid ISO 8601 with both date and time parts
        assert "2024-06-15" in dto["takenAt"]
        assert "T" in dto["takenAt"]

    def test_naive_datetime_iso_formatted(self):
        dt = datetime(2024, 3, 1, 8, 0, 0)
        dto = _snapshot_row_to_dto({"taken_at": dt})
        assert dto["takenAt"] == "2024-03-01T08:00:00"

    def test_string_taken_at_passes_through_unchanged(self):
        s = "2024-09-01T00:00:00Z"
        dto = _snapshot_row_to_dto({"taken_at": s})
        assert dto["takenAt"] == s

    def test_none_taken_at_stays_none(self):
        dto = _snapshot_row_to_dto({"taken_at": None})
        assert dto["takenAt"] is None

    # --- payload parsing ---

    def test_parses_json_string_payload_to_dict(self):
        payload_dict = {"issues": ["stale", "broken"], "count": 5}
        dto = _snapshot_row_to_dto({"payload": json.dumps(payload_dict)})
        assert isinstance(dto["payload"], dict)
        assert dto["payload"]["count"] == 5
        assert dto["payload"]["issues"] == ["stale", "broken"]

    def test_parses_json_string_payload_to_list(self):
        dto = _snapshot_row_to_dto({"payload": "[1, 2, 3]"})
        assert dto["payload"] == [1, 2, 3]

    def test_dict_payload_kept_unchanged(self):
        payload = {"a": 1, "b": [2, 3]}
        dto = _snapshot_row_to_dto({"payload": payload})
        assert dto["payload"] == {"a": 1, "b": [2, 3]}

    def test_none_payload_stays_none(self):
        dto = _snapshot_row_to_dto({"payload": None})
        assert dto["payload"] is None

    def test_unparseable_payload_string_kept_as_string(self):
        bad = "not-valid-json{{{"
        dto = _snapshot_row_to_dto({"payload": bad})
        assert dto["payload"] == bad

    # --- missing / sparse rows ---

    def test_missing_fields_produce_none_values(self):
        dto = _snapshot_row_to_dto({})
        assert dto["snapshotId"] is None
        assert dto["takenAt"] is None
        assert dto["repo"] is None
        assert dto["totalDocs"] is None
        assert dto["qualityAvg"] is None
        assert dto["brokenLinks"] is None
        assert dto["payload"] is None
