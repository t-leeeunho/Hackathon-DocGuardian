"""Offline tests for the DocGuardian MCP server surface.

These don't spawn the stdio server or hit the API — they verify the tool surface
and the evidence-formatting helpers, so the MCP contract can't silently drift.
"""

from __future__ import annotations

from app.mcp_server import _format_citations, _unreachable, mcp


def test_mcp_tools_registered():
    names = sorted(t.name for t in mcp._tool_manager.list_tools())
    assert names == ["ask_docs", "get_document", "list_sources", "search_docs"]


def test_tools_have_descriptions():
    # Descriptions drive when Copilot decides to call a tool — they must be present.
    for tool in mcp._tool_manager.list_tools():
        assert (tool.description or "").strip(), f"{tool.name} is missing a description"


def test_format_citations_renders_grounded_evidence():
    out = _format_citations(
        [
            {
                "doc_id": "garnet/build.md",
                "line_range": [8, 12],
                "commit_sha": "abc123def456",
                "relevance": 0.81,
                "text": "Run dotnet build -c Release",
            }
        ]
    )
    assert "[1] garnet/build.md" in out
    assert "lines 8-12" in out
    assert "commit abc123d" in out  # 7-char short SHA
    assert "81%" in out
    assert "Run dotnet build -c Release" in out


def test_format_citations_handles_empty():
    assert "no supporting sources" in _format_citations([])


def test_unreachable_message_is_actionable():
    msg = _unreachable(ConnectionError("refused"))
    assert "Could not reach the DocGuardian API" in msg
    assert "uvicorn app.main:app" in msg
