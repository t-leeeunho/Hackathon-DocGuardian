"""Structural folder/sibling edges so the graph reflects the file hierarchy.

Conflict/reference edges only connect documents that are similar or explicitly
linked, which leaves many docs floating alone. These ``sibling`` edges connect
every document to its folder's anchor, and each folder anchor up to the repo
anchor — so each project forms one connected tree (no orphan nodes) without an
O(n^2) hairball.

``build_structure_edges`` is pure (unit testable); ``persist_structure_edges``
loads the corpus and upserts.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict

_INDEX_NAMES = {"readme.md", "index.md", "index.mdx", "readme.mdx"}


def _edge_id(a: str, b: str) -> str:
    lo, hi = sorted((a, b))
    return "fs_" + hashlib.sha1(f"{lo}|{hi}|sibling".encode()).hexdigest()[:16]


def _sibling_edge(from_doc: str, to_doc: str) -> dict:
    return {
        "edge_id": _edge_id(from_doc, to_doc),
        "from_doc": from_doc,
        "to_doc": to_doc,
        "type": "sibling",
        "weight": 0.3,
        "reason": "same folder / hierarchy",
        "anchor_text": "",
        "line": None,
        "created_by": "structure",
        "commit_sha": "",
    }


def _parent(doc_id: str) -> str:
    return doc_id.rsplit("/", 1)[0] if "/" in doc_id else doc_id


def _anchor_of(members: list[str]) -> str:
    """The folder's representative doc: a README/index if present, else first."""
    return sorted(
        members,
        key=lambda p: (0 if p.rsplit("/", 1)[-1].lower() in _INDEX_NAMES else 1, p),
    )[0]


def build_structure_edges(doc_ids: list[str]) -> list[dict]:
    """Connect each doc to its folder anchor, and folder anchors to the repo anchor."""
    by_repo: dict[str, list[str]] = defaultdict(list)
    for d in doc_ids:
        by_repo[d.split("/", 1)[0]].append(d)

    edges: list[dict] = []
    seen: set[str] = set()

    def add(a: str, b: str) -> None:
        if a == b:
            return
        eid = _edge_id(a, b)
        if eid in seen:
            return
        seen.add(eid)
        edges.append(_sibling_edge(a, b))

    for _repo, docs in by_repo.items():
        repo_anchor = _anchor_of(docs)
        by_folder: dict[str, list[str]] = defaultdict(list)
        for d in docs:
            by_folder[_parent(d)].append(d)
        for _folder, members in by_folder.items():
            folder_anchor = _anchor_of(members)
            for m in members:
                add(folder_anchor, m)
            add(repo_anchor, folder_anchor)
    return edges


def persist_structure_edges() -> int:
    """Build structure edges for the whole corpus and upsert them. Returns count."""
    from app.storage.queries import list_doc_ids
    from app.storage.vectorstore import upsert_edges

    return upsert_edges(build_structure_edges(list_doc_ids()))
