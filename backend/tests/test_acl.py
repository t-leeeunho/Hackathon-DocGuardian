"""Pure-logic tests for ACL enforcement."""

from app.governance.acl import Principal, can_access, can_write, filter_accessible


def test_empty_acl_is_public():
    p = Principal(user="bob", roles=frozenset())
    assert can_access(p, []) is True
    assert can_access(p, None) is True


def test_requires_grant_intersection():
    p = Principal(user="bob", roles=frozenset({"role:engineer"}))
    assert can_access(p, ["role:engineer"]) is True
    assert can_access(p, ["team:secret"]) is False


def test_user_token_grant():
    p = Principal.from_tokens("alice", [])
    assert can_access(p, ["user:alice"]) is True
    assert can_access(p, ["user:bob"]) is False


def test_can_write_denies_anonymous():
    anon = Principal(user="anonymous")
    assert can_write(anon, []) is False
    named = Principal.from_tokens("alice", [])
    assert can_write(named, []) is True


def test_filter_accessible_drops_restricted():
    p = Principal.from_tokens("alice", ["role:engineer"])
    docs = [
        {"id": "1", "acl": []},
        {"id": "2", "acl": ["role:engineer"]},
        {"id": "3", "acl": ["team:secret"]},
    ]
    kept = {d["id"] for d in filter_accessible(p, docs)}
    assert kept == {"1", "2"}
