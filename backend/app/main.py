"""DocGuardian AI — FastAPI app.

Thin HTTP layer over the verified ingestion/retrieval logic. Implements the
contract documented in README Section 8B. Run with:

    uvicorn app.main:app --reload --port 8000

Interactive docs:
    Swagger UI -> /docs      ReDoc -> /redoc      OpenAPI JSON -> /openapi.json
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.embeddings.provider import get_embedding_provider
from app.ingestion.intake import (
    TEXT_SUFFIXES,
    IngestError,
    UnsupportedFormatError,
    ingest_content,
)
from app.storage.queries import get_doc_summaries, get_document, get_graph, list_doc_ids
from app.storage.vectorstore import search as vector_search
from app.tree import build_tree

API_DESCRIPTION = """
Backend API for **DocGuardian AI**.

This is the contract the LangChain retrieval/agent pipeline builds on
(see README Section 8B). The backend owns **retrieval + data**; the agent
pipeline owns **reasoning**.

- `GET /search` is the LangChain retriever target (pgvector cosine search).
- `POST /documents` is the drop-off intake (upload/paste).
- `GET /tree` / `GET /graph` power the left sidebar and the graph view.
- `POST /chat` / `POST /propose` run the LangGraph Curator/Guardian agents.
"""

tags_metadata = [
    {"name": "system", "description": "Health and runtime info."},
    {"name": "retrieval", "description": "Semantic search over embedded chunks."},
    {"name": "intake", "description": "Add user documents (drop-off)."},
    {"name": "navigation", "description": "File tree and document graph."},
    {"name": "agents", "description": "LangGraph Curator/Guardian reasoning (Azure OpenAI)."},
    {"name": "governance", "description": "Proposals, approval, provenance, metrics."},
    {"name": "verification", "description": "Containerized verification sandbox."},
]
app = FastAPI(
    title="DocGuardian AI API",
    version="0.1.0",
    description=API_DESCRIPTION,
    openapi_tags=tags_metadata,
)

# Allow the Vite dev frontend to call the API during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------------------------------- #
# Request / response models (drive the Swagger schemas)
# --------------------------------------------------------------------------- #
class HealthResponse(BaseModel):
    status: str = "ok"
    embeddingProvider: str = Field(..., examples=["local:BAAI/bge-small-en-v1.5"])
    dim: int = Field(..., examples=[384])


class Match(BaseModel):
    chunkId: str
    docId: str
    repo: str
    headingPath: list[str]
    text: str
    lineRange: tuple[int, int]
    commitSha: str
    score: float = Field(..., description="Cosine similarity in [0,1]; higher = closer")


class SearchResponse(BaseModel):
    query: str
    matches: list[Match]


class IngestRequest(BaseModel):
    name: str = Field(..., examples=["redis-migration.md"])
    content: str = Field(..., examples=["# Redis Migration\n\nHow to migrate ..."])
    namespace: str = Field("user", description="Top-level namespace for the doc")


class IngestResponse(BaseModel):
    docId: str
    chunks: int
    edges: int
    conflictEdges: int = Field(0, description="duplicate/conflict edges found on intake")
    summary: str | None = Field(None, description="AI/extractive one-line description")


class TreeNode(BaseModel):
    name: str
    type: str = Field(..., description="'folder' or 'file'")
    path: str
    summary: str | None = Field(None, description="one-line description for file nodes")
    children: list["TreeNode"] | None = None


class GraphNode(BaseModel):
    id: str
    label: str
    health: str
    size: float
    accessible: bool
    repo: str


class GraphEdgeDTO(BaseModel):
    from_: str = Field(..., alias="from")
    to: str
    type: str
    weight: float | None = None

    model_config = {"populate_by_name": True}


class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdgeDTO]


class ChunkDetail(BaseModel):
    chunkId: str
    headingPath: list[str]
    lineRange: tuple[int | None, int | None]
    text: str


class DocumentResponse(BaseModel):
    docId: str
    repo: str
    path: str
    commitSha: str | None = None
    commitDate: str | None = None
    chunks: list[ChunkDetail]


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #
@app.get("/health", response_model=HealthResponse, tags=["system"], summary="Liveness probe")
def health() -> HealthResponse:
    provider = get_embedding_provider()
    return HealthResponse(status="ok", embeddingProvider=provider.name, dim=provider.dim)


@app.get(
    "/search",
    response_model=SearchResponse,
    tags=["retrieval"],
    summary="Semantic search (LangChain retriever target)",
    description="Cosine-similarity search over embedded chunks in pgvector.",
)
def search(
    q: str = Query(..., description="Natural-language query"),
    repo: str | None = Query(
        None, description="shortName filter: garnet | playwright | onnxruntime | vscode | user"
    ),
    k: int = Query(5, ge=1, le=50, description="Number of results"),
) -> SearchResponse:
    provider = get_embedding_provider()
    query_vec = provider.embed_one(q)
    rows = vector_search(query_vec, top_k=k, repo=repo)
    matches = [
        Match(
            chunkId=r["chunk_id"],
            docId=r["doc_id"],
            repo=r["repo"],
            headingPath=r["heading_path"] or [],
            text=r["text"],
            lineRange=(r["line_start"], r["line_end"]),
            commitSha=r["commit_sha"],
            score=round(float(r["score"]), 4),
        )
        for r in rows
    ]
    return SearchResponse(query=q, matches=matches)


@app.post(
    "/documents",
    response_model=IngestResponse,
    status_code=201,
    tags=["intake"],
    summary="Add a document (drop-off intake)",
    description="Chunks, embeds, and stores user content. Text formats only; "
    "binary formats (PDF/DOCX) return 415.",
)
def add_document(
    req: IngestRequest,
    background: bool = Query(
        False, description="if true, return 202 + a jobId and ingest in the background"
    ),
):
    suffix = ("." + req.name.rsplit(".", 1)[-1].lower()) if "." in req.name else ""
    if suffix not in TEXT_SUFFIXES:
        raise HTTPException(status_code=415, detail=f"{suffix!r} is not a supported text format")

    # Async path: don't make the user wait for embed + summarize + conflict scan.
    if background:
        import threading

        from fastapi.responses import JSONResponse

        from app.ingestion.intake import make_raw_document
        from app.services import jobs

        doc_id = make_raw_document(req.name, req.content, req.namespace).doc_id
        job = jobs.create_job(doc_id)
        threading.Thread(
            target=_run_ingest_job,
            args=(job["jobId"], req.name, req.content, req.namespace),
            daemon=True,
        ).start()
        return JSONResponse(status_code=202, content=job)

    try:
        result = ingest_content(req.name, req.content, req.namespace)
    except UnsupportedFormatError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc
    except IngestError as exc:
        # Whole ingest rolled back — nothing was persisted.
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return IngestResponse(
        docId=result["doc_id"],
        chunks=result["chunks"],
        edges=result["edges"],
        conflictEdges=result.get("conflictEdges", 0),
        summary=result.get("summary"),
    )


def _run_ingest_job(job_id: str, name: str, content: str, namespace: str) -> None:
    """Background worker: run the atomic ingest and broadcast its outcome.

    The ingest itself is all-or-nothing; this only reports progress. A failure
    leaves nothing persisted and emits an ``ingest`` failed event.
    """
    from app.services import events, jobs

    jobs.set_status(job_id, "processing")
    events.publish("ingest", jobId=job_id, status="processing")
    try:
        result = ingest_content(name, content, namespace)
        jobs.set_status(job_id, "succeeded", result=result)
        events.publish(
            "ingest", jobId=job_id, status="ready", docId=result["doc_id"]
        )
        events.publish("graph", docId=result["doc_id"])
    except Exception as exc:  # IngestError or anything else -> nothing persisted
        jobs.set_status(job_id, "failed", error=str(exc))
        events.publish("ingest", jobId=job_id, status="failed", error=str(exc))


@app.get(
    "/jobs/{job_id}",
    tags=["intake"],
    summary="Status of a background ingest job",
)
def job_status(job_id: str) -> dict:
    from app.services import jobs

    job = jobs.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"job not found: {job_id}")
    return job


@app.get(
    "/tree",
    response_model=list[TreeNode],
    tags=["navigation"],
    summary="File-system tree (left sidebar)",
)
def tree(namespace: str | None = Query(None, description="Filter to one namespace/repo")) -> list:
    return build_tree(list_doc_ids(namespace), get_doc_summaries(namespace))


@app.get(
    "/graph",
    response_model=GraphResponse,
    tags=["navigation"],
    summary="Document graph (nodes + edges)",
)
def graph(repo: str | None = Query(None, description="shortName filter")) -> dict:
    # Governed graph: real derived health/importance + ACL filtering. Falls back
    # to the plain query if the governance store is unavailable.
    try:
        from app.governance.store import get_governed_graph

        return get_governed_graph(repo)
    except Exception:  # pragma: no cover - fallback keeps the graph alive
        return get_graph(repo)


@app.get(
    "/documents/{doc_id:path}",
    response_model=DocumentResponse,
    tags=["navigation"],
    summary="Single document with its chunks",
)
def document(doc_id: str) -> dict:
    doc = get_document(doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail=f"document not found: {doc_id}")
    return doc


# --------------------------------------------------------------------------- #
# Agent endpoints (LangGraph + Azure OpenAI)
# --------------------------------------------------------------------------- #
class ChatRequest(BaseModel):
    query: str = Field(..., examples=["how do I build garnet from source?"])
    repo: str | None = Field(None, description="shortName scope (e.g. garnet)")
    k: int = Field(5, ge=1, le=20)


class ProposeRequest(BaseModel):
    instruction: str = Field(..., examples=["Unify the build instructions into one canonical doc"])
    repo: str | None = Field(None, description="shortName scope")
    k: int = Field(6, ge=1, le=20)


@app.post(
    "/chat",
    tags=["agents"],
    summary="Curator agent — evidence-backed answer (LangGraph)",
    description="retrieve -> Curator. Returns an answer with citations and confidence. "
    "Requires Azure OpenAI (503 if not configured).",
)
def chat(req: ChatRequest) -> dict:
    from app.agents.graph import run_chat
    from app.agents.llm import AzureNotConfiguredError

    try:
        return run_chat(req.query, repo=req.repo, k=req.k)
    except AzureNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post(
    "/propose",
    tags=["agents"],
    summary="Curator + Guardian — proposed change (LangGraph)",
    description="retrieve -> Curator (draft) -> Guardian (review). Returns an "
    "AgentProposal. Requires Azure OpenAI (503 if not configured).",
)
def propose(req: ProposeRequest) -> dict:
    from app.agents.graph import run_propose
    from app.agents.llm import AzureNotConfiguredError
    from app.governance.store import save_proposal

    try:
        proposal = run_propose(req.instruction, repo=req.repo, k=req.k)
    except AzureNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    # Persist so the proposal can be looked up, approved, and audited.
    try:
        proposal = save_proposal(proposal)
    except Exception:  # pragma: no cover - persistence is best-effort for the agent path
        pass
    return proposal


# --------------------------------------------------------------------------- #
# Governance endpoints (proposals, approval, provenance, metrics)
# --------------------------------------------------------------------------- #
class ApproveRequest(BaseModel):
    approver: str = Field(..., examples=["alice@example.com"])
    roles: list[str] | None = Field(None, description="ACL grant tokens the approver holds")
    reason: str = Field("", description="why this change is approved")
    force: bool = Field(False, description="apply even if staged-approval would trigger")


@app.get(
    "/proposals/{proposal_id}",
    tags=["governance"],
    summary="Fetch a persisted proposal + approval/provenance context",
)
def get_proposal(proposal_id: str) -> dict:
    from app.governance.store import get_proposal_dto

    dto = get_proposal_dto(proposal_id)
    if dto is None:
        raise HTTPException(status_code=404, detail=f"proposal not found: {proposal_id}")
    return dto


@app.post(
    "/proposals/{proposal_id}/approve",
    tags=["governance"],
    summary="Approve + apply a proposal (writes provenance)",
)
def approve(proposal_id: str, req: ApproveRequest) -> dict:
    from app.governance.service import GovernanceError, StagedApprovalRequired, approve_proposal

    try:
        return approve_proposal(
            proposal_id, req.approver, req.roles, req.reason, force=req.force
        )
    except StagedApprovalRequired as exc:
        raise HTTPException(status_code=202, detail=str(exc)) from exc
    except GovernanceError as exc:
        raise HTTPException(status_code=exc.status, detail=str(exc)) from exc


@app.post(
    "/proposals/{proposal_id}/rollback",
    tags=["governance"],
    summary="Roll back an applied proposal (append-only provenance)",
)
def rollback(proposal_id: str, req: ApproveRequest) -> dict:
    from app.governance.service import GovernanceError, rollback_proposal

    try:
        return rollback_proposal(proposal_id, req.approver, req.roles, req.reason)
    except GovernanceError as exc:
        raise HTTPException(status_code=exc.status, detail=str(exc)) from exc


@app.get(
    "/provenance/{doc_id:path}",
    tags=["governance"],
    summary="Append-only provenance history for a document",
    description="Audit trail for a document. Uses a /provenance/ prefix so the "
    "catch-all /documents/{id} route does not shadow it.",
)
def document_provenance(doc_id: str) -> list[dict]:
    from app.governance.store import list_provenance

    return list_provenance(doc_id=doc_id)


@app.get(
    "/metrics",
    tags=["governance"],
    summary="Governance dashboard counters (MetricsDTO)",
)
def metrics() -> dict:
    from app.governance.store import get_metrics_dto

    return get_metrics_dto()


# --------------------------------------------------------------------------- #
# Ingest refresh (re-process an existing document, stamp verified)
# --------------------------------------------------------------------------- #
class RefreshRequest(BaseModel):
    content: str | None = Field(
        None,
        description="New content to replace the document with. "
        "If omitted the existing chunks are re-embedded + conflict-rescanned.",
    )


class RefreshResponse(BaseModel):
    docId: str
    chunks: int
    conflictEdges: int
    health: str
    stamped: bool = Field(..., description="True if last_verified_sha was updated")


@app.post(
    "/ingest/refresh/{doc_id:path}",
    response_model=RefreshResponse,
    tags=["intake"],
    summary="Re-process a document and stamp it verified",
    description=(
        "Re-runs chunking, embedding, and duplicate/conflict detection for an "
        "existing document. If `content` is supplied the document is replaced; "
        "otherwise the text is reconstructed from its stored chunks. "
        "On success `last_verified_sha` is updated to the document's current "
        "`commit_sha` and graph/metrics WebSocket events are emitted."
    ),
)
def refresh_document(doc_id: str, req: RefreshRequest | None = None) -> dict:
    from app.governance.store import get_document_meta, stamp_verified
    from app.services import events
    from app.storage.db import get_conn
    from app.processing.conflicts import detect_conflicts_for_doc

    meta = get_document_meta(doc_id)
    if meta is None:
        raise HTTPException(status_code=404, detail=f"document not found: {doc_id}")

    new_content = req.content if req else None

    if new_content:
        # Full re-ingest with new content (atomic upsert).
        from app.ingestion.intake import ingest_content
        try:
            result = ingest_content(
                meta["path"], new_content, namespace=meta["repo"]
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        chunks_count = result["chunks"]
        conflict_count = result.get("conflictEdges", 0)
    else:
        # Re-run conflict detection on the existing chunks (no content change).
        try:
            with get_conn() as conn:
                conflict_count = detect_conflicts_for_doc(doc_id, conn=conn)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        # Count existing chunks.
        from psycopg.rows import dict_row
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM chunks WHERE doc_id = %s", (doc_id,))
                chunks_count = cur.fetchone()[0]

    # Stamp verified at the current commit SHA.
    commit_sha = meta.get("commit_sha")
    stamp_verified(doc_id, commit_sha)

    # Derive the new health for the response.
    from app.governance.store import get_governed_graph
    try:
        graph_data = get_governed_graph()
        node = next((n for n in graph_data["nodes"] if n["id"] == doc_id), None)
        health = node["health"] if node else "green"
    except Exception:
        health = "green"

    events.publish("graph", docId=doc_id)
    events.publish("metrics")

    return {
        "docId": doc_id,
        "chunks": chunks_count,
        "conflictEdges": conflict_count,
        "health": health,
        "stamped": True,
    }


# --------------------------------------------------------------------------- #
# Verification sandbox (real containerized execution)
# --------------------------------------------------------------------------- #
class VerifyRequest(BaseModel):
    command: str = Field(..., examples=["python -c 'print(1+1)'"])
    repo: str | None = None
    commitSha: str | None = None
    image: str = Field("python:3.11-slim")
    timeoutMs: int = Field(30_000, ge=1, le=120_000)


@app.post(
    "/verify",
    tags=["verification"],
    summary="Run a verification command in an isolated container",
)
def verify(req: VerifyRequest) -> dict:
    from app.services.verification import SandboxRequest, run_verification

    result = run_verification(
        SandboxRequest(
            command=req.command,
            repo=req.repo,
            commit_sha=req.commitSha,
            image=req.image,
            timeout_ms=req.timeoutMs,
        )
    )
    return result.model_dump()


# --------------------------------------------------------------------------- #
# WebSocket live dashboard (README §8B WS /stream)
# --------------------------------------------------------------------------- #
@app.websocket("/stream")
async def stream(ws: WebSocket) -> None:
    import asyncio

    from app.services import events

    await ws.accept()
    queue = events.subscribe()
    await ws.send_json({"type": "connected"})
    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=15)
                await ws.send_json(event)
            except asyncio.TimeoutError:
                await ws.send_json({"type": "heartbeat"})
    except WebSocketDisconnect:
        pass
    finally:
        events.unsubscribe(queue)

