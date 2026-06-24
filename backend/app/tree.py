"""Build the left-sidebar file-system tree (README Section 7.4).

Every doc_id is already a full repo-relative path (e.g.
"playwright/docs/src/codegen.md"), so the folder tree is derived directly from
the processed documents — no embeddings or DB required.
"""

from __future__ import annotations

from typing import Any, Iterable


def build_tree(doc_ids: Iterable[str]) -> list[dict[str, Any]]:
    """Turn flat doc_ids into a nested [{name, type, path, children?}] tree.

    Folders sort before files; both alphabetically. The top level is one node
    per repo (the first path segment).
    """
    root: dict[str, Any] = {}

    for doc_id in doc_ids:
        parts = doc_id.split("/")
        node = root
        for depth, part in enumerate(parts):
            is_file = depth == len(parts) - 1
            child = node.setdefault(
                part,
                {
                    "name": part,
                    "type": "file" if is_file else "folder",
                    "path": "/".join(parts[: depth + 1]),
                    "_children": {},
                },
            )
            node = child["_children"]

    def to_list(children: dict[str, Any]) -> list[dict[str, Any]]:
        items = []
        for child in children.values():
            entry = {"name": child["name"], "type": child["type"], "path": child["path"]}
            if child["type"] == "folder":
                entry["children"] = to_list(child["_children"])
            items.append(entry)
        items.sort(key=lambda e: (e["type"] == "file", e["name"].lower()))
        return items

    return to_list(root)
