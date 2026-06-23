"""Core data contracts for DocGuardian AI.

These mirror the data formats defined in README Section 8A (System Architecture):
RawDocument (Layer 1), DocChunk + GraphEdge (Layer 2). They are the single
source of truth for what crosses each layer boundary.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RawDocument(BaseModel):
    """Output of the ingestion layer — one record per documentation file."""

    doc_id: str = Field(..., description="Stable key: '<shortName>/<path>'")
    repo: str = Field(..., description="Full GitHub slug, e.g. 'microsoft/garnet'")
    path: str = Field(..., description="Path relative to repo root")
    branch: str
    content: str = Field(..., description="Raw UTF-8 markdown")
    byte_size: int
    encoding: str = "utf-8"
    commit_sha: str
    commit_author: str = ""
    commit_email: str = ""
    commit_date: Optional[datetime] = None
    fetched_at: datetime = Field(default_factory=_utcnow)
    content_hash: str = Field(..., description="sha256 of content, for idempotency")


class EdgeType(str, Enum):
    REFERENCES = "references"
    DUPLICATE_OF = "duplicate-of"
    CONFLICTS_WITH = "conflicts-with"
    DEPRECATED_BY = "deprecated-by"


class DocChunk(BaseModel):
    """Output of the processing layer — one document fans out into many chunks."""

    chunk_id: str = Field(..., description="'<doc_id>#<headingSlug>#<ordinal>'")
    doc_id: str
    repo: str
    heading_path: list[str] = Field(default_factory=list)
    ordinal: int
    text: str
    token_count: int
    line_range: tuple[int, int]
    char_range: tuple[int, int]
    contains_commands: bool = False
    commit_sha: str
    commit_date: Optional[datetime] = None
    content_hash: str = Field(..., description="sha256 of text, for idempotent re-embed")


class GraphEdge(BaseModel):
    """Output of the processing/AI layer — a relationship between two documents."""

    edge_id: str
    from_doc: str = Field(..., alias="from")
    to_doc: str = Field(..., alias="to")
    type: EdgeType
    weight: float = 1.0
    reason: str = ""
    anchor_text: str = ""
    line: Optional[int] = None
    created_by: str = "link-extractor"
    commit_sha: str = ""

    model_config = {"populate_by_name": True}
