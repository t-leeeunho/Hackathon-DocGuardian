"""Structured outputs for the Curator and Guardian agents.

Two layers live here:

* Lean **agent I/O schemas** the LLM actually fills — ``ChatAnswer`` (chat),
  ``CuratorDraft`` (proposal drafting), and ``GuardianReview`` (judgment). Keeping
  these small keeps the LLM cheap and reliable, and lets the deterministic graph
  own provenance instead of trusting the model for it.
* The richer **response contract** ``AgentProposal`` (aligned with README §8A.4):
  identity, evidence, a structured diff, and a verification block. The graph
  assembles it from a ``CuratorDraft`` plus grounded retrieval rows; the model never
  supplies provenance fields (commit SHAs, evidence, verification) directly.

All fields are snake_case (the agent-schema layer). The camelCase HTTP shape the
frontend consumes is produced by DTOs in ``app/main.py``.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

# Shared enums (README §8.2 / §8A.4).
ProposalAction = Literal["create", "update", "merge", "link", "deprecate", "flag"]
RiskLevel = Literal["low", "medium", "high"]
Recommendation = Literal["approve", "needs-review", "reject"]


class Citation(BaseModel):
    doc_id: str = Field(..., description="docId of the supporting document")
    line_range: list[int] = Field(..., description="[start, end] source lines")
    commit_sha: str = Field("", description="commit the evidence came from")
    relevance: float = Field(..., ge=0, le=1, description="how relevant this source is")


class Evidence(BaseModel):
    """A grounded evidence item backing a proposal (README §8A.4 ``evidence[]``).

    System-populated from retrieved rows — never supplied by the model, so the
    quote and commit SHA always trace back to real indexed content.
    """

    chunk_id: str = Field("", description="chunkId of the supporting chunk")
    doc_id: str = Field(..., description="docId the chunk belongs to")
    commit_sha: str = Field("", description="authoritative commit the chunk came from")
    line_range: list[int] = Field(default_factory=list, description="[start, end] lines")
    quote: str = Field("", description="verbatim snippet used as evidence")
    relevance: float = Field(0.0, ge=0, le=1, description="retrieval similarity in [0,1]")


class ProposalDiff(BaseModel):
    """Before/after change rendered in the diff panel (README §8A.4 ``diff{}``)."""

    before: str = Field("", description="current text being changed")
    after: str = Field("", description="proposed replacement text")
    format: Literal["unified", "side-by-side"] = "unified"
    line_range: Optional[list[int]] = Field(None, description="[start, end] lines affected")


class Verification(BaseModel):
    """Sandbox verification result (README §8A.4 ``verification{}``).

    Populated by the P4 verification sandbox once it exists; until then proposals
    carry ``verification = null`` (sandbox not run).
    """

    sandbox_run: bool = False
    passed: Optional[bool] = None
    command: Optional[str] = None
    commit_sha: Optional[str] = None
    duration_ms: Optional[int] = None


class ChatAnswer(BaseModel):
    """Evidence-backed chat answer (README §8A.4 ``ChatAnswer``)."""

    answer: str = Field(..., description="evidence-backed answer to the user's question")
    scope: Optional[str] = Field(
        None, description="repo scope this answer was constrained to (set at runtime)"
    )
    reasoning: str = Field(
        "",
        description="brief trace of how the answer was derived from the sources, "
        "e.g. 'From the build guide I inferred the .NET 8 step; ...'",
    )
    citations: list[Citation] = Field(default_factory=list)
    confidence: float = Field(..., ge=0, le=1)
    needs_human_review: bool = Field(
        False, description="true when evidence is weak or missing (README §6.4)"
    )


class CuratorDraft(BaseModel):
    """Lean Curator drafting surface — what the LLM fills for a proposal.

    Provenance (proposal_id, evidence, verification, authoritative commit SHAs) is
    added deterministically by the graph, so it is intentionally absent here.
    """

    action: ProposalAction = Field(..., description="the single action to take")
    target_doc_id: Optional[str] = Field(None, description="doc the change applies to")
    draft: str = Field(..., description="proposed document body / change")
    citations: list[Citation] = Field(default_factory=list)
    diff: Optional[ProposalDiff] = Field(
        None, description="optional explicit before/after for the change"
    )
    confidence: float = Field(..., ge=0, le=1)
    risk_level: RiskLevel = "medium"
    conflicts_with: list[str] = Field(default_factory=list)


class GuardianReview(BaseModel):
    """Lean Guardian judgment surface — what the LLM fills when reviewing a draft."""

    recommendation: Recommendation = Field(..., description="approve | needs-review | reject")
    guardian_reasoning: str = Field("", description="brief justification for the call")
    confidence: float = Field(..., ge=0, le=1)
    risk_level: RiskLevel = "medium"
    conflicts_with: list[str] = Field(default_factory=list)
    uncertainty: Optional[str] = Field(None, description="explanation when confidence is low")


class AgentProposal(BaseModel):
    """The central proposal artifact handed to the backend and the diff panel.

    Aligned with README §8A.4. The Curator drafts (``action`` … ``conflicts_with``);
    the graph grounds provenance (``proposal_id``, ``source_doc_ids``, ``evidence``,
    commit SHAs, ``created_at``); the Guardian fills the judgment fields
    (``recommendation``, ``guardian_reasoning``, ``uncertainty``). ``verification``
    stays ``None`` until the P4 sandbox runs.
    """

    proposal_id: Optional[str] = Field(None, description="stable id, e.g. 'prop_ab12…'")
    action: ProposalAction
    target_doc_id: Optional[str] = Field(None, description="doc the change applies to")
    source_doc_ids: list[str] = Field(
        default_factory=list, description="docs that informed the change"
    )
    diff: Optional[ProposalDiff] = None
    draft: str = Field(..., description="proposed document body / change")
    citations: list[Citation] = Field(default_factory=list)
    evidence: list[Evidence] = Field(
        default_factory=list, description="grounded evidence items (system-populated)"
    )
    confidence: float = Field(..., ge=0, le=1)
    risk_level: RiskLevel = "medium"
    conflicts_with: list[str] = Field(default_factory=list)
    verification: Optional[Verification] = Field(
        None, description="sandbox result; None until P4 verification runs"
    )
    # Filled by the Guardian agent:
    recommendation: Optional[Recommendation] = None
    guardian_reasoning: Optional[str] = None
    uncertainty: Optional[str] = None
    # Provenance:
    proposed_by: str = Field("curator-agent", description="curator drafts; guardian judges")
    created_at: Optional[str] = Field(None, description="ISO-8601 creation timestamp")
