# README image assets

Drop the images referenced by the root [`README.md`](../../README.md) here, using the **exact
filenames** below. PNG for stills, GIF for the walkthrough. Recommended width ~900px (banner ~1280px)
so they look crisp without bloating the repo.

Brand palette: **purple `#7E14FF` / `#863BFF`** with a **cyan `#47BFFF`** accent (matches
`frontend/public/favicon.svg`). Capture the app at `http://localhost:5173`.

| # | Filename | Where it appears | What to capture |
| --- | --- | --- | --- |
| 1 | `banner.png` | Top hero | Wide banner (~1280×320): lightning-shield logo + "DocGuardian AI" wordmark + tagline on the purple→black gradient. Design tool or app title screen. |
| 2 | `hero-screenshot.png` | Under the title | The "money shot": full 3-pane UI — file tree, center knowledge graph (green/amber/red nodes + one 🔒 locked), chat panel, metrics strip. |
| 3 | `demo.gif` | See It in Action | Animated 5-min hero flow (or one-click **Presenter Mode**): ask → evidence → graph → conflict → propose → approve → provenance → metrics → Copilot. Keep < 10 MB. |
| 4 | `chat-evidence.png` | Key Features | A chat answer with **citation chips** (commit SHAs) + a **confidence badge**. |
| 5 | `graph-health.png` | Key Features | The React Flow graph showing health colors (green/amber/red), node sizes (importance), and a 🔒 locked node. |
| 6 | `conflict-panel.png` | Key Features | The conflict side panel: `build.md` vs `build-legacy.md` with the **.NET 8 vs .NET 6** divergence highlighted. |
| 7 | `diff-approve.png` | Key Features | The Monaco before/after **diff** + the **Approve** button (Proposal panel). |
| 8 | `provenance.png` | Key Features | The **Provenance** panel: an audit entry (what/who/agent/why/sources) + the **Rollback** action. |
| 9 | `insights-trends.png` | Key Features | The **Insights** drawer (quality, broken links, PageRank) + the **Trends** charts. |
| 10 | `mcp-copilot.png` | Use It From Copilot | A terminal: **Copilot CLI** answering the same Garnet question via the DocGuardian **MCP server**. |
| 11 | `architecture.png` | How It Works | A polished 5-layer architecture diagram (redraw the ASCII diagram in README §8A.1). |
| 12 | `agent-loop.png` | How It Works | The governed loop: retrieve (no LLM) → Curator → Guardian → proposal (evidence + confidence) → human approve → provenance → rollback. Note "≤2 LLM calls". |

**Highly recommended first:** `banner.png`, `hero-screenshot.png`, `demo.gif`. The rest enhance the
feature/architecture sections. Until a file is added, GitHub shows the image's alt text — nothing
breaks.
