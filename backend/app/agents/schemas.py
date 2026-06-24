"""Structured outputs for the Curator and Guardian agents.

These match the ChatAnswer and AgentProposal data formats in README Section 8A.4.
They are used both for LLM structured output and as API response models.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class Citation(BaseModel):
    doc_id: str = Field(..., description="docId of the supporting document")
    line_range: list[int] = Field(..., description="[start, end] source lines")
    commit_sha: str = Field("", description="commit the evidence came from")
    relevance: float = Field(..., ge=0, le=1, description="how relevant this source is")


class ChatAnswer(BaseModel):
    answer: str = Field(..., description="evidence-backed answer to the user's question")
    citations: list[Citation] = Field(default_factory=list)
    confidence: float = Field(..., ge=0, le=1)
    needs_human_review: bool = Field(
        False, description="true when evidence is weak or missing (README 6.4)"
    )


class AgentProposal(BaseModel):
    action: Literal["create", "update", "merge", "link", "deprecate", "flag"]
    target_doc_id: Optional[str] = Field(None, description="doc the change applies to")
    draft: str = Field(..., description="proposed document body / change")
    citations: list[Citation] = Field(default_factory=list)
    confidence: float = Field(..., ge=0, le=1)
    risk_level: Literal["low", "medium", "high"] = "medium"
    conflicts_with: list[str] = Field(default_factory=list)
    # Filled by the Guardian agent:
    recommendation: Optional[Literal["approve", "needs-review", "reject"]] = None
    guardian_reasoning: Optional[str] = None
    uncertainty: Optional[str] = None
