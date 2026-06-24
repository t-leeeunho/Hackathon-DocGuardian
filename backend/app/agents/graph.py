"""LangGraph agent graphs (README Section 8.2).

Two compiled graphs share a single retrieval tool and the two LLM agents:

    /chat     :  retrieve -> curator(answer)                 -> ChatAnswer
    /propose  :  retrieve -> curator(draft) -> guardian      -> AgentProposal

The retrieve node calls the local vector store in-process (no HTTP hop); only
the curator and guardian nodes call Azure OpenAI.
"""

from __future__ import annotations

from typing import Any, Optional, TypedDict

from langgraph.graph import END, StateGraph

from app.agents.llm import get_chat_llm
from app.agents.schemas import AgentProposal, ChatAnswer, Citation
from app.embeddings.provider import get_embedding_provider
from app.storage.vectorstore import search as vector_search

# Evidence below this similarity is treated as "weak" (README 6.4).
WEAK_EVIDENCE_THRESHOLD = 0.45


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
            answer="I'm DocGuardian's documentation assistant, so I answer only from the "
            "indexed docs — and I couldn't find evidence for that. Try asking about a "
            "specific project's setup, build, configuration, or APIs (e.g. \"How do I "
            "build Garnet from source?\").",
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
    # Guarantee citations are grounded in real retrieved rows.
    if not answer.citations:
        answer.citations = _citations_from_rows(rows[:3])
    answer.citations = _enrich_citations(answer.citations, rows)
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
    llm = get_chat_llm().with_structured_output(AgentProposal)
    prompt = (
        f"{CURATOR_DRAFT_SYSTEM}\n\n"
        f"INSTRUCTION:\n{state.get('instruction', state['query'])}\n\n"
        f"SOURCES:\n{_format_sources(rows)}"
    )
    proposal: AgentProposal = llm.invoke(prompt)
    if not proposal.citations:
        proposal.citations = _citations_from_rows(rows[:3])
    proposal.citations = _enrich_citations(proposal.citations, rows)
    return {"proposal": proposal.model_dump()}


def guardian_node(state: AgentState) -> AgentState:
    curator_proposal = state["proposal"]
    rows = state.get("retrieved", [])
    llm = get_chat_llm(temperature=0.0).with_structured_output(AgentProposal)
    prompt = (
        f"{GUARDIAN_SYSTEM}\n\n"
        f"PROPOSED CHANGE (JSON):\n{curator_proposal}\n\n"
        f"EVIDENCE:\n{_format_sources(rows)}\n\n"
        "Return the same proposal with recommendation, guardian_reasoning, and a "
        "calibrated confidence filled in."
    )
    reviewed: AgentProposal = llm.invoke(prompt)

    # The Guardian only contributes its JUDGMENT. Preserve the Curator's draft and
    # evidence-grounded citations (the LLM may otherwise hallucinate, e.g. commit SHAs).
    merged = {
        **curator_proposal,
        "recommendation": reviewed.recommendation or "needs-review",
        "guardian_reasoning": reviewed.guardian_reasoning,
        "confidence": reviewed.confidence,
        "risk_level": reviewed.risk_level,
        "conflicts_with": reviewed.conflicts_with or curator_proposal.get("conflicts_with", []),
        "uncertainty": reviewed.uncertainty,
    }
    return {"proposal": merged}


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
    g.set_entry_point("retrieve")
    g.add_edge("retrieve", "curator")
    g.add_edge("curator", "guardian")
    g.add_edge("guardian", END)
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
