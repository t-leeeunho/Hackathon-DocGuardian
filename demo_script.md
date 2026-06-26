# DocGuardian AI — 4-Person Live Demo Script

> The stage-ready companion to [`demo_plan.md`](demo_plan.md). Same hero story (Maya
> builds Garnet; `.NET 8` vs a stale `.NET 6` doc), same ~5 minutes — but here the
> ~5 minutes is **split across four presenters, each narrating the slice they built.**
>
> **Format per beat:** **Speaker** · **Driver** (who's on the keyboard) · **Say**
> (verbatim) · **Do** (on-screen) · **Hand off** (the literal baton-pass line) · **Proves**.
>
> Primary run path = **Presenter Mode** (offline auto-pilot — it does the clicking; the
> presenter just advances beats). See [How to run it](#how-to-run-it-two-paths) at the end.

---

## Cast — who presents what, and why it's *their* part

Fill in real names. Each person owns the beats that map 1:1 to the layer they built
(see `docs/team-plan.md` §1). That's the secret to a credible demo: nobody is reading
someone else's work off a card.

| | Person / role | Built (their lane) | Their demo beats | Anchor word |
| --- | --- | --- | --- | --- |
| **P1** | **Frontend & Demo** — _____ | The whole UI: graph, chat, diff, panels | **0 Hook**, **2 Map** (frame), close bookend | *experience* |
| **P2** | **Retrieval & Detection** — _____ | Ingestion, embeddings, duplicate/conflict/health detection | **2 Map** (the detections), **3a Conflict** | *detect* |
| **P3** | **AI Orchestration** — _____ | Curator + Guardian agents, evidence/confidence, RAG, MCP | **1 Answer**, **3b Propose**, **6 Copilot/MCP** | *evidence* |
| **P4** | **Governance & Metrics** — _____ | ACL, approval, provenance, rollback, metrics, sandbox | **4 Approve**, **5 Scoreboard** | *govern* |

**P1 is the Host + default Driver** (holds the clicker, keeps the click-path muscle-memory
clean) and hands the keyboard to **P4 for Beat 4–5** and to **P3 for the Beat 6 terminal**.

---

## The handoff map (one screen — memorize this)

| Beat | Time | Speaker | Driver | Baton passes to |
| --- | --- | --- | --- | --- |
| **0 Hook** | 0:00–0:30 | **P1** | P1 | → P3 |
| **1 Answer** (evidence) | 0:30–1:15 | **P3** | P1 | → P1 |
| **2 Map** (fresh vs stale) | 1:15–2:00 | **P1** then **P2** | P1 | → P2 |
| **3 Conflict + Propose** ★ | 2:00–3:00 | **P2** then **P3** | P1 | → P4 |
| **4 Approve + Provenance** | 3:00–3:50 | **P4** | **P4** | (stays P4) |
| **5 Scoreboard moves** | 3:50–4:20 | **P4** | P4 | → P3 |
| **6 Copilot / MCP finale** | 4:20–5:00 | **P3** then **P1** (close) | **P3** | — |
| **Total** | **~5:00** | all four | | |

★ Beat 3 is the money moment: **P2 detects** the conflict → **P3 proposes** the fix.
That's literally the product pipeline, told by the two people who built each half.

---

## Pre-flight — per person (run 30 min before)

Each person verifies **their own** slice so no one waits on anyone else.

- **P1 (Driver):** Presenter Mode runs clean end-to-end on the demo machine; browser
  zoom + font up for the projector; clicker/keyboard works; **fallback recording open in a
  background tab**. Knows the transport: **Space** play/pause, **←/→** prev/next, **R**
  restart, **C** captions, **Esc** exit.
- **P2:** the red node `build-legacy.md` shows quality **0.34**, **2 broken links**,
  orphan; the `conflicts-with` edge (**0.88**) and the `install.md ⟷ install-old.md`
  `duplicate-of` (**0.94**) are present; the locked node renders gray.
- **P3:** hero `/chat` answer is the deterministic one (`dotnet build -c Release`, **.NET 8**,
  **0.82**); `/propose` returns the **needs-human-review** proposal (0.79); **MCP server
  registered and answering** in the Copilot CLI (`docs/mcp.md`), terminal pre-opened and
  font enlarged.
- **P4:** approve → toast → Provenance entry appears; metrics tick (conflicts ↑1, stale ↓1,
  dupes ↓1, broken links ↓2); Rollback button visible.

**Golden rule (all):** if anything flakes live, **narrate over the recording — never debug on stage.**

---

## The script

### Beat 0 — Hook · `experience` · 0:00–0:30
- **Speaker:** **P1** · **Driver:** P1
- **Say (P1):** *"Raise your hand if your team's docs are 100% up to date. Right — nobody.
  A new hire's first week is a scavenger hunt through stale, contradictory docs. **Copilot
  answers from those docs. Obsidian stores them. DocGuardian governs them.** I'm [name], and
  with me are [P2], [P3], and [P4] — we each built a layer of this, and we'll each show you ours."*
- **Do:** Title screen → the DocGuardian knowledge graph already loaded. (If using Presenter
  Mode, press **Space** to begin.)
- **Hand off (P1 → P3):** *"It starts the moment Maya, our new hire, asks her first question.
  [P3] built the part that answers her — [P3], take it."*
- **Proves:** Framing + differentiation, up front.

### Beat 1 — Ask, get evidence not a guess · `evidence` · 0:30–1:15
- **Speaker:** **P3** · **Driver:** P1
- **Say (P3):** *"Maya asks: how do I build Garnet from source? Watch — DocGuardian answers
  with its **sources** and a **confidence score**. And if it can't ground an answer, it says
  'needs human review' instead of bluffing. We call that **evidence-or-silence** — and it's
  the same agent everywhere, including inside Copilot, which I'll show you at the end."*
- **Do (P1 drives):** Type in chat → **"How do I build Garnet from source?"** → answer renders
  (`dotnet build -c Release`, **.NET 8**) with **citation chips** (`build.md` + `README.md`,
  with commit SHAs) and a **0.82 confidence** badge. Click a chip → it **highlights the source
  node** in the graph ("show your work").
- **Hand off (P3 → P1):** *"But how did it know `build.md` was the one to trust? Because the
  whole library is a living, scored map — [P1] built it. [P1]?"*
- **Proves:** Productivity, Learning, Trust.

### Beat 2 — The knowledge map: fresh vs stale · `detect` · 1:15–2:00
*Two voices: P1 frames the map; P2 explains the detections P2's pipeline produced.*
- **Speakers:** **P1** (frame) → **P2** (detections) · **Driver:** P1
- **Say (P1):** *"This is the whole team's knowledge as one living map. **Green is fresh, red
  is stale, gray-locked means you don't have access.** No human drew these links — we derived
  them from the docs and the commits. A new hire sees the shape of the system on day one."*
- **Do (P1):** Pan the graph; hover the **red** node **`build-legacy.md`** (tooltip: stale
  .NET 6 guide, old commit). Point out a **gray locked** node (`install-old.md`) and the
  **`duplicate-of`** pair (`install.md ⟷ install-old.md`).
- **Say (P2):** *"And the red isn't a guess from a calendar. My pipeline scores every doc:
  this one is **quality 0.34**, with **two broken links**, it's an **orphan**, and high
  staleness risk — open the Insights drawer and it's all right there. That locked node? It's
  **permission-aware** — content the user can't see never reaches the screen."*
- **Do (P2/P1):** Open the **Insights drawer** on `build-legacy.md` → low quality, broken
  links, orphan, staleness risk.
- **Hand off (P2):** *"Now here's the trap I detected — and it's the reason this demo exists."*
- **Proves:** Onboarding, Observability, Trust (permissions).

### Beat 3 — The conflict + the contrast vs RAG · `★ differentiation` · 2:00–3:00
*The money moment — P2 detects, P3 proposes. The pipeline, narrated by its two builders.*
- **Speakers:** **P2** (conflict) → **P3** (propose) · **Driver:** P1
- **Say (P2):** *"Two docs describe building Garnet — but one targets **.NET 8** and the stale
  one still says **.NET 6**. A normal copilot blends them and sounds confident, and Maya loses
  her afternoon. My detector flags the contradiction as a **first-class problem** — see the
  `conflicts-with` edge, weight **0.88**."*
- **Do (P1 drives):** Click the **`conflicts-with` edge** between `build.md` and
  `build-legacy.md` → side panel shows both snippets, divergent SDK versions highlighted.
- **Say (P2 → contrast):** *"This is the whole difference. RAG patches the **answer**; we fix
  the **source**. [P3]'s agents do the fixing — [P3]?"*
- **Say (P3):** *"One click. The **Curator** drafts a single canonical 'Building Garnet' doc —
  merges into `build.md`, supersedes the legacy page. Then the **Guardian** reviews it and
  attaches **evidence** — the .NET 6 quote and its commit — plus a **0.79 confidence** and a
  recommendation. And notice: because `build-legacy.md` still has **inbound links**, it does
  **not** auto-approve — it routes to **human review**. Two LLM calls, never more. The
  evidence is pulled from retrieved chunks, never invented."*
- **Do (P1 drives):** Click **"Propose fix"** → proposal renders with evidence + 0.79 +
  **needs-human-review**.
- **Hand off (P3 → P4):** *"Nothing changes without a human. The owner, Sam — that's [P4]'s
  layer — decides. [P4]?"*
- **Proves:** Data quality, Decision-making — differentiation, live.

### Beat 4 — Human in the loop: approve, audit + rollback · `govern` · 3:00–3:50
- **Speaker:** **P4** · **Driver:** **P4** (takes the keyboard)
- **Say (P4):** *"I built the governance layer, so this is the part I care about most. Sam
  reviews a **before/after diff** with the evidence right beside it, and approves. The instant
  he does, we write an **immutable provenance record**: what changed, who approved it, **which
  agent** proposed it, why, the sources, and the **previous version**. And it's **reversible** —
  one click rolls the whole thing back."*
- **Do (P4 drives):** Open the **diff (Monaco)** → click **Approve** → toast confirms → open
  the **Provenance panel** showing the new audit entry → hover **Rollback** to show it exists.
- **Hand off (P4):** *"And the moment I approve, the scoreboard I built moves — live."*
- **Proves:** Collaboration, Trust, Governance.

### Beat 5 — The dashboard moves · `impact` · 3:50–4:20
- **Speaker:** **P4** · **Driver:** P4
- **Say (P4):** *"Over the WebSocket, with no refresh: **one conflict resolved, one stale doc
  on the mend, duplicates down, broken links fixed, quality up.** The Insights trend charts the
  same over time, and PageRank centrality ranks the most-relied-on docs. This is knowledge
  health a leader can actually **manage** — not vibes."*
- **Do (P4):** Show the **metrics strip + Insights trends** updating (conflicts ↑1, stale ↓1,
  dupes ↓1, broken links ↓2, quality ↑).
- **Hand off (P4 → P3):** *"And the best part — this verified knowledge doesn't live in our app.
  [P3], show them where it goes."*
- **Proves:** Observability, Decision-making, measurable impact.

### Beat 6 — The Microsoft tie-in finale · `Microsoft` · 4:20–5:00
- **Speakers:** **P3** (MCP) → **P1** (close) · **Driver:** **P3** (takes the keyboard / terminal)
- **Say (P3):** *"This isn't a walled garden. The same evidence-backed agent is exposed over
  an **MCP server**, so it answers right where engineers already work — the **Copilot CLI**.
  Same question, governed answer, not a guess."*
- **Do (P3 drives):** Switch to the pre-opened terminal → in a `copilot` session ask
  **"How do I build Garnet from source?"** → Copilot calls DocGuardian's `ask_docs` tool → the
  **same canonical, sourced** answer (doc + line range + commit SHA) comes back.
- **Hand off (P3 → P1):** *"[P1], bring it home."*
- **Say (P1 — close):** *"Copilot answers. Obsidian stores. **DocGuardian governs** — and makes
  every Copilot answer trustworthy. That's how teams onboard faster and decide with confidence.
  We're [P1], [P2], [P3], [P4]. Questions?"*
- **Proves:** Enhance MS tools — the bonus the challenge explicitly asks for.

---

## Q&A — who fields what

The Narrator who built that layer answers; **P1 redirects to the recording** if anything's
flaky. (Full rehearsed answers live in `demo_plan.md` §9.)

| Question | Lead | Backup |
| --- | --- | --- |
| "Isn't this just Copilot / RAG?" | **P3** | P1 |
| "Isn't this Confluence / Notion with AI?" | **P2** | P3 |
| "How do you stop the AI hallucinating a bad edit?" | **P3** | P4 |
| "How do you know a doc is stale / conflicting?" | **P2** | — |
| "Permissions / who can see what?" | **P4** | P2 |
| "Audit & rollback — is it real?" | **P4** | — |
| "Does it scale beyond eng docs?" | **P2** | P1 |
| "What's built vs mocked?" | **P3 / P4** | — |
| "Business impact?" | **P1** | P4 |

---

## How to run it — two paths

**Path A — Presenter Mode (PRIMARY, offline, can't flake on Wi-Fi).**
Click **"Run guided demo"** in the header. The auto-pilot drives the *real* handlers over
offline fixtures — no Azure, no DB, no network — with teleprompter captions. The presenter
**just advances beats**; the app does the clicking. Pass the clicker at the handoff points
(P1 → P4 before Beat 4 → P3 before Beat 6). Transport: **Space** play/pause · **←/→** prev/next
· **R** restart · **C** captions · **Esc** exit. **Beat 6 (Copilot/MCP) is manual** — exit
Presenter Mode (**Esc**) and switch to P3's terminal.

**Path B — Live backend (deterministic, offline).** Only if rehearsed solid.
```powershell
# Backend
cd backend
docker compose up -d                       # Postgres + pgvector — auto-seeds a demo corpus
$env:CHAT_PROVIDER = "fake"                 # deterministic agents, no Azure/network
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000   # API + Swagger at /docs
# Frontend
cd ../frontend
npm install
npm run build && npm run preview            # or: npm run dev (http://localhost:5173)
```
> **Live-seed caveat:** the auto-seed currently plants a *security-policy vs zero-trust*
> conflict + a *deployment* duplicate — **not** the Garnet build story. Drive the hero
> scenario through **Presenter Mode** (its fixtures already match this script), or re-seed
> the DB to the Garnet story. For Beat 6, the MCP server must be registered (`docs/mcp.md`).

---

## One-line rehearsal checklist (per person)

- **P1:** Beat 0 + Beat 2 frame + the close. Drive beats 0–3. Recording one tab away.
- **P2:** Beat 2 detections + Beat 3a conflict. Know your numbers: 0.34 / 2 links / 0.88 / 0.94.
- **P3:** Beat 1 answer + Beat 3b propose + Beat 6 MCP. Drive the terminal. Numbers: 0.82 / 0.79.
- **P4:** Beat 4 approve/provenance/rollback + Beat 5 metrics. Drive beats 4–5. Delta: +1/−1/−1/−2.

**Rehearse the handoffs more than the lines.** A clean baton pass is what makes four people
look like one product.
