"""DocGuardian AI — FastAPI app.

Thin HTTP layer over the verified ingestion/retrieval logic. Implements the
contract documented in README Section 8B. Run with:

    uvicorn app.main:app --reload --port 8000

Interactive docs:
    Swagger UI -> /docs      ReDoc -> /redoc      OpenAPI JSON -> /openapi.json
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.embeddings.provider import get_embedding_provider
from app.ingestion.intake import TEXT_SUFFIXES, UnsupportedFormatError, ingest_content
from app.storage.queries import get_document, get_graph, list_doc_ids
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


class TreeNode(BaseModel):
    name: str
    type: str = Field(..., description="'folder' or 'file'")
    path: str
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
def add_document(req: IngestRequest) -> IngestResponse:
    suffix = ("." + req.name.rsplit(".", 1)[-1].lower()) if "." in req.name else ""
    if suffix not in TEXT_SUFFIXES:
        raise HTTPException(status_code=415, detail=f"{suffix!r} is not a supported text format")
    try:
        result = ingest_content(req.name, req.content, req.namespace)
    except UnsupportedFormatError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc
    return IngestResponse(docId=result["doc_id"], chunks=result["chunks"], edges=result["edges"])


@app.get(
    "/tree",
    response_model=list[TreeNode],
    tags=["navigation"],
    summary="File-system tree (left sidebar)",
)
def tree(namespace: str | None = Query(None, description="Filter to one namespace/repo")) -> list:
    return build_tree(list_doc_ids(namespace))


@app.get(
    "/graph",
    response_model=GraphResponse,
    tags=["navigation"],
    summary="Document graph (nodes + edges)",
)
def graph(repo: str | None = Query(None, description="shortName filter")) -> dict:
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

    try:
        return run_propose(req.instruction, repo=req.repo, k=req.k)
    except AzureNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

