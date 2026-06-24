"""Pure-logic tests for health + importance derivation."""

from app.governance.health import DocSignals, derive_health, derive_importance


def test_conflict_is_red():
    sig = DocSignals(has_conflict_edge=True, last_verified_sha="a", current_commit_sha="a")
    assert derive_health(sig) == "red"


def test_deprecated_is_gray():
    sig = DocSignals(is_deprecated=True, last_verified_sha="a", current_commit_sha="a")
    assert derive_health(sig) == "gray"


def test_duplicate_or_stale_is_yellow():
    dup = DocSignals(has_duplicate_edge=True, last_verified_sha="a", current_commit_sha="a")
    assert derive_health(dup) == "yellow"
    stale = DocSignals(last_verified_sha="old", current_commit_sha="new")
    assert derive_health(stale) == "yellow"


def test_verified_current_is_green():
    sig = DocSignals(last_verified_sha="sha1", current_commit_sha="sha1")
    assert derive_health(sig) == "green"


def test_never_verified_is_stale_yellow():
    sig = DocSignals(last_verified_sha=None, current_commit_sha="sha1")
    assert sig.is_stale is True
    assert derive_health(sig) == "yellow"


def test_importance_bounds_and_centrality():
    low = derive_importance(DocSignals(inbound_refs=0))
    high = derive_importance(DocSignals(inbound_refs=20))
    assert 0.1 <= low <= high <= 1.0
    assert high > low
