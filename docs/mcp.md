# DocGuardian MCP Server

Expose DocGuardian's documentation corpus **and its evidence-backed Curator agent**
to MCP clients — most notably the **GitHub Copilot CLI** — so another coding agent can
ask your team's wiki/docs a question and get a grounded, cited answer instead of guessing.

> Demo one-liner: *"Copilot CLI doesn't know how to build Garnet — so it asks DocGuardian
> over MCP, and gets back the exact steps with the source docs, line ranges, and commit
> SHAs it relied on."*

## What it exposes

The server (`backend/app/mcp_server.py`, built on the official `mcp` Python SDK /
`FastMCP`, stdio transport) is a thin adapter over the running DocGuardian REST API, so
MCP clients get the **same** answers the app does — "evidence or silence".

| Tool | What it does | Backed by |
| --- | --- | --- |
| `ask_docs(question, repo?)` | Curator agent: a grounded answer **with citations** (doc, line range, commit SHA) + confidence; flags "needs human review" when evidence is weak. | `POST /chat` |
| `search_docs(query, repo?, k?)` | Raw semantic search — the most relevant chunks with source, heading, lines, commit, score. | `GET /search` |
| `get_document(doc_id)` | The AI-curated text of one document + provenance. | `GET /documents/{id}` |
| `list_sources(namespace?)` | The documentation library (every indexed file + one-line summary). | `GET /tree` |

## Prerequisites

1. The DocGuardian backend must be **running** (the MCP server proxies to it):
   ```powershell
   cd backend
   uvicorn app.main:app --port 8000      # needs Postgres+pgvector; agents use Azure or CHAT_PROVIDER=fake
   ```
2. The `mcp` SDK is installed (already in `requirements.txt`): `pip install -r requirements.txt`.

## Configure GitHub Copilot CLI

Copilot CLI reads MCP servers from **`~/.copilot/mcp-config.json`** (override the dir with
`COPILOT_HOME`). Two ways to register DocGuardian:

**A. Interactive** — in a `copilot` session run `/mcp add`, then fill in:
- Name: `docguardian`
- Type: `local` (stdio)
- Command: the venv Python, e.g. `C:\workspace\Intern-Hackathon-DocGuardian\backend\.venv\Scripts\python.exe`
- Args: `C:\workspace\Intern-Hackathon-DocGuardian\backend\app\mcp_server.py`
- Env: `DOCGUARDIAN_API_URL=http://localhost:8000`

Press <kbd>Ctrl</kbd>+<kbd>S</kbd> to save.

**B. File** — copy `backend/mcp-config.example.json` into `~/.copilot/mcp-config.json`
(adjust the absolute paths to your checkout). The JSON shape:

```json
{
  "mcpServers": {
    "docguardian": {
      "type": "local",
      "command": "<abs path>\\backend\\.venv\\Scripts\\python.exe",
      "args": ["<abs path>\\backend\\app\\mcp_server.py"],
      "env": { "DOCGUARDIAN_API_URL": "http://localhost:8000" },
      "tools": ["*"]
    }
  }
}
```

Verify it loaded with `/mcp` (or `/env`) inside Copilot CLI — you should see `docguardian`
with its four tools.

> The `args` use the **file path** to `mcp_server.py` (not `-m app.mcp_server`) so the
> server starts correctly regardless of the spawned process's working directory. The
> module only imports `httpx` + `mcp`, so it does not need the `app` package on `sys.path`.

## Demo script

With the backend running and DocGuardian registered, start `copilot` and ask something the
model can't know from the code alone, e.g.:

```
How do I build Garnet from source? Use the docguardian tools to check our docs.
```

Copilot will call `ask_docs`, and you'll see DocGuardian return the step-by-step answer
(clone → install .NET 10 SDK → `dotnet build -c Release`) **with the source doc, lines, and
commit SHA**. Follow-ups that show it off:
- *"Search our docs for cluster configuration"* → `search_docs`
- *"List what documentation we have under the `user` namespace"* → `list_sources`
- *"Show me the full doc at `garnet/website/docs/getting-started/build.md`"* → `get_document`

## Smoke test (no Copilot needed)

`backend/scripts/mcp_smoke.py` spawns the server over stdio exactly like a client would,
lists the tools, and calls each against the running API:

```powershell
cd backend
.venv\Scripts\python.exe scripts\mcp_smoke.py
```

## Other MCP clients

The same server works with any MCP client (it's standard stdio MCP):
- **VS Code** (`.vscode/mcp.json` or user settings) — a `servers` entry with the same
  `command`/`args`/`env`.
- **Claude Desktop** (`claude_desktop_config.json`) — an `mcpServers` entry with the same
  `command`/`args`/`env`.

## Configuration

| Env var | Default | Purpose |
| --- | --- | --- |
| `DOCGUARDIAN_API_URL` | `http://localhost:8000` | Where the DocGuardian REST API is running. |
| `DOCGUARDIAN_MCP_TIMEOUT` | `90` | HTTP timeout (seconds) for proxied calls (agent calls can be slow). |
| `DOCGUARDIAN_MCP_TRANSPORT` | `stdio` | MCP transport (`stdio` for Copilot CLI; `sse`/`streamable-http` possible). |

## Troubleshooting

- **"Could not reach the DocGuardian API"** — start the backend (`uvicorn app.main:app --port 8000`)
  or point `DOCGUARDIAN_API_URL` at the right host/port.
- **`ask_docs` says the agent is unavailable (503-style message)** — the chat model isn't
  configured on the server; set `AZURE_OPENAI_*` or run the backend with `CHAT_PROVIDER=fake`.
- **Copilot CLI doesn't list the server** — confirm `~/.copilot/mcp-config.json` is valid JSON
  and the `command` path points at the venv Python that has `mcp`+`httpx` installed.
