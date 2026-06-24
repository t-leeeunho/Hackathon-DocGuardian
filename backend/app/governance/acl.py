"""ACL enforcement (README §10.7 — mocked auth, real ACL).

A document's ``acl`` is a list of grant tokens such as ``team:platform`` or
``role:engineer``. A principal holds a set of those tokens. The rules are
deliberately simple and **fail closed**:

* An empty ACL means the document is **public** (the director default for the
  hackathon corpus, which is all open-source docs).
* Otherwise the principal must hold at least one token in the document's ACL.

The same check is applied at retrieval, answer, write, and WebSocket fan-out so
restricted content can never leak through any layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Principal:
    """The (mocked) authenticated user making a request."""

    user: str = "anonymous"
    roles: frozenset[str] = field(default_factory=frozenset)

    @classmethod
    def from_tokens(cls, user: str, tokens: list[str] | None) -> "Principal":
        return cls(user=user, roles=frozenset(tokens or []))

    @property
    def grants(self) -> frozenset[str]:
        """Everything this principal can match an ACL against."""
        return self.roles | {f"user:{self.user}"}


# A permissive default principal for the open-source demo corpus. Swap for a
# real (mocked) user/role map at the API boundary when demoing ACLs.
PUBLIC_PRINCIPAL = Principal(user="demo", roles=frozenset({"role:engineer"}))


def can_access(principal: Principal, acl: list[str] | None) -> bool:
    """True if ``principal`` may read a doc with the given ``acl``.

    Empty/None ACL is public. Otherwise require a grant intersection.
    """
    if not acl:
        return True
    return bool(principal.grants & set(acl))


def can_write(principal: Principal, acl: list[str] | None) -> bool:
    """Write rights mirror read rights for the MVP (no separate write ACL yet).

    Public docs are writable by any authenticated (non-anonymous) principal so an
    approver identity is always recorded.
    """
    if principal.user == "anonymous":
        return False
    return can_access(principal, acl)


def filter_accessible(principal: Principal, docs: list[dict]) -> list[dict]:
    """Drop documents the principal cannot read. ``docs`` carry an ``acl`` key."""
    return [d for d in docs if can_access(principal, d.get("acl"))]
