"""LangGraph agent graphs (README Section 8.2).

Two compiled graphs share a single retrieval tool and the two LLM agents:

    /chat     :  retrieve -> curator(answer)                 -> ChatAnswer
    /propose  :  retrieve -> curator(draft) -> guardian      -> AgentProposal

The retrieve node calls the local vector store in-process (no HTTP hop); only
the curator and guardian nodes call Azure OpenAI.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional, TypedDict

from langgraph.graph import END, StateGraph

from app.agents.llm import get_chat_llm
from app.agents.schemas import (
    AgentProposal,
    ChatAnswer,
    Citation,
    CuratorDraft,
    Evidence,
    GuardianReview,
    ProposalDiff,
)
from app.embeddings.provider import get_embedding_provider
from app.storage.vectorstore import search as vector_search

# Retrieval similarity below this is treated as "weak" evidence (README §6.4).
WEAK_EVIDENCE_THRESHOLD = 0.45
# Self-reported proposal confidence below this forces human review (README §8A.4).
LOW_CONFIDENCE_THRESHOLD = 0.5
# Cap on grounded evidence items attached to a proposal.
MAX_EVIDENCE = 5


class AgentState(TypedDict, total=False):
    query: str
    repo: Optional[str]
    k: int
    instruction: str
    retrieved: list[dict[str, Any]]
    chat_answer: dict[str, Any]
    proposal: dict[str, Any]


# --------------------------------------------------------------------------- #
# Shared retrieval node (deterministic tool — no LLM)
# --------------------------------------------------------------------------- #
def retrieve_node(state: AgentState) -> AgentState:
    provider = get_embedding_provider()
    query = state["query"]
    rows = vector_search(provider.embed_one(query), top_k=state.get("k", 5), repo=state.get("repo"))
    return {"retrieved": rows}


def _format_sources(rows: list[dict]) -> str:
    blocks = []
    for i, r in enumerate(rows, 1):
        heading = " > ".join(r["heading_path"]) if r["heading_path"] else "(root)"
        blocks.append(
            f"[{i}] doc_id={r['doc_id']} lines={r['line_start']}-{r['line_end']} "
            f"score={r['score']:.3f}\n    heading: {heading}\n    {r['text'][:600]}"
        )
    return "\n\n".join(blocks) if blocks else "(no sources found)"


def _citations_from_rows(rows: list[dict]) -> list[Citation]:
    return [
        Citation(
            doc_id=r["doc_id"],
            line_range=[r["line_start"], r["line_end"]],
            commit_sha=r.get("commit_sha", ""),
            relevance=round(float(r["score"]), 4),
        )
        for r in rows
    ]


def _enrich_citations(citations: list[Citation], rows: list[dict]) -> list[Citation]:
    """Force commit_sha to the authoritative value from retrieved rows.

    commit_sha is provenance from our own data, never something the LLM should
    supply — models will otherwise hallucinate SHAs (e.g. "abc123"). We override
    it by doc_id; citations to docs that were not retrieved get an empty SHA.
    """
    sha_by_doc = {r["doc_id"]: r.get("commit_sha", "") for r in rows}
    for c in citations:
        c.commit_sha = sha_by_doc.get(c.doc_id, "")
    return citations


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _proposal_id() -> str:
    return "prop_" + uuid.uuid4().hex[:24]


def _evidence_from_rows(rows: list[dict]) -> list[Evidence]:
    """Grounded evidence built straight from retrieved rows (never the model)."""
    return [
        Evidence(
            chunk_id=r.get("chunk_id", ""),
            doc_id=r["doc_id"],
            commit_sha=r.get("commit_sha", ""),
            line_range=[r["line_start"], r["line_end"]],
            quote=r["text"][:240].strip(),
            relevance=round(float(r["score"]), 4),
        )
        for r in rows[:MAX_EVIDENCE]
    ]


def _unique_source_doc_ids(citations: list[Citation], target_doc_id: str | None) -> list[str]:
    ids: list[str] = []
    if target_doc_id:
        ids.append(target_doc_id)
    for c in citations:
        if c.doc_id not in ids:
            ids.append(c.doc_id)
    return ids


def _build_diff(
    draft: CuratorDraft, rows: list[dict], citations: list[Citation]
) -> ProposalDiff | None:
    """Prefer the model's explicit before/after; otherwise synthesize one."""
    if draft.diff and (draft.diff.before or draft.diff.after):
        diff = draft.diff
    else:
        before = rows[0]["text"][:280].strip() if rows else ""
        diff = ProposalDiff(before=before, after=draft.draft[:280].strip(), format="unified")
    if diff.line_range is None and citations:
        diff.line_range = citations[0].line_range
    return diff


def _finalize_proposal(proposal: dict[str, Any]) -> dict[str, Any]:
    """Deterministic evidence gate applied to EVERY proposal (README §6.3–6.4).

    Forces the explicit human-review path when a proposal is not backed by grounded
    evidence or is low-confidence, regardless of what the Guardian LLM returned.
    """
    citations = proposal.get("citations") or []
    grounded = [c for c in citations if c.get("commit_sha")]
    confidence = float(proposal.get("confidence") or 0.0)
    reasons: list[str] = []
    if not citations:
        reasons.append("no supporting citations")
    elif not grounded:
        reasons.append("citations are missing commit provenance")
    if confidence < LOW_CONFIDENCE_THRESHOLD:
        reasons.append(f"confidence {confidence:.2f} is below {LOW_CONFIDENCE_THRESHOLD}")
    if reasons:
        proposal["recommendation"] = "needs-review"
        note = "Forced human review: " + "; ".join(reasons) + "."
        existing = proposal.get("uncertainty")
        proposal["uncertainty"] = f"{existing} {note}".strip() if existing else note
    return proposal


def _ground_chat_citations(answer: ChatAnswer, rows: list[dict]) -> ChatAnswer:
    """Evidence gate for chat answers — the mirror of ``_finalize_proposal``.

    The model may only cite documents that were actually retrieved; citations to
    other doc_ids are dropped (it cannot introduce new sources). If it cited *only*
    non-retrieved docs, we fall back to the real retrieved evidence and flag the
    answer for human review. Low self-reported confidence also forces review.
    """
    retrieved_docs = {r["doc_id"] for r in rows}
    model_cited = list(answer.citations or [])
    grounded = [c for c in model_cited if c.doc_id in retrieved_docs]
    if not grounded:
        grounded = _citations_from_rows(rows[:3])
        if model_cited:  # it cited only non-retrieved docs -> do not trust the answer
            answer.needs_human_review = True
    answer.citations = _enrich_citations(grounded, rows)
    if answer.confidence < LOW_CONFIDENCE_THRESHOLD:
        answer.needs_human_review = True
    return answer


# --------------------------------------------------------------------------- #
# Curator agent — chat answer
# --------------------------------------------------------------------------- #
CURATOR_CHAT_SYSTEM = """You are the Curator agent for DocGuardian AI.
Answer the user's question USING ONLY the provided documentation sources.
Rules:
- Cite the doc_id and line range of every source you use.
- Give a confidence score in [0,1].
- If the sources do not actually answer the question, set needs_human_review to
  true and say you are not sure rather than guessing.
Be concise and engineering-accurate."""


def curator_chat_node(state: AgentState) -> AgentState:
    rows = state.get("retrieved", [])
    top_score = max((r["score"] for r in rows), default=0.0)

    # Short-circuit: no usable evidence -> explicit "needs human review" (no LLM cost).
    if not rows or top_score < WEAK_EVIDENCE_THRESHOLD:
        answer = ChatAnswer(
            answer="I'm not sure. The available documentation does not clearly answer "
            "this. This needs human review.",
            citations=_citations_from_rows(rows[:3]),
            confidence=round(float(top_score), 2),
            needs_human_review=True,
        )
        return {"chat_answer": answer.model_dump()}

    llm = get_chat_llm().with_structured_output(ChatAnswer)
    prompt = (
        f"{CURATOR_CHAT_SYSTEM}\n\n"
        f"QUESTION:\n{state['query']}\n\n"
        f"SOURCES:\n{_format_sources(rows)}"
    )
    answer: ChatAnswer = llm.invoke(prompt)
    # Evidence-or-silence: drop ungrounded citations, force review when unsupported.
    answer = _ground_chat_citations(answer, rows)
    return {"chat_answer": answer.model_dump()}


# --------------------------------------------------------------------------- #
# Curator agent — draft a proposal; Guardian agent — review it
# --------------------------------------------------------------------------- #
CURATOR_DRAFT_SYSTEM = """You are the Curator agent for DocGuardian AI.
Given an instruction and related documentation sources, decide the best action
(create / update / merge / link / deprecate / flag) and draft the change.
Cite the sources you relied on, set a confidence score, and flag any documents
this might conflict with. Only propose what the sources support."""

GUARDIAN_SYSTEM = """You are the Guardian agent for DocGuardian AI.
Review the Curator's proposed change for safety and correctness against the
evidence. Decide a recommendation: "approve" (well-supported, low risk),
"needs-review" (uncertain or risky), or "reject" (contradicted by sources).
Set a calibrated confidence and explain your reasoning briefly. When in doubt,
prefer needs-review over approve."""


def curator_draft_node(state: AgentState) -> AgentState:
    rows = state.get("retrieved", [])
    llm = get_chat_llm().with_structured_output(CuratorDraft)
    prompt = (
        f"{CURATOR_DRAFT_SYSTEM}\n\n"
        f"INSTRUCTION:\n{state.get('instruction', state['query'])}\n\n"
        f"SOURCES:\n{_format_sources(rows)}"
    )
    draft: CuratorDraft = llm.invoke(prompt)

    # Ground citations in real retrieved rows and force authoritative commit SHAs.
    citations = draft.citations or _citations_from_rows(rows[:3])
    citations = _enrich_citations(citations, rows)

    # Assemble the rich AgentProposal; provenance comes from our data, not the model.
    proposal = AgentProposal(
        proposal_id=_proposal_id(),
        action=draft.action,
        target_doc_id=draft.target_doc_id,
        source_doc_ids=_unique_source_doc_ids(citations, draft.target_doc_id),
        diff=_build_diff(draft, rows, citations),
        draft=draft.draft,
        citations=citations,
        evidence=_evidence_from_rows(rows),
        confidence=draft.confidence,
        risk_level=draft.risk_level,
        conflicts_with=draft.conflicts_with,
        verification=None,  # P4 sandbox pending
        proposed_by="curator-agent",
        created_at=_utcnow_iso(),
    )
    return {"proposal": proposal.model_dump()}


def guardian_node(state: AgentState) -> AgentState:
    curator_proposal = state["proposal"]
    rows = state.get("retrieved", [])
    llm = get_chat_llm(temperature=0.0).with_structured_output(GuardianReview)
    prompt = (
        f"{GUARDIAN_SYSTEM}\n\n"
        f"PROPOSED CHANGE (JSON):\n{curator_proposal}\n\n"
        f"EVIDENCE:\n{_format_sources(rows)}\n\n"
        "Judge the change: set recommendation, guardian_reasoning, a calibrated "
        "confidence, risk_level, and any uncertainty."
    )
    review: GuardianReview = llm.invoke(prompt)

    # The Guardian only contributes its JUDGMENT. Preserve the Curator's draft and
    # evidence-grounded citations (the LLM may otherwise hallucinate, e.g. commit SHAs).
    merged = {
        **curator_proposal,
        "recommendation": review.recommendation or "needs-review",
        "guardian_reasoning": review.guardian_reasoning,
        "confidence": review.confidence,
        "risk_level": review.risk_level,
        "conflicts_with": review.conflicts_with or curator_proposal.get("conflicts_with", []),
        "uncertainty": review.uncertainty,
    }
    # Final deterministic evidence gate — evidence-or-review, no matter what the LLM said.
    return {"proposal": _finalize_proposal(merged)}


def _route_after_retrieve(state: AgentState) -> str:
    """Route to the Curator only when retrieval produced usable evidence."""
    rows = state.get("retrieved", [])
    top = max((r["score"] for r in rows), default=0.0)
    return "curator" if rows and top >= WEAK_EVIDENCE_THRESHOLD else "no_evidence"


def no_evidence_proposal_node(state: AgentState) -> AgentState:
    """Short-circuit weak/empty retrieval into a needs-review proposal — no LLM cost."""
    rows = state.get("retrieved", [])
    top = round(float(max((r["score"] for r in rows), default=0.0)), 2)
    proposal = AgentProposal(
        proposal_id=_proposal_id(),
        action="flag",
        target_doc_id=None,
        source_doc_ids=[],
        diff=None,
        draft=(
            "No sufficiently relevant documentation was found to support this change. "
            "Flagging for human review instead of guessing."
        ),
        citations=_citations_from_rows(rows[:3]),
        evidence=_evidence_from_rows(rows),
        confidence=top,
        risk_level="high",
        conflicts_with=[],
        verification=None,
        recommendation="needs-review",
        uncertainty=(
            "Insufficient retrieval evidence; the proposal was short-circuited before "
            "any LLM call (no Curator/Guardian cost)."
        ),
        proposed_by="orchestrator",
        created_at=_utcnow_iso(),
    )
    return {"proposal": proposal.model_dump()}


# --------------------------------------------------------------------------- #
# Compiled graphs
# --------------------------------------------------------------------------- #
def _build_chat_graph():
    g = StateGraph(AgentState)
    g.add_node("retrieve", retrieve_node)
    g.add_node("curator", curator_chat_node)
    g.set_entry_point("retrieve")
    g.add_edge("retrieve", "curator")
    g.add_edge("curator", END)
    return g.compile()


def _build_propose_graph():
    g = StateGraph(AgentState)
    g.add_node("retrieve", retrieve_node)
    g.add_node("curator", curator_draft_node)
    g.add_node("guardian", guardian_node)
    g.add_node("no_evidence", no_evidence_proposal_node)
    g.set_entry_point("retrieve")
    g.add_conditional_edges(
        "retrieve",
        _route_after_retrieve,
        {"curator": "curator", "no_evidence": "no_evidence"},
    )
    g.add_edge("curator", "guardian")
    g.add_edge("guardian", END)
    g.add_edge("no_evidence", END)
    return g.compile()


_chat_graph = None
_propose_graph = None


def run_chat(query: str, repo: str | None = None, k: int = 5) -> dict:
    global _chat_graph
    if _chat_graph is None:
        _chat_graph = _build_chat_graph()
    result = _chat_graph.invoke({"query": query, "repo": repo, "k": k})
    answer = result["chat_answer"]
    answer["scope"] = repo or "all"
    return answer


def run_propose(instruction: str, repo: str | None = None, k: int = 6) -> dict:
    global _propose_graph
    if _propose_graph is None:
        _propose_graph = _build_propose_graph()
    result = _propose_graph.invoke(
        {"query": instruction, "instruction": instruction, "repo": repo, "k": k}
    )
    return result["proposal"]
