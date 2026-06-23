"""Layer 2 — Processing.

Turns one RawDocument into many DocChunks plus structural GraphEdges.
Pure and deterministic: same input always yields the same output (idempotent).
Mirrors README Section 8A.3.
"""

from __future__ import annotations

import hashlib
import re
from posixpath import normpath
from urllib.parse import urlparse

from app.models import DocChunk, EdgeType, GraphEdge, RawDocument

# Target chunk sizing (token counts are approximated by whitespace word count).
MAX_TOKENS = 800
MIN_TOKENS_FOR_SPLIT = 1000

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*$")
_FENCE_RE = re.compile(r"^\s*(```|~~~)")
_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "section"


def _approx_tokens(text: str) -> int:
    return len(text.split())


def _sha256(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _strip_front_matter(content: str) -> tuple[str, int]:
    """Remove a leading YAML front-matter block. Returns (body, lines_removed)."""
    lines = content.splitlines()
    if lines and lines[0].strip() == "---":
        for idx in range(1, len(lines)):
            if lines[idx].strip() == "---":
                return "\n".join(lines[idx + 1 :]), idx + 1
    return content, 0


class _Section:
    __slots__ = ("heading_path", "start_line", "lines", "has_commands")

    def __init__(self, heading_path: list[str], start_line: int):
        self.heading_path = heading_path
        self.start_line = start_line
        self.lines: list[str] = []
        self.has_commands = False


def _split_into_sections(body: str, line_offset: int) -> list[_Section]:
    """Split markdown into heading-delimited sections, ignoring headings in code."""
    sections: list[_Section] = []
    heading_stack: list[tuple[int, str]] = []  # (level, title)
    in_fence = False
    current = _Section([], line_offset + 1)

    for i, line in enumerate(body.splitlines()):
        line_no = line_offset + i + 1

        if _FENCE_RE.match(line):
            in_fence = not in_fence
            current.lines.append(line)
            current.has_commands = True
            continue

        heading = None if in_fence else _HEADING_RE.match(line)
        if heading:
            if current.lines:
                sections.append(current)
            level = len(heading.group(1))
            title = heading.group(2).strip()
            heading_stack = [h for h in heading_stack if h[0] < level]
            heading_stack.append((level, title))
            current = _Section([t for _, t in heading_stack], line_no)
            current.lines.append(line)
        else:
            current.lines.append(line)

    if current.lines:
        sections.append(current)
    return sections


def chunk_document(raw: RawDocument) -> list[DocChunk]:
    """Produce heading-aware DocChunks for a RawDocument."""
    body, removed = _strip_front_matter(raw.content)
    sections = _split_into_sections(body, line_offset=removed)

    chunks: list[DocChunk] = []
    ordinal = 0
    for section in sections:
        text = "\n".join(section.lines).strip()
        if not text:
            continue

        # Split oversized sections by blank-line paragraphs.
        if _approx_tokens(text) > MIN_TOKENS_FOR_SPLIT:
            blocks = [b for b in re.split(r"\n\s*\n", text) if b.strip()]
        else:
            blocks = [text]

        line_cursor = section.start_line
        for block in blocks:
            block_lines = block.count("\n") + 1
            start_line = line_cursor
            end_line = line_cursor + block_lines - 1
            line_cursor = end_line + 1

            heading_slug = _slugify(section.heading_path[-1]) if section.heading_path else "root"
            chunk_id = f"{raw.doc_id}#{heading_slug}#{ordinal}"
            chunks.append(
                DocChunk(
                    chunk_id=chunk_id,
                    doc_id=raw.doc_id,
                    repo=raw.repo,
                    heading_path=section.heading_path,
                    ordinal=ordinal,
                    text=block,
                    token_count=_approx_tokens(block),
                    line_range=(start_line, end_line),
                    char_range=(0, len(block)),
                    contains_commands="```" in block or "~~~" in block,
                    commit_sha=raw.commit_sha,
                    commit_date=raw.commit_date,
                    content_hash=_sha256(block),
                )
            )
            ordinal += 1

    return chunks


def _resolve_link(from_doc_id: str, target: str) -> str | None:
    """Resolve a relative markdown link to a doc_id in the same repo, else None."""
    target = target.split("#", 1)[0].split("?", 1)[0].strip()
    if not target:
        return None
    if urlparse(target).scheme in ("http", "https", "mailto"):
        return None
    if not target.endswith((".md", ".mdx")):
        return None

    short_name = from_doc_id.split("/", 1)[0]
    from_path = from_doc_id.split("/", 1)[1] if "/" in from_doc_id else ""
    from_dir = from_path.rsplit("/", 1)[0] if "/" in from_path else ""

    if target.startswith("/"):
        resolved = normpath(target.lstrip("/"))
    else:
        base = f"{from_dir}/{target}" if from_dir else target
        resolved = normpath(base)

    if resolved.startswith(".."):
        return None
    return f"{short_name}/{resolved}"


def extract_edges(raw: RawDocument) -> list[GraphEdge]:
    """Extract structural 'references' edges from markdown links."""
    edges: list[GraphEdge] = []
    seen: set[str] = set()

    for line_idx, line in enumerate(raw.content.splitlines(), start=1):
        for match in _LINK_RE.finditer(line):
            anchor_text, target = match.group(1), match.group(2)
            to_doc = _resolve_link(raw.doc_id, target)
            if not to_doc or to_doc == raw.doc_id or to_doc in seen:
                continue
            seen.add(to_doc)
            edges.append(
                GraphEdge(
                    edge_id=f"{raw.doc_id}->{to_doc}:references",
                    **{"from": raw.doc_id, "to": to_doc},
                    type=EdgeType.REFERENCES,
                    weight=1.0,
                    reason="explicit-markdown-link",
                    anchor_text=anchor_text[:120],
                    line=line_idx,
                    created_by="link-extractor",
                    commit_sha=raw.commit_sha,
                )
            )
    return edges
