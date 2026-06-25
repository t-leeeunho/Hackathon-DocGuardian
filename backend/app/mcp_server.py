"""DocGuardian MCP server.

Exposes DocGuardian's documentation corpus and its evidence-backed **Curator agent**
to MCP clients such as the GitHub Copilot CLI / IDE. The server is a thin adapter
over the running DocGuardian REST API, so an MCP client gets the *same* grounded,
cited answers the app produces — "evidence or silence". This lets another coding
agent (Copilot) ask your team's wiki/docs a question and get a trustworthy answer
with the exact source docs, line ranges, and commit SHAs it relied on.

Tools exposed:
  - ask_docs(question, repo?)        -> Curator agent: grounded answer + citations
  - search_docs(query, repo?, k?)    -> raw semantic search over indexed chunks
  - get_document(doc_id)             -> the AI-curated document text + provenance
  - list_sources(namespace?)         -> the documentation library (tree of files)

Run (stdio transport — what MCP clients spawn):
    python -m app.mcp_server

Point it at a non-default backend with DOCGUARDIAN_API_URL (default
http://localhost:8000). The DocGuardian API must be running.
"""

from __future__ import annotations

import os

import httpx
from mcp.server.fastmcp import FastMCP

API_BASE = os.getenv("DOCGUARDIAN_API_URL", "http://localhost:8000").rstrip("/")
TIMEOUT = float(os.getenv("DOCGUARDIAN_MCP_TIMEOUT", "90"))

mcp = FastMCP("docguardian")


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=API_BASE, timeout=TIMEOUT)


def _sha(value: str | None, n: int = 7) -> str:
    return (value or "")[:n]


def _unreachable(exc: Exception) -> str:
    return (
        f"⚠ Could not reach the DocGuardian API at {API_BASE} ({type(exc).__name__}: {exc}).\n"
        "Start the backend first:  cd backend && uvicorn app.main:app --port 8000\n"
        "or set DOCGUARDIAN_API_URL to point at a running instance."
    )


def _pct(value) -> str:
    try:
        return f"{round(float(value) * 100)}%"
    except (TypeError, ValueError):
        return "n/a"


def _format_citations(citations: list[dict]) -> str:
    """Render /chat citations (snake_case) as a numbered, evidence-backed list."""
    if not citations:
        return "_(no supporting sources)_"
    lines: list[str] = []
    for i, c in enumerate(citations, 1):
        doc = c.get("doc_id", "?")
        lr = c.get("line_range") or []
        loc = f"lines {lr[0]}-{lr[1]}" if len(lr) == 2 else ""
        sha = _sha(c.get("commit_sha"))
        rel = _pct(c.get("relevance"))
        head = f"[{i}] {doc}"
        meta = " · ".join(p for p in (loc, f"commit {sha}" if sha else "", f"relevance {rel}") if p)
        snippet = (c.get("text") or "").strip().replace("\n", " ")
        if len(snippet) > 240:
            snippet = snippet[:239] + "…"
        block = f"{head}\n    {meta}" if meta else head
        if snippet:
            block += f'\n    "{snippet}"'
        lines.append(block)
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Tools
# --------------------------------------------------------------------------- #
@mcp.tool()
async def ask_docs(question: str, repo: str | None = None) -> str:
    """Ask DocGuardian's Curator agent a question about the team's documentation / wiki.

    Use this whenever you need authoritative information about THIS organization's
    internal docs — build/setup steps, configuration, APIs, architecture, runbooks —
    instead of guessing. The answer is EVIDENCE-BACKED: it comes with the exact source
    documents, line ranges, and commit SHAs it relied on, plus a confidence score. If
    the documentation does not actually support an answer, DocGuardian says so (flags
    it for human review) rather than inventing one, so the citations can be trusted.

    Args:
        question: A natural-language question about the documentation.
        repo: Optional short name to scope the search to one source (e.g. "garnet").
    """
    payload = {"query": question}
    if repo:
        payload["repo"] = repo
    try:
        async with _client() as c:
            r = await c.post("/chat", json=payload)
    except Exception as exc:  # noqa: BLE001 - report any transport error to the client
        return _unreachable(exc)

    if r.status_code == 503:
        return (
            "⚠ DocGuardian's Curator agent is unavailable: the chat model is not "
            "configured on the server (set AZURE_OPENAI_* or CHAT_PROVIDER=fake)."
        )
    if r.status_code >= 400:
        return f"⚠ DocGuardian returned HTTP {r.status_code}: {r.text[:300]}"

    data = r.json()
    answer = (data.get("answer") or "").strip() or "_(no answer)_"
    parts = [answer, ""]
    meta = f"Confidence: {_pct(data.get('confidence'))}"
    if data.get("scope"):
        meta += f"  ·  Scope: {data['scope']}"
    parts.append(meta)
    if data.get("needs_human_review"):
        parts.append(
            "⚠ Needs human review — the evidence was weak or missing, so treat this "
            "answer with caution and verify with a person."
        )
    if data.get("reasoning"):
        parts.append(f"\nReasoning: {data['reasoning']}")
    parts.append("\nSources:")
    parts.append(_format_citations(data.get("citations") or []))
    return "\n".join(parts)


@mcp.tool()
async def search_docs(query: str, repo: str | None = None, k: int = 5) -> str:
    """Semantic search over DocGuardian's indexed documentation chunks.

    Returns the most relevant snippets with their source document, heading, line
    range, commit SHA, and similarity score — the raw evidence, without an agent
    summarizing it. Use this when you want to read the underlying source passages
    yourself; use `ask_docs` when you want a synthesized, cited answer.

    Args:
        query: What to search for.
        repo: Optional short name to scope to one source (e.g. "garnet").
        k: Number of chunks to return (1-20).
    """
    params = {"q": query, "k": max(1, min(20, k))}
    if repo:
        params["repo"] = repo
    try:
        async with _client() as c:
            r = await c.get("/search", params=params)
    except Exception as exc:  # noqa: BLE001
        return _unreachable(exc)
    if r.status_code >= 400:
        return f"⚠ DocGuardian returned HTTP {r.status_code}: {r.text[:300]}"

    matches = (r.json() or {}).get("matches") or []
    if not matches:
        return f'No documentation matched "{query}".'

    out = [f'Top {len(matches)} matches for "{query}":', ""]
    for i, m in enumerate(matches, 1):
        heading = " › ".join(m.get("headingPath") or []) or "(root)"
        lr = m.get("lineRange") or []
        loc = f"lines {lr[0]}-{lr[1]}" if len(lr) == 2 else ""
        sha = _sha(m.get("commitSha"))
        score = _pct(m.get("score"))
        snippet = (m.get("text") or "").strip().replace("\n", " ")
        if len(snippet) > 280:
            snippet = snippet[:279] + "…"
        meta = " · ".join(p for p in (loc, f"commit {sha}" if sha else "", f"score {score}") if p)
        out.append(f"[{i}] {m.get('docId', '?')}  ({heading})")
        if meta:
            out.append(f"    {meta}")
        out.append(f"    {snippet}")
        out.append("")
    return "\n".join(out).rstrip()


@mcp.tool()
async def get_document(doc_id: str) -> str:
    """Fetch the full AI-curated text of one document by its doc_id.

    DocGuardian shows the Librarian's agent-friendly rewrite by default; this returns
    that curated content (reconstructed from the indexed chunks) plus provenance
    (commit, and — for user drop-offs — where the original was filed). Get a doc_id
    from `search_docs`, `ask_docs` citations, or `list_sources`.

    Args:
        doc_id: The document id / path, e.g. "garnet/website/docs/getting-started/build.md".
    """
    try:
        async with _client() as c:
            r = await c.get(f"/documents/{doc_id}")
    except Exception as exc:  # noqa: BLE001
        return _unreachable(exc)
    if r.status_code == 404:
        return f"No document found with id {doc_id!r}."
    if r.status_code >= 400:
        return f"⚠ DocGuardian returned HTTP {r.status_code}: {r.text[:300]}"

    doc = r.json()
    header = [f"# {doc.get('title') or doc_id}", ""]
    prov = f"doc_id: {doc.get('docId', doc_id)}  ·  commit: {_sha(doc.get('commitSha')) or 'n/a'}"
    if doc.get("aiRewritten"):
        prov += "  ·  AI-curated rewrite"
        if doc.get("originalPath"):
            prov += f" (original dropped at {doc['originalPath']})"
    header.append(prov)
    body = "\n\n".join((c.get("text") or "") for c in (doc.get("chunks") or [])).strip()
    return "\n".join(header) + "\n\n" + (body or "_(no content)_")


@mcp.tool()
async def list_sources(namespace: str | None = None) -> str:
    """List the documentation files available in DocGuardian (the library tree).

    Returns each document's id/path and one-line description, so you know what can be
    asked about. Optionally restrict to one namespace/repo (e.g. "garnet" or "user").
    """
    params = {"namespace": namespace} if namespace else None
    try:
        async with _client() as c:
            r = await c.get("/tree", params=params)
    except Exception as exc:  # noqa: BLE001
        return _unreachable(exc)
    if r.status_code >= 400:
        return f"⚠ DocGuardian returned HTTP {r.status_code}: {r.text[:300]}"

    files: list[tuple[str, str]] = []

    def _walk(nodes: list[dict]) -> None:
        for n in nodes:
            if n.get("type") == "folder":
                _walk(n.get("children") or [])
            else:
                files.append((n.get("path", "?"), (n.get("summary") or "").strip()))

    _walk(r.json() or [])
    if not files:
        return "No documents are indexed yet."
    files.sort()
    shown = files[:120]
    lines = [f"{len(files)} document(s) indexed" + (f" (showing {len(shown)})" if len(files) > len(shown) else "") + ":", ""]
    for path, summary in shown:
        lines.append(f"- {path}" + (f" — {summary}" if summary else ""))
    return "\n".join(lines)


def main() -> None:
    transport = os.getenv("DOCGUARDIAN_MCP_TRANSPORT", "stdio")
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
