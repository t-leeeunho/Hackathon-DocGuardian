"""Smoke test for the DocGuardian MCP server.

Spawns ``app.mcp_server`` over stdio exactly like an MCP client (e.g. Copilot CLI)
would, lists the tools, and calls each one against the running DocGuardian API.

Usage (from backend/, with the API running on :8000):
    .venv\\Scripts\\python.exe scripts\\mcp_smoke.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

BACKEND_DIR = Path(__file__).resolve().parent.parent
API_URL = os.getenv("DOCGUARDIAN_API_URL", "http://localhost:8000")


def _text(result) -> str:
    parts = [getattr(b, "text", "") for b in result.content]
    return "\n".join(p for p in parts if p)


async def main() -> int:
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "app.mcp_server"],
        cwd=str(BACKEND_DIR),
        env={**os.environ, "DOCGUARDIAN_API_URL": API_URL},
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = (await session.list_tools()).tools
            print("=== TOOLS ===")
            for t in tools:
                print(f"  • {t.name}: {(t.description or '').splitlines()[0]}")

            print("\n=== list_sources(namespace='user') ===")
            print(_text(await session.call_tool("list_sources", {"namespace": "user"}))[:400])

            print("\n=== search_docs('build garnet from source', k=2) ===")
            print(_text(await session.call_tool("search_docs", {"query": "build garnet from source", "k": 2}))[:600])

            print("\n=== ask_docs('How do I build Garnet from source?') ===")
            print(_text(await session.call_tool("ask_docs", {"question": "How do I build Garnet from source?"}))[:900])

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
